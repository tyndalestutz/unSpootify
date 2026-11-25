"""Experimental: turn the lossless songs a run downloaded (FLAC/WAV/AIFF) into MP3.

Runs after the downloader is done, inside the run. Uses libsndfile (bundled with the `soundfile`
package, which includes the LAME encoder) so nothing has to be installed on the user's computer.

Per song: encode VBR V0 to a hidden ".part" file in the album's "[MP3]" folder, copy the tags and
cover, check the result plays for as long as the original, move it into place, update every playlist
row that pointed at the old file, and only then delete the original. Folders are never renamed:
songs move into the "Album [MP3]" folder next to the old one, and the old folder is removed once it
has no music left. Hi-res (>48 kHz), multichannel, and formats libsndfile can't read (ALAC, APE…)
are left alone. Lossy formats (AAC, Ogg, Opus) are never re-encoded.
"""

from __future__ import annotations

import os
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

LOSSLESS = {"flac", "wav", "aif", "aiff"}
SIDE_EXTS = {"jpg", "jpeg", "png", "webp", "lrc"}
_EXT_TAG = re.compile(r"\s\[(FLAC|WAV|AIFF|AIF)\]$", re.I)
MAX_RATE = 48000
DURATION_SLACK = 1.5  # seconds


class Stopped(Exception):
    pass


@dataclass
class Result:
    converted: list[tuple[Path, Path]] = field(default_factory=list)  # (old, new)
    folders: list[tuple[Path, Path]] = field(default_factory=list)  # (old album folder, new album folder)
    skipped: list[tuple[Path, str]] = field(default_factory=list)  # (file, why)
    failed: list[tuple[Path, str]] = field(default_factory=list)
    stopped_early: str | None = None  # e.g. "disk is nearly full"


def should_convert(*, enabled: bool, mode: str, preferred: str, formats: list[str]) -> bool:
    """Automatic mode only. MP3 chosen as the format -> always; FLAC chosen -> only when at least
    3 of every 4 songs downloaded in this run came as MP3 anyway."""
    if not enabled or mode != "auto":
        return False
    if preferred == "mp3":
        return True
    got = [f.lower() for f in formats if f]
    return bool(got) and sum(f == "mp3" for f in got) / len(got) >= 0.75


def mp3_folder(folder: Path) -> Path:
    """'Album [FLAC]' -> 'Album [MP3]'; any other folder stays the same."""
    return folder.with_name(_EXT_TAG.sub(" [MP3]", folder.name)) if _EXT_TAG.search(folder.name) else folder


def lossless_files(paths: list[Path]) -> list[Path]:
    """Expand playlist row paths (a song file, an album folder or an artist folder) to lossless files."""
    out: dict[str, Path] = {}

    def add_folder(d: Path) -> None:
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower().lstrip(".") in LOSSLESS and not f.name.startswith("."):
                out[str(f)] = f

    for p in paths:
        if p.is_file() and p.suffix.lower().lstrip(".") in LOSSLESS:
            out[str(p)] = p
        elif p.is_dir():
            if _EXT_TAG.search(p.name):
                add_folder(p)
            else:  # artist folder: only its lossless "[FLAC]" style album folders
                for d in sorted(p.iterdir()):
                    if d.is_dir() and _EXT_TAG.search(d.name):
                        add_folder(d)
    return list(out.values())


def _copy_tags(src: Path, dst: Path) -> None:
    from mutagen import File as MutagenFile
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import APIC, ID3, USLT, ID3NoHeaderError

    source = MutagenFile(src)
    easy = MutagenFile(src, easy=True)
    try:
        out = EasyID3(dst)
    except ID3NoHeaderError:
        out = EasyID3()
    if easy is not None and easy.tags:
        for key, values in easy.tags.items():
            k = key.lower()
            if k in EasyID3.valid_keys and values:
                try:
                    out[k] = [str(v) for v in values]
                except Exception:  # odd values: skip that tag, keep the rest
                    pass
    out.save(dst, v2_version=3)
    id3 = ID3(dst)
    pictures = list(getattr(source, "pictures", []) or [])
    if pictures:
        pic = next((p for p in pictures if p.type == 3), pictures[0])
        id3.add(APIC(encoding=3, mime=pic.mime or "image/jpeg", type=3, desc="Cover", data=pic.data))
    else:
        cover = next((c for c in (src.parent / "cover.jpg", src.parent / "cover.png") if c.exists()), None)
        if cover and cover.stat().st_size < 5 * 2**20:
            mime = "image/png" if cover.suffix == ".png" else "image/jpeg"
            id3.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover.read_bytes()))
    lyrics = source.tags.get("lyrics") or source.tags.get("unsyncedlyrics") if source and source.tags else None
    if lyrics:
        id3.add(USLT(encoding=3, lang="eng", desc="", text=str(lyrics[0])))
    id3.save(dst, v2_version=3)


def convert_file(src: Path, cancel: threading.Event) -> tuple[Path | None, str | None]:
    """Returns (new file, None) on success, (None, reason-to-skip) when left alone. Raises on failure."""
    import soundfile as sf
    from mutagen.mp3 import MP3

    try:
        info = sf.info(str(src))
    except Exception:
        return None, "can't be read"
    if info.samplerate > MAX_RATE:
        return None, f"hi-res ({info.samplerate // 1000} kHz)"
    if info.channels > 2:
        return None, "more than two channels"
    dest_dir = mp3_folder(src.parent)
    target = dest_dir / f"{src.stem}.mp3"
    if target.exists():  # already have this song as MP3: keep that one
        src.unlink()
        return target, None
    dest_dir.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(dest_dir).free < src.stat().st_size + 200 * 2**20:
        raise OSError(28, "disk is nearly full")
    part = dest_dir / f".{src.stem}.mp3.part"
    try:
        with sf.SoundFile(str(src)) as inp, sf.SoundFile(
            str(part), "w", inp.samplerate, inp.channels, format="MP3", subtype="MPEG_LAYER_III",
            compression_level=0.0, bitrate_mode="VARIABLE",
        ) as out:
            for block in inp.blocks(blocksize=1 << 16, dtype="float32"):
                if cancel.is_set():
                    raise Stopped
                out.write(block)
        _copy_tags(src, part)
        length = MP3(part).info.length
        if abs(length - info.duration) > DURATION_SLACK:
            raise ValueError(f"MP3 is {length:.0f}s, original {info.duration:.0f}s")
        os.replace(part, target)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    src.unlink()
    return target, None


def _tidy_old_folder(old: Path, new: Path) -> None:
    """Move cover/lyrics across (never overwriting), then drop the old folder if no music is left."""
    if old == new or not old.is_dir():
        return
    for f in list(old.iterdir()):
        if f.is_file() and f.suffix.lower().lstrip(".") in SIDE_EXTS and not (new / f.name).exists():
            shutil.move(str(f), str(new / f.name))
    if any(f.suffix.lower().lstrip(".") in LOSSLESS | {"mp3", "m4a", "ogg", "opus", "wma", "ape", "wv", "alac"}
           for f in old.iterdir()):
        return
    for f in old.iterdir():
        if f.is_file():
            f.unlink()
    try:
        old.rmdir()
    except OSError:
        pass


def convert_all(files: list[Path], cancel: threading.Event, progress: Callable[[int, int], None],
                workers: int | None = None) -> Result:
    res = Result()
    total, done = len(files), 0
    lock = threading.Lock()
    halt = threading.Event()
    progress(0, total)
    for folder in {f.parent for f in files}:  # leftovers from an interrupted earlier pass
        for stale in mp3_folder(folder).glob(".*.mp3.part") if mp3_folder(folder).is_dir() else []:
            stale.unlink(missing_ok=True)

    def one(src: Path) -> None:
        nonlocal done
        if cancel.is_set() or halt.is_set():
            return
        try:
            new, why = convert_file(src, cancel)
            with lock:
                if new:
                    res.converted.append((src, new))
                else:
                    res.skipped.append((src, why or "skipped"))
        except Stopped:
            return
        except OSError as exc:
            with lock:
                res.failed.append((src, exc.strerror or str(exc)))
                if exc.errno == 28:
                    res.stopped_early = "the disk is nearly full"
                    halt.set()
        except Exception as exc:  # noqa: BLE001  one bad file never stops the rest
            with lock:
                res.failed.append((src, f"{type(exc).__name__}: {exc}"))
        with lock:
            done += 1
            progress(done, total)

    n = workers or max(1, (os.cpu_count() or 2) - 1)
    with ThreadPoolExecutor(max_workers=n, thread_name_prefix="mp3") as pool:
        list(pool.map(one, files))
    for old in sorted({o.parent for o, _ in res.converted}):
        new = mp3_folder(old)
        try:
            _tidy_old_folder(old, new)
        except OSError:
            pass
        res.folders.append((old, new))
    return res

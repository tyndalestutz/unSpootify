"""Called by sockseek after each successful file: move it into the library with the house naming.

Prints `success;<new path>` so sockseek's index (used for skip-existing) points at the final file.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from unspootify.naming import final_path, unique

_NUM_PREFIX = re.compile(r"^\s*(?:(?:disc|cd)\s*\d+\s*[-.]?\s*)?(\d{1,3})\s*[-._)\]]?\s*")


AUDIO_EXTS = {"mp3", "flac", "m4a", "aac", "ogg", "oga", "opus", "wav", "aif", "aiff", "alac", "wma", "ape", "wv", "dsf"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
JUNK_EXTS = {"nfo", "yml", "yaml", "log", "m3u", "m3u8", "txt", "url", "db", "ini", "cue", "sfv", "md5",
             "accurip", "pls", "html", "htm", "pdf", "sh", "exe", "lnk"}
_SEP = r"\s*[-._]\s*|\s+"


def _strip_prefix(stem: str, name: str) -> str:
    """Drop a leading 'Artist - ' / 'Album_' style prefix (case-insensitive)."""
    if name:
        m = re.match(rf"\s*{re.escape(name)}(?:{_SEP})", stem, re.I)
        if m:
            return stem[m.end():]
    return stem


def parse_filename(stem: str, artist: str, album: str = "") -> tuple[int | None, str]:
    """Best-effort (track number, title) from the many ways sharers name files:
    '03 - Artist - Song', 'Album - 03 - Song', 'Artist_Album_03_Song', '1-03 Song', '03. Song'."""
    rest = stem
    for _ in range(2):  # 'Artist - Album - 03 - Song'
        rest = _strip_prefix(_strip_prefix(rest, artist), album)
    number = None
    m = re.match(r"\s*(?:(?:disc|cd)\s*\d+\s*[-._]?\s*)?(?:\d{1,2}\s*[-.]\s*(?=\d))?(\d{1,3})(?:\s*[-._)\]]\s*|\s+)", rest, re.I)
    if m:
        number, rest = int(m.group(1)), rest[m.end():]
    for _ in range(2):  # '03 - Artist - Song'
        rest = _strip_prefix(_strip_prefix(rest, artist), album)
    return number, rest.strip(" -._") or "Untitled"


def read_tags(path: Path) -> tuple[int | None, str | None]:
    """(track number, title) from the file's own tags, which beat any filename guess."""
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(path, easy=True)
    except Exception:
        return None, None
    if not audio or not audio.tags:
        return None, None

    def first(key: str) -> str | None:
        values = audio.tags.get(key)
        return str(values[0]).strip() if values else None

    title = first("title")
    number = None
    raw = first("tracknumber")
    if raw:
        m = re.match(r"\s*(\d+)", raw)
        number = int(m.group(1)) if m else None
    return number, title or None


def album_from_folder(folder: str, artist: str) -> str:
    """'The Killers - Hot Fuss (2004) [FLAC]' -> 'Hot Fuss'"""
    name = folder
    if artist and name.lower().startswith(artist.lower() + " - "):
        name = name[len(artist) + 3:]
    name = re.sub(r"\s*[\[(][^\])]*[\])]\s*$", "", name)  # trailing [FLAC] / (2004)
    name = re.sub(r"\s*[\[(][^\])]*[\])]\s*$", "", name)
    return name.strip() or folder


def _key(s: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", s.lower())


def find_job(manifest: dict, snum: int, staged: Path) -> dict:
    """Songs: by input line. Albums/artists: by the source artist/album folders sockseek staged it under."""
    if manifest["mode"] == "songs":
        return manifest["jobs"][snum - 1]
    try:
        parts = staged.resolve().relative_to(Path(manifest["stage"]).resolve()).parts
    except ValueError:
        parts = staged.parts[-4:]
    artist = _key(parts[0]) if parts else ""
    album = _key(parts[1]) if len(parts) > 1 else ""
    jobs = [j for j in manifest["jobs"] if _key(j["artist"]) == artist]
    if manifest["mode"] == "albums":
        jobs = [j for j in jobs if _key(j["album"]) == album] or jobs
    if not jobs:
        raise LookupError(f"no job for {staged}")
    return jobs[0]


def destination(manifest: dict, snum: int, staged: Path) -> Path:
    job = find_job(manifest, snum, staged)
    library = Path(manifest["library"])
    ext = staged.suffix
    if manifest["mode"] == "songs":
        return final_path(library, artist=job["artist"], album=job["album"], title=job["title"],
                          number=job["number"], ext=ext)
    album = job["album"] if manifest["mode"] == "albums" else album_from_folder(staged.parent.name, job["artist"])
    number, title = parse_filename(staged.stem, job["artist"], album)
    tag_number, tag_title = read_tags(staged)
    number, title = tag_number or number, tag_title or title
    return final_path(library, artist=job["artist"], album=album, title=title, number=number, ext=ext)


def main(argv: list[str]) -> int:
    """Never fails: a non-zero exit makes sockseek treat the whole album as failed and remove the
    files it already got. Anything we can't place is left alone ('ignored')."""
    try:
        return _main(argv)
    except Exception as exc:  # noqa: BLE001
        print(f"unspootify finalize: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"ignored;{argv[2] if len(argv) > 2 else ''}")
        return 0


def _main(argv: list[str]) -> int:
    manifest_path, snum, staged = Path(argv[0]), int(argv[1]), Path(argv[2])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if staged.suffix.lower().lstrip(".") not in AUDIO_EXTS:
        # cover art, lyrics, .nfo: sockseek moves these next to the album's music itself (it fails the
        # album if we touch them); the runner tidies the album folder afterwards (tidy_album_folder)
        print(f"ignored;{staged}")
        return 0
    dest = destination(manifest, snum, staged)
    if staged.resolve() == dest.resolve():
        print(f"success;{dest}")
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest = unique(dest)
    shutil.move(str(staged), str(dest))
    # tidy empty staging folders
    for parent in staged.parents:
        if parent.name == "stage" or not parent.exists():
            break
        try:
            parent.rmdir()
        except OSError:
            break
    print(f"success;{dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


def tidy_album_folder(folder: Path) -> None:
    """After an album lands: drop junk (.nfo, .yml, playlists…), keep one cover as cover.jpg,
    and name lyrics like their song so players pair them."""
    files = [f for f in folder.iterdir() if f.is_file()]
    for f in files:
        if f.suffix.lower().lstrip(".") in JUNK_EXTS:
            f.unlink(missing_ok=True)
    images = sorted((f for f in files if f.exists() and f.suffix.lower().lstrip(".") in IMAGE_EXTS),
                    key=lambda f: (not re.match(r"(cover|folder|front)", f.stem, re.I), f.name.lower()))
    if images and not any(f.stem.lower() == "cover" for f in images):
        best = images[0]
        best.rename(folder / f"cover{'.jpg' if best.suffix.lower() == '.jpeg' else best.suffix.lower()}")
    songs = {}
    for f in folder.iterdir():
        if f.suffix.lower().lstrip(".") in AUDIO_EXTS:
            m = re.match(r"(\d+)\. ", f.name)
            if m:
                songs[int(m.group(1))] = f.stem
    for f in list(folder.glob("*.lrc")):
        number, _ = parse_filename(f.stem, "", "")
        target = songs.get(number) if number else None
        if target and f.stem != target and not (folder / f"{target}.lrc").exists():
            f.rename(folder / f"{target}.lrc")

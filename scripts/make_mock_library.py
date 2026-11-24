"""Build a fake "Soulseek share" of tagged audio files for offline tests.

sockseek's --mock-files-dir searches this folder instead of the network, so the whole
pipeline can be exercised without an account, a network, or the risk of a ban.

Usage:
  uv run python scripts/make_mock_library.py <playlist.csv> <out_dir>
      [--missing 3,7] [--flac 2,5] [--flac-only 6] [--album-extras 3]

Row numbers are 1-based playlist positions.
  --missing      not in the share at all (-> "Not found")
  --flac         available as MP3 and FLAC
  --flac-only    only FLAC (tests Force MP3 misses)
  --album-extras add N extra tracks to every album folder (tests Full albums mode)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from unspootify.csvfile import read_tracks  # noqa: E402


def rows(arg: str) -> set[int]:
    return {int(x) for x in arg.split(",") if x.strip()} if arg else set()


def safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "_"


def make_audio(path: Path, *, title: str, artist: str, album: str, track: int, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # 44.1 kHz CBR MP3 (MPEG-1) so tag readers compute the right duration
    codec = ["-c:a", "flac", "-sample_fmt", "s16"] if path.suffix == ".flac" else ["-b:a", "64k"]
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-ac", "1", "-ar", "44100", *codec,
         "-metadata", f"title={title}", "-metadata", f"artist={artist}", "-metadata", f"album_artist={artist}",
         "-metadata", f"album={album}", "-metadata", f"track={track}", str(path)],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--missing", default="")
    ap.add_argument("--flac", default="")
    ap.add_argument("--flac-only", default="")
    ap.add_argument("--album-extras", type=int, default=0)
    ap.add_argument("--side-files", action="store_true", help="add folder.jpg + album.nfo to each album folder")
    a = ap.parse_args()

    missing, flac, flac_only = rows(a.missing), rows(a.flac), rows(a.flac_only)
    jobs: list[tuple[Path, dict]] = []
    albums: dict[tuple[str, str], int] = {}
    for n, t in enumerate(read_tracks(a.csv), start=1):
        if n in missing:
            continue
        seconds = (t.length_ms or 200_000) / 1000
        folder = a.out / safe(f"{t.artist} - {t.album or 'Singles'}")
        num = albums.setdefault((t.artist, t.album), 0) + 1
        albums[(t.artist, t.album)] = num
        exts = [".flac"] if n in flac_only else [".mp3", ".flac"] if n in flac else [".mp3"]
        for ext in exts:
            sub = folder if ext == ".mp3" else folder.with_name(folder.name + " [FLAC]")
            jobs.append((sub / f"{num:02d} - {safe(t.title)}{ext}",
                         dict(title=t.title, artist=t.artist, album=t.album, track=num, seconds=seconds)))
    for (artist, album), count in albums.items():
        for k in range(a.album_extras):
            folder = a.out / safe(f"{artist} - {album or 'Singles'}")
            jobs.append((folder / f"{count + k + 1:02d} - Album Track {k + 1}.mp3",
                         dict(title=f"Album Track {k + 1}", artist=artist, album=album, track=count + k + 1, seconds=180)))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda j: make_audio(j[0], **j[1]), jobs))
    if a.side_files:
        for folder in {p.parent for p, _ in jobs}:
            (folder / "folder.jpg").write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
            (folder / "album.nfo").write_text("ripped by someone")
    print(f"Mock library written to {a.out}")


if __name__ == "__main__":
    main()

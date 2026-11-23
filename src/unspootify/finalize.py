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


def parse_filename(stem: str, artist: str) -> tuple[int | None, str]:
    """'03 - Artist - Song Name' -> (3, 'Song Name')"""
    number = None
    m = _NUM_PREFIX.match(stem)
    if m and len(m.group(1)) <= 3:
        number, stem = int(m.group(1)), stem[m.end():]
    if artist and stem.lower().startswith(artist.lower() + " - "):
        stem = stem[len(artist) + 3:]
    return number, stem.strip() or "Untitled"


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
    number, title = parse_filename(staged.stem, job["artist"])
    album = job["album"] if manifest["mode"] == "albums" else album_from_folder(staged.parent.name, job["artist"])
    return final_path(library, artist=job["artist"], album=album, title=title, number=number, ext=ext)


def main(argv: list[str]) -> int:
    manifest_path, snum, staged = Path(argv[0]), int(argv[1]), Path(argv[2])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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

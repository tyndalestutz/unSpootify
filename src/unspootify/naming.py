"""Final file names in the library: Artist/Album [EXT]/NN. Title.ext"""

from __future__ import annotations

import re
from pathlib import Path

_BAD = re.compile(r'[\x00-\x1f*?"<>|:]')


def clean(name: str, fallback: str = "Unknown") -> str:
    """Make a name safe on macOS, Linux and Windows drives (and keep it readable)."""
    name = name.replace("/", "-").replace("\\", "-")
    name = _BAD.sub("", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:120].rstrip(" .") or fallback


def final_path(library: Path, *, artist: str, album: str, title: str, number: int | None, ext: str) -> Path:
    ext = ext.lower().lstrip(".")
    folder = library / clean(artist, "Unknown Artist") / f"{clean(album, 'Unknown Album')} [{ext.upper()}]"
    prefix = f"{number:02d}. " if number else ""
    return folder / f"{prefix}{clean(title, 'Untitled')}.{ext}"


def unique(path: Path) -> Path:
    """Avoid overwriting a different file: 'Song.mp3' -> 'Song (2).mp3'."""
    if not path.exists():
        return path
    for n in range(2, 1000):
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError(f"too many copies of {path}")

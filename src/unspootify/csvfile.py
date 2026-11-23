"""Read playlist CSVs (Exportify and similar) into plain track rows."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from unspootify.contract import AppError

# Column names we recognise, most specific first (compared case-insensitively).
# Exportify, Soundiiz, TuneMyMusic and generic exports.
TITLE_COLS = ("track name", "title", "track title", "track", "song", "song name", "name")
ARTIST_COLS = ("artist name(s)", "artist names", "artist", "artists", "artist name", "creator")
ALBUM_COLS = ("album name", "album", "album title", "release")
LENGTH_COLS = ("duration (ms)", "track duration (ms)", "duration_ms", "duration ms", "length", "duration", "time")

MAX_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class CsvTrack:
    title: str
    artist: str
    album: str
    length_ms: int | None


def _pick(header: list[str], names: tuple[str, ...]) -> int | None:
    lowered = [h.strip().lower() for h in header]
    for name in names:
        if name in lowered:
            return lowered.index(name)
    return None


def _length_ms(raw: str, column: str) -> int | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        if ":" in raw:  # m:ss or h:mm:ss
            secs = 0.0
            for part in raw.split(":"):
                secs = secs * 60 + float(part)
            return int(secs * 1000)
        value = float(raw)
    except ValueError:
        return None
    return int(value if "ms" in column.lower() else value * 1000)


def decode(data: bytes) -> str:
    """UTF-8 (with or without BOM), UTF-16 (Excel 'Unicode text'), else Windows-1252."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            text = data.decode("utf-16")
        except UnicodeDecodeError as exc:
            raise AppError("CSV_UNREADABLE") from exc
        if "\x00" in text:
            raise AppError("CSV_UNREADABLE")
        return text
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    text = data.decode("cp1252", errors="replace")
    if "\x00" in text:  # binary file, not a CSV
        raise AppError("CSV_UNREADABLE")
    return text


def read_tracks(path: Path) -> list[CsvTrack]:
    """Parse a playlist CSV. Raises AppError(CSV_UNREADABLE / CSV_NO_TRACKS)."""
    try:
        if path.stat().st_size > MAX_BYTES:
            raise AppError("CSV_UNREADABLE")
        text = decode(path.read_bytes())
    except OSError as exc:
        raise AppError("CSV_UNREADABLE") from exc

    # Exports differ: Exportify/Soundiiz use commas, some tools use ; or tabs.
    first = text.splitlines()[0] if text.strip() else ""
    delimiter = max((",", ";", "\t"), key=first.count) if first else ","
    try:
        rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    except csv.Error as exc:
        raise AppError("CSV_UNREADABLE") from exc
    if not rows:
        raise AppError("CSV_NO_TRACKS")

    header = rows[0]
    ti, ai, li = _pick(header, TITLE_COLS), _pick(header, ARTIST_COLS), _pick(header, LENGTH_COLS)
    al = _pick(header, ALBUM_COLS)
    if ti is None and al is None:
        raise AppError("CSV_UNREADABLE")

    def cell(row: list[str], idx: int | None) -> str:
        return row[idx].strip() if idx is not None and idx < len(row) else ""

    tracks = []
    for row in rows[1:]:
        title, album = cell(row, ti), cell(row, al)
        if not title and not album:
            continue
        tracks.append(
            CsvTrack(
                title=title,
                artist=cell(row, ai),
                album=album,
                length_ms=_length_ms(cell(row, li), header[li]) if li is not None else None,
            )
        )
    if not tracks:
        raise AppError("CSV_NO_TRACKS")
    return tracks


def write_tracks(path: Path, tracks: list[CsvTrack], *, albums_only: bool = False) -> None:
    """Write tracks in a CSV sockseek understands. albums_only drops titles (album jobs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if albums_only:
            w.writerow(["Artist", "Album"])
            seen = set()
            for t in tracks:
                key = (t.artist.lower(), t.album.lower())
                if t.album and key not in seen:
                    seen.add(key)
                    w.writerow([t.artist, t.album])
        else:
            w.writerow(["Artist", "Title", "Album", "Length"])
            for t in tracks:
                w.writerow([t.artist, t.title, t.album, round(t.length_ms / 1000) if t.length_ms else ""])

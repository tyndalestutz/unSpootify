"""Playlists and per-track state, kept in SQLite in the app data folder."""

from __future__ import annotations

import hashlib
import re
import shutil
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from unspootify.contract import DONE, FAILED, QUEUED, SKIPPED, STATES, TERMINAL, AppError
from unspootify.csvfile import read_tracks
from unspootify.paths import app_data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS playlists (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, source_file TEXT NOT NULL,
  added_at REAL NOT NULL, finished INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tracks (
  playlist_id TEXT NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL, title TEXT, artist TEXT, album TEXT, length_ms INTEGER,
  state TEXT NOT NULL DEFAULT 'queued', pct INTEGER NOT NULL DEFAULT 0,
  format TEXT, user TEXT, path TEXT, reason TEXT,
  PRIMARY KEY (playlist_id, idx)
);
"""


@dataclass
class Track:
    index: int
    title: str
    artist: str
    album: str
    length_ms: int | None
    state: str = QUEUED
    pct: int = 0
    format: str | None = None
    user: str | None = None
    path: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def playlist_name(path: Path) -> str:
    name = re.sub(r"[_]+", " ", path.stem).strip()
    return name or "playlist"


class Store:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or app_data_dir()
        self.playlist_dir = self.root / "playlists"
        self.playlist_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.root / "unspootify.db", check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript("PRAGMA foreign_keys = ON;" + SCHEMA)

    # ---- playlists ----
    def import_csv(self, src: Path) -> dict[str, Any]:
        """Copy a CSV into the playlists folder and load its songs. Re-importing the same file updates it."""
        tracks = read_tracks(src)  # raises AppError for bad files
        digest = hashlib.sha1(src.read_bytes()).hexdigest()[:8]
        slug = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-")[:40] or "playlist"
        pid = f"{slug}-{digest}"
        dest = self.playlist_dir / f"{pid}.csv"
        if src.resolve() != dest.resolve():
            shutil.copyfile(src, dest)
        with self._lock, self._db:
            if self._db.execute("SELECT 1 FROM playlists WHERE id=?", (pid,)).fetchone():
                return self.playlist(pid)
            self._db.execute(
                "INSERT INTO playlists (id, name, source_file, added_at) VALUES (?,?,?,?)",
                (pid, playlist_name(src), str(dest), time.time()),
            )
            self._db.executemany(
                "INSERT INTO tracks (playlist_id, idx, title, artist, album, length_ms) VALUES (?,?,?,?,?,?)",
                [(pid, i, t.title, t.artist, t.album, t.length_ms) for i, t in enumerate(tracks)],
            )
        return self.playlist(pid)

    def playlists(self) -> list[dict[str, Any]]:
        with self._lock:
            ids = [r["id"] for r in self._db.execute("SELECT id FROM playlists ORDER BY added_at")]
        return [self.playlist(i) for i in ids]

    def playlist(self, pid: str) -> dict[str, Any]:
        with self._lock:
            row = self._db.execute("SELECT * FROM playlists WHERE id=?", (pid,)).fetchone()
            if not row:
                raise KeyError(pid)
            counts = dict(
                self._db.execute(
                    "SELECT state, COUNT(*) FROM tracks WHERE playlist_id=? GROUP BY state", (pid,)
                ).fetchall()
            )
        total = sum(counts.values())
        return {
            "id": row["id"], "name": row["name"], "source_file": row["source_file"],
            "added_at": row["added_at"], "finished": bool(row["finished"]), "total": total,
            "done": counts.get(DONE, 0) + counts.get(SKIPPED, 0), "downloaded": counts.get(DONE, 0),
            "skipped": counts.get(SKIPPED, 0), "failed": counts.get(FAILED, 0),
        }

    def set_finished(self, pid: str, finished: bool) -> None:
        with self._lock, self._db:
            self._db.execute("UPDATE playlists SET finished=? WHERE id=?", (int(finished), pid))

    # ---- tracks ----
    def tracks(self, pid: str) -> list[Track]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM tracks WHERE playlist_id=? ORDER BY idx", (pid,)).fetchall()
        return [
            Track(index=r["idx"], title=r["title"], artist=r["artist"], album=r["album"], length_ms=r["length_ms"],
                  state=r["state"], pct=r["pct"], format=r["format"], user=r["user"], path=r["path"],
                  reason=r["reason"])
            for r in rows
        ]

    def track(self, pid: str, index: int) -> Track:
        with self._lock:
            r = self._db.execute("SELECT * FROM tracks WHERE playlist_id=? AND idx=?", (pid, index)).fetchone()
        if not r:
            raise KeyError((pid, index))
        return Track(index=r["idx"], title=r["title"], artist=r["artist"], album=r["album"], length_ms=r["length_ms"],
                     state=r["state"], pct=r["pct"], format=r["format"], user=r["user"], path=r["path"],
                     reason=r["reason"])

    def update_track(self, pid: str, index: int, **fields: Any) -> None:
        allowed = {"state", "pct", "format", "user", "path", "reason"}
        if set(fields) - allowed:
            raise ValueError(f"bad fields {set(fields) - allowed}")
        if "state" in fields and fields["state"] not in STATES:
            raise ValueError(fields["state"])
        sets = ", ".join(f"{k}=?" for k in fields)
        with self._lock, self._db:
            self._db.execute(f"UPDATE tracks SET {sets} WHERE playlist_id=? AND idx=?", (*fields.values(), pid, index))

    def reset_unfinished(self, pid: str) -> None:
        """After a stop or crash: anything mid-flight goes back to Waiting."""
        placeholders = ",".join("?" * len(TERMINAL))
        with self._lock, self._db:
            self._db.execute(
                f"UPDATE tracks SET state='queued', pct=0, user=NULL WHERE playlist_id=? AND state NOT IN ({placeholders})",
                (pid, *TERMINAL),
            )

    def requeue(self, pid: str, indexes: list[int]) -> None:
        with self._lock, self._db:
            self._db.executemany(
                "UPDATE tracks SET state='queued', pct=0, reason=NULL, user=NULL WHERE playlist_id=? AND idx=?",
                [(pid, i) for i in indexes],
            )
            self._db.execute("UPDATE playlists SET finished=0 WHERE id=?", (pid,))

    def reset_all(self, pid: str) -> None:
        with self._lock, self._db:
            self._db.execute(
                "UPDATE tracks SET state='queued', pct=0, format=NULL, user=NULL, path=NULL, reason=NULL "
                "WHERE playlist_id=?", (pid,),
            )
            self._db.execute("UPDATE playlists SET finished=0 WHERE id=?", (pid,))

    def close(self) -> None:
        with self._lock:
            self._db.close()


__all__ = ["Store", "Track", "AppError"]

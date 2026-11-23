"""Run sockseek and translate its output into contract track updates."""

from __future__ import annotations

import atexit
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from unspootify.contract import (
    DONE, DOWNLOADING, FAILED, QUEUED, SEARCHING, SKIPPED, TERMINAL, WAITING, AppError, event,
)
from unspootify.naming import clean, final_path
from unspootify.plan import Job, RunPlan
from unspootify.store import Store

_JOB_LINE = re.compile(r"\[(\d+)\] ([A-Za-z ]+?): (.*)$")
_DECODER = json.JSONDecoder()
_FAIL = re.compile(r"^failed(?: \[([^\]]*)\])?: (.*)$")

# sockseek failure reasons -> contract reasons
_REASONS = {"NoSearchResults": "not_found", "NoSuitableFileFound": "not_found", "AllDownloadsFailed": "error",
            "Cancelled": "cancelled", "No search results": "not_found", "No suitable file found": "not_found"}

# Best-effort detection of fatal problems from sockseek's text output (verify with a real account).
_FATAL = [
    ("LOGIN_FAILED", re.compile(r"(?i)invalid ?pass|login (?:failed|rejected)|wrong password|failed to log ?in")),
    ("PORT_BLOCKED", re.compile(r"(?i)address already in use|could not (?:bind|listen)")),
    ("NO_NETWORK", re.compile(r"(?i)(?:could not|failed to|unable to) connect|name or service not known|"
                                r"network is unreachable|no such host|connection refused")),
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


@dataclass
class JobState:
    state: str = QUEUED
    pct: int = 0
    user: str | None = None
    format: str | None = None
    path: str | None = None
    reason: str | None = None
    files_started: int = 0
    files_done: int = 0


@dataclass
class Update:
    job: int  # index into plan.jobs
    fields: dict[str, Any]


@dataclass
class LogLine:
    bold: str
    text: str


class EventMapper:
    """Pure translation: sockseek output lines -> job updates and log lines."""

    def __init__(self, mode: str, jobs: list[Job], library: Path, secret: str = "") -> None:
        self.mode, self.jobs, self.library, self.secret = mode, jobs, library, secret
        self.states = [JobState() for _ in jobs]
        self.by_song: dict[tuple[str, str], list[int]] = defaultdict(list)
        self.by_label: dict[str, int] = {}
        self.by_artist: dict[str, int] = {}
        for i, j in enumerate(jobs):
            self.by_song[(_norm(j.artist), _norm(j.title))].append(i)
            self.by_label[_norm(f"{j.artist} - {j.album}")] = i
            self.by_artist.setdefault(_norm(j.artist), i)
        self.jobno: dict[str, int] = {}  # sockseek "[003]" -> job
        self.folder: dict[str, int] = {}  # remote folder -> job (album/artist modes)
        self.pending_sizes: list[tuple[int, int]] = []  # (size, job) from download_start
        self.progress_ids: dict[str, int] = {}  # download_progress jobId -> job
        self.fatal: str | None = None
        self.completed = False  # saw sockseek's final "[cli] Completed:" summary
        self.active = False  # searching has begun (so we're logged in)
        self.tail: list[str] = []

    def scrub(self, text: str) -> str:
        """Hide the password. Very short passwords would garble every line, so only the
        `--pass X` / `password = X` patterns are scrubbed for those."""
        text = re.sub(r"(?i)(--pass(?:word)?\s+|password\s*[=:]\s*)\S+", r"\1***", text)
        if self.secret and len(self.secret) >= 4:
            text = text.replace(self.secret, "***")
        return text

    # ---- helpers ----
    def _song(self, artist: str, title: str) -> int | None:
        cands = self.by_song.get((_norm(artist), _norm(title)))
        if not cands:
            return None
        for i in cands:
            if self.states[i].state not in TERMINAL:
                return i
        return cands[0]

    def _album_job(self, label: str) -> int | None:
        label = _norm(label)
        if label in self.by_label and self.mode == "albums":
            return self.by_label[label]
        if self.mode == "artist":
            if label in self.by_artist:
                return self.by_artist[label]
            for artist, i in self.by_artist.items():
                if label.startswith(artist + " - "):
                    return i
        return None

    def _set(self, i: int | None, **f: Any) -> list[Update]:
        if i is None:
            return []
        st = self.states[i]
        if st.state in TERMINAL and f.get("state") not in (None, *TERMINAL):
            return []  # never move a finished job backwards
        changed = {k: v for k, v in f.items() if getattr(st, k) != v}
        for k, v in changed.items():
            setattr(st, k, v)
        return [Update(i, changed)] if changed else []

    def _done_path(self, i: int, ext: str | None, download_path: str | None) -> str | None:
        j = self.jobs[i]
        if self.mode == "songs" and ext:
            return str(final_path(self.library, artist=j.artist, album=j.album, title=j.title,
                                  number=j.number, ext=ext))
        if self.mode != "songs":
            return str(self.library / clean(j.artist, "Unknown Artist"))
        return download_path

    def _log(self, line: str) -> LogLine | None:
        text = line.rstrip()
        if not text.strip():
            return None
        text = self.scrub(text)
        m = _JOB_LINE.search(text)
        if m:
            phase, _, rest = m.group(3).partition(": ")
            return LogLine(phase[:1].upper() + phase[1:] + ":", " " + rest if rest else "")
        m = re.match(r"^\[(\w+)\] (.*)$", text)
        if m:
            return LogLine("", m.group(2))
        return LogLine("", text.strip())

    # ---- main entry ----
    def feed(self, line: str) -> list[Update | LogLine]:
        """One line of sockseek output. sockseek writes from several threads, so a line can hold
        text and JSON glued together; pull out every JSON event and treat the rest as text."""
        out: list[Update | LogLine] = []
        rest = line.rstrip("\n")
        while (k := rest.find('{"type"')) >= 0:
            try:
                ev, end = _DECODER.raw_decode(rest, k)
            except ValueError:
                break
            if rest[:k].strip():
                out += self._feed_text(rest[:k])
            if isinstance(ev, dict):
                out += self._json(ev.get("type", ""), ev.get("data") or {})
            rest = rest[end:]
        if rest.strip():
            out += self._feed_text(rest)
        return out

    def _feed_text(self, line: str) -> list[Update | LogLine]:
        line = self.scrub(line)
        self.tail = (self.tail + [line])[-40:]
        if "[cli] Completed:" in line:
            self.completed = True
        if re.search(r"\] (?:SongJob|AlbumJob|Album Aggregate): searching", line):
            self.active = True
        # Login/network problems show up before any search starts; later, peers refuse
        # connections all the time in healthy runs, so stop looking once searching has begun.
        if self.fatal is None and not self.active:
            for code, rx in _FATAL:
                if rx.search(line):
                    self.fatal = code
                    break
        out: list[Update | LogLine] = []
        if self.mode != "songs":
            out += self._text(line)
        log = self._log(line)
        if log:
            out.append(log)
        return out

    def _json(self, kind: str, d: dict[str, Any]) -> list[Update | LogLine]:
        if kind == "track_list" and self.mode == "songs":
            out: list[Update | LogLine] = []
            for t in d.get("tracks", []):
                i = self._song(t.get("artist", ""), t.get("title", ""))
                skip = t.get("skipReason", "None")
                if skip in ("AlreadyExists", "ExistsInMusicDir", "AlreadyDownloaded"):
                    out += self._set(i, state=SKIPPED, pct=100)
                elif skip == "NotFoundLastTime":
                    out += self._set(i, state=FAILED, reason="not_found")
                elif skip not in ("None", None, ""):
                    out += self._set(i, state=SKIPPED, pct=100)
            return out
        if kind in ("search_start", "download_start"):
            self.active = True
        if kind == "search_start" and self.mode == "songs":
            return self._set(self._song(d.get("artist", ""), d.get("title", "")), state=SEARCHING)
        if kind == "download_start":
            if self.mode == "songs":
                i = self._song(d.get("artist", ""), d.get("title", ""))
            else:
                i = self.folder.get(str(d.get("filename", "")).rsplit("\\", 1)[0])
            if i is not None:
                self.pending_sizes.append((int(d.get("size") or 0), i))
            ext = d.get("extension")
            return self._set(i, state=DOWNLOADING, user=d.get("username"),
                             format=ext.upper() if ext else None)
        if kind == "download_progress":
            jid = str(d.get("jobId", ""))
            i = self.progress_ids.get(jid)
            if i is None and self.pending_sizes:
                size = int(d.get("totalBytes") or 0)
                match = next((p for p in self.pending_sizes if p[0] == size), self.pending_sizes[-1])
                self.pending_sizes.remove(match)
                i = self.progress_ids[jid] = match[1]
            if i is None or self.mode != "songs":
                return []
            return self._set(i, state=DOWNLOADING, pct=max(0, min(99, int(d.get("percent") or 0))))
        if kind == "track_state":
            return self._track_state(d)
        return []

    def _track_state(self, d: dict[str, Any]) -> list[Update | LogLine]:
        outcome, skip = d.get("terminalOutcome", "None"), d.get("skipReason", "None")
        phase = str(d.get("activityPhase", "None"))
        if self.mode != "songs":
            if outcome == "Succeeded":
                folder = str(d.get("filename", "")).rsplit("\\", 1)[0]
                i = self.folder.get(folder)
                if i is None:
                    i = self.by_artist.get(_norm(d.get("artist", ""))) if self.mode == "artist" else None
                if i is not None:
                    st = self.states[i]
                    st.files_done += 1
                    pct = min(99, int(100 * st.files_done / max(st.files_started, st.files_done, 1)))
                    return self._set(i, state=DOWNLOADING, pct=pct)
            return []
        i = self._song(d.get("artist", ""), d.get("title", ""))
        if outcome == "Succeeded":
            ext = d.get("extension") or Path(str(d.get("downloadPath") or "")).suffix.lstrip(".") or None
            return self._set(i, state=DONE, pct=100, format=ext.upper() if ext else self.states[i].format if i is not None else None,
                             path=self._done_path(i, ext, d.get("downloadPath")) if i is not None else None, reason=None)
        if outcome == "Failed":
            return self._set(i, state=FAILED, pct=0, reason=_REASONS.get(d.get("failureReason", ""), "not_found"))
        if outcome in ("Cancelled", "Canceled"):
            return self._set(i, state=QUEUED, pct=0)
        if skip not in ("None", None, ""):
            return self._set(i, state=SKIPPED, pct=100)
        if "wait" in phase.lower():
            return self._set(i, state=WAITING)
        return []

    def _text(self, line: str) -> list[Update | LogLine]:
        ex = re.search(r"Already exists: (.+?): (?:completed|exists)", line)
        if ex:  # album/artist already downloaded in an earlier run (sockseek's index)
            i = self._album_job(ex.group(1))
            return self._set(i, state=SKIPPED, pct=100)
        m = _JOB_LINE.search(line.strip())
        if not m:
            return []
        no, kind, rest = m.groups()
        kind = kind.strip()
        if kind in ("AlbumJob", "Album Aggregate"):
            if rest.startswith("searching: "):
                i = self._album_job(rest[len("searching: "):])
                if i is not None:
                    self.jobno[no] = i
                return self._set(i, state=SEARCHING)
            i = self.jobno.get(no)
            if rest.startswith("downloading"):
                return self._set(i, state=DOWNLOADING)
            if rest.startswith("succeeded"):
                if kind == "Album Aggregate" or self.mode == "albums":
                    return self._set(i, state=DONE, pct=100, path=self._done_path(i, None, None) if i is not None else None)
                return []
            fm = _FAIL.match(rest)
            if fm:
                if self.mode == "artist" and kind == "AlbumJob":
                    return []  # one album of an artist failing isn't the artist failing
                reason = _REASONS.get(fm.group(1) or "", "not_found")
                return self._set(i, state=FAILED, pct=0, reason=reason)
            return []
        if kind == "Album File" and rest.startswith("downloading: "):
            i = self.jobno.get(no)
            remote = rest.rsplit(": ", 1)[-1]  # user\folder\file
            parts = remote.split("\\")
            if i is None or len(parts) < 2:
                return []
            self.folder["\\".join(parts[1:-1])] = i
            st = self.states[i]
            st.files_started += 1
            ext = Path(parts[-1]).suffix.lstrip(".")
            pct = min(99, int(100 * st.files_done / max(st.files_started, 1)))
            return self._set(i, state=DOWNLOADING, user=parts[0], format=ext.upper() or None, pct=pct)
        return []

    def all_settled(self) -> bool:
        return all(st.state in TERMINAL for st in self.states)

    def finish(self, stopped: bool) -> list[Update]:
        """When sockseek exits: settle every job that never reached an end state."""
        out: list[Update] = []
        for i, st in enumerate(self.states):
            if st.state in TERMINAL:
                continue
            if stopped or (not self.completed and not self.all_settled()):
                out += self._set(i, state=QUEUED, pct=0, user=None)
            elif self.mode != "songs" and st.files_done:
                # album/artist: files arrived but the job's own end line was lost in interleaved output
                out += self._set(i, state=DONE, pct=100, path=self._done_path(i, None, None))
            else:
                out += self._set(i, state=FAILED, pct=0, reason="not_found")
        return out


Emit = Callable[[dict[str, Any]], None]

def child_env() -> dict[str, str]:
    """Environment for sockseek. A PyInstaller build points LD_LIBRARY_PATH (Linux) /
    DYLD_LIBRARY_PATH (macOS) at its own bundled libraries; sockseek must get the user's originals."""
    env = dict(os.environ)
    if getattr(sys, "frozen", False):
        for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
            original = env.pop(f"{var}_ORIG", None)
            if original is not None:
                env[var] = original
            else:
                env.pop(var, None)
    return env


# sockseek processes we started: killed if the app exits (even without a clean shutdown)
_LIVE: set[subprocess.Popen] = set()


@atexit.register
def _kill_children() -> None:
    for proc in list(_LIVE):
        if proc.poll() is None:
            proc.kill()


# Note: Linux PR_SET_PDEATHSIG is NOT used. It fires when the *thread* that spawned the child exits,
# and pywebview runs commands on short-lived worker threads, so sockseek would be killed instantly.


@dataclass
class Runner:
    """One sockseek process for one playlist."""

    store: Store
    playlist_id: str
    plan: RunPlan
    sockseek: Path
    emit: Emit
    secret: str = ""
    force_format: str | None = None  # set when running in Force mode (for the follow-up offer)
    on_exit: Callable[[Runner], None] | None = None
    proc: subprocess.Popen | None = None
    stopped: bool = False
    timed_out: bool = False
    login_timeout: float = 120.0  # seconds without any search before we call it a connection problem
    _started_at: float = 0.0
    mapper: EventMapper = field(init=False)
    _thread: threading.Thread | None = None

    def __post_init__(self) -> None:
        self.mapper = EventMapper(self.plan.mode, self.plan.jobs, self.plan.library, self.secret)

    def start(self) -> None:
        if not self.sockseek.exists():
            raise AppError("SOCKSEEK_MISSING", str(self.sockseek))
        try:
            self.proc = subprocess.Popen(
                [str(self.sockseek), *self.plan.args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", bufsize=1,
                cwd=self.plan.input_path.parent, env=child_env(),
            )
        except OSError as exc:  # not executable (permissions, macOS quarantine), wrong architecture…
            self._cleanup()
            raise AppError("SOCKSEEK_MISSING", str(exc)) from exc
        _LIVE.add(self.proc)
        for job in self.plan.jobs:
            for idx in job.indexes:
                self.store.update_track(self.playlist_id, idx, state=QUEUED, pct=0, reason=None, user=None)
        self.store.set_finished(self.playlist_id, False)
        self.emit(event("run_started", playlist_id=self.playlist_id,
                        total=sum(len(j.indexes) for j in self.plan.jobs)))
        self.emit(event("status", phase="connecting"))
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._pump, name="sockseek", daemon=True)
        self._thread.start()
        threading.Thread(target=self._watchdog, name="sockseek-watchdog", daemon=True).start()

    def stop(self) -> None:
        self.stopped = True
        self._terminate()

    def _terminate(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def _watchdog(self) -> None:
        """If sockseek never starts searching (can't log in / no network), give up with a clear error."""
        while self.proc and self.proc.poll() is None:
            if self.mapper.active:
                return
            if time.monotonic() - self._started_at > self.login_timeout:
                self.timed_out = True
                self._terminate()
                return
            time.sleep(0.5)

    def _cleanup(self) -> None:
        try:  # the per-run config holds the password
            (self.plan.input_path.parent / "sockseek.conf").unlink(missing_ok=True)
        except OSError:
            pass

    def wait(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _apply(self, items: list[Update | LogLine]) -> None:
        for item in items:
            if isinstance(item, LogLine):
                self.emit(event("log", bold=item.bold, text=item.text))
                continue
            fields = {k: v for k, v in item.fields.items() if k in ("state", "pct", "format", "user", "path", "reason")}
            if not fields:
                continue
            for idx in self.plan.jobs[item.job].indexes:
                self.store.update_track(self.playlist_id, idx, **fields)
                self.emit(event("track", playlist_id=self.playlist_id, **self.store.track(self.playlist_id, idx).to_dict()))

    def _pump(self) -> None:
        assert self.proc and self.proc.stdout
        was_active = False
        for line in self.proc.stdout:
            self._apply(self.mapper.feed(line))
            if self.mapper.active and not was_active:
                was_active = True
                self.emit(event("status", phase="logged_in"))
        self.proc.wait()
        _LIVE.discard(self.proc)
        self._cleanup()
        crashed_after_work = not self.mapper.completed and self.mapper.all_settled() and not self.timed_out
        self._apply(self.mapper.finish(self.stopped))
        error: AppError | None = None
        # sockseek exits non-zero when some songs failed; that's a normal finish, not a crash.
        if self.timed_out:
            error = AppError(self.mapper.fatal or "LOGIN_TIMEOUT", "\n".join(self.mapper.tail[-8:]))
        elif not self.stopped and not self.mapper.completed and not crashed_after_work:
            error = AppError(self.mapper.fatal or "SOCKSEEK_CRASHED", "\n".join(self.mapper.tail[-8:]))
        elif crashed_after_work and not self.stopped:
            self.emit(event("log", bold="Note:", text=" the downloader closed oddly after finishing every song;"
                            " nothing was lost."))
        queued_left = any(t.state not in TERMINAL for t in self.store.tracks(self.playlist_id))
        finished = not self.stopped and error is None and not queued_left
        self.store.set_finished(self.playlist_id, finished)
        if error:
            self.emit(error.to_event())
        self.emit(event("status", phase="idle"))
        missing = None
        if finished and self.force_format:
            missing = sum(1 for t in self.store.tracks(self.playlist_id) if t.state == FAILED) or None
        self.emit(event("run_finished", playlist_id=self.playlist_id, stopped=self.stopped,
                        counts=self.store.playlist(self.playlist_id), missing_format=missing,
                        force_format=self.force_format if missing else None))
        if self.on_exit:
            self.on_exit(self)

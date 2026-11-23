"""The real backend: implements the commands in docs/ui-contract.md.

The window (Phase 3) and the headless CLI both drive this class; events go to `emit`.
"""

from __future__ import annotations

import os
import shutil
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from unspootify import __version__, porttest
from unspootify.contract import FAILED, AppError, event
from unspootify.paths import app_data_dir, sockseek_path
from unspootify.plan import prepare
from unspootify.runner import Runner
from unspootify.settings import SettingsStore
from unspootify.store import Store

EXPORTIFY_URL = "https://exportify.net/"


class Backend:
    def __init__(self, emit: Callable[[dict[str, Any]], None], root: Path | None = None,
                 mock_dir: Path | None = None, sockseek: Path | None = None,
                 extra_args: list[str] | None = None) -> None:
        self.root = root or app_data_dir()
        self.emit = emit
        self.settings = SettingsStore(self.root / "settings.json")
        self.store = Store(self.root)
        self.mock_dir = mock_dir  # offline test mode: sockseek "downloads" from this folder
        self.sockseek = sockseek or sockseek_path()
        self.extra_args = extra_args or []  # tests only (e.g. --mock-files-slow)
        self.login_timeout = 120.0
        self.runner: Runner | None = None
        self._lock = threading.Lock()
        for p in self.store.playlists():  # anything left mid-flight by a crash goes back to Waiting
            self.store.reset_unfinished(p["id"])

    # ---- state ----
    def get_state(self) -> dict[str, Any]:
        run = None
        if self.runner and self.runner.running:
            run = {"playlist_id": self.runner.playlist_id, "running": True}
        return {"settings": self.settings.settings.to_dict(), "playlists": self.store.playlists(),
                "run": run, "app_version": __version__, "offline_test": self.mock_dir is not None}

    def save_settings(self, partial: dict[str, Any]) -> dict[str, Any]:
        return self.settings.update(partial).to_dict()

    def get_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.store.tracks(playlist_id)]

    # ---- playlists ----
    def import_csv_path(self, path: str) -> dict[str, Any]:
        playlist = self.store.import_csv(Path(path))
        self.emit(event("log", bold="Added playlist", text=f' "{playlist["name"]}" ({playlist["total"]} songs)'))
        return playlist

    def open_exportify(self) -> None:
        webbrowser.open(EXPORTIFY_URL)

    # ---- runs ----
    def _check_ready(self) -> None:
        s = self.settings.settings
        if self.mock_dir is None and not (s.username.strip() and s.password):
            raise AppError("NO_LOGIN")
        if self.runner and self.runner.running:
            raise AppError("ALREADY_RUNNING")
        library = Path(s.library_path).expanduser()
        if not library.exists():
            # Inside the home folder we simply create it (a fresh computer may not have ~/Music yet).
            # Elsewhere, a missing parent usually means an unplugged drive: say so instead of
            # silently writing to the wrong disk.
            in_home = Path.home() in library.parents
            if not in_home and not library.parent.exists():
                raise AppError("FOLDER_MISSING", str(library))
            try:
                library.mkdir(parents=True)
            except OSError as exc:
                raise AppError("FOLDER_NOT_WRITABLE", str(library)) from exc
        if not os.access(library, os.W_OK):
            raise AppError("FOLDER_NOT_WRITABLE", str(library))
        if not self.sockseek.exists():
            raise AppError("SOCKSEEK_MISSING", str(self.sockseek))

    def _launch(self, playlist_id: str, *, only: list[int] | None = None, format_override: str | None = None,
                force_override: bool | None = None, try_harder: bool | None = None,
                offer_followup: bool = True, requeue: list[int] | None = None) -> dict[str, Any]:
        with self._lock:
            self._check_ready()  # nothing changes until we know the run can start
            s = self.settings.settings
            if requeue:
                self.store.requeue(playlist_id, requeue)
            self._forget_missing_files(playlist_id)
            run_dir = self.root / "runs" / playlist_id
            shutil.rmtree(run_dir / "stage", ignore_errors=True)
            run_dir.mkdir(parents=True, exist_ok=True)
            plan = prepare(s, playlist_id, self.store.tracks(playlist_id), run_dir, only=only,
                           format_override=format_override, force_override=force_override,
                           try_harder=try_harder, mock_dir=self.mock_dir, extra_args=self.extra_args)
            if not plan.jobs:
                # finished only if nothing is left; Advanced "Only first / Skip first" can leave rows untried
                left = any(t.state == "queued" for t in self.store.tracks(playlist_id))
                self.store.set_finished(playlist_id, not left)
                self.emit(event("run_finished", playlist_id=playlist_id, stopped=False,
                                counts=self.store.playlist(playlist_id), missing_format=None, force_format=None,
                                nothing_to_do=True))
                return {"ok": True, "nothing_to_do": True}
            force = s.options.mode == "force" if force_override is None else force_override
            self.runner = Runner(self.store, playlist_id, plan, self.sockseek, self.emit, secret=s.password,
                                 force_format=(format_override or s.options.format) if force and offer_followup else None,
                                 login_timeout=self.login_timeout)
            self.runner.start()
            return {"ok": True}

    def start(self, playlist_id: str) -> dict[str, Any]:
        return self._launch(playlist_id)

    def stop(self) -> dict[str, Any]:
        if self.runner:
            self.runner.stop()
            self.runner.wait(10)
        return {"ok": True}

    def failed_indexes(self, playlist_id: str) -> list[int]:
        return [t.index for t in self.store.tracks(playlist_id) if t.state == FAILED]

    def retry(self, playlist_id: str) -> dict[str, Any]:
        """Search again for the misses, trying harder."""
        missing = self.failed_indexes(playlist_id)
        return self._launch(playlist_id, only=missing, try_harder=True, requeue=missing)

    def force_followup(self, playlist_id: str, accept: bool, forced_format: str | None = None) -> dict[str, Any]:
        """Force mode missed some songs: get them in the other format (or leave them).
        forced_format is the format the finished run was forced to (from run_finished)."""
        if not accept:
            return {"ok": True}
        fmt = forced_format if forced_format in ("mp3", "flac") else self.settings.settings.options.format
        other = "flac" if fmt == "mp3" else "mp3"
        missing = self.failed_indexes(playlist_id)
        return self._launch(playlist_id, only=missing, format_override=other, force_override=True,
                            offer_followup=False, requeue=missing)

    def reset_playlist(self, playlist_id: str) -> dict[str, Any]:
        """'Download again': forget results so every song is tried (what's in the library is skipped)."""
        if self.runner and self.runner.running and self.runner.playlist_id == playlist_id:
            raise AppError("ALREADY_RUNNING")
        self._forget_missing_files(playlist_id)
        self.store.reset_all(playlist_id)
        return self.store.playlist(playlist_id)

    def archive_playlist(self, playlist_id: str, archived: bool) -> dict[str, Any]:
        self.store.set_archived(playlist_id, bool(archived))
        return self.store.playlist(playlist_id)

    def remove_playlist(self, playlist_id: str) -> dict[str, Any]:
        """Remove from the app only; downloaded music stays in the library."""
        if self.runner and self.runner.running and self.runner.playlist_id == playlist_id:
            raise AppError("ALREADY_RUNNING")
        self.store.playlist(playlist_id)  # KeyError if unknown
        self.store.remove(playlist_id)
        shutil.rmtree(self.root / "runs" / playlist_id, ignore_errors=True)
        for index in (self.root / "runs").glob(f"index-{playlist_id}-*.csv"):
            index.unlink(missing_ok=True)
        return {"ok": True}

    def _forget_missing_files(self, playlist_id: str) -> None:
        """Songs marked downloaded whose file is gone (folder changed, deleted, drive unplugged) get retried."""
        gone = [t.index for t in self.store.tracks(playlist_id)
                if t.state == "done" and t.path and not Path(t.path).exists()]
        if gone:
            self.store.requeue(playlist_id, gone)
            # sockseek's own index would still call them downloaded; let it rebuild
            for index in (self.root / "runs").glob(f"index-{playlist_id}-*.csv"):
                index.unlink(missing_ok=True)
            self.emit(event("log", bold="Note:", text=f" {len(gone)} downloaded songs aren't in the music folder"
                            " anymore; they'll be downloaded again."))

    # ---- connection ----
    def test_port(self, port: int | None = None) -> dict[str, Any]:
        result = porttest.test_port(port or self.settings.settings.advanced.listen_port)
        self.emit(event("port_result", **result))
        return result

    def close(self) -> None:
        self.stop()
        self.store.close()

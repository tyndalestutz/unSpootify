"""Opens the unSpootify window and connects the page to the backend (docs/ui-contract.md)."""

from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import webview

from unspootify.contract import AppError, event
from unspootify.paths import ui_dir

URLS = {"soundiiz": "https://soundiiz.com/", "exportify": "https://exportify.net/"}


def _guard(fn):
    """Commands never throw into the page: AppErrors become {"error": {...}}."""

    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AppError as exc:
            return {"error": exc.to_event()}
        except KeyError:
            return {"error": {"code": "NOT_FOUND", "message": "That playlist isn't there anymore.", "action": None}}
        except Exception as exc:  # never leave the page waiting on a rejected promise
            import traceback

            traceback.print_exc()
            return {"error": AppError("UNEXPECTED", f"{type(exc).__name__}: {exc}").to_event()}

    wrapper.__name__ = fn.__name__
    return wrapper


class Api:
    """Methods the page calls as `window.pywebview.api.<name>()`."""

    def __init__(self, mode: str, offline_dir: Path | None = None) -> None:
        self._mode = mode
        self._offline_dir = offline_dir
        self._window: webview.Window | None = None
        self._backend = None

    # pywebview exposes public attributes, so keep internals underscored
    def _attach(self, window: webview.Window) -> None:
        self._window = window
        if self._mode == "real":
            from unspootify.backend import Backend

            self._backend = Backend(self._emit, mock_dir=self._offline_dir)

    def _emit(self, ev: dict[str, Any]) -> None:
        if self._window is None:
            return
        payload = json.dumps(ev, ensure_ascii=False)
        try:
            self._window.evaluate_js(f"window.dispatchEvent(new CustomEvent('unspootify', {{detail: {payload}}}))")
        except Exception:  # window closing
            pass

    def get_mode(self) -> str:
        return self._mode

    # ---- window-level commands ----
    def choose_folder(self) -> str | None:
        if self._window is None:
            return None
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None

    @_guard
    def import_csv(self) -> dict | None:
        if self._window is None or self._backend is None:
            return None
        result = self._window.create_file_dialog(webview.FileDialog.OPEN,
                                                 file_types=("Playlist files (*.csv;*.txt)", "All files (*.*)"))
        if not result:
            return None
        return self._backend.import_csv_path(result[0])

    @_guard
    def import_csv_data(self, name: str, data_b64: str) -> dict:
        """A CSV dropped on the window: the page sends the raw bytes (base64) so any encoding works."""
        raw = base64.b64decode(data_b64, validate=False)
        if len(raw) > 50 * 1024 * 1024:
            raise AppError("CSV_UNREADABLE", "too big")
        stem = "".join(c for c in Path(name).stem if c.isalnum() or c in " ._-()").strip(" .")[:80] or "playlist"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"{stem}.csv"
            path.write_bytes(raw)
            return self._backend.import_csv_path(str(path))

    def open_url(self, which: str) -> None:
        import webbrowser

        if which in URLS:
            webbrowser.open(URLS[which])

    # ---- backend commands (contract) ----
    @_guard
    def get_state(self) -> dict:
        return self._backend.get_state()

    @_guard
    def save_settings(self, partial: dict) -> dict:
        return self._backend.save_settings(partial)

    @_guard
    def get_tracks(self, playlist_id: str) -> list:
        return self._backend.get_tracks(playlist_id)

    @_guard
    def start(self, playlist_id: str) -> dict:
        return self._backend.start(playlist_id)

    @_guard
    def stop(self) -> dict:
        threading.Thread(target=self._backend.stop, daemon=True).start()  # don't block the page
        return {"ok": True}

    @_guard
    def retry(self, playlist_id: str) -> dict:
        return self._backend.retry(playlist_id)

    @_guard
    def force_followup(self, playlist_id: str, accept: bool, forced_format: str | None = None) -> dict:
        return self._backend.force_followup(playlist_id, bool(accept), forced_format)

    @_guard
    def archive_playlist(self, playlist_id: str, archived: bool) -> dict:
        return self._backend.archive_playlist(playlist_id, bool(archived))

    @_guard
    def remove_playlist(self, playlist_id: str) -> dict:
        return self._backend.remove_playlist(playlist_id)

    @_guard
    def reset_playlist(self, playlist_id: str) -> dict:
        return self._backend.reset_playlist(playlist_id)

    @_guard
    def test_port(self, port: int | None = None) -> dict:
        return self._backend.test_port(int(port) if port else None)

    def _close(self) -> None:
        if self._backend:
            self._backend.close()


# Runs inside the page: did every stylesheet and script load, and did the app start?
_SMOKE_JS = """
(() => {
  const sheets = [...document.styleSheets];
  const broken = sheets.filter(s => { try { return s.cssRules.length === 0; } catch (e) { return true; } })
                       .map(s => s.href);
  return JSON.stringify({
    sheets: sheets.length, broken, ready: !!window.unspootifyReady,
    backend: window.UI && window.UI.backend ? window.UI.backend.constructor.name : null,
    trackRows: document.querySelectorAll('#trackRows .track-row').length,
  });
})()
"""
_smoke_failed = False


def _smoke_test(window: webview.Window) -> None:
    global _smoke_failed
    window.events.loaded.wait(30)
    result: dict = {}
    for _ in range(80):
        result = json.loads(window.evaluate_js(_SMOKE_JS))
        if result["ready"]:
            break
        threading.Event().wait(0.25)
    ok = not result["broken"] and result["ready"]
    print(f"SMOKE {'ok' if ok else 'FAIL'}: {json.dumps(result)}")
    _smoke_failed = not ok
    window.destroy()


def _ui_script(window: webview.Window, script: str, timeout: float = 180) -> None:
    """Testing: run a JS test script in the real window and print its CHECK lines."""
    global _smoke_failed
    window.events.loaded.wait(30)
    for _ in range(80):
        if window.evaluate_js("!!window.unspootifyReady"):
            break
        threading.Event().wait(0.25)
    window.evaluate_js(script)
    printed, deadline = 0, time.time() + timeout
    while time.time() < deadline:
        lines = json.loads(window.evaluate_js("JSON.stringify(window.__checkLog || [])"))
        for line in lines[printed:]:
            print(line, flush=True)
        printed = len(lines)
        if "CHECK DONE" in lines:
            break
        threading.Event().wait(0.5)
    else:
        print("CHECK FAIL timeout: script never finished", flush=True)
    _smoke_failed = any(l.startswith("CHECK FAIL") for l in lines)
    window.destroy()


def _linux_icon(icon: str) -> None:
    """Show the eject icon: set it on the Qt app (pywebview doesn't), and when running as an
    AppImage add an app-menu entry once so the dock/Activities know the icon too."""
    from qtpy.QtGui import QGuiApplication, QIcon
    from qtpy.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["unspootify", *sys.argv[1:]])  # WM_CLASS = unspootify
    app.setWindowIcon(QIcon(icon))
    QGuiApplication.setDesktopFileName("unspootify")
    appimage = os.environ.get("APPIMAGE")
    if not appimage:
        return
    try:
        share = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        icon_dest = share / "icons" / "hicolor" / "256x256" / "apps" / "unspootify.png"
        icon_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(icon, icon_dest)
        entry = share / "applications" / "unspootify.desktop"
        entry.parent.mkdir(parents=True, exist_ok=True)
        text = (f"[Desktop Entry]\nType=Application\nName=unSpootify\nComment=Turn your playlists into a music "
                f"library you own\nExec=\"{appimage}\" %U\nIcon=unspootify\nStartupWMClass=unspootify\n"
                f"Categories=AudioVideo;Audio;Network;\nTerminal=false\n")
        if not entry.exists() or entry.read_text() != text:
            entry.write_text(text)
    except OSError:
        pass  # menu entry is a nicety


def _window_background(mode: str) -> str:
    """Paint the empty window in the saved look's color so there's no flash before the page loads."""
    if mode == "real":
        from unspootify.settings import SettingsStore

        if SettingsStore().settings.look == "jukebox":
            return "#c9ccd2"
    return "#020a04"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    offline = None
    if "--offline-test" in argv:  # real backend, but sockseek "downloads" from a local test folder
        offline = Path(argv[argv.index("--offline-test") + 1]).expanduser()
    mode = "fake" if "--mockups" in argv else "real"
    api = Api(mode, offline)
    window = webview.create_window(
        "unSpootify", url=str(ui_dir() / "index.html"), js_api=api,
        width=1120, height=820, min_size=(940, 760), background_color=_window_background(mode),
    )
    api._attach(window)
    window.events.closed += api._close
    gui = "qt" if sys.platform.startswith("linux") else None
    icon = str(ui_dir() / "icon.png")
    if gui == "qt":
        _linux_icon(icon)
    if "--ui-script" in argv:
        script = Path(argv[argv.index("--ui-script") + 1]).read_text(encoding="utf-8")
        webview.start(_ui_script, (window, script), gui=gui, icon=icon)
        api._close()
        return 1 if _smoke_failed else 0
    if "--smoke-test" in argv:
        webview.start(_smoke_test, window, gui=gui, icon=icon)
        api._close()
        return 1 if _smoke_failed else 0
    webview.start(gui=gui, icon=icon)
    return 0


__all__ = ["main", "Api", "event"]

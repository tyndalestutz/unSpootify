"""Opens the unSpootify window."""

import subprocess
import sys
import threading

import webview

from unspootify import __version__
from unspootify.paths import sockseek_path, ui_dir


def sockseek_version() -> str | None:
    path = sockseek_path()
    if not path.exists():
        return None
    try:
        out = subprocess.run(
            [str(path), "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None


class Api:
    """Methods the page can call as `window.pywebview.api.<name>()`."""

    def __init__(self) -> None:
        self._window: webview.Window | None = None

    def get_info(self) -> dict:
        return {"app_version": __version__, "sockseek_version": sockseek_version()}

    def choose_folder(self) -> str | None:
        """Show the OS folder picker; return the chosen path or None."""
        if self._window is None:
            return None
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None


def _smoke_test(window: webview.Window) -> None:
    """Wait for the page to finish talking to Python, print what it shows, quit."""
    window.events.loaded.wait(30)
    status = ""
    for _ in range(120):
        status = window.evaluate_js("document.getElementById('status').dataset.state || ''")
        if status in ("ok", "missing"):
            break
        threading.Event().wait(0.25)
    text = window.evaluate_js("document.getElementById('status').textContent")
    print(f"SMOKE {status}: {text}")
    window.destroy()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # --mockups: Phase 1 look check (fake data, simulated downloads)
    page = ui_dir() / ("mockups/index.html" if "--mockups" in argv else "index.html")
    api = Api()
    window = webview.create_window(
        "unSpootify",
        url=str(page),
        js_api=api,
        width=1120,
        height=820,
        min_size=(940, 640),
        background_color="#000000",
    )
    api._window = window
    gui = "qt" if sys.platform.startswith("linux") else None
    if "--smoke-test" in argv:
        webview.start(_smoke_test, window, gui=gui)
    else:
        webview.start(gui=gui)
    return 0

"""Opens the unSpootify window."""

import json
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


# Runs inside the page: did every stylesheet and script load, and did the page render?
_SMOKE_JS = """
(() => {
  const sheets = [...document.styleSheets];
  const broken = sheets.filter(s => { try { return s.cssRules.length === 0; } catch (e) { return true; } })
                       .map(s => s.href);
  const status = document.getElementById('status');
  return JSON.stringify({
    sheets: sheets.length, broken,
    status: status ? (status.dataset.state || '') : null,
    text: status ? status.textContent : null,
    trackRows: document.querySelectorAll('#trackRows .track-row').length,
  });
})()
"""


def _smoke_test(window: webview.Window) -> None:
    """Load the page, check its CSS/JS actually loaded, print the result, quit."""
    window.events.loaded.wait(30)
    result: dict = {}
    for _ in range(80):
        result = json.loads(window.evaluate_js(_SMOKE_JS))
        if result["status"] in ("ok", "missing") or result["trackRows"] > 0:
            break
        threading.Event().wait(0.25)
    ok = not result["broken"] and (result["status"] == "ok" or result["trackRows"] > 0)
    print(f"SMOKE {'ok' if ok else 'FAIL'}: {json.dumps(result)}")
    window.destroy()
    global _smoke_failed
    _smoke_failed = not ok


_smoke_failed = False


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # --mockups: Phase 1 look check (fake data, simulated downloads)
    page = ui_dir() / ("mockups.html" if "--mockups" in argv else "index.html")
    api = Api()
    window = webview.create_window(
        "unSpootify",
        url=str(page),
        js_api=api,
        width=1120,
        height=820,
        min_size=(940, 760),
        background_color="#000000",
    )
    api._window = window
    gui = "qt" if sys.platform.startswith("linux") else None
    if "--smoke-test" in argv:
        webview.start(_smoke_test, window, gui=gui)
        return 1 if _smoke_failed else 0
    webview.start(gui=gui)
    return 0

"""Dev tool: render a UI page offscreen with Qt WebEngine and save a PNG.

Serves the page over HTTP rooted at the page's own folder, exactly like pywebview
does in the app, so paths that break in the app also break here.

Usage: uv run python scripts/screenshot_ui.py <page.html> <out.png> [query] [WxH] [script.js]
(script.js runs after load; its console.log output is printed, then the shot is taken.)
"""

import functools
import http.server
import os
import sys
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtWebEngineCore import QWebEnginePage  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


class ConsolePage(QWebEnginePage):
    """Print JS console warnings/errors so broken pages are obvious."""

    def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802
        if level != QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel:
            sys.stderr.write(f"JS {level.name}: {message} ({source}:{line})\n")
        elif message.startswith("CHECK"):
            print(message, flush=True)
            if message.startswith("CHECK DONE"):
                self.done = True


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # only report missing files
        if args and str(args[1]).startswith("4"):
            sys.stderr.write(f"HTTP {args[1]}: {args[0]}\n")


def main() -> None:
    page, out = sys.argv[1], sys.argv[2]
    query = sys.argv[3] if len(sys.argv) > 3 else ""
    w, h = map(int, (sys.argv[4] if len(sys.argv) > 4 else "1280x800").split("x"))
    app = QApplication([])
    view = QWebEngineView()
    view.setPage(ConsolePage(view))
    view.resize(w, h)
    root, name = os.path.split(os.path.abspath(page))
    handler = functools.partial(QuietHandler, directory=root)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = QUrl(f"http://127.0.0.1:{httpd.server_address[1]}/{name}")
    if query:
        url.setQuery(query)
    view.load(url)
    view.show()

    def snap() -> None:
        view.grab().save(out)
        app.quit()

    script = open(sys.argv[5]).read() if len(sys.argv) > 5 else ""

    page = view.page()
    page.done = False
    timeout_ms = int(os.environ.get("UI_SCRIPT_TIMEOUT_MS", "90000"))

    def loaded(_ok: bool) -> None:
        if not script:
            QTimer.singleShot(1500, snap)
            return
        page.runJavaScript(script)
        # Scripts that print "CHECK DONE" end the run; others get 4 s.
        waited = {"ms": 0}

        def poll() -> None:
            waited["ms"] += 200
            if page.done or (waited["ms"] >= 4000 and "CHECK DONE" not in script) or waited["ms"] >= timeout_ms:
                if not page.done and "CHECK DONE" in script:
                    print("CHECK FAIL timeout: script never finished", flush=True)
                snap()
            else:
                QTimer.singleShot(200, poll)

        QTimer.singleShot(200, poll)

    view.loadFinished.connect(loaded)
    app.exec()


if __name__ == "__main__":
    main()

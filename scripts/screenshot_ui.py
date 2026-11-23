"""Dev tool: render a UI page offscreen with Qt WebEngine and save a PNG.

Serves the page over HTTP rooted at the page's own folder, exactly like pywebview
does in the app, so paths that break in the app also break here.

Usage: uv run python scripts/screenshot_ui.py <page.html> <out.png> [query] [WxH]
"""

import functools
import http.server
import os
import sys
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


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

    view.loadFinished.connect(lambda _ok: QTimer.singleShot(1500, snap))
    app.exec()


if __name__ == "__main__":
    main()

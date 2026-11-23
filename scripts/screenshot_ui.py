"""Dev tool: render a UI page offscreen with Qt WebEngine and save a PNG.

Usage: uv run python scripts/screenshot_ui.py <page.html> <out.png> [query] [WxH]
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def main() -> None:
    page, out = sys.argv[1], sys.argv[2]
    query = sys.argv[3] if len(sys.argv) > 3 else ""
    w, h = map(int, (sys.argv[4] if len(sys.argv) > 4 else "1280x800").split("x"))
    app = QApplication([])
    view = QWebEngineView()
    view.resize(w, h)
    url = QUrl.fromLocalFile(os.path.abspath(page))
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

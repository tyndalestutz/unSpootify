"""Shrink a Linux PyInstaller build: drop Qt libraries nothing loads, QML, and translations.

Keeps the transitive dependencies (via ldd) of the PySide6 modules we import, every Qt plugin,
and the QtWebEngineProcess helper. Usage: python scripts/prune_qt.py dist/unspootify
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

USED_MODULES = ["QtCore", "QtGui", "QtWidgets", "QtNetwork", "QtWebEngineCore", "QtWebEngineWidgets",
                "QtWebChannel", "QtPrintSupport", "QtOpenGL"]


def deps(binary: Path, libdir: Path) -> set[str]:
    out = subprocess.run(["ldd", str(binary)], capture_output=True, text=True,
                         env={**os.environ, "LD_LIBRARY_PATH": str(libdir)}).stdout
    return set(re.findall(r"(libQt6[\w.]+\.so\.6)", out))


def main(dist: Path) -> None:
    qt = dist / "_internal" / "PySide6" / "Qt"
    lib = qt / "lib"
    before = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    roots = [dist / "_internal" / "PySide6" / f"{m}.abi3.so" for m in USED_MODULES]
    roots += [p for p in (qt / "plugins").rglob("*.so")]
    roots += [qt / "libexec" / "QtWebEngineProcess"]
    keep: set[str] = set()
    todo = [r for r in roots if r.exists()]
    while todo:
        found = deps(todo.pop(), lib) - keep
        keep |= found
        todo += [lib / f for f in found if (lib / f).exists()]
    for f in lib.glob("libQt6*.so*"):
        if f.name not in keep:
            f.unlink()
    # unused PySide6 bindings
    for f in (dist / "_internal" / "PySide6").glob("Qt*.abi3.so"):
        if f.name.split(".")[0] not in USED_MODULES:
            f.unlink()
    shutil.rmtree(qt / "qml", ignore_errors=True)
    for f in (qt / "translations").glob("*.qm"):
        f.unlink()
    for f in (qt / "translations" / "qtwebengine_locales").glob("*.pak"):
        if f.name != "en-US.pak":
            f.unlink()
    after = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    print(f"pruned {dist}: {before / 1e6:.0f} MB -> {after / 1e6:.0f} MB ({len(keep)} Qt libs kept)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

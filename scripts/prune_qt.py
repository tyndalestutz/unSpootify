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

# Libraries that must come from the user's system, never the build machine: graphics drivers
# (GL/EGL/gbm/drm), X11/xcb/Wayland, GTK/GLib (system plugins load against them), fonts, sound,
# D-Bus, NSS. Bundling the build machine's copies (e.g. from an older Ubuntu) breaks on newer
# desktops ("Could not initialize GLX"). Mirrors the AppImage project's excludelist idea.
SYSTEM_LIBS = re.compile(
    r"^lib(GL|GLX|GLdispatch|EGL|OpenGL|gbm|drm|epoxy|X11|X11-xcb|Xau|Xdmcp|Xext|Xrender|Xi|Xfixes|Xrandr|Xcursor|"
    r"Xdamage|Xcomposite|Xinerama|Xtst|xshmfence|xcb.*|xkbcommon.*|wayland-.*|"
    r"gtk-3|gdk-3|gdk_pixbuf-2\.0|atk-1\.0|atk-bridge-2\.0|atspi|cairo|cairo-gobject|pango-1\.0|pangocairo-1\.0|"
    r"pangoft2-1\.0|harfbuzz|fribidi|thai|datrie|graphite2|pixman-1|"
    r"glib-2\.0|gio-2\.0|gobject-2\.0|gmodule-2\.0|gthread-2\.0|pcre2?-.*|pcre|ffi|mount|blkid|selinux|"
    r"fontconfig|freetype|expat|png16|brotli.*|asound|pulse.*|dbus-1|systemd|udev|cups|avahi-.*|"
    r"nss3|nssutil3|nspr4|plc4|plds4|smime3|ssl3|softokn3|freebl3|freeblpriv3|"
    r"gnutls|nettle|hogweed|gmp|idn2|unistring|tasn1|p11-kit|gcrypt|gpg-error|"
    r"krb5|krb5support|k5crypto|gssapi_krb5|com_err|keyutils|cap|bsd|md|lz4|"
    # the C++ runtime too: the system's graphics driver needs the system's (newer) libstdc++
    r"stdc\+\+|gcc_s)\.so"
)

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
    internal = dist / "_internal"
    for f in internal.iterdir():
        if SYSTEM_LIBS.match(f.name) or (f.is_symlink() and not f.exists()):
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

# PyInstaller spec for unSpootify (Linux onedir; macOS .app via BUNDLE in Phase 5).
# Build: uv run pyinstaller packaging/unspootify.spec --noconfirm   (after scripts/fetch_sockseek.sh)
#
# onedir, not onefile: sockseek calls the app back once per finished song (`unspootify finalize`),
# and a onefile build would unpack itself every time.
import platform
import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"
VERSION = re.search(r'__version__ = "([^"]+)"', (SRC / "unspootify" / "__init__.py").read_text()).group(1)
machine = platform.machine().lower()
if sys.platform == "darwin":
    KEY = "osx-arm64" if machine == "arm64" else "osx-x64"
else:
    KEY = "linux-x64"
SOCKSEEK = ROOT / "vendor" / "sockseek" / KEY / "sockseek"
if not SOCKSEEK.exists():
    raise SystemExit(f"missing {SOCKSEEK}: run scripts/fetch_sockseek.sh {KEY}")

from PyInstaller.utils.hooks import collect_submodules

hidden = ["unspootify.cli", "unspootify.finalize", "unspootify.backend", "unspootify.porttest",
          *collect_submodules("mutagen")]  # tag reading for file names (imported lazily)
if sys.platform.startswith("linux"):
    hidden += ["webview.platforms.qt", "qtpy", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore",
               "PySide6.QtWebChannel", "PySide6.QtNetwork"]
else:
    hidden += ["webview.platforms.cocoa"]

a = Analysis(
    [str(SRC / "unspootify" / "__main__.py")],  # dispatches `finalize`/`run` before any window code
    pathex=[str(SRC)],
    binaries=[(str(SOCKSEEK), f"vendor/sockseek/{KEY}")],  # as a binary: keeps the exec bit, signed on macOS
    datas=[(str(SRC / "unspootify" / "ui"), "unspootify/ui")],
    hiddenimports=hidden,
    excludes=["tkinter", "PyQt5", "PyQt6", "pytest", "IPython", "matplotlib", "numpy",
              "PySide6.Qt3DCore", "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
              "PySide6.QtMultimedia", "PySide6.QtBluetooth", "PySide6.QtSensors", "PySide6.QtSerialPort",
              "PySide6.QtPdf", "PySide6.QtDesigner", "PySide6.QtLocation", "PySide6.QtSpatialAudio"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="unspootify", console=False,
          icon=None if sys.platform == "darwin" else str(ROOT / "assets" / "icon" / "png" / "unspootify-256.png"))
coll = COLLECT(exe, a.binaries, a.datas, name="unspootify")

if sys.platform == "darwin":
    app = BUNDLE(coll, name="unSpootify.app", icon=str(ROOT / "assets" / "icon" / "unspootify.icns"),
                 bundle_identifier="app.unspootify", version=VERSION,
                 info_plist={"NSHighResolutionCapable": True, "LSMinimumSystemVersion": "12.0",
                             "CFBundleShortVersionString": VERSION, "CFBundleVersion": VERSION,
                             "LSApplicationCategoryType": "public.app-category.music"})

"""Where bundled files live, in development and inside a packaged app."""

import platform
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def _bundle_root() -> Path:
    # PyInstaller unpacks bundled data under sys._MEIPASS.
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen)
    return PACKAGE_DIR.parent.parent  # repo root in development


def platform_key() -> str:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        return "osx-arm64" if machine == "arm64" else "osx-x64"
    if sys.platform.startswith("linux") and machine in ("x86_64", "amd64"):
        return "linux-x64"
    raise RuntimeError(f"Unsupported platform: {sys.platform} {machine}")


def ui_dir() -> Path:
    return PACKAGE_DIR / "ui"


def sockseek_path() -> Path:
    return _bundle_root() / "vendor" / "sockseek" / platform_key() / "sockseek"

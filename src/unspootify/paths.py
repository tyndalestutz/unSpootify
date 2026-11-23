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


def app_data_dir() -> Path:
    """Where settings, playlists, the database and run files live (UNSPOOTIFY_HOME overrides)."""
    import os

    override = os.environ.get("UNSPOOTIFY_HOME")
    if override:
        base = Path(override)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "unSpootify"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "unSpootify"
    base.mkdir(parents=True, exist_ok=True)
    return base


def default_library() -> Path:
    return Path.home() / "Music" / "unSpootify"


def self_command() -> list[str]:
    """How to invoke this app's CLI from a child process (dev or packaged)."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "unspootify"]

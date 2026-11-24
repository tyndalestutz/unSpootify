"""Check GitHub for a newer release and install it in place.

Linux (AppImage): download the new AppImage next to the running one, verify it, swap the file, restart.
macOS (.app): download the .dmg, verify it, copy the new app out, and let a small helper replace the old
app after this one quits, then reopen it. Files the app downloads itself carry no quarantine flag, so
macOS doesn't ask for "Open Anyway" again.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable

from unspootify import __version__
from unspootify.contract import AppError

REPO = "tyndalestutz/unSpootify"
API = os.environ.get("UNSPOOTIFY_UPDATE_API", f"https://api.github.com/repos/{REPO}/releases/latest")
UA = {"User-Agent": "unSpootify-updater", "Accept": "application/vnd.github+json"}


def parse_version(v: str) -> tuple[int, ...]:
    """'v1.2.0' -> (1, 2, 0). Pre-release suffixes sort before the release ('1.2.0-rc.1' < '1.2.0')."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", v.strip())
    if not m:
        return (0, 0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if m.group(4) else 1)


def wanted_asset() -> str | None:
    """File-name suffix of this platform's download, or None when this copy can't update itself
    (e.g. running from source)."""
    if sys.platform.startswith("linux") and os.environ.get("APPIMAGE"):
        return "-x86_64.AppImage"
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        return "-arm64.dmg" if platform.machine().lower() == "arm64" else "-x86_64.dmg"
    return None


def _get(url: str, timeout: float = 20) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def check(current: str = __version__, fetch: Callable[[str], bytes] = _get) -> dict[str, Any]:
    """{available, current, latest, notes_url, installable, asset}. Never raises for network trouble."""
    try:
        rel = json.loads(fetch(API))
    except Exception as exc:  # offline, rate-limited, GitHub down
        return {"available": False, "current": current, "error": f"{type(exc).__name__}"}
    latest = str(rel.get("tag_name", "")).lstrip("v")
    newer = parse_version(latest) > parse_version(current) and not rel.get("prerelease")
    suffix = wanted_asset()
    assets = {a["name"]: a for a in rel.get("assets", [])}
    asset = next((a for n, a in assets.items() if suffix and n.endswith(suffix)), None)
    checksum = assets.get(f"{asset['name']}.sha256") if asset else None
    return {
        "available": newer, "current": current, "latest": latest, "notes_url": rel.get("html_url"),
        "installable": bool(newer and asset and checksum),
        "asset": {"name": asset["name"], "url": asset["browser_download_url"], "size": asset.get("size"),
                  "sha256_url": checksum["browser_download_url"]} if asset and checksum else None,
    }


def download(asset: dict[str, Any], dest: Path, fetch: Callable[[str], bytes] = _get) -> Path:
    """Download and verify against the release's .sha256 file."""
    expected = fetch(asset["sha256_url"]).decode().split()[0].lower()
    req = urllib.request.Request(asset["url"], headers=UA) if fetch is _get else None
    digest = hashlib.sha256()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        if req is not None:
            with urllib.request.urlopen(req, timeout=60) as r:
                while chunk := r.read(1 << 20):
                    digest.update(chunk)
                    out.write(chunk)
        else:
            data = fetch(asset["url"])
            digest.update(data)
            out.write(data)
    if digest.hexdigest() != expected:
        dest.unlink(missing_ok=True)
        raise AppError("UPDATE_FAILED", "the download didn't match its checksum")
    return dest


def install_linux(asset: dict[str, Any], fetch: Callable[[str], bytes] = _get) -> Path:
    """Replace the running AppImage file (same path, so the menu/dock entry keeps working)."""
    target = Path(os.environ["APPIMAGE"])
    new = download(asset, target.with_name(f".{target.name}.update"), fetch)
    new.chmod(0o755)
    os.replace(new, target)  # the running copy keeps working until it quits
    return target


def install_macos(asset: dict[str, Any], pid: int, fetch: Callable[[str], bytes] = _get) -> Path:
    """Stage the new app; a helper swaps it in after this process exits and reopens it."""
    bundle = Path(sys.executable).resolve().parents[2]  # …/unSpootify.app/Contents/MacOS/unspootify
    if bundle.suffix != ".app":
        raise AppError("UPDATE_FAILED", "not running from an app bundle")
    if "AppTranslocation" in str(bundle) or not os.access(bundle.parent, os.W_OK):
        raise AppError("UPDATE_FAILED", "move unSpootify into your Applications folder first")
    work = Path(tempfile.mkdtemp(prefix="unspootify-update-"))
    dmg = download(asset, work / asset["name"], fetch)
    mnt = work / "mnt"
    mnt.mkdir()
    subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mnt), str(dmg)],
                   check=True, capture_output=True)
    try:
        staged = bundle.parent / f".{bundle.name}.update"
        shutil.rmtree(staged, ignore_errors=True)
        subprocess.run(["ditto", str(mnt / "unSpootify.app"), str(staged)], check=True, capture_output=True)
    finally:
        subprocess.run(["hdiutil", "detach", str(mnt), "-quiet"], check=False, capture_output=True)
    helper = work / "swap.sh"
    helper.write_text(
        "#!/bin/sh\n"
        f"while kill -0 {pid} 2>/dev/null; do sleep 0.5; done\n"
        f'rm -rf "{bundle}" && mv "{staged}" "{bundle}"\n'
        f'xattr -dr com.apple.quarantine "{bundle}" 2>/dev/null\n'
        f'open "{bundle}"\n'
        f'rm -rf "{work}"\n'
    )
    helper.chmod(0o755)
    subprocess.Popen(["/bin/sh", str(helper)], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return bundle


def relaunch_linux(target: Path) -> None:
    subprocess.Popen([str(target)], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

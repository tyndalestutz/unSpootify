import hashlib
import json

import pytest

from unspootify import updater


def release(tag, assets, prerelease=False):
    return json.dumps({"tag_name": tag, "prerelease": prerelease, "html_url": "https://x/rel", "assets": [
        {"name": n, "browser_download_url": f"https://dl/{n}", "size": 3} for n in assets]}).encode()


def test_versions():
    assert updater.parse_version("v1.2.0") > updater.parse_version("1.1.9")
    assert updater.parse_version("1.2.0") > updater.parse_version("1.2.0-rc.3")
    assert updater.parse_version("garbage") < updater.parse_version("0.0.1")


def test_check_picks_this_platforms_file(monkeypatch):
    monkeypatch.setattr(updater.sys, "platform", "linux")
    monkeypatch.setenv("APPIMAGE", "/x/unSpootify.AppImage")
    names = ["unSpootify-1.2.0-x86_64.AppImage", "unSpootify-1.2.0-x86_64.AppImage.sha256", "unSpootify-1.2.0-arm64.dmg"]
    r = updater.check("1.1.0", fetch=lambda url: release("v1.2.0", names))
    assert r["available"] and r["installable"] and r["asset"]["name"].endswith(".AppImage")
    r = updater.check("1.2.0", fetch=lambda url: release("v1.2.0", names))
    assert not r["available"]
    r = updater.check("1.1.0", fetch=lambda url: release("v1.3.0-rc.1", names, prerelease=True))
    assert not r["available"]
    assert updater.check("1.1.0", fetch=lambda url: (_ for _ in ()).throw(OSError()))["available"] is False


def test_running_from_source_never_installs(monkeypatch):
    monkeypatch.delenv("APPIMAGE", raising=False)
    monkeypatch.setattr(updater.sys, "platform", "linux")
    r = updater.check("1.1.0", fetch=lambda url: release("v9.0.0", ["unSpootify-9.0.0-x86_64.AppImage"]))
    assert r["available"] and not r["installable"]


def test_linux_swap_verifies_checksum(tmp_path, monkeypatch):
    current = tmp_path / "unSpootify-1.1.0-x86_64.AppImage"
    current.write_bytes(b"old")
    monkeypatch.setenv("APPIMAGE", str(current))
    new = b"new-appimage"
    files = {"https://dl/a": new, "https://dl/a.sha256": f"{hashlib.sha256(new).hexdigest()}  a\n".encode()}
    asset = {"url": "https://dl/a", "sha256_url": "https://dl/a.sha256", "name": "a"}
    assert updater.install_linux(asset, fetch=files.__getitem__) == current
    assert current.read_bytes() == new and current.stat().st_mode & 0o111
    files["https://dl/a.sha256"] = b"0" * 64
    with pytest.raises(updater.AppError):
        updater.install_linux(asset, fetch=files.__getitem__)
    assert current.read_bytes() == new  # untouched on a bad download

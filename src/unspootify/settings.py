"""User settings, saved as JSON in the app data folder (readable only by the user)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from unspootify.paths import app_data_dir, default_library

GRABS = ("songs", "albums", "artist")
FORMATS = ("mp3", "flac")
MODES = ("auto", "force")
LOOKS = ("phosphor", "jukebox")


@dataclass
class Options:
    grab: str = "songs"
    format: str = "mp3"
    mode: str = "auto"
    skip_existing: bool = True
    album_art: bool = True
    try_harder: bool = False


@dataclass
class Advanced:
    first_n: int | None = None
    skip_n: int | None = None
    fast: bool = False
    strict_title: bool = False
    min_bitrate: int | None = None
    listen_port: int | None = None


@dataclass
class Settings:
    username: str = ""
    password: str = ""
    library_path: str = field(default_factory=lambda: str(default_library()))
    look: str = "phosphor"
    options: Options = field(default_factory=Options)
    advanced: Advanced = field(default_factory=Advanced)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def public_dict(self) -> dict[str, Any]:
        """For logs: never include the password."""
        d = self.to_dict()
        d["password"] = "***" if self.password else ""
        return d


def _merge(dc: Any, data: dict[str, Any]) -> None:
    """Copy known keys from data onto a dataclass, validating types and choices."""
    for f in fields(dc):
        if f.name not in data:
            continue
        value, current = data[f.name], getattr(dc, f.name)
        if hasattr(current, "__dataclass_fields__"):
            if isinstance(value, dict):
                _merge(current, value)
            continue
        if isinstance(current, bool) or f.type in ("bool",):
            setattr(dc, f.name, bool(value))
        elif f.type in ("int | None",):
            setattr(dc, f.name, _int_or_none(value))
        else:
            setattr(dc, f.name, "" if value is None else str(value))
    _validate(dc)


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def _validate(dc: Any) -> None:
    if isinstance(dc, Options):
        if dc.grab not in GRABS:
            dc.grab = "songs"
        if dc.format not in FORMATS:
            dc.format = "mp3"
        if dc.mode not in MODES:
            dc.mode = "auto"
    if isinstance(dc, Settings) and dc.look not in LOOKS:
        dc.look = "phosphor"
    if isinstance(dc, Advanced) and dc.listen_port is not None and not 1024 <= dc.listen_port <= 65535:
        dc.listen_port = None


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "settings.json"
        self.settings = self._load()

    def _load(self) -> Settings:
        s = Settings()
        try:
            _merge(s, json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        return s

    def update(self, partial: dict[str, Any]) -> Settings:
        _merge(self.settings, partial)
        self.save()
        return self.settings

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.settings.to_dict(), indent=2), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

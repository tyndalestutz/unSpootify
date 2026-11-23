"""Names shared with the UI. Mirrors docs/ui-contract.md; change both together."""

from __future__ import annotations

from typing import Any

# Track states and failure reasons
QUEUED, SEARCHING, WAITING, DOWNLOADING, DONE, SKIPPED, FAILED = (
    "queued", "searching", "waiting", "downloading", "done", "skipped", "failed",
)
STATES = (QUEUED, SEARCHING, WAITING, DOWNLOADING, DONE, SKIPPED, FAILED)
TERMINAL = (DONE, SKIPPED, FAILED)
REASONS = ("not_found", "wrong_format", "cancelled", "error")

# Error codes -> (plain message, suggested action for the UI)
ERRORS: dict[str, tuple[str, str | None]] = {
    "LOGIN_FAILED": ("Soulseek didn't accept that username or password.", "focus_login"),
    "PORT_BLOCKED": ("This network seems to block Soulseek's port.", "test_connection"),
    "NO_NETWORK": ("Can't reach Soulseek. Check your internet connection.", "retry"),
    "FOLDER_MISSING": ("The music folder isn't there anymore. Is the drive unplugged?", "choose_folder"),
    "FOLDER_NOT_WRITABLE": ("Can't save into that folder. Pick another one.", "choose_folder"),
    "CSV_UNREADABLE": ("That file doesn't look like a playlist CSV.", "playlist_guide"),
    "CSV_NO_TRACKS": ("That CSV has no songs in it.", None),
    "SOCKSEEK_MISSING": ("Part of the app is missing. Please reinstall unSpootify.", None),
    "SOCKSEEK_CRASHED": ("The downloader stopped unexpectedly. Details has more.", "retry"),
    "NO_LOGIN": ("Enter a Soulseek username and password first.", "focus_login"),
    "ALREADY_RUNNING": ("A download is already running.", None),
}


class AppError(Exception):
    """An error the UI can show as-is."""

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in ERRORS:
            raise ValueError(f"unknown error code {code}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail

    def to_event(self) -> dict[str, Any]:
        message, action = ERRORS[self.code]
        return event("error", code=self.code, message=message, action=action, detail=self.detail)


def event(kind: str, **data: Any) -> dict[str, Any]:
    return {"type": kind, **data}

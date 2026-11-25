"""Headless commands. `run` prints contract events as JSON lines (the same stream the window gets)."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

COMMANDS = ("run", "finalize", "port-test")


def _run(a: argparse.Namespace) -> int:
    from unspootify.backend import Backend
    from unspootify.contract import AppError

    finished = threading.Event()
    last: dict = {}

    def emit(ev: dict) -> None:
        if ev["type"] == "log" and not a.verbose:
            return
        print(json.dumps(ev, ensure_ascii=False), flush=True)
        if ev["type"] == "run_finished":
            last.clear()
            last.update(ev)
            finished.set()

    backend = Backend(emit, root=a.home, mock_dir=a.mock_dir)
    partial: dict = {"options": {}, "advanced": {}}
    if a.library:
        partial["library_path"] = str(a.library)
    if a.user is not None:
        partial["username"] = a.user
    if a.password is not None:
        partial["password"] = a.password
    for key in ("grab", "format"):
        if getattr(a, key):
            partial["options"][key] = getattr(a, key)
    if a.force:
        partial["options"]["mode"] = "force"
    if a.no_skip:
        partial["options"]["skip_existing"] = False
    if a.convert_mp3:
        partial["advanced"]["convert_mp3"] = True
    backend.save_settings(partial)
    try:
        playlist = backend.import_csv_path(str(a.csv))
        if a.reset:
            backend.store.reset_all(playlist["id"])
        steps = [lambda: backend.start(playlist["id"])]
        while steps:
            finished.clear()
            result = steps.pop(0)()
            if result.get("nothing_to_do"):
                continue
            finished.wait()
            backend.runner.wait()
            if a.followup and last.get("missing_format"):
                a.followup = False
                steps.append(lambda: backend.force_followup(playlist["id"], True))
            elif a.retry and last.get("counts", {}).get("failed"):
                a.retry = False
                steps.append(lambda: backend.retry(playlist["id"]))
    except AppError as exc:
        print(json.dumps(exc.to_event(), ensure_ascii=False), flush=True)
        return 2
    finally:
        backend.close()
    return 0


def main(argv: list[str]) -> int:
    if argv[0] == "finalize":
        from unspootify.finalize import main as finalize_main

        return finalize_main(argv[1:])
    if argv[0] == "port-test":
        from unspootify.porttest import test_port

        print(json.dumps(test_port(int(argv[1]) if len(argv) > 1 else None)))
        return 0

    ap = argparse.ArgumentParser(prog="unspootify run", description="Download a playlist CSV without the window.")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--home", type=Path, help="app data folder (default: the normal one)")
    ap.add_argument("--library", type=Path)
    ap.add_argument("--mock-dir", type=Path, help="offline test: use this folder instead of Soulseek")
    ap.add_argument("--user")
    ap.add_argument("--pass", dest="password")
    ap.add_argument("--grab", choices=("songs", "albums", "artist"))
    ap.add_argument("--format", choices=("mp3", "flac"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--followup", action="store_true", help="after Force, get the misses in the other format")
    ap.add_argument("--retry", action="store_true", help="retry misses once with Try harder")
    ap.add_argument("--no-skip", action="store_true")
    ap.add_argument("--convert-mp3", action="store_true", help="experimental: lossless downloads -> MP3")
    ap.add_argument("--reset", action="store_true", help="forget previous results for this playlist")
    ap.add_argument("-v", "--verbose", action="store_true", help="include log lines")
    return _run(ap.parse_args(argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

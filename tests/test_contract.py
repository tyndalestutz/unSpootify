"""docs/ui-contract.md and the code must agree."""

import re

from unspootify.backend import Backend
from unspootify.contract import ERRORS, STATES
from conftest import ROOT

DOC = (ROOT / "docs" / "ui-contract.md").read_text()
WINDOW_ONLY = {"choose_folder", "import_csv", "import_csv_text", "open_url"}  # window layer (app.py)


def test_every_command_exists():
    commands = set(re.findall(r"^\| `(\w+)\(", DOC, re.M))
    assert commands, "no commands found in contract"
    for name in commands - WINDOW_ONLY:
        assert callable(getattr(Backend, name, None)), f"Backend.{name} missing"


def test_error_codes_match():
    documented = set(re.findall(r"^\| `([A-Z_]+)` \|", DOC, re.M))
    assert documented == set(ERRORS)


def test_states_match():
    assert all(f'"{s}"' in DOC for s in STATES)


def test_window_commands_exist():
    from unspootify.app import Api

    for name in WINDOW_ONLY | {"get_state", "save_settings", "get_tracks", "start", "stop", "retry", "force_followup", "test_port"}:
        assert callable(getattr(Api, name, None)), f"Api.{name} missing"


def test_js_backends_implement_every_command():
    ui = ROOT / "src" / "unspootify" / "ui" / "app"
    js = {"getState", "saveSettings", "chooseFolder", "importCsv", "importCsvText", "openUrl", "getTracks", "start",
          "stop", "retry", "forceFollowup", "testPort"}
    for f in ("real-backend.js", "fake-backend.js"):
        src = (ui / f).read_text()
        missing = [m for m in js if not re.search(rf"\b(async )?{m}\(", src)]
        assert not missing, f"{f} missing {missing}"

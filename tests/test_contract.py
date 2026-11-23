"""docs/ui-contract.md and the code must agree."""

import re

from unspootify.backend import Backend
from unspootify.contract import ERRORS, STATES
from conftest import ROOT

DOC = (ROOT / "docs" / "ui-contract.md").read_text()
WINDOW_ONLY = {"choose_folder", "import_csv"}  # native dialogs live in the window layer (Phase 3)


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

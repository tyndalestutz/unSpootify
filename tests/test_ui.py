"""Scripted UI checks in the real rendering engine, against the FakeBackend."""

import os
import subprocess
import sys

import pytest

from conftest import ROOT

UI = ROOT / "tests" / "ui"
CASES = [("controls.js", "normal"), ("followup.js", "normal"), ("errors.js", "loggedOut"), ("network.js", "network")]

try:
    import PySide6  # noqa: F401
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@pytest.mark.skipif(not HAVE_QT, reason="PySide6 not installed")
@pytest.mark.parametrize("script, scenario", CASES)
def test_ui_script(tmp_path, script, scenario):
    combined = tmp_path / script
    combined.write_text((UI / "harness.js").read_text() + "\n" + (UI / script).read_text())
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    for theme in ("phosphor", "jukebox"):
        out = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "screenshot_ui.py"), str(ROOT / "src/unspootify/ui/index.html"),
             str(tmp_path / f"{theme}.png"), f"fake&scn={scenario}&theme={theme}", "1120x790", str(combined)],
            capture_output=True, text=True, timeout=180, env=env,
        )
        lines = [l for l in out.stdout.splitlines() if l.startswith("CHECK")]
        js_errors = [l for l in out.stderr.splitlines() if l.startswith("JS ")]
        assert "CHECK DONE" in lines, out.stdout + out.stderr
        failures = [l for l in lines if l.startswith("CHECK FAIL")]
        assert not failures and not js_errors, f"[{theme}] " + "\n".join(failures + js_errors)

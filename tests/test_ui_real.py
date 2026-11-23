"""The real window with the real backend and real sockseek (offline mock share), driven by a script."""

import json
import os
import shutil
import subprocess
import sys

import pytest

from unspootify.paths import sockseek_path
from conftest import ROAD_TRIP, ROOT

pytestmark = pytest.mark.skipif(not sockseek_path().exists(), reason="run scripts/fetch_sockseek.sh first")


def test_real_window_end_to_end(tmp_path, mock_share):
    pytest.importorskip("PySide6")
    script = (ROOT / "tests/ui/harness.js").read_text() + "\n" + (ROOT / "tests/ui/real_e2e.js").read_text()
    script = script.replace("__CSV__", json.dumps(ROAD_TRIP.read_text())).replace("__LIB__", json.dumps(str(tmp_path / "lib")))
    path = tmp_path / "e2e.js"
    path.write_text(script)
    # pywebview's Qt window can't run on the offscreen platform: use a virtual display if available,
    # otherwise the real one (a window flashes up while the test runs).
    env = {**os.environ, "UNSPOOTIFY_HOME": str(tmp_path / "home")}
    env.pop("QT_QPA_PLATFORM", None)
    cmd = [sys.executable, "-m", "unspootify", "--offline-test", str(mock_share), "--ui-script", str(path)]
    if shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a", *cmd]
    elif not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        pytest.skip("needs a display or xvfb-run")
    out = subprocess.run(cmd,
                         capture_output=True, text=True, timeout=300, env=env, cwd=ROOT)
    lines = [l for l in out.stdout.splitlines() if l.startswith("CHECK")]
    assert "CHECK DONE" in lines, out.stdout[-3000:] + out.stderr[-3000:]
    failures = [l for l in lines if l.startswith("CHECK FAIL")]
    assert not failures, "\n".join(failures)
    assert (tmp_path / "lib" / "The Killers" / "Hot Fuss [MP3]" / "01. Mr. Brightside.mp3").exists()

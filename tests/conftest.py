import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
ROAD_TRIP = FIXTURES / "road_trip.csv"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never touch the real app data folder."""
    monkeypatch.setenv("UNSPOOTIFY_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture(scope="session")
def mock_share(tmp_path_factory):
    """Offline 'Soulseek share' for road_trip.csv: row 8 missing, row 4 also in FLAC, row 6 FLAC only."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    out = tmp_path_factory.mktemp("share")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_mock_library.py"), str(ROAD_TRIP), str(out),
                    "--missing", "8", "--flac", "4", "--flac-only", "6", "--album-extras", "2"],
                   check=True, capture_output=True)
    return out

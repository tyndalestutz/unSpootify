"""End-to-end through the real Backend and the real sockseek binary, offline (--mock-files-dir)."""

import threading
import time
from pathlib import Path

import pytest

from unspootify.backend import Backend
from unspootify.contract import AppError
from unspootify.paths import sockseek_path
from conftest import ROAD_TRIP

pytestmark = pytest.mark.skipif(not sockseek_path().exists(), reason="run scripts/fetch_sockseek.sh first")


class Recorder:
    def __init__(self):
        self.events, self.done = [], threading.Event()

    def __call__(self, ev):
        self.events.append(ev)
        if ev["type"] == "run_finished":
            self.done.set()

    def of(self, kind):
        return [e for e in self.events if e["type"] == kind]

    def wait(self, backend, timeout=120):
        assert self.done.wait(timeout), "run never finished"
        if backend.runner:
            backend.runner.wait(timeout)
        self.done.clear()
        return self.of("run_finished")[-1]


@pytest.fixture
def setup(tmp_path, mock_share):
    rec = Recorder()
    backend = Backend(rec, root=tmp_path / "home", mock_dir=mock_share)
    backend.save_settings({"library_path": str(tmp_path / "lib")})
    pid = backend.import_csv_path(str(ROAD_TRIP))["id"]
    yield backend, rec, pid, tmp_path / "lib"
    backend.close()


def states(backend, pid):
    return [t["state"] for t in backend.get_tracks(pid)]


def test_songs_run_skip_and_rerun(setup):
    backend, rec, pid, lib = setup
    backend.start(pid)
    fin = rec.wait(backend)
    assert states(backend, pid) == ["done"] * 7 + ["failed"]
    assert fin["counts"]["downloaded"] == 7 and fin["counts"]["failed"] == 1 and fin["counts"]["finished"]
    assert (lib / "The Killers" / "Hot Fuss [MP3]" / "01. Mr. Brightside.mp3").exists()
    track = backend.get_tracks(pid)[0]
    assert Path(track["path"]).exists() and track["format"] == "MP3"
    # every song row the UI shows got live updates
    assert {e["index"] for e in rec.of("track")} == set(range(8))
    assert rec.of("run_started")[0]["total"] == 8
    # Download again: nothing left to try
    assert backend.start(pid)["nothing_to_do"]
    # Forget results: sockseek's index skips what's already in the library
    backend.store.reset_all(pid)
    backend.start(pid)
    rec.wait(backend)
    assert states(backend, pid) == ["skipped"] * 7 + ["failed"]


def test_force_mp3_then_followup_flac(setup):
    backend, rec, pid, lib = setup
    backend.save_settings({"options": {"mode": "force", "format": "mp3"}})
    backend.start(pid)
    fin = rec.wait(backend)
    assert fin["missing_format"] == 2 and fin["force_format"] == "mp3"
    assert states(backend, pid)[5] == "failed"  # Hey Ya! only exists as FLAC
    backend.force_followup(pid, True)
    fin = rec.wait(backend)
    assert states(backend, pid)[5] == "done" and fin["missing_format"] is None
    assert (lib / "OutKast" / "Speakerboxxx-The Love Below [FLAC]" / "06. Hey Ya!.flac").exists()


def test_retry_tries_only_the_misses(setup):
    backend, rec, pid, _ = setup
    backend.start(pid)
    rec.wait(backend)
    started = len(rec.of("run_started"))
    backend.retry(pid)
    rec.wait(backend)
    assert len(rec.of("run_started")) == started + 1 and rec.of("run_started")[-1]["total"] == 1
    assert "-d" in backend.runner.plan.args


@pytest.mark.parametrize("grab", ["albums", "artist"])
def test_album_and_artist_modes(setup, grab):
    backend, rec, pid, lib = setup
    backend.save_settings({"options": {"grab": grab}})
    backend.start(pid)
    rec.wait(backend)
    assert states(backend, pid) == ["done"] * 7 + ["failed"]
    assert (lib / "The Killers" / "Hot Fuss [MP3]" / "02. Album Track 1.mp3").exists()


def test_stop_returns_unfinished_rows_to_waiting(tmp_path, mock_share):
    rec = Recorder()
    backend = Backend(rec, root=tmp_path / "home", mock_dir=mock_share, extra_args=["--mock-files-slow"])
    backend.save_settings({"library_path": str(tmp_path / "lib")})
    pid = backend.import_csv_path(str(ROAD_TRIP))["id"]
    backend.start(pid)
    deadline = time.time() + 30
    while time.time() < deadline and not any(e["state"] in ("searching", "downloading") for e in rec.of("track")):
        time.sleep(0.1)
    backend.stop()
    fin = rec.wait(backend)
    assert fin["stopped"] is True and not fin["counts"]["finished"]
    assert all(s in ("queued", "done", "skipped", "failed") for s in states(backend, pid))
    assert "queued" in states(backend, pid)
    backend.close()


def test_errors_are_contract_codes(tmp_path, mock_share):
    rec = Recorder()
    backend = Backend(rec, root=tmp_path / "home")  # real mode, no login
    pid = backend.import_csv_path(str(ROAD_TRIP))["id"]
    with pytest.raises(AppError) as e:
        backend.start(pid)
    assert e.value.code == "NO_LOGIN"
    backend.save_settings({"username": "u", "password": "p", "library_path": "/nonexistent-drive/Music"})
    with pytest.raises(AppError) as e:
        backend.start(pid)
    assert e.value.code == "FOLDER_MISSING"
    bad = tmp_path / "bad.csv"
    bad.write_text("nope\n1\n")
    with pytest.raises(AppError) as e:
        backend.import_csv_path(str(bad))
    assert e.value.code == "CSV_UNREADABLE"
    backend.close()

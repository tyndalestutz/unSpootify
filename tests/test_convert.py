import shutil
import subprocess
import threading

import pytest
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3

from unspootify import convert

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg makes the test files")


def make(path, *, rate=44100, secs=3, title="Song", track="1"):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=duration={secs}:sample_rate={rate}",
                    "-ac", "2", "-metadata", f"title={title}", "-metadata", f"track={track}",
                    "-metadata", "artist=Bänd", "-metadata", "album=LP", str(path)], check=True)
    return path


def test_should_convert():
    sc = convert.should_convert
    assert sc(enabled=True, mode="auto", preferred="mp3", formats=["FLAC"])
    assert not sc(enabled=False, mode="auto", preferred="mp3", formats=["FLAC"])
    assert not sc(enabled=True, mode="force", preferred="mp3", formats=["FLAC"])
    assert sc(enabled=True, mode="auto", preferred="flac", formats=["MP3"] * 3 + ["FLAC"])
    assert not sc(enabled=True, mode="auto", preferred="flac", formats=["MP3"] * 2 + ["FLAC"])
    assert convert.mp3_folder(convert.Path("/l/A/LP [FLAC]")).name == "LP [MP3]"
    assert convert.mp3_folder(convert.Path("/l/A/Odd")).name == "Odd"


def test_album_folder_converted_merged_and_tidied(tmp_path):
    old = tmp_path / "Bänd" / "LP [FLAC]"
    a = make(old / "01. Ä.flac", title="Ä", track="1")
    b = make(old / "02. B.flac", title="B", track="2")
    (old / "cover.jpg").write_bytes(b"\xff\xd8\xff\xe0img")
    (old / "01. Ä.lrc").write_text("[00:01]la")
    existing = tmp_path / "Bänd" / "LP [MP3]" / "02. B.mp3"  # already had this song as MP3
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"keep me")
    events = []
    res = convert.convert_all(convert.lossless_files([old]), threading.Event(), lambda n, t: events.append((n, t)))
    new = tmp_path / "Bänd" / "LP [MP3]"
    assert not old.exists()  # everything moved, empty folder removed
    assert sorted(p.name for p in new.iterdir()) == ["01. Ä.lrc", "01. Ä.mp3", "02. B.mp3", "cover.jpg"]
    assert existing.read_bytes() == b"keep me"
    mp3 = MP3(new / "01. Ä.mp3")
    assert abs(mp3.info.length - 3) < 1.5
    tags = MutagenFile(new / "01. Ä.mp3", easy=True)
    assert tags["title"] == ["Ä"] and tags["artist"] == ["Bänd"] and tags["tracknumber"][0].startswith("1")
    assert "APIC:Cover" in MP3(new / "01. Ä.mp3").tags  # cover embedded from cover.jpg
    assert events[0] == (0, 2) and events[-1] == (2, 2)
    assert {str(o) for o, _ in res.converted} == {str(a), str(b)}


def test_hires_left_alone_and_cancel_keeps_originals(tmp_path):
    old = tmp_path / "A" / "LP [FLAC]"
    hi = make(old / "01. Hi.flac", rate=96000)
    lo = make(old / "02. Lo.flac")
    stop = threading.Event()
    stop.set()
    res = convert.convert_all([lo], stop, lambda *_: None)
    assert lo.exists() and not res.converted
    res = convert.convert_all(convert.lossless_files([old]), threading.Event(), lambda *_: None)
    assert hi.exists() and [p for p, _ in res.skipped] == [hi]
    assert old.exists()  # still has music in it
    assert (tmp_path / "A" / "LP [MP3]" / "02. Lo.mp3").exists() and not lo.exists()
    assert not list((tmp_path / "A").rglob("*.part"))

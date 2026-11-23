import json
from pathlib import Path

from unspootify import finalize, porttest


def test_finalize_songs_moves_and_reports(tmp_path, capsys):
    stage, lib = tmp_path / "stage", tmp_path / "lib"
    stage.mkdir()
    f = stage / "1.mp3"
    f.write_text("audio")
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"mode": "songs", "library": str(lib), "stage": str(stage), "jobs": [
        {"snum": 1, "artist": "AC/DC", "album": "Back in Black", "title": "Hells Bells", "indexes": [0], "number": 1}]}))
    assert finalize.main([str(manifest), "1", str(f)]) == 0
    dest = lib / "AC-DC" / "Back in Black [MP3]" / "01. Hells Bells.mp3"
    assert dest.read_text() == "audio"
    assert capsys.readouterr().out.strip() == f"success;{dest}"


def test_finalize_albums_by_staged_path(tmp_path, capsys):
    stage, lib = tmp_path / "stage", tmp_path / "lib"
    f = stage / "The Killers" / "Hot Fuss" / "The Killers - Hot Fuss (2004) [FLAC]" / "03 - The Killers - Somebody Told Me.flac"
    f.parent.mkdir(parents=True)
    f.write_text("x")
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"mode": "albums", "library": str(lib), "stage": str(stage), "jobs": [
        {"snum": 1, "artist": "Modest Mouse", "album": "Good News", "title": "", "indexes": [1], "number": None},
        {"snum": 2, "artist": "The Killers", "album": "Hot Fuss", "title": "", "indexes": [0], "number": None}]}))
    finalize.main([str(manifest), "1", str(f)])
    assert (lib / "The Killers" / "Hot Fuss [FLAC]" / "03. Somebody Told Me.flac").exists()


def test_parse_helpers():
    assert finalize.parse_filename("03 - Artist - Song", "Artist") == (3, "Song")
    assert finalize.parse_filename("Song Only", "X") == (None, "Song Only")
    assert finalize.album_from_folder("The Killers - Hot Fuss (2004) [FLAC]", "The Killers") == "Hot Fuss"


def test_porttest_parse_and_flow():
    html = "IP: 1.2.3.4 Port: 50123/tcp OPEN. Great"
    assert porttest.parse(html, 50123) is True
    assert porttest.parse("Port: 50123/tcp CLOSED.", 50123) is False
    assert porttest.parse("nothing", 50123) is None
    ok = lambda *a, **k: type("C", (), {"close": lambda self: None})()
    r = porttest.test_port(50123, fetch=lambda url: "Port: 50123/tcp CLOSED.", connect=ok)
    assert r["open"] is False and r["server"] is True and 50000 <= r["suggested_port"] <= 59999
    def boom(*a, **k):
        raise OSError("down")
    r = porttest.test_port(50123, fetch=lambda url: (_ for _ in ()).throw(OSError()), connect=boom)
    assert r == {"open": None, "port": 50123, "server": False, "error": "NO_NETWORK"}
    assert porttest.test_port(80)["error"] == "BAD_PORT"

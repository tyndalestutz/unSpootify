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


def test_parse_filename_patterns():
    pf = finalize.parse_filename
    assert pf("Sink Into Me - 01 - Heartbeat", "Babeheaven", "Sink Into Me") == (1, "Heartbeat")
    assert pf("Σtella_Up and Away_08_The Truth Is", "Σtella", "Up and Away") == (8, "The Truth Is")
    assert pf("1-01 Hold Me (LUCASV remix)", "spill tab", "ANGIE") == (1, "Hold Me (LUCASV remix)")
    assert pf("1901", "Phoenix", "Wolfgang") == (None, "1901")


def test_finalize_album_uses_tags_and_handles_side_files(tmp_path, capsys):
    import shutil as sh
    import subprocess
    import pytest as _pt

    if not sh.which("ffmpeg"):
        _pt.skip("ffmpeg")
    stage, lib = tmp_path / "stage", tmp_path / "lib"
    folder = stage / "Band" / "LP" / "Band - LP (2004) [FLAC]"
    folder.mkdir(parents=True)
    song = folder / "weird_name_xyz.flac"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=1", "-c:a", "flac",
                    "-metadata", "title=Real Title", "-metadata", "track=7/12", str(song)], check=True)
    (folder / "front.jpg").write_bytes(b"img")
    (folder / "rip.nfo").write_text("x")
    (folder / "07 Real Title.lrc").write_text("[00:01]la")
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"mode": "albums", "library": str(lib), "stage": str(stage), "jobs": [
        {"snum": 1, "artist": "Band", "album": "LP", "title": "", "indexes": [0], "number": None}]}))
    for name in ("weird_name_xyz.flac", "front.jpg", "rip.nfo", "07 Real Title.lrc"):
        finalize.main([str(manifest), "1", str(folder / name)])
    album = lib / "Band" / "LP [FLAC]"
    assert [p.name for p in album.iterdir()] == ["07. Real Title.flac"]  # named from tags; side files left to sockseek
    assert (folder / "front.jpg").exists()  # untouched ("ignored")
    for name in ("front.jpg", "rip.nfo", "07 Real Title.lrc"):  # sockseek moves these in itself
        sh.move(str(folder / name), str(album / name))
    finalize.tidy_album_folder(album)
    assert sorted(p.name for p in album.iterdir()) == ["07. Real Title.flac", "07. Real Title.lrc", "cover.jpg"]

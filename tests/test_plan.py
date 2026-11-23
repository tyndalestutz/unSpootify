from pathlib import Path

import pytest

from unspootify.plan import build_args, make_jobs, pick_tracks, prepare
from unspootify.settings import Settings
from unspootify.store import Store
from conftest import ROAD_TRIP


def args_for(**opts):
    s = Settings(username="u", password="p", library_path="/lib")
    for k, v in opts.items():
        target = s.advanced if hasattr(s.advanced, k) else s.options
        setattr(target, k, v)
    return build_args(s, mode=opts.get("grab", "songs"), input_path=Path("in.csv"), stage=Path("st"),
                      index_path=Path("i.csv"), manifest_path=Path("m.json"))


@pytest.mark.parametrize("opts, present, absent", [
    ({}, ["--pref-format mp3", "--skip-music-dir /lib", "--progress-json", "--no-config"], ["-d", "-g", "--format ", "--user", "--pass"]),
    ({"format": "flac", "mode": "force"}, ["--format flac"], ["--pref-format"]),
    ({"skip_existing": False}, ["--no-skip-existing"], ["--skip-music-dir"]),
    ({"try_harder": True}, ["-d"], []),
    ({"fast": True, "strict_title": True}, ["--fast-search", "--strict-title"], []),
    ({"min_bitrate": 256, "listen_port": 50123}, ["--min-bitrate 256", "--listen-port 50123"], []),
    ({"grab": "albums", "album_art": True}, ["--album-art largest", "--input-type csv"], ["-g", "--skip-music-dir"]),
    ({"grab": "artist"}, ["-g", "--input-type list"], []),
    ({"grab": "songs", "album_art": True}, [], ["--album-art"]),
])
def test_option_mapping(opts, present, absent):
    args = args_for(**opts)
    joined = " " + " ".join(args) + " "
    for p in present:
        assert f" {p} " in joined, p
    for a in absent:
        assert a.strip() not in args if " " not in a.strip() else a not in joined, a


def test_finalize_hook_and_staging():
    args = args_for()
    hook = args[args.index("--on-complete") + 1]
    assert hook.startswith("when=success scope=track update-index -- ")
    assert '"finalize"' in hook and '{snum} "{path}"' in hook
    assert args[args.index("--name-format") + 1] == "{snum}"


def test_jobs_by_mode():
    store = Store()
    pid = store.import_csv(ROAD_TRIP)["id"]
    tracks = store.tracks(pid)
    assert [len(j.indexes) for j in make_jobs("songs", tracks)] == [1] * 8
    assert len(make_jobs("albums", tracks)) == 8
    assert {j.artist for j in make_jobs("artist", tracks)} == {t.artist for t in tracks}


def test_pick_tracks_limits_and_unfinished():
    store = Store()
    pid = store.import_csv(ROAD_TRIP)["id"]
    store.update_track(pid, 0, state="done")
    s = Settings()
    assert [t.index for t in pick_tracks(store.tracks(pid), s)] == list(range(1, 8))
    s.advanced.skip_n, s.advanced.first_n = 2, 3
    assert [t.index for t in pick_tracks(store.tracks(pid), s)] == [2, 3, 4]
    assert [t.index for t in pick_tracks(store.tracks(pid), Settings(), only=[0, 5])] == [0, 5]


def test_prepare_writes_inputs(tmp_path):
    store = Store()
    pid = store.import_csv(ROAD_TRIP)["id"]
    s = Settings(username="u", password="p", library_path=str(tmp_path / "lib"))
    plan = prepare(s, pid, store.tracks(pid), tmp_path / "run")
    lines = plan.input_path.read_text().splitlines()
    assert lines[0] == "Artist,Title,Album,Length" and lines[1] == "The Killers,Mr. Brightside,Hot Fuss,223"
    s.options.grab = "artist"
    plan = prepare(s, pid, store.tracks(pid), tmp_path / "run2")
    assert plan.input_path.read_text().splitlines()[0] == '"artist=The Killers"'


def test_login_goes_in_private_config_not_args(tmp_path):
    store = Store()
    pid = store.import_csv(ROAD_TRIP)["id"]
    s = Settings(username="me", password="s3cret-pass", library_path=str(tmp_path / "lib"))
    plan = prepare(s, pid, store.tracks(pid), tmp_path / "run")
    assert "s3cret-pass" not in " ".join(plan.args) and "--user" not in plan.args
    conf = tmp_path / "run" / "sockseek.conf"
    assert plan.args[plan.args.index("--config") + 1] == str(conf)
    assert conf.read_text() == "username = me\npassword = s3cret-pass\n"
    assert conf.stat().st_mode & 0o777 == 0o600


def test_search_cleanup():
    from unspootify.plan import primary_artist, search_title
    assert primary_artist("Matthew Herbert;Herbert;Momoko Gill") == "Matthew Herbert"
    assert search_title("In The Wee Small Hours Of The Morning - Remastered 1998") == "In The Wee Small Hours Of The Morning"
    assert search_title("My Rifle, My Pony And Me - Remastered") == "My Rifle, My Pony And Me"
    assert search_title("Song (2011 Remaster)") == "Song"
    assert search_title("Hold Me (feat. Someone)") == "Hold Me"
    assert search_title("Remastered") == "Remastered"
    assert search_title("Dear Mexico (Thank You for Joyce)") == "Dear Mexico (Thank You for Joyce)"


def test_flac_prefers_cd_quality():
    joined = " ".join(args_for(format="flac"))
    assert "--pref-max-bitdepth 16" in joined and "--fast-search" not in joined


def test_same_album_songs_are_searched_together():
    from unspootify.store import Track as T
    rows = [T(0, "A1", "Band", "LP", None), T(1, "B1", "Other", "EP", None), T(2, "A2", "Band;Guest", "LP", None)]
    jobs = make_jobs("songs", rows)
    assert [j.indexes[0] for j in jobs] == [0, 2, 1]
    assert "--pref-strict-album" in args_for()

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
    ({}, ["--pref-format mp3", "--skip-music-dir /lib", "--progress-json", "--user u", "--pass p"], ["-d", "-g", "--format "]),
    ({"format": "flac", "mode": "force"}, ["--format flac"], ["--pref-format"]),
    ({"skip_existing": False}, ["--no-skip-existing"], ["--skip-music-dir"]),
    ({"try_harder": True}, ["-d"], []),
    ({"fast": True, "strict_title": True}, ["--fast-search", "--strict-title"], []),
    ({"min_bitrate": 256, "listen_port": 50123}, ["--min-bitrate 256", "--listen-port 50123"], []),
    ({"grab": "albums", "album_art": True}, ["--album-art largest", "--input-type csv"], ["-g"]),
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

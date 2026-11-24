from pathlib import Path

from unspootify.plan import Job
from unspootify.runner import EventMapper, LogLine, Update
from conftest import FIXTURES

SONGS = [("The Killers", "Mr. Brightside", "Hot Fuss"), ("Modest Mouse", "Float On", "Good News for People Who Love Bad News"),
         ("Franz Ferdinand", "Take Me Out", "Franz Ferdinand"), ("Yeah Yeah Yeahs", "Maps", "Fever to Tell"),
         ("The White Stripes", "Seven Nation Army", "Elephant"), ("OutKast", "Hey Ya!", "Speakerboxxx/The Love Below"),
         ("The Postal Service", "Such Great Heights", "Give Up"), ("The Strokes", "Last Nite", "Is This It")]


def song_jobs():
    return [Job(i + 1, a, al, t, [i]) for i, (a, t, al) in enumerate(SONGS)]


def run(mapper, path):
    out = []
    for line in Path(path).read_text().splitlines():
        out += mapper.feed(line)
    return out


def test_songs_fixture_reaches_expected_states(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path)
    run(m, FIXTURES / "sockseek_songs.out")
    m.finish(stopped=False)
    states = [s.state for s in m.states]
    assert states == ["done"] * 7 + ["failed"]
    assert m.states[7].reason == "not_found"
    assert m.states[5].format == "FLAC" and m.states[0].format == "MP3"
    assert m.states[0].path == str(tmp_path / "The Killers" / "Hot Fuss [MP3]" / "Mr. Brightside.mp3")
    assert m.completed and m.fatal is None


def test_albums_fixture(tmp_path):
    albums = sorted({(a, al) for a, _, al in SONGS}, key=lambda x: [s[0] for s in SONGS].index(x[0]))
    jobs = [Job(i + 1, a, al, "", [i]) for i, (a, al) in enumerate(albums)]
    m = EventMapper("albums", jobs, tmp_path)
    out = run(m, FIXTURES / "sockseek_albums.out")
    m.finish(stopped=False)
    by_artist = {j.artist: s.state for j, s in zip(jobs, m.states)}
    assert by_artist["The Strokes"] == "failed"
    assert all(v == "done" for k, v in by_artist.items() if k != "The Strokes")
    assert any(isinstance(u, Update) and u.fields.get("state") == "downloading" for u in out)


def test_interleaved_json_and_text_on_one_line(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path)
    line = ('[006] SongJob: succeeded: Yeah  {"type":"track_state","data":{"artist":"Franz Ferdinand",'
            '"title":"Take Me Out","terminalOutcome":"Succeeded","extension":"mp3"}}')
    out = m.feed(line)
    assert m.states[2].state == "done"
    assert any(isinstance(o, LogLine) for o in out)


def test_progress_correlated_by_size(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path)
    m.feed('{"type":"download_start","data":{"artist":"The Killers","title":"Mr. Brightside","username":"u1","size":100,"extension":"mp3"}}')
    m.feed('{"type":"download_start","data":{"artist":"Modest Mouse","title":"Float On","username":"u2","size":200,"extension":"flac"}}')
    m.feed('{"type":"download_progress","data":{"jobId":"B","totalBytes":200,"percent":40}}')
    m.feed('{"type":"download_progress","data":{"jobId":"A","totalBytes":100,"percent":70}}')
    m.feed('{"type":"download_progress","data":{"jobId":"B","totalBytes":200,"percent":90}}')
    assert (m.states[0].pct, m.states[1].pct) == (70, 90)
    assert m.states[1].user == "u2" and m.states[1].format == "FLAC"


def test_never_moves_backwards_and_skips(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path)
    m.feed('{"type":"track_list","data":{"tracks":[{"artist":"The Killers","title":"Mr. Brightside","skipReason":"AlreadyExists"}]}}')
    m.feed('{"type":"search_start","data":{"artist":"The Killers","title":"Mr. Brightside"}}')
    assert m.states[0].state == "skipped"


def test_stop_and_crash_return_unfinished_to_queued(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path)
    m.feed('{"type":"search_start","data":{"artist":"The Killers","title":"Mr. Brightside"}}')
    m.finish(stopped=True)
    assert m.states[0].state == "queued"
    m2 = EventMapper("songs", song_jobs(), tmp_path)
    m2.feed("[error] Login failed: INVALIDPASS")
    m2.finish(stopped=False)  # never completed -> fatal, rows go back to Waiting
    assert m2.fatal == "LOGIN_FAILED" and m2.states[0].state == "queued"


def test_password_never_logged(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path, secret="hunter22")
    out = m.feed("[cli] args: --pass hunter22")
    assert all("hunter22" not in o.text for o in out if isinstance(o, LogLine))


def test_album_already_exists_is_skipped(tmp_path):
    jobs = [Job(1, "The Killers", "Hot Fuss", "", [0])]
    m = EventMapper("albums", jobs, tmp_path)
    m.feed("[003] AlbumJob: Already exists: The Killers - Hot Fuss: completed at /lib/x")
    assert m.states[0].state == "skipped"


def test_short_password_not_garbling_logs(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path, secret="e")
    out = m.feed("[003] SongJob: searching: The White Stripes - Seven Nation Army --pass e")
    text = "".join(o.bold + o.text for o in out if isinstance(o, LogLine))
    assert "Seven Nation Army" in text and "--pass ***" in text


def test_fatal_patterns_ignored_once_searching(tmp_path):
    m = EventMapper("songs", song_jobs(), tmp_path)
    m.feed('{"type":"search_start","data":{"artist":"The Killers","title":"Mr. Brightside"}}')
    m.feed("[peer] connection refused by 1.2.3.4")
    assert m.fatal is None


def test_crash_after_everything_settled(tmp_path):
    m = EventMapper("songs", song_jobs()[:1], tmp_path)
    m.feed('{"type":"track_state","data":{"artist":"The Killers","title":"Mr. Brightside","terminalOutcome":"Succeeded","extension":"mp3"}}')
    assert m.all_settled() and not m.completed
    m.finish(stopped=False)
    assert m.states[0].state == "done"


def test_album_progress_with_shortened_paths_and_audio_only_format(tmp_path):
    jobs = [Job(1, "Nick Leng", "Spirals", "", [0])]
    m = EventMapper("albums", jobs, tmp_path)
    m.feed("[003] AlbumJob: searching: Nick Leng - Spirals")
    for f in ("01 A.mp3", "02 B.mp3", "cover.jpg"):
        m.feed(f"[003] Album File: downloading: Nick Leng - Spirals: kula35\\..\\Nick Leng\\Nick Leng - Spirals\\{f}")
    assert m.states[0].format == "MP3"
    m.feed('{"type":"track_state","data":{"artist":"Nick Leng","title":"A","terminalOutcome":"Succeeded",'
           '"filename":"Music\\\\Nick Leng\\\\Nick Leng - Spirals\\\\01 A.mp3"}}')
    assert m.states[0].pct == 50 and m.states[0].format == "MP3"

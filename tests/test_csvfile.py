import pytest

from unspootify.contract import AppError
from unspootify.csvfile import read_tracks, write_tracks
from conftest import ROAD_TRIP


def test_exportify_columns_and_ms_lengths():
    tracks = read_tracks(ROAD_TRIP)
    assert len(tracks) == 8
    t = tracks[0]
    assert (t.title, t.artist, t.album, t.length_ms) == ("Mr. Brightside", "The Killers", "Hot Fuss", 222973)


def test_generic_columns_seconds_and_bom(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("﻿Title,Artist,Album,Length\nSong,Band,LP,3:05\nOther,Band,LP,200\n", encoding="utf-8")
    a, b = read_tracks(p)
    assert a.length_ms == 185000 and b.length_ms == 200000


def test_errors(tmp_path):
    empty = tmp_path / "e.csv"
    empty.write_text("Track Name,Artist Name(s)\n", encoding="utf-8")
    with pytest.raises(AppError) as e:
        read_tracks(empty)
    assert e.value.code == "CSV_NO_TRACKS"
    junk = tmp_path / "j.csv"
    junk.write_text("foo,bar\n1,2\n", encoding="utf-8")
    with pytest.raises(AppError) as e:
        read_tracks(junk)
    assert e.value.code == "CSV_UNREADABLE"
    binary = tmp_path / "b.csv"
    binary.write_bytes(b"\xff\xfe\x00\x00garbage")
    with pytest.raises(AppError) as e:
        read_tracks(binary)
    assert e.value.code == "CSV_UNREADABLE"


def test_album_rows_dedupe(tmp_path):
    tracks = read_tracks(ROAD_TRIP)
    out = tmp_path / "a.csv"
    write_tracks(out, tracks + tracks, albums_only=True)
    assert out.read_text().count("Hot Fuss") == 1

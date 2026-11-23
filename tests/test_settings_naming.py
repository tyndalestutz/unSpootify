from pathlib import Path

from unspootify.naming import clean, final_path, unique
from unspootify.settings import SettingsStore


def test_settings_roundtrip_and_validation(tmp_path):
    store = SettingsStore(tmp_path / "s.json")
    store.update({"username": "u", "password": "p", "options": {"grab": "albums", "format": "nope"},
                  "advanced": {"listen_port": "80", "first_n": "5", "min_bitrate": ""}})
    again = SettingsStore(tmp_path / "s.json").settings
    assert again.username == "u" and again.options.grab == "albums"
    assert again.options.format == "mp3"  # invalid choice falls back
    assert again.advanced.listen_port is None  # out of range
    assert again.advanced.first_n == 5 and again.advanced.min_bitrate is None
    assert (tmp_path / "s.json").stat().st_mode & 0o777 == 0o600
    assert "p" not in str(again.public_dict()["password"])


def test_clean_names():
    assert clean('AC/DC: "Back" in <Black>?') == "AC-DC Back in Black"
    assert clean("   ...  ") == "Unknown"
    assert len(clean("x" * 500)) == 120


def test_final_path(tmp_path):
    p = final_path(tmp_path, artist="The Killers", album="Hot Fuss", title="Mr. Brightside", number=1, ext=".MP3")
    assert p == tmp_path / "The Killers" / "Hot Fuss [MP3]" / "01. Mr. Brightside.mp3"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    assert unique(p).name == "01. Mr. Brightside (2).mp3"
    assert final_path(Path("/m"), artist="", album="", title="", number=None, ext="flac").parts[-3:] == (
        "Unknown Artist", "Unknown Album [FLAC]", "Untitled.flac")

from unspootify.paths import platform_key, sockseek_path, ui_dir


def test_ui_page_exists():
    assert (ui_dir() / "index.html").is_file()


def test_sockseek_path_is_platform_specific():
    assert sockseek_path().parent.name == platform_key()
    assert sockseek_path().name == "sockseek"

import json
import os

from src.config import (
    APP_VERSION, THEME, get_icon, get_provider_name, get_provider_id,
    load_config, save_config, get_config_dir, get_config_path,
    add_search_history,
)


def test_app_version():
    assert APP_VERSION == "0.1.0"


def test_theme_has_required_keys():
    for key in ("fg", "dim", "border", "primary", "accent", "success", "warning", "error"):
        assert key in THEME


def test_get_icon_nerd_fonts_disabled(monkeypatch):
    monkeypatch.setattr("src.config._nerd_fonts_enabled", False)
    icon = get_icon("search")
    assert icon == "⚲ "


def test_get_icon_nerd_fonts_enabled(monkeypatch):
    monkeypatch.setattr("src.config._nerd_fonts_enabled", True)
    icon = get_icon("search")
    assert icon == " "


def test_get_provider_name():
    assert get_provider_name(0) == "Anime3rb"
    assert get_provider_name(1) == "WitAnime"
    assert get_provider_name(2) == "Anineko"
    assert get_provider_name(999) == "Unknown"


def test_get_provider_id():
    assert get_provider_id("Anime3rb") == 0
    assert get_provider_id("WitAnime") == 1
    assert get_provider_id("Anineko") == 2
    assert get_provider_id("NonExistent") == 0


def test_load_config_creates_defaults(config_path_override, monkeypatch):
    monkeypatch.setattr("src.config._config_cache", None)
    cfg = load_config()
    assert cfg["preferred_player"] == "auto"
    assert cfg["default_quality"] == "auto"
    assert cfg["history_tracking"] is True
    assert cfg["fullscreen"] is True
    assert cfg["nerd_fonts"] is False
    assert cfg["scraping_method"] == "auto"
    assert cfg["enabled_sources"] == [0, 1]
    assert cfg["search_history"] == []


def test_load_config_reads_existing(config_path_override, monkeypatch):
    custom_cfg = {"preferred_player": "mpv", "default_quality": "1080p"}
    with open(config_path_override + "/config.json", "w") as f:
        json.dump(custom_cfg, f)
    monkeypatch.setattr("src.config._config_cache", None)
    cfg = load_config()
    assert cfg["preferred_player"] == "mpv"
    assert cfg["default_quality"] == "1080p"
    assert cfg["history_tracking"] is True  # default fallback


def test_save_config(config_path_override):
    cfg = {"preferred_player": "vlc", "test_key": "test_value"}
    save_config(cfg)
    with open(config_path_override + "/config.json") as f:
        saved = json.load(f)
    assert saved["preferred_player"] == "vlc"
    assert saved["test_key"] == "test_value"


def test_add_search_history(config_path_override, monkeypatch):
    monkeypatch.setattr("src.config._config_cache", None)
    add_search_history("naruto")
    cfg = load_config()
    assert "naruto" in cfg["search_history"]


def test_get_config_dir_creates_path(config_path_override, monkeypatch):
    monkeypatch.setattr("src.config.read_custom_config_dir", lambda: None)
    monkeypatch.setattr("src.config.get_default_config_dir", lambda: config_path_override)
    d = get_config_dir()
    assert os.path.exists(d)


def test_get_config_path(config_path_override, monkeypatch):
    monkeypatch.setattr("src.config.get_config_dir", lambda: config_path_override)
    path = get_config_path()
    assert path == os.path.join(config_path_override, "config.json")

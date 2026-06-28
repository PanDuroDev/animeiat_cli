import os

import pytest

from src.playback.discovery import (
    find_vlc, find_mpv, find_iina, find_celluloid, find_haruna,
    get_cached_players, clear_player_cache,
)


def test_find_vlc_not_found(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    monkeypatch.setattr("os.name", "linux")
    result = find_vlc()
    assert result is None


def test_find_mpv_not_found(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    monkeypatch.setattr("os.name", "linux")
    result = find_mpv()
    assert result is None


def test_find_iina_not_found(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    monkeypatch.setattr("sys.platform", "linux")
    result = find_iina()
    assert result is None


def test_find_celluloid_not_found(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    result = find_celluloid()
    assert result is None


def test_find_haruna_not_found(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    result = find_haruna()
    assert result is None


def test_get_cached_players(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    monkeypatch.setattr("os.name", "linux")
    monkeypatch.setattr("sys.platform", "linux")
    players = get_cached_players()
    assert players == {"vlc": None, "mpv": None, "iina": None, "celluloid": None, "haruna": None}
    clear_player_cache()


def test_find_vlc_with_shutil(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/vlc" if x == "vlc" else None)
    result = find_vlc()
    assert result == "/usr/bin/vlc"


def test_find_mpv_with_shutil(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/mpv" if x in ("mpv", "mpvnet") else None)
    result = find_mpv()
    assert result == "/usr/bin/mpv"


def test_find_vlc_windows_common_paths(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setattr("os.path.exists", lambda p: "vlc.exe" in p)
    vlc_path = find_vlc()
    assert vlc_path is not None
    assert vlc_path.endswith("vlc.exe")

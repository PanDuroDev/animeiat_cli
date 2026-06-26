import os

import pytest

from src.db import (
    init_db, get_db_path, get_db_connection,
    save_episode_progress, get_episode_progress,
    toggle_favorite_state, is_favorite_slug,
    add_download_entry, get_downloads, remove_download_entry, update_download_status,
    add_watch_history, get_watch_history,
    save_account_token, get_account_token, remove_account,
    get_all_episode_progress,
    clean_slug_for_search,
)


@pytest.fixture
def db(clean_db, db_path_override):
    return db_path_override


def test_init_db_creates_tables(db):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cursor.fetchall()}
    expected = {"favorites", "shows", "watched_episodes", "downloads", "stream_cache", "episode_progress", "accounts"}
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"
    conn.close()


def test_get_db_path(db):
    path = get_db_path()
    assert path.endswith(".db")


def test_save_and_get_episode_progress(db):
    save_episode_progress("naruto", 1, 300.0, 1440.0)
    result = get_episode_progress("naruto", 1)
    assert result is not None
    assert result["time_pos"] == 300.0
    assert result["duration"] == 1440.0


def test_get_episode_progress_not_found(db):
    result = get_episode_progress("nonexistent", 1)
    assert result is None


def test_get_all_episode_progress(db):
    save_episode_progress("naruto", 1, 100.0, 1440.0)
    save_episode_progress("naruto", 2, 200.0, 1440.0)
    results = get_all_episode_progress("naruto")
    assert len(results) == 2
    assert results[1]["time_pos"] == 100.0
    assert results[2]["time_pos"] == 200.0


def test_toggle_favorite_add(db):
    result = toggle_favorite_state("Naruto", "https://anime3rb.com/titles/naruto", False, "naruto")
    assert result is True
    assert is_favorite_slug("naruto") is True


def test_toggle_favorite_remove(db):
    toggle_favorite_state("Naruto", "https://anime3rb.com/titles/naruto", False, "naruto")
    result = toggle_favorite_state("Naruto", "https://anime3rb.com/titles/naruto", False, "naruto")
    assert result is False
    assert is_favorite_slug("naruto") is False


def test_is_favorite_slug_not_found(db):
    assert is_favorite_slug("nonexistent") is False


def test_add_and_get_downloads(db):
    result = add_download_entry("naruto", 1, "https://example.com/stream.m3u8", "1080p")
    assert result is True
    downloads = get_downloads("naruto")
    assert len(downloads) == 1
    assert downloads[0]["episode"] == 1
    assert downloads[0]["slug"] == "naruto"


def test_get_downloads_all(db):
    add_download_entry("naruto", 1, "https://example.com/1.m3u8")
    add_download_entry("bleach", 1, "https://example.com/2.m3u8")
    all_dl = get_downloads()
    assert len(all_dl) == 2


def test_remove_download_entry(db):
    add_download_entry("naruto", 1, "https://example.com/stream.m3u8")
    result = remove_download_entry("naruto", 1)
    assert result is True
    downloads = get_downloads("naruto")
    assert len(downloads) == 0


def test_update_download_status(db):
    add_download_entry("naruto", 1, "https://example.com/stream.m3u8")
    result = update_download_status("naruto", 1, "completed", "/path/to/file.mp4")
    assert result is True
    downloads = get_downloads("naruto")
    assert downloads[0]["status"] == "completed"
    assert downloads[0]["file_path"] == "/path/to/file.mp4"


def test_add_and_get_watch_history(db):
    add_watch_history("naruto", 5, "Naruto", provider=0)
    history = get_watch_history("naruto", provider=0)
    assert history["last_watched"] == 5
    assert 5 in history["watched"]


def test_get_watch_history_not_found(db):
    history = get_watch_history("nonexistent")
    assert history["last_watched"] == 0
    assert history["watched"] == []


def test_save_and_get_account_token(db):
    result = save_account_token("anilist", "test_token", "client123", "refresh123", 3600)
    assert result is True
    token = get_account_token("anilist")
    assert token is not None
    assert token["token"] == "test_token"
    assert token["client_id"] == "client123"


def test_get_account_token_not_found(db):
    token = get_account_token("nonexistent")
    assert token is None


def test_remove_account(db):
    save_account_token("anilist", "test_token")
    result = remove_account("anilist")
    assert result is True
    token = get_account_token("anilist")
    assert token is None


def test_clean_slug_for_search(db):
    assert clean_slug_for_search("naruto-sub") == "naruto"
    assert clean_slug_for_search("naruto-shippuden-season") == "naruto shippuden"

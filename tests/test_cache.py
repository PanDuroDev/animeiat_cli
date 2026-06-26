import pytest

from src.cache import cache_stream_url, get_cached_stream_url, clear_stream_cache


@pytest.fixture(autouse=True)
def setup_cache_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test_cache.db"
    monkeypatch.setattr("src.db.get_db_path", lambda: str(db_path))
    from src.db import init_db
    init_db()
    yield
    for f in (db_path, tmp_path / "test_cache.db-wal", tmp_path / "test_cache.db-shm"):
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass


def test_cache_stream_url(setup_cache_db):
    cache_stream_url("naruto", 1, "https://example.com/stream.m3u8", "1080p", provider=0)
    result = get_cached_stream_url("naruto", 1, provider=0, max_age_hours=24)
    assert result is not None
    assert result["stream_url"] == "https://example.com/stream.m3u8"
    assert result["quality"] == "1080p"


def test_get_cached_stream_url_expired(setup_cache_db):
    cache_stream_url("naruto", 1, "https://example.com/stream.m3u8", provider=0)
    result = get_cached_stream_url("naruto", 1, provider=0, max_age_hours=0)
    assert result is None


def test_get_cached_stream_url_not_found(setup_cache_db):
    result = get_cached_stream_url("nonexistent", 1)
    assert result is None


def test_clear_stream_cache_all(setup_cache_db):
    cache_stream_url("naruto", 1, "https://example.com/1.m3u8", provider=0)
    cache_stream_url("bleach", 1, "https://example.com/2.m3u8", provider=0)
    clear_stream_cache(max_age_hours=0, provider=0)
    assert get_cached_stream_url("naruto", 1) is None
    assert get_cached_stream_url("bleach", 1) is None


def test_clear_stream_cache_by_slug(setup_cache_db):
    cache_stream_url("naruto", 1, "https://example.com/1.m3u8", provider=0)
    cache_stream_url("bleach", 1, "https://example.com/2.m3u8", provider=0)
    clear_stream_cache(slug="naruto", max_age_hours=0, provider=0)
    assert get_cached_stream_url("naruto", 1) is None
    assert get_cached_stream_url("bleach", 1) is not None

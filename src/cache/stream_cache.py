"""
Stream cache implementation — SQLite-backed storage for resolved stream URLs.
"""

import time

from src.db import get_db_connection, _db_write_lock
from src.providers import ProviderId

# Bump this when URL format changes to invalidate all old caches
CACHE_VERSION = 2


def _cache_key(slug, provider):
    return f"{slug}_{provider}_v{CACHE_VERSION}"


def cache_stream_url(slug, episode, stream_url, quality="", provider=ProviderId.ANIME3RB):
    with _db_write_lock:
        slug_key = _cache_key(slug, provider)
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO stream_cache (slug, episode, stream_url, fetched_at, quality) VALUES (?, ?, ?, ?, ?)",
                (slug_key, episode, stream_url, time.time(), quality)
            )
            conn.commit()
        except Exception as e:
            print(f"[animeiat-cli] Warning: cache_stream_url failed: {e}")
        finally:
            if conn:
                conn.close()


def get_cached_stream_url(slug, episode, provider=ProviderId.ANIME3RB, max_age_hours=24):
    slug_key = _cache_key(slug, provider)
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stream_url, fetched_at, quality FROM stream_cache WHERE slug = ? AND episode = ?",
            (slug_key, episode)
        )
        row = cursor.fetchone()
        if row:
            fetched_at = row[1]
            if time.time() - fetched_at < max_age_hours * 3600:
                return {"stream_url": row[0], "quality": row[2]}
    except Exception as e:
        print(f"[animeiat-cli] Warning: get_cached_stream_url failed: {e}")
    finally:
        if conn:
            conn.close()
    return None


def clear_stream_cache(slug=None, max_age_hours=24, provider=ProviderId.ANIME3RB):
    with _db_write_lock:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cutoff = time.time() - max_age_hours * 3600
            if slug:
                slug_key = _cache_key(slug, provider)
                cursor.execute("DELETE FROM stream_cache WHERE slug = ? AND fetched_at < ?", (slug_key, cutoff))
            elif provider:
                prov_pattern = f"%_{provider}_v{CACHE_VERSION}"
                cursor.execute("DELETE FROM stream_cache WHERE slug LIKE ? AND fetched_at < ?", (prov_pattern, cutoff))
            else:
                cursor.execute("DELETE FROM stream_cache WHERE fetched_at < ?", (cutoff,))
            conn.commit()
        except Exception as e:
            print(f"[animeiat-cli] Warning: clear_stream_cache failed: {e}")
        finally:
            if conn:
                conn.close()

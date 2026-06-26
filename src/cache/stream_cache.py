"""
Stream cache implementation — SQLite-backed storage for resolved stream URLs.
"""

import time

from src.db import get_db_connection

# Bump this when URL format changes to invalidate all old caches
CACHE_VERSION = 2


def _cache_key(slug, provider):
    return f"{slug}_{provider}_v{CACHE_VERSION}"


def cache_stream_url(slug, episode, stream_url, quality="", provider=0):
    slug_key = _cache_key(slug, provider)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO stream_cache (slug, episode, stream_url, fetched_at, quality) VALUES (?, ?, ?, ?, ?)",
            (slug_key, episode, stream_url, time.time(), quality)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[animeiat-cli] Warning: cache_stream_url failed: {e}")


def get_cached_stream_url(slug, episode, provider=0, max_age_hours=24):
    slug_key = _cache_key(slug, provider)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stream_url, fetched_at, quality FROM stream_cache WHERE slug = ? AND episode = ?",
            (slug_key, episode)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            fetched_at = row[1]
            if time.time() - fetched_at < max_age_hours * 3600:
                return {"stream_url": row[0], "quality": row[2]}
    except Exception as e:
        print(f"[animeiat-cli] Warning: get_cached_stream_url failed: {e}")
    return None


def clear_stream_cache(slug=None, max_age_hours=24, provider=0):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cutoff = time.time() - max_age_hours * 3600
        if slug:
            slug_key = _cache_key(slug, provider)
            cursor.execute("DELETE FROM stream_cache WHERE slug = ? AND fetched_at < ?", (slug_key, cutoff))
        else:
            cursor.execute("DELETE FROM stream_cache WHERE fetched_at < ?", (cutoff,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[animeiat-cli] Warning: clear_stream_cache failed: {e}")

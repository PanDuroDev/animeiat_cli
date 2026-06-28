# Changelog

## 0.3.0 (2026-06-28)

### Added
- `get_all_favorites()` — shared DB abstraction for favorites queries.
- Provider URL patterns for Continue Watching fallback (no favorites required).
- SSRF protection in `validate_url()` — blocks loopback, private IPs, unresolved hosts.
- Batch download support: `--download` flag now queues all episodes.
- UPSERT in `add_download_entry()` — preserves existing download status on re-enqueue.
- Progress debounce: saves only when position changes ≥2s or ≥1% of duration.
- `_merge_watch_tables()` migration — consolidates `shows` + `watched_episodes` into `episode_progress`.
- `test_utils.py` SSRF tests + `test_db.py` favorites/merge/UPSERT/provider tests.
- 8 new tests (71 total, all passing).

### Changed
- `validate_url()` now performs DNS resolution to reject private IP ranges.
- `add_download_entry()` uses `ON CONFLICT DO UPDATE` instead of `INSERT OR REPLACE`.
- `poll_mpv_progress()` debounces writes; SQLite I/O drops from ~1/s to ~0.1/s.
- `add_watch_history()` / `get_watch_history()` use `episode_progress` table exclusively.
- `_handle_continue_watching()` queries `episode_progress` directly (no `{slug}_{provider}` key parsing).
- `_handle_export()` derives `shows` + `watched_episodes` data from `episode_progress`.
- CLI `eps_to_scrape` uses all episodes when `--download` is set.
- Stream cache functions use `try/finally` for guaranteed connection close.

### Fixed
- `except Exception` → `except sqlite3.Error` in all DB functions (16 in `db/__init__.py`, 5 in `tui.py`).
- `extract_slug()` no longer returns arbitrary path segments for unknown domains.
- `add_download_entry()` no longer resets `status`/`file_path`/`downloaded_at` on re-enqueue.
- `_handle_continue_watching()` now handles shows not in favorites (reconstructs URL from provider ID).
- Connection leaks in `stream_cache.py` — all three functions now use `finally` blocks.
- Old conflicting `src` package in `site-packages` removed (caused `ModuleNotFoundError` at entry point).

### Removed
- Redundant `shows` and `watched_episodes` tables (data merged into `episode_progress`).
- Generic path-split fallback in `extract_slug()`.
- `--download` single-episode limit — now processes all episodes in batch.

## 0.2.0 (2026-06-27)

### Added
- Synchronized Output protocol for flicker-free TUI rendering.
- Modular scraping architecture: `_cookies.py`, `_utils.py`, `_scraper.py`.
- SQLite WAL mode with thread-safe `get_db_connection()`.
- Playback progress stop tracking (`stop_progress_tracking()`).
- `extra_args` support for all media players.
- Interactive prompts in player installer (replaces silent `time.sleep()`).
- 63 unit tests across config, DB, cache, utils, and playback.

### Changed
- Replaced all emoji icons (`🔗`, `📁`, `⏳`) with monochrome Unicode symbols.
- All `live.update()` calls wrapped in synchronized output sequences.
- Hardcoded status symbols in scraper now use `get_icon()`.
- Reduced IPC poll interval from 2s to 1s; retry sleep from 0.5s to 0.3s.
- `check_for_update()` tuple unpacking fixed (was crashing settings).
- Windows console mode fixed (preserves existing flags).

### Removed
- Monolithic `scraping.py` — split into provider utilities.
- Root-level shim modules (`config.py`, `db.py`, `player.py`).
- Dead code: `link_anilist_flow`, `link_myanimelist_flow`, unused player vars.
- Blocking `time.sleep()` calls in discovery module (7 → 2 remaining).
- `_simple_read_line()` function and export.
- `PLAYBACK` state from `title_map`.
- Experimental `anime_cli.py` entry point, `tests/` directory (moved to `develop` branch).

## 0.1.0 (2025-06-23)

### Added
- Initial open-source release.
- Interactive TUI with Rich (search, browse, select episodes).
- Multi-provider support: Anime3rb, Witanime
- Browser cookie extraction (Chrome/Edge) for provider access.
- Player support: VLC, MPV, IINA (macOS), Celluloid, Haruna.
- Playback progress tracking with resume support.
- Stream URL caching with configurable TTL.
- Favorites and continue-watching lists.
- Download manager for queuing episodes.
- Settings: player, search sources, data sync, appearance, config.
- AniList and MyAnimeList account linking (scaffolding).
- Export/import watch history (JSON/CSV).
- Multi-platform: Windows, macOS, Linux.
- Docker support.

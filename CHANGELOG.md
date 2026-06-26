# Changelog

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

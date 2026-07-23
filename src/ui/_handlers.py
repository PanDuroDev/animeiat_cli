"""
TUI state handlers — main menu, search, URL input, favorites, episodes, etc.
"""
import os
import re
import shutil
import sqlite3
import sys
import time
from urllib.parse import urlparse, quote_plus

from src.config import (
    APP_VERSION, THEME, console, get_icon, get_provider_name,
    load_config, save_config, add_search_history,
)
from src.db import (
    get_db_connection, toggle_favorite_state, is_favorite_slug,
    add_watch_history, get_watch_history,
    get_account_token, remove_account,
    fetch_anime_metadata, fetch_anilist_user_list, fetch_mal_user_list,
    get_all_episode_progress, get_all_favorites,
    add_download_entry, get_downloads, remove_download_entry, update_download_status,
)
from src.downloader import enqueue_selected
from src.cache import cache_stream_url, get_cached_stream_url
from src.playback.discovery import (
    get_cached_players, clear_player_cache,
    find_vlc, find_mpv, find_iina, find_celluloid, find_haruna, install_player,
)
from src.playback.launch import (
    play_with_vlc, play_with_mpv, play_with_iina,
    play_with_celluloid, play_with_haruna,
)
from src.playback.progress import stop_progress_tracking, _episode_finished
from src.playback.discovery import _invalidate_player_cfg as invalidate_player_cfg
from src.log_util import log
from src.providers._utils import validate_url, extract_slug, detect_provider_from_url
from src.providers._cookies import get_preferred_cookies
from src.providers._scraper import fetch_episodes_list_async, scrape_multiple_streams_async
from src.providers import ProviderId, registry as provider_registry, search_providers_for_media

from ._core import _run_async, clear_screen, set_terminal_title, read_key
from ._widgets import (
    interactive_select, interactive_checklist, _show_track_selector,
    _centered_message, _centered_prompt, _centered_status,
    print_hotkey_guide, _show_help_panel, get_context_panel,
    check_for_update, TRACK_DEFAULTS,
)
from ._settings import (
    _settings_player, _settings_search_sources, _settings_data_sync,
    _settings_appearance, _settings_config_dir, _settings_about,
)
# Extracted from tui.py lines 1454-2608

def _handle_main_menu(current, stack, ctx):
    platforms = [
        f"{get_icon('search')}Search Anime",
        f"{get_icon('direct_url')}Enter URL Directly",
        f"{get_icon('favorite_on')}Favorites / Library",
        f"{get_icon('watch_history')}Continue Watching",
        f"{get_icon('download')}Download Manager",
        f"{get_icon('settings')}Settings / Configuration",
        f"{get_icon('exit')}Exit"
    ]
    try:
        fav_count = len(get_all_favorites())
    except sqlite3.Error as e:
        print(f"[animeiat-cli] Warning: favorites count DB query failed: {e}")
        fav_count = 0
    update_info = check_for_update(APP_VERSION)
    menu_metadata = {
        "pref_player": ctx["cfg"].get("preferred_player", "auto"),
        "default_quality": ctx["cfg"].get("default_quality", "auto"),
        "pref_browser": ctx["cfg"].get("preferred_browser", "auto"),
        "favorites_count": fav_count,
        "anilist_linked": get_account_token("anilist") is not None,
        "mal_linked": get_account_token("myanimelist") is not None,
        "update_info": update_info,
    }
    choice_idx, choice_opt = interactive_select(
        platforms, "Main Menu", context_type="main_menu", metadata=menu_metadata,
        player_name=ctx["player_name"], active_player=ctx["active_player"],
        pref_player=ctx["pref_player"], icons=ctx["layout_icons"]
    )
    if choice_idx == 6 or choice_idx == -1:
        return False
    if choice_idx == 0:
        stack.append({"state": "SEARCH_INPUT"})
    elif choice_idx == 1:
        stack.append({"state": "URL_INPUT"})
    elif choice_idx == 2:
        stack.append({"state": "FAVORITES"})
    elif choice_idx == 3:
        stack.append({"state": "CONTINUE_WATCHING"})
    elif choice_idx == 4:
        stack.append({"state": "DOWNLOAD_MANAGER"})
    elif choice_idx == 5:
        stack.append({"state": "SETTINGS"})
    return True


def _handle_search_input(current, stack, ctx):
    cfg = ctx["cfg"]
    search_hist = cfg.get("search_history", [])
    query = None
    if search_hist:
        hist_opts = ["[New Search Query]"] + search_hist
        sel_idx, sel_opt = interactive_select(hist_opts, "Recent Searches")
        if sel_idx == -1:
            stack.pop()
            return True
        if sel_idx == 0:
            query = _centered_prompt("Enter search query")
        else:
            query = sel_opt
    else:
        query = _centered_prompt("Enter search query")
    if not query:
        stack.pop()
        return True
    add_search_history(query)
    priorities = cfg.get("search_priorities", [ProviderId.ANIME3RB, ProviderId.WITANIME])
    active_providers = [p for p in provider_registry.get_all() if p.provider_id in priorities]
    source_names = [p.provider_name for p in active_providers]
    with _centered_status(f"Searching {', '.join(source_names)}...", icon="search"):
        try:
            from src.providers import search_all_providers as _search_all
            from src.config import PROVIDER_IDS as _PID
            raw = _run_async(_search_all(query, provider_ids=priorities, priorities=priorities))
            search_results = []
            seen = set()
            for pid, items in raw.items():
                pname = _PID.get(pid, f"Provider {pid}")
                for item in items:
                    title = item.get("title", "?")
                    url = item.get("url", "")
                    key = (pid, url)
                    if key not in seen:
                        seen.add(key)
                        search_results.append({
                            "title": title,
                            "url": url,
                            "provider_id": pid,
                            "provider_name": pname,
                        })
        except KeyboardInterrupt:
            search_results = []
            _centered_message("Search cancelled by user.", level="warn")
    if not search_results:
        _centered_message("No search results found.", level="warn")
        return True
    stack.append({
        "state": "SEARCH_RESULTS",
        "query": query,
        "search_results": search_results,
    })
    return True


def _try_open_episodes(stack, anime_url, is_witanime, slug, title_text, came_from_search, active_cookies):
    with _centered_status("Loading episodes list...", icon="watch"):
        try:
            eps, err = _run_async(fetch_episodes_list_async(anime_url, is_witanime, active_cookies))
        except KeyboardInterrupt:
            eps, err = [], "Action cancelled."
        except Exception as exc:
                eps, err = [], str(exc)
    if err:
        hint = ""
        err_lower = err.lower()
        if "timeout" in err_lower or "connect" in err_lower or "connection" in err_lower:
            hint = " (check your internet connection or try again later)"
        elif "cloudflare" in err_lower or "just a moment" in err_lower:
            hint = " (site is behind Cloudflare — try disabling IPv6 or using a different network)"
        elif "404" in err_lower or "not found" in err_lower:
            hint = " (anime page not found — it may have been removed or the URL is incorrect)"
        _centered_message(f"Error fetching episodes: {err}{hint}", level="error")
        return False
    if not eps:
        _centered_message("No episodes found.", level="warn")
        return False
    metadata = fetch_anime_metadata(title_text)
    stack.append({
        "state": "EPISODE_SELECTION",
        "eps": eps, "slug": slug, "anime_url": anime_url,
        "is_witanime": is_witanime, "title": title_text,
        "came_from_search": came_from_search, "auto_play": False,
        "anime_metadata": metadata
    })
    return True


def _browse_platform_list(token, fetch_func, platform_name, stack):
    with _centered_status(f"Fetching {platform_name} watch list...", icon="watch"):
        media_list = fetch_func(token)
    if not media_list:
        _centered_message(f"No entries found on {platform_name}.", level="warn")
        return False
    options = [entry["title"] for entry in media_list]
    idx, opt = interactive_select(options, f"{platform_name} Watch List")
    if idx == -1:
        return False
    selected = media_list[idx]
    title = selected["title"]
    with _centered_status(f"Searching providers for '{title}'...", icon="search"):
        result = search_providers_for_media(title)
    if not result:
        _centered_message(f"Could not find '{title}' on any supported provider.", level="warn")
        return False
    display_title, anime_url, is_witanime = result
    slug = extract_slug(anime_url)
    if not slug:
        _centered_message("Could not extract slug from URL.", level="warn")
        return False
    active_cookies = get_preferred_cookies()
    _try_open_episodes(stack, anime_url, is_witanime, slug, display_title, True, active_cookies)
    return True


def _handle_search_results(current, stack, ctx):
    query = current["query"]
    search_results = current["search_results"]
    options = [f"[{r['provider_name']}] {r['title']}" for r in search_results]
    results_metadata = {"search_query": query, "search_entries": search_results}
    sel_idx, sel_opt = interactive_select(
        options, f"Results for '{query}'", context_type="search_results",
        metadata=results_metadata, player_name=ctx["player_name"],
        active_player=ctx["active_player"], pref_player=ctx["pref_player"],
        icons=ctx["layout_icons"]
    )
    if sel_idx == -1:
        stack.pop()
        return True
    selected = search_results[sel_idx]
    title_text = selected["title"]
    anime_url = selected["url"]
    is_witanime = selected["provider_id"]
    chosen_name = selected["provider_name"]

    slug = extract_slug(anime_url)
    if not slug:
        slug = anime_url.strip("/").split("/")[-1] if anime_url.strip("/") else None
    if not slug:
        _centered_message(f"Could not extract slug from URL: {anime_url}.", level="error")
        return True
    _centered_message(f"[{chosen_name}] Target: {slug}", level="info")
    with _centered_status("Syncing cookies from browser profiles...", icon="watch"):
        active_cookies = get_preferred_cookies()
    if active_cookies:
        _centered_message(f"Synced {len(active_cookies)} cookies.", level="info")
    else:
        _centered_message("No cookies synced. Using clean session.", level="warn")
    _try_open_episodes(stack, anime_url, is_witanime, slug, title_text, True, active_cookies)
    return True


def _handle_url_input(current, stack, ctx):
    anime_url = current.get("prefilled_url") or _centered_prompt("Enter Anime URL (or press Enter/Esc to go back)")
    if not anime_url:
        stack.pop()
        return True
    valid, err_msg = validate_url(anime_url)
    if not valid:
        _centered_message(f"Invalid URL: {err_msg}.", level="error")
        return True
    anime_url = anime_url.strip()
    p = urlparse(anime_url)
    is_witanime = detect_provider_from_url(anime_url)

    if 'search_param=animes' in p.query:
        from urllib.parse import parse_qs
        params = parse_qs(p.query)
        search_query = params.get('s', [None])[0]
        if search_query:
            add_search_history(search_query)
            with _centered_status("Searching...", icon="search"):
                try:
                    cfg_s = load_config()
                    priorities = cfg_s.get("search_priorities", [0, 1])
                    from src.providers import search_all_providers as _search_all
                    from src.config import PROVIDER_IDS as _PID
                    raw = _run_async(_search_all(search_query, provider_ids=priorities, priorities=priorities))
                    search_results = []
                    seen = set()
                    for pid, items in raw.items():
                        pname = _PID.get(pid, f"Provider {pid}")
                        for item in items:
                            title = item.get("title", "?")
                            url = item.get("url", "")
                            key = (pid, url)
                            if key not in seen:
                                seen.add(key)
                                search_results.append({
                                    "title": title,
                                    "url": url,
                                    "provider_id": pid,
                                    "provider_name": pname,
                                })
                except KeyboardInterrupt:
                    search_results = []
                    _centered_message("Search cancelled.", level="warn")
            if not search_results:
                _centered_message("No results found.", level="warn")
                return True
            stack.append({"state": "SEARCH_RESULTS", "query": search_query, "search_results": search_results})
            return True
        else:
            query = _centered_prompt("Enter search query")
            if not query:
                return True
            current["prefilled_url"] = anime_url.split('?')[0] + f'?search_param=animes&s={quote_plus(query)}'
            return _handle_url_input(current, stack, ctx)

    direct_ep = None
    slug = None

    m = re.search(r'/episode/(.+)-[\u0600-\u06FF]+-(\d+)(?:/|$)', p.path)
    if m:
        direct_ep = int(m.group(2))
        slug = m.group(1).rstrip('-')
    if direct_ep is None:
        m = re.search(r'/episode[-\s]?(\d+)(?:/|$)', p.path)
        if m:
            direct_ep = int(m.group(1))
    if direct_ep is None and '/episode/' in p.path:
        nums = re.findall(r'/(\d+)/', p.path + '/')
        if nums:
            direct_ep = int(nums[-1])

    if direct_ep is not None:
        if slug is None:
            path_parts = p.path.strip("/").split("/")
            for part in path_parts:
                if part and not re.match(r'^\d+$', part) and part != "episode" and part != "anime" and "episode" not in part.lower():
                    slug = part
                    break
            if not slug:
                slug = extract_slug(anime_url)
            if not slug:
                slug = path_parts[-2] if len(path_parts) >= 2 else path_parts[-1]
        if not slug:
            _centered_message(f"Could not extract slug from URL: {anime_url}.", level="error")
            return True
        _centered_message(f"Direct episode URL detected \u2014 Episode {direct_ep}", level="info")
        with _centered_status("Syncing cookies...", icon="watch"):
            active_cookies = get_preferred_cookies()
        if active_cookies:
            _centered_message(f"Synced {len(active_cookies)} cookies.", level="info")
        else:
            _centered_message("No cookies synced. Using clean session.", level="warn")
        title_text = slug.replace('-', ' ').title()
        metadata = fetch_anime_metadata(title_text)
        single_eps = [{"episode": direct_ep, "page_url": anime_url}]
        stack.append({
            "state": "EPISODE_SELECTION",
            "eps": single_eps, "slug": slug, "anime_url": anime_url,
            "is_witanime": is_witanime, "title": title_text,
            "came_from_search": False, "auto_play": True,
            "anime_metadata": metadata
        })
        return True

    slug = extract_slug(anime_url)
    if slug:
        with _centered_status("Syncing cookies from browser profiles...", icon="watch"):
            active_cookies = get_preferred_cookies()
        if active_cookies:
            _centered_message(f"Synced {len(active_cookies)} cookies.", level="info")
        else:
            _centered_message("No cookies synced. Using clean session.", level="warn")
        title_text = slug.replace('-', ' ').title()
        _try_open_episodes(stack, anime_url, is_witanime, slug, title_text, False, active_cookies)
        return True

    _centered_message(f"Could not recognize URL format: {anime_url}.", level="error")
    return True


def _handle_favorites(current, stack, ctx):
    favs = get_all_favorites()
    if not favs:
        _centered_message("No favorites bookmarked yet.", level="warn")
        stack.pop()
        return True
    fav_slugs = [f["slug"] for f in favs]
    favorites_metadata = {"fav_slugs": fav_slugs}
    options = [f"{f['title']} ({get_provider_name(f.get('is_witanime', 0))})" for f in favs]
    sel_idx, sel_opt = interactive_select(
        options, "Bookmarked Anime", context_type="favorites", metadata=favorites_metadata,
        player_name=ctx["player_name"], active_player=ctx["active_player"],
        pref_player=ctx["pref_player"], icons=ctx["layout_icons"]
    )
    if sel_idx == -1:
        stack.pop()
        return True
    selected_fav = favs[sel_idx]
    anime_url = selected_fav["url"]
    is_witanime = int(selected_fav.get("is_witanime", 0))
    slug = selected_fav["slug"]
    with _centered_status("Syncing cookies...", icon="watch"):
        active_cookies = get_preferred_cookies()
    _try_open_episodes(stack, anime_url, is_witanime, slug, selected_fav["title"], False, active_cookies)
    return True


def _handle_settings(current, stack, ctx):
    cfg = ctx["cfg"]
    current_player = cfg.get("preferred_player", "auto")
    current_quality = cfg.get("default_quality", "auto")
    current_browser = cfg.get("preferred_browser", "auto")
    history_enabled = cfg.get("history_tracking", True)
    fullscreen_enabled = cfg.get("fullscreen", True)
    player_args = cfg.get("custom_player_args", "")

    while True:
        cat_opts = [
            "Player & Playback",
            "Search & Sources",
            "Data & Sync",
            "Appearance",
            "Config / Data Directory",
            "About animeiat-cli",
            "Go Back"
        ]
        cat_idx, _ = interactive_select(cat_opts, "Settings",
            player_name=ctx["player_name"], active_player=ctx["active_player"],
            pref_player=ctx["pref_player"], icons=ctx["layout_icons"])
        if cat_idx == -1 or cat_idx == 6:
            stack.pop()
            return True

        if cat_idx == 0:
            _settings_player(cfg, ctx)
        elif cat_idx == 1:
            _settings_search_sources(cfg)
        elif cat_idx == 2:
            if _settings_data_sync(cfg, stack):
                return True
        elif cat_idx == 3:
            _settings_appearance(cfg)
        elif cat_idx == 4:
            _settings_config_dir(cfg)
        elif cat_idx == 5:
            _settings_about(ctx)

    return True


def _handle_episode_selection(current, stack, ctx):
    eps = current["eps"]
    slug = current["slug"]
    anime_url = current["anime_url"]
    is_witanime = current["is_witanime"]
    anime_title = current.get("title", slug)
    active_player = ctx["active_player"]
    player_name = ctx["player_name"]
    pref_player = ctx["pref_player"]

    history_data = get_watch_history(slug, provider=is_witanime)
    last_watched = history_data.get("last_watched", 0)
    watched_list = history_data.get("watched", [])
    last_watched_idx = next((i for i, x in enumerate(eps) if x['episode'] == last_watched), -1)
    default_idx = 0
    if last_watched_idx != -1:
        default_idx = last_watched_idx + 1 if last_watched_idx + 1 < len(eps) else last_watched_idx
    progress_data = get_all_episode_progress(slug, provider=is_witanime)
    ep_options = []
    for x in eps:
        ep_num = x['episode']
        prog = progress_data.get(ep_num)
        bar_str = ""
        if prog and prog.get("duration", 0) > 0:
            pct = prog["time_pos"] / prog["duration"]
            pct = min(max(pct, 0), 1)
            filled = int(pct * 10)
            empty = 10 - filled
            bar_str = f" [dim {THEME['dim']}][[/dim {THEME['dim']}]{'█' * filled}{'░' * empty}[dim {THEME['dim']}]][/dim {THEME['dim']}] [bold {THEME['accent']}]{int(pct * 100)}%[/bold {THEME['accent']}]"
        if ep_num in watched_list:
            ep_options.append(f"Episode {ep_num}{bar_str} [dim {THEME['dim']}](watched ✓)[/dim {THEME['dim']}]")
        else:
            ep_options.append(f"Episode {ep_num}{bar_str}")
    fav_status = is_favorite_slug(slug)

    def on_toggle_fav():
        return toggle_favorite_state(anime_title, anime_url, is_witanime, slug)

    if current.get("auto_play", False) and len(eps) == 1:
        selected_indices = [0]
    else:
        ep_metadata = {
            "anime_title": anime_title,
            "provider": get_provider_name(is_witanime),
            "player_name": player_name,
            "anime_metadata": current.get("anime_metadata")
        }
        selected_indices = interactive_checklist(
            ep_options, title=f"Select episodes ({anime_title})",
            default_start_idx=default_idx, is_favorite=fav_status,
            on_toggle_favorite=on_toggle_fav, context_type="episode_selection",
            metadata=ep_metadata, player_name=player_name,
            active_player=active_player, pref_player=pref_player,
            icons=ctx["layout_icons"]
        )
    if not selected_indices:
        stack.pop()
        return True

    eps_to_scrape = [eps[i] for i in selected_indices]
    ep_numbers = [ep["episode"] for ep in eps_to_scrape]
    log("SELECT", f"episode_selection: slug={slug}, episodes={ep_numbers}, player={player_name}")

    uncached = []
    cached_urls = {}
    for ep in eps_to_scrape:
        ep_num = ep["episode"]
        cached = get_cached_stream_url(slug, ep_num, provider=is_witanime)
        if cached:
            cached_urls[ep_num] = cached["stream_url"]
        else:
            uncached.append(ep)

    if cached_urls:
        _centered_message(f"{len(cached_urls)} episode(s) loaded from stream cache.", level="info")

    if uncached:
        log("SCRAPE", f"scraping {len(uncached)} uncached episodes for slug={slug}")
        _centered_message(f"Scraping stream URLs for {len(uncached)} episodes...", level="info")
        active_cookies = get_preferred_cookies()
        try:
            results = _run_async(scrape_multiple_streams_async(uncached, is_witanime, active_cookies))
        except KeyboardInterrupt:
            _centered_message("Scraping cancelled by user.", level="warn")
            return True
        except Exception as exc:
            _centered_message(f"Scraping engine error: {exc}.", level="error")
            return True
        for ep in uncached:
            ep_num = ep["episode"]
            u_str = results.get(ep_num)
            if u_str:
                cache_stream_url(slug, ep_num, u_str, provider=is_witanime)
                cached_urls[ep_num] = u_str

    stream_urls = []
    for ep in eps_to_scrape:
        ep_num = ep["episode"]
        u_str = cached_urls.get(ep_num)
        if u_str:
            stream_urls.append(u_str)
    if not stream_urls:
        _centered_message("No stream URLs resolved (site may be blocking playback or episodes may be expired).", level="error")
        return True

    if not active_player:
        target_to_install = pref_player if pref_player in ("mpv", "vlc", "iina", "celluloid", "haruna") else "mpv"
        _centered_message(f"Preferred player {target_to_install.upper()} not installed. Downloading now...", level="warn")
        success_install = install_player(target_to_install)
        if success_install:
            clear_player_cache()
            nv = find_vlc(); nm = find_mpv(); ni = find_iina()
            nc = find_celluloid(); nh = find_haruna()
            if target_to_install == "mpv" and nm: active_player, player_name = nm, "MPV"
            elif target_to_install == "vlc" and nv: active_player, player_name = nv, "VLC"
            elif target_to_install == "iina" and ni: active_player, player_name = ni, "IINA"
            elif target_to_install == "celluloid" and nc: active_player, player_name = nc, "Celluloid"
            elif target_to_install == "haruna" and nh: active_player, player_name = nh, "Haruna"
        if not active_player:
            for p_name, find_func, display_name in [
                ("mpv", find_mpv, "MPV"), ("vlc", find_vlc, "VLC"),
                ("iina", find_iina, "IINA"), ("celluloid", find_celluloid, "Celluloid"),
                ("haruna", find_haruna, "Haruna"),
            ]:
                p_path = find_func()
                if p_path:
                    _centered_message(f"{target_to_install.upper()} install failed. Falling back to {display_name}.", level="warn")
                    active_player = p_path
                    player_name = display_name
                    break
        if not active_player:
            default_fallback = "mpv"
            if sys.platform == "darwin":
                default_fallback = "iina"
            _centered_message(f"Trying to install {default_fallback.upper()} as fallback...", level="info")
            if install_player(default_fallback):
                nv = find_vlc(); nm = find_mpv(); ni = find_iina()
                nc = find_celluloid(); nh = find_haruna()
                p_path = find_iina() if default_fallback == "iina" else find_mpv()
                if p_path:
                    active_player = p_path
                    player_name = default_fallback.upper()
        if not active_player:
            _centered_message("Player installation failed and no fallback player is available.", level="error")
            choice = ["Show Streaming Links Only", "Go Back"]
            c_idx, _ = interactive_select(choice, "How would you like to proceed?")
            if c_idx == 1 or c_idx == -1:
                return True

    track_info = dict(TRACK_DEFAULTS)
    if active_player:
        _centered_message(f"Press [bold]T[/bold] for tracks, [bold]D[/bold] to queue for download, or [bold]Enter[/bold] to play...", level="info")
        key = read_key()
        if key in ('t', 'T'):
            probe_url = stream_urls[0] if stream_urls else None
            result = _show_track_selector(track_info, stream_url=probe_url)
            if result is not None:
                track_info = result
        elif key in ('d', 'D'):
            queued = enqueue_selected(eps_to_scrape, cached_urls, slug)
            _centered_message(f"{queued} episode(s) queued for download.\nCheck 'Download Manager' in the menu for progress.", level="ok")
            return True
        elif key in (KEY_ESC, KEY_CTRL_C):
            return True

        print_hotkey_guide(player_name)
        track_args = []
        if player_name == "MPV":
            if track_info["audio_id"] is not None:
                track_args.append(f"--aid={track_info['audio_id']}")
            if track_info["sub_id"] is not None:
                track_args.append(f"--sid={track_info['sub_id']}")
            else:
                track_args.append("--sid=no")
        elif player_name == "VLC":
            if track_info["audio_id"] is not None:
                track_args.append(f":audio-track={track_info['audio_id']}")
            if track_info["sub_id"] is not None:
                track_args.append(f":sub-track={track_info['sub_id']}")
        auto_play = load_config().get("auto_play_next", False) and len(stream_urls) > 1

        def _launch_one(urls, ep_idx):
            ep = eps_to_scrape[ep_idx]
            if player_name == "MPV":
                return play_with_mpv(urls, slug=slug, ep=ep["episode"], extra_args=track_args, provider=is_witanime)
            elif player_name == "VLC":
                return play_with_vlc(urls, extra_args=track_args, slug=slug, ep=ep["episode"], provider=is_witanime)
            elif player_name == "IINA":
                return play_with_iina(urls, extra_args=track_args, slug=slug, ep=ep["episode"], provider=is_witanime)
            elif player_name == "Celluloid":
                return play_with_celluloid(urls, extra_args=track_args, slug=slug, ep=ep["episode"], provider=is_witanime)
            elif player_name == "Haruna":
                return play_with_haruna(urls, extra_args=track_args, slug=slug, ep=ep["episode"], provider=is_witanime)
            return False

        def _countdown_wait(sec=5):
            for remaining in range(sec, 0, -1):
                _centered_message(f"Next episode in {remaining}... Press any key to skip.", level="info")
                for _ in range(10):
                    if os.name == 'nt':
                        import msvcrt
                        if msvcrt.kbhit():
                            msvcrt.getwch()
                            return
                    else:
                        import select
                        if select.select([sys.stdin], [], [], 0)[0]:
                            sys.stdin.read(1)
                            return
                    time.sleep(0.1)

        log("PLAYER", f"launching {player_name}: slug={slug}, episode={eps_to_scrape[0]['episode']}, auto_play={auto_play}")
        launch_success = _launch_one(stream_urls[:1], 0)
        if launch_success:
            log("PLAYER", f"{player_name} started successfully")
            add_watch_history(slug, eps_to_scrape[0]["episode"], anime_title, provider=is_witanime)
            if auto_play:
                log("PLAYER", f"auto-play enabled: {len(stream_urls)} episodes queued")
                _centered_message(f"Auto-play enabled. {len(stream_urls)} episode(s) queued.", level="info")
                for idx in range(1, len(stream_urls)):
                    _episode_finished.clear()
                    if player_name != "MPV":
                        _episode_finished.wait(timeout=1800)
                    else:
                        _episode_finished.wait()
                    _countdown_wait(5)
                    _launch_one(stream_urls[idx:idx+1], idx)
                    add_watch_history(slug, eps_to_scrape[idx]["episode"], anime_title, provider=is_witanime)
            _centered_message(f"Playback started! {len(stream_urls)} episode(s) queued in {player_name}.", level="info")
        else:
            _centered_message(f"Failed to launch {player_name}. Showing links instead:", level="error")
            _centered_message("\n".join(f"{i+1}. {s_url}" for i, s_url in enumerate(stream_urls)), level="info")
    else:
        _centered_message("Streaming Links\n" + "\n".join(f"{i+1}. {s_url}" for i, s_url in enumerate(stream_urls)), level="info")

    _centered_message("Done. Returning to episode selection.", level="info")
    return True


def _handle_export():
    formats = ["JSON (.json)", "CSV (.csv)"]
    f_idx, f_opt = interactive_select(formats, "Export Format")
    if f_idx == -1:
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT slug, episode, time_pos, duration, provider FROM episode_progress ORDER BY slug, episode")
        progress = cursor.fetchall()

        conn.close()
    except sqlite3.Error as e:
        _centered_message(f"Database read error: {e}", level="error")
        return

    shows = {}
    watched = {}
    prog_dict = {}
    for slug, ep, tp, dur, _prov in progress:
        shows[slug] = max(shows.get(slug, 0), ep)
        watched.setdefault(slug, []).append(ep)
        prog_dict.setdefault(slug, []).append({"episode": ep, "time_pos": tp, "duration": dur})

    data = {
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": APP_VERSION,
        "shows": {k: {"last_watched": v} for k, v in shows.items()},
        "watched_episodes": watched,
        "episode_progress": prog_dict,
    }

    export_dir = get_config_dir()
    ts = time.strftime("%Y%m%d_%H%M%S")
    if f_idx == 0:
        fpath = os.path.join(export_dir, f"animeiat_cli_export_{ts}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _centered_message(f"Exported to: {fpath}", level="ok")
        return
    else:
        import csv
        fpath = os.path.join(export_dir, f"animeiat_cli_export_{ts}.csv")
        with open(fpath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["slug", "field", "episode", "value"])
            for slug, lw in shows.items():
                writer.writerow([slug, "last_watched", "", lw])
            for slug, ep in watched.items():
                writer.writerow([slug, "watched", ep, ""])
            for slug, ep, tp, dur in progress:
                writer.writerow([slug, "progress", ep, f"{tp}/{dur}"])
        _centered_message(f"Exported to: {fpath}", level="ok")


def _handle_download_manager(current, stack, ctx):
    from src.downloader import start_download, get_download_dir
    downloads = get_downloads()
    if not downloads:
        _centered_message("No downloads queued yet. Select episodes and choose 'D' to add them.", level="warn")
        stack.pop()
        return True

    status_emoji = {
        "completed": get_icon("check"),
        "downloading": get_icon("watch_history"),
        "pending": " ",
        "failed": get_icon("cross"),
    }

    options = []
    for d in downloads:
        icon = status_emoji.get(d["status"], get_icon("cross"))
        label = d["status"]
        if d["status"] == "completed":
            fname = os.path.basename(d.get("file_path", "")) if d.get("file_path") else ""
            label = f"done {fname}" if fname else "done"
        options.append(f"Ep {d['episode']} ({d['slug']}) [{icon} {label}]")

    idx, opt = interactive_select(options, "Download Manager (select to manage)")
    if idx == -1:
        stack.pop()
        return True

    selected = downloads[idx]
    if selected["status"] == "completed":
        fp = selected.get("file_path", "")
        _centered_message(
            f"Downloaded: {fp if fp else 'location unknown'}\nURL: {selected['stream_url']}",
            level="info"
        )
    elif selected["status"] == "failed":
        _centered_message(
            f"Episode {selected['episode']} — Download failed.\nURL: {selected['stream_url']}",
            level="error"
        )
        retry = _centered_prompt("Retry download? (y/N)")
        if retry and retry.lower() == 'y':
            start_download(selected["slug"], selected["episode"], selected["stream_url"], selected.get("quality", ""))
            _centered_message("Re-queued for download.", level="info")
    elif selected["status"] == "downloading":
        _centered_message(f"Still downloading episode {selected['episode']}...", level="info")
    else:
        _centered_message(
            f"Episode {selected['episode']} — Status: {selected['status']}\nURL: {selected['stream_url']}",
            level="info"
        )
        start_now = _centered_prompt("Start download now? (y/N)")
        if start_now and start_now.lower() == 'y':
            start_download(selected["slug"], selected["episode"], selected["stream_url"], selected.get("quality", ""))
            _centered_message("Download started.", level="info")

    remove = _centered_prompt("Remove this entry? (y/N)")
    if remove and remove.lower() == 'y':
        remove_download_entry(selected["slug"], selected["episode"])
        _centered_message("Entry removed.", level="info")

    _centered_message(f"Downloads folder: {get_download_dir()}", level="info")
    return True


def _handle_continue_watching(current, stack, ctx):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT slug, MAX(episode) as last_watched, provider
            FROM episode_progress
            GROUP BY slug, provider
            ORDER BY MAX(episode) DESC
            LIMIT 50
        """)
        rows = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        print(f"[animeiat-cli] Warning: continue watching query failed: {e}")
        rows = []
    if not rows:
        _centered_message("No watch history found. Watch some episodes first!", level="info")
        stack.pop()
        return True
    _PROVIDER_URL_PATTERNS = [
        "https://anime3rb.com/titles/{slug}",
        "https://witanime.bond/anime/{slug}",
    ]
    items = []
    for slug, last_watched, provider in rows:
        title = slug
        anime_url = ""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT title, url FROM favorites WHERE slug = ?", (slug,))
            fav_row = c.fetchone()
            if fav_row:
                title = fav_row[0] if fav_row[0] else slug
                anime_url = fav_row[1] if fav_row[1] else ""
            conn.close()
        except Exception as e:
            print(f"[animeiat-cli] Warning: continue watching fav lookup failed: {e}")
        if not anime_url and 0 <= provider < len(_PROVIDER_URL_PATTERNS):
            anime_url = _PROVIDER_URL_PATTERNS[provider].format(slug=slug)
        if anime_url:
            items.append({"slug": slug, "title": title, "url": anime_url, "is_witanime": provider, "last_watched": last_watched})
    if not items:
        _centered_message("No watch history found. Watch some episodes first!", level="info")
        stack.pop()
        return True
    opts = []
    for item in items:
        opts.append(f"Ep. {item['last_watched']} \u2014 {item['title']}")
    idx, _ = interactive_select(opts, "Continue Watching")
    if idx == -1:
        stack.pop()
        return True
    selected = items[idx]
    selected["prefilled_url"] = selected["url"]
    with _centered_status("Syncing cookies...", icon="watch"):
        active_cookies = get_preferred_cookies()
    _try_open_episodes(stack, selected["url"], selected["is_witanime"], selected["slug"], selected["title"], False, active_cookies)
    return True


_STATE_HANDLERS = {
    "MAIN_MENU": _handle_main_menu,
    "SEARCH_INPUT": _handle_search_input,
    "SEARCH_RESULTS": _handle_search_results,
    "URL_INPUT": _handle_url_input,
    "FAVORITES": _handle_favorites,
    "SETTINGS": _handle_settings,
    "EPISODE_SELECTION": _handle_episode_selection,
    "DOWNLOAD_MANAGER": _handle_download_manager,
    "CONTINUE_WATCHING": _handle_continue_watching,
}
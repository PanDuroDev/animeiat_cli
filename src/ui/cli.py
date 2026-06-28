"""
CLI entry points for animeiat-cli — argument parsing, non-interactive mode, and main().
"""

import argparse
import asyncio
import atexit
import json
import os
import sys
import traceback
from urllib.parse import urlparse

from src.config import (
    APP_VERSION, THEME, console, load_config, _config_cache,
)
from src.db import (
    get_db_path, init_db, migrate_json_to_sqlite,
    add_watch_history, add_download_entry,
)
from src.downloader import download_and_wait
from src.cache import get_cached_stream_url
from src.playback.discovery import (
    get_cached_players,
    find_vlc, find_mpv, find_iina, find_celluloid, find_haruna,
)
from src.playback.launch import (
    play_with_vlc, play_with_mpv, play_with_iina,
    play_with_celluloid, play_with_haruna,
)
from src.providers._utils import validate_url, extract_slug, detect_provider_from_url
from src.providers._cookies import get_preferred_cookies
from src.providers._scraper import fetch_episodes_list_async, scrape_multiple_streams_async

from src.ui.tui import (
    clear_screen, enter_alt_screen, exit_alt_screen, run_app,
)


@atexit.register
def _show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def run_noninteractive(initial_url, player_override=None, quality_override=None,
                       json_output=False, list_episodes=False, download_mode=False):
    def _emit(data_dict, exit_code=0):
        if json_output:
            print(json.dumps(data_dict, ensure_ascii=False, indent=2))
        else:
            for k, v in data_dict.items():
                if v is not None:
                    print(f"{k}: {v}")
        return exit_code

    valid, err_msg = validate_url(initial_url)
    if not valid:
        sys.exit(_emit({"error": f"Invalid URL \u2014 {err_msg}", "success": False}, exit_code=1))

    anime_url = initial_url.strip()
    p = urlparse(anime_url)
    is_witanime = detect_provider_from_url(anime_url)
    slug = extract_slug(anime_url)
    if not slug:
        sys.exit(_emit({"error": f"Could not extract slug from URL: {anime_url}", "success": False}, exit_code=1))

    if not json_output:
        print(f"Anime: {slug}")
        print("Syncing cookies...")
    active_cookies = get_preferred_cookies()
    if not json_output:
        print(f"  {'Synced' if active_cookies else 'No'} cookies {'synced' if active_cookies else 'found'}.")

    if not json_output:
        print("Fetching episodes list...")
    try:
        eps, err = asyncio.run(fetch_episodes_list_async(anime_url, is_witanime, active_cookies))
    except Exception as exc:
        sys.exit(_emit({"error": f"Fetch failed: {exc}", "success": False}, exit_code=1))

    if err:
        sys.exit(_emit({"error": f"Fetch failed: {err}", "success": False}, exit_code=1))

    if not eps:
        sys.exit(_emit({"error": "No episodes found.", "success": False}, exit_code=1))

    if list_episodes:
        ep_list = [{"episode": e["episode"], "page_url": e.get("page_url", "")} for e in eps]
        sys.exit(_emit({"slug": slug, "total_episodes": len(eps), "episodes": ep_list, "success": True}, exit_code=0))

    if not json_output:
        print(f"  Found {len(eps)} episode(s).")

    if quality_override:
        _config_cache["default_quality"] = quality_override

    eps_to_scrape = eps if download_mode else [eps[0]]
    if not json_output:
        msg = f"Scraping stream URLs for {len(eps_to_scrape)} episode(s)..."
        print(msg)
    try:
        results = asyncio.run(scrape_multiple_streams_async(eps_to_scrape, is_witanime, active_cookies))
    except KeyboardInterrupt:
        sys.exit(_emit({"error": "Scraping cancelled.", "success": False}, exit_code=1))
    except Exception as exc:
        sys.exit(_emit({"error": f"Scraping error: {exc}", "success": False}, exit_code=1))

    stream_urls = [results[ep["episode"]] for ep in eps_to_scrape if results.get(ep["episode"])]
    if not stream_urls:
        sys.exit(_emit({"error": "No stream URLs resolved.", "success": False}, exit_code=1))

    if download_mode:
        queued = 0
        for ep in eps_to_scrape:
            ep_num = ep["episode"]
            u_str = results.get(ep_num)
            if u_str:
                add_download_entry(slug, ep_num, u_str, quality=quality_override or "")
                print(f"  Downloading episode {ep_num}...")
                ok = download_and_wait(slug, ep_num, u_str, quality=quality_override or "")
                if ok:
                    queued += 1
                    print(f"  Episode {ep_num} downloaded.")
                else:
                    print(f"  Episode {ep_num} download failed.")
        sys.exit(_emit({"slug": slug, "queued": queued, "mode": "download", "success": queued > 0}, exit_code=0 if queued > 0 else 1))

    if json_output:
        sys.exit(_emit({"slug": slug, "episode": eps[0]["episode"], "stream_urls": stream_urls, "success": True, "mode": "stream"}, exit_code=0))

    if not json_output:
        print(f"  Resolved {len(stream_urls)} stream URL(s).")

    if player_override and player_override != "auto":
        pref_player = player_override
    else:
        cfg = load_config()
        pref_player = cfg.get("preferred_player", "auto")

    players = get_cached_players()
    active_player = None
    player_name = "None"

    if pref_player == "vlc" and players.get("vlc"):
        active_player = players["vlc"]
        player_name = "VLC"
    elif pref_player == "mpv" and players.get("mpv"):
        active_player = players["mpv"]
        player_name = "MPV"
    elif pref_player == "iina" and players.get("iina"):
        active_player = players["iina"]
        player_name = "IINA"
    elif pref_player == "celluloid" and players.get("celluloid"):
        active_player = players["celluloid"]
        player_name = "Celluloid"
    elif pref_player == "haruna" and players.get("haruna"):
        active_player = players["haruna"]
        player_name = "Haruna"
    else:
        if players.get("mpv"):
            active_player = players["mpv"]
            player_name = "MPV"
        elif players.get("vlc"):
            active_player = players["vlc"]
            player_name = "VLC"
        elif players.get("iina"):
            active_player = players["iina"]
            player_name = "IINA"
        elif players.get("celluloid"):
            active_player = players["celluloid"]
            player_name = "Celluloid"
        elif players.get("haruna"):
            active_player = players["haruna"]
            player_name = "Haruna"

    if not player_name or player_name == "None":
        for s in stream_urls:
            print(f"  {s}")
        sys.exit(_emit({"error": "No media player found.", "streams": stream_urls, "success": False}, exit_code=0))

    launch_success = False
    if player_name == "MPV":
        launch_success = play_with_mpv(stream_urls, slug=slug, ep=eps_to_scrape[0]["episode"], provider=is_witanime)
    elif player_name == "VLC":
        launch_success = play_with_vlc(stream_urls, slug=slug, ep=eps_to_scrape[0]["episode"], provider=is_witanime)
    elif player_name == "IINA":
        launch_success = play_with_iina(stream_urls, slug=slug, ep=eps_to_scrape[0]["episode"], provider=is_witanime)
    elif player_name == "Celluloid":
        launch_success = play_with_celluloid(stream_urls, slug=slug, ep=eps_to_scrape[0]["episode"], provider=is_witanime)
    elif player_name == "Haruna":
        launch_success = play_with_haruna(stream_urls, slug=slug, ep=eps_to_scrape[0]["episode"], provider=is_witanime)

    if launch_success:
        if not json_output:
            print(f"Playback started in {player_name} with {len(stream_urls)} stream(s).")
        for ep_num in [ep["episode"] for ep in eps_to_scrape]:
            add_watch_history(slug, ep_num, slug, provider=is_witanime)
        sys.exit(_emit({"success": True, "player": player_name, "streams": len(stream_urls)}, exit_code=0))
    else:
        for s in stream_urls:
            print(f"  {s}")
        sys.exit(_emit({"error": f"Failed to launch {player_name}.", "streams": stream_urls, "success": False}, exit_code=0))


def main():
    parser = argparse.ArgumentParser(
        prog="animeiat-cli",
        description="Anime CLI Player \u2014 Stream & Play anime from the terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  animeiat-cli                          Start the interactive TUI\n"
            "  animeiat-cli --url https://...        Open TUI with URL pre-filled\n"
            "  animeiat-cli --url https://... --no-tui  Play URL directly, no TUI\n"
            "  animeiat-cli --url ... --no-tui --json   Machine-readable JSON output\n"
            "  animeiat-cli --url ... --no-tui --list-episodes  List episodes and exit\n"
            "  animeiat-cli --url ... --no-tui --download       Queue episode for download\n"
            "  animeiat-cli --player mpv             Start TUI with MPV preferred\n"
            "  animeiat-cli --version                Show version and exit\n"
        )
    )
    parser.add_argument("--player", "-p",
                        help="Preferred player (auto, vlc, mpv, iina, celluloid, haruna)")
    parser.add_argument("--quality", "-q",
                        help="Default stream quality (auto, 1080p, 720p, 480p, 360p)")
    parser.add_argument("--url", "-u",
                        help="Anime URL to play (anime3rb.com or witanime.bond)")
    parser.add_argument("--no-tui", action="store_true",
                        help="Non-interactive mode: play URL and exit")
    parser.add_argument("--version", "-V", action="store_true",
                        help="Show version and exit")
    parser.add_argument("--json", action="store_true",
                        help="JSON output (machine-readable) for non-interactive mode")
    parser.add_argument("--list-episodes", action="store_true",
                        help="List all episodes and exit (non-interactive)")
    parser.add_argument("--download", action="store_true",
                        help="Queue stream URL for download and exit (non-interactive)")
    args = parser.parse_args()

    if args.version:
        print(f"animeiat-cli version {APP_VERSION}")
        return

    if args.url and args.no_tui:
        valid_players = {"auto", "vlc", "mpv", "iina", "celluloid", "haruna"}
        if args.player and args.player.lower() not in valid_players:
            err = f"Error: invalid player '{args.player}'. Must be one of: {', '.join(sorted(valid_players))}"
            print(err) if not args.json else print(json.dumps({"error": err}))
            sys.exit(1)
        valid_qualities = {"auto", "1080p", "720p", "480p", "360p"}
        if args.quality and args.quality.lower() not in valid_qualities:
            err = f"Error: invalid quality '{args.quality}'. Must be one of: {', '.join(sorted(valid_qualities))}"
            print(err) if not args.json else print(json.dumps({"error": err}))
            sys.exit(1)

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception as e:
            print(f"[animeiat-cli] Warning: stdout encoding reconfigure failed: {e}")

    init_db()
    migrate_json_to_sqlite()

    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32(0)
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 7)
        except Exception as e:
            print(f"[animeiat-cli] Warning: console mode set failed: {e}")

    if args.no_tui and args.url:
        run_noninteractive(
            args.url, args.player, args.quality,
            json_output=args.json,
            list_episodes=args.list_episodes,
            download_mode=args.download
        )
        return

    player_override = args.player if args.player else None
    quality_override = args.quality if args.quality else None

    enter_alt_screen()
    try:
        run_app(initial_url=args.url, player_override=player_override, quality_override=quality_override)
    except Exception as e:
        exit_alt_screen()
        traceback.print_exc()
        input("\nAn unexpected error occurred. Press Enter to exit...")
    finally:
        exit_alt_screen()


if __name__ == "__main__":
    main()

"""
TUI settings — player, search, data sync, appearance, config dir, about.
"""
import os
import shutil
import sqlite3
import sys
import time

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box as rich_box

from src.providers import ProviderId
from src.config import (
    APP_VERSION, THEME, console, get_icon, get_provider_name,
    get_config_dir, load_config, save_config, write_custom_config_dir,
)
from src.db import (
    get_db_path, get_db_connection,
    get_account_token, remove_account,
    fetch_anilist_user_list, fetch_mal_user_list,
)
from src.playback.discovery import get_cached_players, install_player
from src.playback.discovery import _invalidate_player_cfg as invalidate_player_cfg
from src.log_util import log

from ._core import read_key
from ._widgets import interactive_select, interactive_priority_list, _centered_message, _centered_prompt
# Extracted from tui.py lines 1848-2171

def _settings_player(cfg, ctx):
    history_enabled = cfg.get("history_tracking", True)
    fullscreen_enabled = cfg.get("fullscreen", False)
    player_args = cfg.get("custom_player_args", "")
    current_player = cfg.get("preferred_player", "auto")
    current_quality = cfg.get("default_quality", "auto")
    auto_play = cfg.get("auto_play_next", False)
    _player_paths = {k: ctx.get(k) for k in ("mpv", "vlc", "iina", "celluloid", "haruna")}

    while True:
        opts = [
            f"Preferred Player       (Current: {current_player.upper()})",
            f"Default Video Quality  (Current: {current_quality.upper()})",
            f"Auto Fullscreen        (Current: {'ENABLED' if fullscreen_enabled else 'DISABLED'})",
            f"Custom Player Args     (Current: '{player_args if player_args else 'None'}')",
            f"Auto-Play Next Episode (Current: {'ENABLED' if auto_play else 'DISABLED'})",
            "Go Back"
        ]
        sel_idx, sel_opt = interactive_select(opts, "Player & Playback")
        if sel_idx == -1 or sel_idx == 5:
            break
        if sel_idx == 0:
            players = ["auto", "vlc", "mpv", "iina", "celluloid", "haruna"]
            p_idx, p_opt = interactive_select(players, "Select Preferred Player")
            if p_idx != -1:
                cfg["preferred_player"] = p_opt
                save_config(cfg)
                current_player = cfg.get("preferred_player", "auto")
                invalidate_player_cfg()
                is_missing = False
                if p_opt == "mpv" and not _player_paths["mpv"]: is_missing = True
                elif p_opt == "vlc" and not _player_paths["vlc"]: is_missing = True
                elif p_opt == "iina" and not _player_paths["iina"]: is_missing = True
                elif p_opt == "celluloid" and not _player_paths["celluloid"]: is_missing = True
                elif p_opt == "haruna" and not _player_paths["haruna"]: is_missing = True
                if is_missing:
                    c_idx, _ = interactive_select([f"Yes, install {p_opt.upper()} now", "No, install it manually later"], f"{p_opt.upper()} not found \u2014 install?")
                    if c_idx == 0:
                        install_player(p_opt)
                        _centered_message(f"{p_opt.upper()} installed!", "info")
                    else:
                        _centered_message(f"Remember to install {p_opt.upper()} manually.", "info")
                else:
                    _centered_message(f"Preferred player set to: {p_opt.upper()}", "info")
        elif sel_idx == 1:
            qualities = ["auto", "1080p", "720p", "480p", "360p"]
            q_idx, q_opt = interactive_select(qualities, "Select Default Quality")
            if q_idx != -1:
                cfg["default_quality"] = q_opt
                save_config(cfg)
                current_quality = cfg.get("default_quality", "auto")
                _centered_message(f"Default quality set to: {q_opt.upper()}", "info")
        elif sel_idx == 2:
            cfg["fullscreen"] = not fullscreen_enabled
            save_config(cfg)
            invalidate_player_cfg()
            status_str = "ENABLED" if not fullscreen_enabled else "DISABLED"
            _centered_message(f"Auto Fullscreen set to: {status_str}", "info")
            fullscreen_enabled = cfg.get("fullscreen", False)
        elif sel_idx == 3:
            new_args = _centered_prompt("Enter custom player arguments (e.g. --fs --volume=80). Leave empty to clear.")
            if new_args is not None:
                cfg["custom_player_args"] = new_args.strip()
                save_config(cfg)
                invalidate_player_cfg()
                _centered_message("Custom player arguments updated!", "info")
                player_args = cfg.get("custom_player_args", "")
        elif sel_idx == 4:
            cfg["auto_play_next"] = not auto_play
            save_config(cfg)
            status_str = "ENABLED" if not auto_play else "DISABLED"
            _centered_message(f"Auto-Play Next Episode set to: {status_str}", "info")
            auto_play = cfg.get("auto_play_next", False)


def _settings_search_sources(cfg):
    while True:
        scrap_method = cfg.get("scraping_method", "auto")
        priorities = cfg.get("search_priorities", [ProviderId.ANIME3RB, ProviderId.WITANIME])
        method_labels = {"auto": "Auto (httpx -> Playwright)", "playwright_only": "Playwright Only", "alternative_only": "httpx Only"}
        opts = [
            f"Search Source Priorities   (Current: {len(priorities)} providers)",
            f"Scraping Method            (Current: {scrap_method.upper()})",
            "Clear Search History",
            "Go Back"
        ]
        sel_idx, _ = interactive_select(opts, "Search & Sources")
        if sel_idx == -1 or sel_idx == 3:
            break
        if sel_idx == 0:
            from src.config import PROVIDER_IDS as _PID
            all_ids = sorted(_PID.keys())
            provider_options = [f"{_PID[pid]} ({pid})" for pid in all_ids]
            old_priorities = cfg.get("search_priorities", [ProviderId.ANIME3RB, ProviderId.WITANIME])
            current_order = [p for p in old_priorities if p in all_ids]
            missing = [p for p in all_ids if p not in current_order]
            new_priorities = current_order + missing
            selected = interactive_priority_list(
                provider_options, new_priorities,
            )
            if selected is not None:
                cfg["search_priorities"] = selected
                save_config(cfg)
                _centered_message(f"Search priorities updated", "info")
        elif sel_idx == 1:
            methods = ["auto", "playwright_only", "alternative_only"]
            m_labels = {"auto": "Auto (httpx -> Playwright)", "playwright_only": "Playwright Only", "alternative_only": "httpx Only"}
            m_idx, m_opt = interactive_select([m_labels[m] for m in methods], "Select Scraping Method")
            if m_idx != -1:
                cfg["scraping_method"] = methods[m_idx]
                save_config(cfg)
                _centered_message(f"Scraping method set to: {m_labels[methods[m_idx]]}", "info")
        elif sel_idx == 2:
            cfg["search_history"] = []
            save_config(cfg)
            _centered_message("Search history cleared!", "info")


def _settings_data_sync(cfg, stack):
    while True:
        history_enabled = cfg.get("history_tracking", True)
        current_browser = cfg.get("preferred_browser", "auto")
        opts = [
            f"Cookie Sync Browser    (Current: {current_browser.upper()})",
            f"History Tracking       (Current: {'ENABLED' if history_enabled else 'DISABLED'})",
            "Accounts Integration (AniList / MyAnimeList)",
            "Clear All Watch History & Bookmarks",
            "Export Watch History / Progress",
            "Go Back"
        ]
        sel_idx, sel_opt = interactive_select(opts, "Data & Sync")
        if sel_idx == -1 or sel_idx == 5:
            break
        if sel_idx == 0:
            browsers = ["auto", "chrome", "edge"]
            b_idx, b_opt = interactive_select(browsers, "Select Preferred Cookie Browser")
            if b_idx != -1:
                cfg["preferred_browser"] = b_opt
                save_config(cfg)
                _centered_message(f"Preferred browser for cookies set to: {b_opt.upper()}", "info")
        elif sel_idx == 1:
            cfg["history_tracking"] = not history_enabled
            save_config(cfg)
            status_str = "ENABLED" if not history_enabled else "DISABLED"
            _centered_message(f"Watch history tracking set to: {status_str}", "info")
        elif sel_idx == 2:
            while True:
                anilist_info = get_account_token("anilist")
                mal_info = get_account_token("myanimelist")
                al_linked = anilist_info is not None
                mal_linked = mal_info is not None
                al_s = f"[bold green]Linked[/bold green]" if al_linked else "[dim]Not Linked[/dim]"
                mal_s = f"[bold green]Linked[/bold green]" if mal_linked else "[dim]Not Linked[/dim]"
                acc_opts = [
                    f"Link AniList Account       (Status: {al_s}) [Coming Soon]",
                    f"Link MyAnimeList Account   (Status: {mal_s}) [Coming Soon]",
                    "Unlink AniList Account" if al_linked else "Unlink AniList Account (Disabled)",
                    "Unlink MyAnimeList Account" if mal_linked else "Unlink MyAnimeList Account (Disabled)",
                    "Browse AniList Watch List",
                    "Browse MyAnimeList Watch List",
                    "Go Back"
                ]
                sub_idx, _ = interactive_select(acc_opts, "Accounts Integration")
                if sub_idx == -1 or sub_idx == 6:
                    break
                if sub_idx == 0:
                    _centered_message("AniList account linking is not yet implemented.\nCheck back in a future update.", "info")
                elif sub_idx == 1:
                    _centered_message("MyAnimeList account linking is not yet implemented.\nCheck back in a future update.", "info")
                elif sub_idx == 2:
                    if al_linked:
                        remove_account("anilist")
                        _centered_message("Unlinked AniList account.", "info")
                elif sub_idx == 3:
                    if mal_linked:
                        remove_account("myanimelist")
                        _centered_message("Unlinked MyAnimeList account.", "info")
                elif sub_idx == 4:
                    if not al_linked:
                        _centered_message("AniList account not linked. Link it first.", level="warn")
                        continue
                    from ._handlers import _browse_platform_list as _bpl
                    if _bpl(anilist_info["token"], fetch_anilist_user_list, "AniList", stack):
                        return True
                elif sub_idx == 5:
                    if not mal_linked:
                        _centered_message("MyAnimeList account not linked. Link it first.", level="warn")
                        continue
                    from ._handlers import _browse_platform_list as _bpl2
                    if _bpl2(mal_info["token"], fetch_mal_user_list, "MyAnimeList", stack):
                        return True
        elif sel_idx == 3:
            confirm = _centered_prompt("Type 'yes' to confirm clearing ALL watch history, bookmarks, and accounts")
            if confirm is None or confirm.strip().lower() != "yes":
                continue
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM favorites")
                cursor.execute("DELETE FROM shows")
                cursor.execute("DELETE FROM watched_episodes")
                cursor.execute("DELETE FROM episode_progress")
                cursor.execute("DELETE FROM accounts")
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                print(f"[animeiat-cli] Warning: DB cleanup failed: {e}")
            cfg["history"] = {}
            cfg["favorites"] = []
            save_config(cfg)
            _centered_message("Watch history, bookmarks, and linked accounts cleared!", "info")
        elif sel_idx == 4:
            from ._handlers import _handle_export
            _handle_export()
            break

    return False


def _settings_appearance(cfg):
    while True:
        use_nerd = cfg.get("nerd_fonts", False)
        opts = [
            f"Nerd Font Icons        (Current: {'ENABLED' if use_nerd else 'DISABLED'})",
            "Go Back"
        ]
        sel_idx, _ = interactive_select(opts, "Appearance")
        if sel_idx == -1 or sel_idx == 1:
            break
        if sel_idx == 0:
            cfg["nerd_fonts"] = not use_nerd
            save_config(cfg)
            status_str = "ENABLED" if not use_nerd else "DISABLED"
            _centered_message(f"Nerd Font Icons support set to: {status_str}", "info")


def _settings_config_dir(cfg):
    new_path = _centered_prompt(f"New config directory path (Current: {get_config_dir()}). Existing data will be moved automatically. Leave empty to keep current.")
    if new_path and new_path.strip():
        expanded = os.path.expanduser(new_path.strip())
        abs_path = os.path.abspath(expanded)
        if os.path.isdir(abs_path) or not os.path.exists(abs_path):
            old_dir = get_config_dir()
            if abs_path != old_dir:
                write_custom_config_dir(abs_path)
                os.makedirs(abs_path, exist_ok=True)
                old_cfg = os.path.join(old_dir, "config.json")
                new_cfg = os.path.join(abs_path, "config.json")
                if os.path.exists(old_cfg) and not os.path.exists(new_cfg):
                    try:
                        import shutil
                        shutil.move(old_cfg, new_cfg)
                    except Exception as e:
                        print(f"[animeiat-cli] Warning: config migration failed: {e}")
                    old_db = os.path.join(old_dir, "animeiat_cli.db")
                    new_db = os.path.join(abs_path, "animeiat_cli.db")
                    if os.path.exists(old_db) and not os.path.exists(new_db):
                        try:
                            import shutil
                            shutil.move(old_db, new_db)
                        except Exception as e:
                            print(f"[animeiat-cli] Warning: DB migration failed: {e}")
                        _centered_message(f"Config directory changed to: {abs_path}", "info")
        else:
            _centered_message(f"Invalid path: '{abs_path}' is not a directory.", level="error")
    else:
        _centered_message("Config directory unchanged.", "info")


def _settings_about(ctx):
    players = get_cached_players()
    vlc_ok = players.get("vlc") is not None
    mpv_ok = players.get("mpv") is not None
    iina_ok = players.get("iina") is not None
    celluloid_ok = players.get("celluloid") is not None
    haruna_ok = players.get("haruna") is not None

    anilist_token = get_account_token("anilist")
    mal_token = get_account_token("myanimelist")

    table = Table(box=None, show_header=False, pad_edge=False)
    table.add_column("Key", style=f"bold {THEME['fg']}")
    table.add_column("Val", style=THEME['success'])

    table.add_row("Version", f"animeiat-cli {APP_VERSION}")
    table.add_row("Config Path", get_config_dir())
    table.add_row("DB Path", get_db_path())
    table.add_row("Active Player", f"{ctx['player_name']} ({ctx['active_player'] or 'None'})")
    table.add_row("Theme", THEME.get('name', 'Catppuccin Mocha'))
    table.add_row("MPV", "[green]Installed[/green]" if mpv_ok else "[red]Not Found[/red]")
    table.add_row("VLC", "[green]Installed[/green]" if vlc_ok else "[red]Not Found[/red]")
    if sys.platform == "darwin":
        table.add_row("IINA", "[green]Installed[/green]" if iina_ok else "[red]Not Found[/red]")
    else:
        table.add_row("Celluloid", "[green]Installed[/green]" if celluloid_ok else "[red]Not Found[/red]")
        table.add_row("Haruna", "[green]Installed[/green]" if haruna_ok else "[red]Not Found[/red]")
    table.add_row("AniList", "[green]Linked[/green]" if anilist_token else "[dim]Not Linked[/dim]")
    table.add_row("MyAnimeList", "[green]Linked[/green]" if mal_token else "[dim]Not Linked[/dim]")
    table.add_row("Platform", sys.platform)
    table.add_row("Python", sys.version.split()[0])

    panel = Panel(
        Group(
            Text("animeiat-cli", style=f"bold {THEME['primary']}", justify="center"),
            Text("Anime Streaming Terminal CLI", style=f"{THEME['fg']}", justify="center"),
            Text(""),
            table,
            Text(""),
            Text.from_markup(f"[{THEME['dim']}]Check for updates: Press 'u' | Go back: Any key[/{THEME['dim']}]", justify="center"),
        ),
        title="[bold] About animeiat-cli [/bold]",
        border_style=THEME['border'],
        box=rich_box.ROUNDED,
        padding=(1, 2),
    )
    ts = shutil.get_terminal_size()
    h = ts.lines
    console.clear()
    console.print(Align(panel, align="center", vertical="middle", height=h))
    key = read_key()
    if key in ("u", "U"):
        update = check_for_update(APP_VERSION)
        if update:
            latest, _ = update
            _centered_message(f"Current version: {APP_VERSION}\nLatest version: {latest}\nPress 'u' in main menu to update.", level="info")
        else:
            _centered_message(f"Current version: {APP_VERSION}\nYou are up to date!", level="info")
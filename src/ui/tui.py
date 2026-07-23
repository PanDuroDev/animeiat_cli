"""
TUI components for animeiat-cli — interactive terminal UI, state machine, and widgets.
"""
import sys

from src.config import load_config, get_icon
from src.playback.discovery import get_cached_players
from src.playback.progress import stop_progress_tracking
from src.log_util import log
from src.providers._utils import validate_url

from ._core import clear_screen, set_terminal_title, _should_sync
from ._handlers import _STATE_HANDLERS
from ._widgets import _centered_message


def run_app(initial_url=None, player_override=None, quality_override=None):
    from src.log_util import get_log_path
    log("STATE", "APP_START — entering MAIN_MENU")
    log("INFO", f"log path: {get_log_path()}")
    stack = [{"state": "MAIN_MENU"}]
    if initial_url:
        valid, err_msg = validate_url(initial_url)
        if valid:
            log("STATE", f"prefilled URL: {initial_url}")
            stack.append({"state": "URL_INPUT", "prefilled_url": initial_url})
        else:
            _centered_message(f"Invalid URL: {err_msg}", level="error")

    while stack:
        cfg = load_config()
        pref_player = player_override or cfg.get("preferred_player", "auto")
        if quality_override:
            cfg["default_quality"] = quality_override

        players = get_cached_players()
        vlc = players.get("vlc"); mpv = players.get("mpv")
        iina = players.get("iina"); celluloid = players.get("celluloid"); haruna = players.get("haruna")

        active_player = None
        player_name = "None"
        if pref_player == "vlc" and vlc: active_player, player_name = vlc, "VLC"
        elif pref_player == "mpv" and mpv: active_player, player_name = mpv, "MPV"
        elif pref_player == "iina" and iina: active_player, player_name = iina, "IINA"
        elif pref_player == "celluloid" and celluloid: active_player, player_name = celluloid, "Celluloid"
        elif pref_player == "haruna" and haruna: active_player, player_name = haruna, "Haruna"
        else:
            if mpv: active_player, player_name = mpv, "MPV"
            elif vlc: active_player, player_name = vlc, "VLC"
            elif iina: active_player, player_name = iina, "IINA"
            elif celluloid: active_player, player_name = celluloid, "Celluloid"
            elif haruna: active_player, player_name = haruna, "Haruna"

        clear_screen()
        layout_icons = {
            "sparkle": get_icon('sparkle'),
            "check": get_icon('check'),
            "warning": get_icon('warning'),
        }

        current = stack[-1]
        state = current["state"]

        title_map = {
            "MAIN_MENU": "Anime CLI Player",
            "SEARCH_INPUT": "Search Input",
            "SEARCH_RESULTS": f"Search Results: {current.get('query', '')}",
            "URL_INPUT": "Direct URL Input",
            "FAVORITES": "Favorites Library",
            "SETTINGS": "Configuration Settings",
            "EPISODE_SELECTION": f"Episodes: {current.get('slug', '')}",
        }
        set_terminal_title(title_map.get(state, "Anime CLI Player"))

        try:
            handler = _STATE_HANDLERS.get(state)
            if handler is not None:
                ctx = {
                    "cfg": cfg, "players": players,
                    "active_player": active_player, "player_name": player_name,
                    "pref_player": pref_player, "layout_icons": layout_icons,
                    "vlc": vlc, "mpv": mpv, "iina": iina,
                    "celluloid": celluloid, "haruna": haruna,
                }
                log("STATE", f"handling state={state}, stack_depth={len(stack)}")
                if not handler(current, stack, ctx):
                    log("STATE", f"handler returned False — breaking loop (state={state})")
                    break
                new_state = stack[-1]["state"] if stack else "None"
                if new_state != state:
                    log("STATE", f"transition: {state} → {new_state}")
        except KeyboardInterrupt:
            log("STATE", f"KeyboardInterrupt (stack_depth={len(stack)})")
            if len(stack) > 1:
                stack.pop()
            else:
                break
        except Exception as exc:
            log("ERROR", f"unhandled exception in state={state}: {exc}")
            _centered_message(f"Unexpected error: {exc}\nSee traceback above for details.", level="error")
            import traceback
            traceback.print_exc()
            if len(stack) > 1:
                stack.pop()
            else:
                break

    log("STATE", "APP_EXIT")
    stop_progress_tracking()
    if _should_sync():
        sys.stdout.write("\033[?2026l")
    sys.stdout.flush()

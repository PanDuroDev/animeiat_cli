"""
TUI widgets — centered helpers, interactive selection, track selector, panels.
"""
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

if os.name == 'nt':
    import msvcrt
else:
    msvcrt = None

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.markup import escape
from rich import box as rich_box

from src.config import APP_VERSION, THEME, console, get_icon, get_http_client, load_config, get_provider_name
from src.db import get_watch_history
from src.playback.discovery import get_cached_players
from src.log_util import log

from ._core import (
    read_key, RawModeContext,
    KEY_UP, KEY_DOWN, KEY_ENTER, KEY_SPACE, KEY_ESC, KEY_CTRL_C, KEY_A, KEY_UNKNOWN,
    flush_input_buffer, _should_sync, detect_layout_mode,
    _ANIM_DURATION, _DRAG_THRESHOLD, _PAGE_SIZE, _LAYOUT_SPLIT, _REFRESH_RATE,
)
# Extracted from tui.py lines 310-342, 344-418, 420-1449

def print_hotkey_guide(player_name):
    title = f" [bold {THEME['primary']}]{player_name} Keyboard Controls / Shortcuts[/bold {THEME['primary']}] "

    table = Table(box=None, show_header=True, header_style=f"bold {THEME['accent']}", pad_edge=False)
    table.add_column("Action", style=f"bold {THEME['fg']}")
    table.add_column("Hotkey / Shortcut", style=f"bold {THEME['success']}")

    if player_name == "MPV":
        table.add_row("Play / Pause", "SPACE")
        table.add_row("Seek Back / Forward (5s)", "LEFT / RIGHT")
        table.add_row("Seek Back / Forward (1m)", "UP / DOWN")
        table.add_row("Adjust Volume", "9 / 0")
        table.add_row("Toggle Fullscreen", "F")
        table.add_row("Exit Player", "Q")
    else:
        table.add_row("Play / Pause", "SPACE")
        table.add_row("Seek Back / Forward", "ALT + LEFT / RIGHT")
        table.add_row("Adjust Volume", "CTRL + UP / DOWN")
        table.add_row("Toggle Fullscreen", "F")
        table.add_row("Exit Player", "Q / ESC")

    panel = Panel(
        table,
        title=title,
        border_style=THEME['border'],
        box=rich_box.ROUNDED,
        padding=(1, 2),
        expand=False
    )
    w, h = shutil.get_terminal_size()
    console.clear()
    console.print(Align(panel, align="center", vertical="middle", height=h))



def _centered_message(msg, level="info"):
    icon_map = {"info": "info", "ok": "check", "warn": "warning", "error": "cross"}
    color_map = {"info": THEME['primary'], "ok": THEME['success'], "warn": THEME['warning'], "error": THEME['error']}
    icon = get_icon(icon_map.get(level, "info"))
    color = color_map.get(level, THEME['fg'])

    w, h = shutil.get_terminal_size()
    panel = Panel(
        Group(Text.from_markup(f"{icon} {msg}", style=color, justify="center"), Text("")),
        box=rich_box.ROUNDED,
        border_style=THEME['border'],
        padding=(1, 2),
        width=min(80, w - 4),
    )
    console.clear()
    console.print(Align(
        Group(panel, Text(""), Text("Press any key to continue...", style=THEME['dim'], justify="center")),
        align="center", vertical="middle", height=h
    ))
    read_key()


def _centered_prompt(prompt_text):
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
    try:
        w, h = shutil.get_terminal_size()
        panel = Panel(
            Text.from_markup(f"{get_icon('settings')} {prompt_text}", style=THEME['fg'], justify="center"),
            box=rich_box.ROUNDED,
            border_style=THEME['border'],
            padding=(1, 2),
            width=min(80, w - 4),
        )
        console.clear()
        console.print(Align(
            Group(panel, Text(""), Text("Type your answer and press Enter (Esc to cancel):", style=THEME['dim'], justify="center")),
            align="center", vertical="middle", height=h
        ))
        val = console.input(f"[bold {THEME['accent']}]\u276f[/bold {THEME['accent']}] ").strip()
        return val
    except (KeyboardInterrupt, EOFError):
        return None
    finally:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()


@contextlib.contextmanager
def _centered_status(text, spinner="dots", icon="search"):
    spinner_renderable = Spinner(spinner, text="", style=THEME['primary'])
    icon_map = {"search": get_icon("search"), "watch": get_icon("watch_history"), "play": get_icon("play"), "settings": get_icon("settings"), "download": get_icon("download")}
    prefix = icon_map.get(icon, "")

    def _make():
        ts = shutil.get_terminal_size()
        return Align(
            Panel(
                Group(Text.from_markup(f"{prefix} {text}", style=THEME['primary'], justify="center"), Text(""), spinner_renderable),
                box=rich_box.ROUNDED,
                border_style=THEME['border'],
                padding=(1, 2),
            ),
            align="center",
            vertical="middle",
            height=ts.lines
        )

    with Live(_make(), refresh_per_second=20, transient=True) as live:
        yield live



UPDATE_CHECK_URL = "https://raw.githubusercontent.com/PanDuroDev/animeiat_cli/main/VERSION"
_update_cache = {"latest": None, "checked": False}


def check_for_update(current_version):
    if _update_cache["checked"]:
        latest = _update_cache["latest"]
        if latest is None:
            return None
        return latest, latest != current_version

    _update_cache["checked"] = True
    try:
        resp = get_http_client().get(UPDATE_CHECK_URL, timeout=5.0)
        if resp.status_code == 200:
            latest = resp.text.strip()
            _update_cache["latest"] = latest
            return latest, latest != current_version
    except Exception as e:
        print(f"[animeiat-cli] Warning: update check failed: {e}")
    return None


TRACK_DEFAULTS = {"audio_id": None, "sub_id": None, "audio_lang": None, "sub_lang": None}


def _probe_stream_tracks(stream_url):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_streams", stream_url],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        tracks = {"audio": [], "subtitle": []}
        for s in data.get("streams", []):
            codec_type = s.get("codec_type")
            idx = s.get("index", 0)
            lang = s.get("tags", {}).get("language", "und")
            title = s.get("tags", {}).get("title", "")
            label = f"#{idx} [{lang}] {title}" if title else f"#{idx} [{lang}]"
            if codec_type == "audio":
                tracks["audio"].append({"id": idx, "lang": lang, "label": label})
            elif codec_type == "subtitle":
                tracks["subtitle"].append({"id": idx, "lang": lang, "label": label})
        return tracks if (tracks["audio"] or tracks["subtitle"]) else None
    except Exception:
        return None


def _show_track_selector(track_info=None, stream_url=None):
    if track_info is None:
        track_info = dict(TRACK_DEFAULTS)

    probed_tracks = None
    if stream_url:
        probed_tracks = _probe_stream_tracks(stream_url)

    while True:
        table = Table(box=rich_box.ROUNDED, show_header=True, header_style=f"bold {THEME['accent']}", border_style=THEME['border'])
        table.add_column("Track Type", style=f"bold {THEME['fg']}")
        table.add_column("Setting", style=THEME['fg'])
        table.add_column("Action Key", style=THEME['dim'])

        table.add_row(
            "Audio Track",
            f"[{THEME['accent']}]{track_info['audio_lang'] or 'Default'}[/{THEME['accent']}] (ID: {track_info['audio_id'] or 'auto'})",
            "[bold]a[/bold] to set, [bold]A[/bold] to clear"
        )
        table.add_row(
            "Subtitle Track",
            f"[{THEME['accent']}]{track_info['sub_lang'] or 'None'}[/{THEME['accent']}] (ID: {track_info['sub_id'] or 'off'})",
            "[bold]s[/bold] to set, [bold]S[/bold] to clear"
        )

        if probed_tracks:
            for ttype, color in [("audio", "green"), ("subtitle", "cyan")]:
                items = probed_tracks.get(ttype, [])
                if items:
                    labels = ", ".join(item["label"] for item in items)
                    table.add_row(
                        f"[bold {color}]{ttype.capitalize()} Streams[/bold {color}]",
                        f"[{color}]{labels}[/{color}]",
                        ""
                    )
        else:
            hint = "[dim]Install ffprobe (ffmpeg) to auto-detect available tracks[/dim]" if stream_url else "[dim]Available tracks are detected from your stream[/dim]"
            table.add_row("", hint, "")

        panel = Panel(
            table,
            title="[bold]Audio / Subtitle Tracks[/bold]",
            border_style=THEME['border'],
            box=rich_box.ROUNDED,
            padding=(1, 2)
        )
        w, h = shutil.get_terminal_size()
        hotkey_bar = Text("a=Set audio ID  s=Set sub ID  A=Clear audio  S=Clear sub  Enter=Done  Esc=Cancel", style=THEME['dim'], justify="center")
        console.clear()
        console.print(Align(Group(panel, Text(""), hotkey_bar), align="center", vertical="middle", height=h))
        key = read_key()
        if key in (KEY_ENTER,):
            return track_info
        if key in (KEY_ESC, KEY_CTRL_C):
            return None
        if key == 'a':
            raw = _centered_prompt("Enter audio track ID (or leave empty for auto)")
            if raw:
                try:
                    track_info["audio_id"] = int(raw)
                    track_info["audio_lang"] = f"Track {raw}"
                except ValueError:
                    pass
        elif key == 'A':
            track_info["audio_id"] = None
            track_info["audio_lang"] = None
        elif key == 's':
            raw = _centered_prompt("Enter subtitle track ID (or leave empty for off)")
            if raw:
                try:
                    track_info["sub_id"] = int(raw)
                    track_info["sub_lang"] = f"Track {raw}"
                except ValueError:
                    pass
        elif key == 'S':
            track_info["sub_id"] = None
            track_info["sub_lang"] = None


def get_context_panel(context_type, selected_idx, options, metadata=None):
    if not metadata:
        metadata = {}

    title_text = "Information"

    players = get_cached_players()
    vlc_ok = players.get("vlc") is not None
    mpv_ok = players.get("mpv") is not None
    iina_ok = players.get("iina") is not None
    celluloid_ok = players.get("celluloid") is not None
    haruna_ok = players.get("haruna") is not None

    if context_type == "main_menu":
        title_text = "System Status & Info"
        table = Table(box=None, show_header=False, pad_edge=False)
        table.add_column("Key", style=f"bold {THEME['fg']}")
        table.add_column("Val", style=THEME['success'])

        player_status = "MPV" if mpv_ok else ("VLC" if vlc_ok else "None")
        pref_player = metadata.get("pref_player", "auto").upper()

        table.add_row(f"{get_icon('play')}Preferred Player", f"{pref_player} (Active: {player_status})")
        table.add_row(f"{get_icon('settings')}Quality", metadata.get("default_quality", "auto").upper())
        table.add_row(f"{get_icon('direct_url')}Cookie Browser", metadata.get("pref_browser", "auto").upper())
        table.add_row(f"{get_icon('favorite_on')}Library Size", f"{metadata.get('favorites_count', 0)} show(s)")

        al_linked = "[green]Linked[/green]" if metadata.get("anilist_linked") else "[dim]Not Linked[/dim]"
        mal_linked = "[green]Linked[/green]" if metadata.get("mal_linked") else "[dim]Not Linked[/dim]"
        table.add_row(f"{get_icon('watch_history')}AniList Sync", al_linked)
        table.add_row(f"{get_icon('watch_history')}MyAnimeList Sync", mal_linked)

        desc = ""
        if selected_idx == 0:
            desc = "Search for anime series across multiple streaming sources (Anime3rb, WitAnime) in real-time."
        elif selected_idx == 1:
            desc = "Directly play an anime URL from any supported source (Anime3rb, WitAnime) without performing a search."
        elif selected_idx == 2:
            desc = "Browse your bookmarked library of shows, view history, and resume playing."
        elif selected_idx == 3:
            desc = "Configure preferred video players, stream quality, cookie sync browsers, and account integrations."
        elif selected_idx == 4:
            desc = "Close the application and exit back to the shell."

        update_row = metadata.get("update_info")
        if update_row:
            latest_ver, is_newer = update_row
            if is_newer:
                update_msg = f"[bold {THEME['warning']}]Update available: {latest_ver}[/bold {THEME['warning']}]"
            else:
                update_msg = f"[dim {THEME['dim']}]Up to date ({latest_ver})[/dim {THEME['dim']}]"
            table.add_row(f"{get_icon('warning')}Version", update_msg)

        desc_esc = escape(desc)
        renderables = [
            Text("━━━ SYSTEM DIAGNOSTICS ━━━", style=f"bold {THEME['accent']}"),
            Text(""),
            table,
            Text(""),
            Text("━━━ DESCRIPTION ━━━", style=f"bold {THEME['accent']}"),
            Text(f"\n{desc_esc}\n", style=THEME['fg']),
            Text("━━━ QUICK CONTROLS ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(f"\n  \u2022 [bold {THEME['primary']}]\u2191 / \u2193[/bold {THEME['primary']}]   : Move cursor\n  \u2022 [bold {THEME['primary']}]ENTER[/bold {THEME['primary']}]   : Select option\n  \u2022 [bold {THEME['primary']}]ESC[/bold {THEME['primary']}]     : Go back / Exit\n", style=THEME['fg'])
        ]

    elif context_type == "search_results":
        title_text = "Search Details"
        query = metadata.get("search_query", "")
        search_entries = metadata.get("search_entries", [])

        selected_item = search_entries[selected_idx] if selected_idx < len(search_entries) else None
        if selected_item:
            sel_title = selected_item.get("title", "")
            sel_provider = selected_item.get("provider_name", "Unknown")
            sel_url = selected_item.get("url", "")
        else:
            sel_title = ""
            sel_provider = "Unknown"
            sel_url = ""

        query_esc = escape(query)
        title_esc = escape(sel_title)
        url_esc = escape(sel_url)

        renderables = [
            Text("━━━ SEARCH CONTEXT ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(f"\n  \u2022 [bold {THEME['primary']}]Active Query[/bold {THEME['primary']}] : '{query_esc}'\n  \u2022 [bold {THEME['primary']}]Total Results[/bold {THEME['primary']}]: {len(options)} item(s) found\n", style=THEME['fg']),
            Text("━━━ SELECTED ITEM ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(f"\n  \u2022 [bold {THEME['primary']}]Title[/bold {THEME['primary']}]        : {title_esc}\n  \u2022 [bold {THEME['primary']}]Provider[/bold {THEME['primary']}]     : {sel_provider}\n  \u2022 [bold {THEME['primary']}]URL[/bold {THEME['primary']}]         : {url_esc}\n", style=THEME['fg']),
            Text("━━━ INSTRUCTIONS ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(f"\n  \u2022 Press [bold {THEME['success']}]ENTER[/bold {THEME['success']}] to load this anime's episode list.\n  \u2022 Press [bold {THEME['warning']}]ESC[/bold {THEME['warning']}] to return to the search input screen.\n", style=THEME['fg'])
        ]

    elif context_type == "favorites":
        title_text = "Bookmark Details"
        selected_opt = options[selected_idx] if selected_idx < len(options) else ""
        show_slug = metadata.get("fav_slugs", [])[selected_idx] if selected_idx < len(metadata.get("fav_slugs", [])) else None

        title_esc = escape(selected_opt)
        info_text_markup = f"\n  \u2022 [bold {THEME['primary']}]Title[/bold {THEME['primary']}]        : {title_esc}\n"
        if show_slug:
            hist = get_watch_history(show_slug)
            last_ep = hist.get("last_watched", 0)
            watched_eps = len(hist.get("watched", []))
            info_text_markup += f"  \u2022 [bold {THEME['primary']}]Last Watched[/bold {THEME['primary']}]   : Episode {last_ep if last_ep > 0 else 'None'}\n"
            info_text_markup += f"  \u2022 [bold {THEME['primary']}]Watched Count[/bold {THEME['primary']}]  : {watched_eps} episode(s)\n"

        renderables = [
            Text("━━━ LIBRARY STATS ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(f"\n  \u2022 [bold {THEME['primary']}]Total Bookmarks[/bold {THEME['primary']}] : {len(options)} show(s)\n", style=THEME['fg']),
            Text("━━━ SELECTED BOOKMARK ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(info_text_markup, style=THEME['fg']),
            Text("━━━ INSTRUCTIONS ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(f"\n  \u2022 Press [bold {THEME['success']}]ENTER[/bold {THEME['success']}] to open this show's episodes list.\n  \u2022 Press [bold {THEME['warning']}]ESC[/bold {THEME['warning']}] to return to the main menu.\n", style=THEME['fg'])
        ]

    elif context_type == "episode_selection":
        title_text = "Episode Selection & Controls"
        anime_title = metadata.get("anime_title", "Anime Show")
        provider = metadata.get("provider", "Unknown")
        player_name = metadata.get("player_name", "MPV")
        anime_meta = metadata.get("anime_metadata")

        anime_title_esc = escape(anime_title)
        provider_esc = escape(provider)

        meta_lines = []
        if anime_meta:
            synopsis = anime_meta.get("synopsis")
            if synopsis:
                synopsis_clean = re.sub(r'<[^>]+>', '', synopsis)
                if len(synopsis_clean) > 180:
                    w, _ = shutil.get_terminal_size()
                    max_chars = max(80, w * 2)
                    synopsis_clean = synopsis_clean[:max_chars] + "..."
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Synopsis[/bold {THEME['primary']}]    : {escape(synopsis_clean)}")
            genres = anime_meta.get("genres", [])
            if genres:
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Genres[/bold {THEME['primary']}]      : {', '.join(genres[:5])}")
            score = anime_meta.get("average_score")
            if score:
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Rating[/bold {THEME['primary']}]       : {score}%")
            ep_count = anime_meta.get("episodes")
            if ep_count:
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Episodes[/bold {THEME['primary']}]    : {ep_count}")
            studios = anime_meta.get("studios", [])
            if studios:
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Studio[/bold {THEME['primary']}]      : {', '.join(studios[:2])}")
            season = anime_meta.get("season")
            season_year = anime_meta.get("season_year")
            if season and season_year:
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Season[/bold {THEME['primary']}]      : {season.title()} {season_year}")
            elif season_year:
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Year[/bold {THEME['primary']}]        : {season_year}")
            status_val = anime_meta.get("status")
            if status_val:
                meta_lines.append(f"  \u2022 [bold {THEME['primary']}]Status[/bold {THEME['primary']}]      : {status_val.replace('_', ' ').title()}")

        show_meta_markup = f"\n  \u2022 [bold {THEME['primary']}]Title[/bold {THEME['primary']}]        : {anime_title_esc}\n  \u2022 [bold {THEME['primary']}]Provider[/bold {THEME['primary']}]     : {provider_esc}\n"
        if meta_lines:
            show_meta_markup += "\n" + "\n".join(meta_lines) + "\n"

        renderables = [
            Text("━━━ SHOW METADATA ━━━", style=f"bold {THEME['accent']}"),
            Text.from_markup(show_meta_markup, style=THEME['fg']),
        ]

    return Panel(
        Group(*renderables),
        title=f"[bold {THEME['primary']}] {title_text} [/bold {THEME['primary']}]",
        border_style=THEME['border'],
        box=rich_box.ROUNDED,
        padding=(1, 2),
        expand=True
    )


def _show_help_panel(help_items, title="Keyboard Shortcuts", live=None):
    table = Table(show_header=True, header_style=f"bold {THEME['accent']}", border_style=THEME['border'], box=rich_box.ROUNDED)
    table.add_column("Key", style=f"bold {THEME['primary']}")
    table.add_column("Action", style=THEME['fg'])
    for key, action in help_items:
        table.add_row(key, action)
    panel = Panel(table, title=f"[bold {THEME['primary']}] {title} [/bold {THEME['primary']}]", border_style=THEME['border'], padding=(1, 2))
    w, h = shutil.get_terminal_size()
    rendered = Align(panel, align="center", vertical="middle", height=h)
    if live:
        live.update(rendered)
    else:
        console.clear()
        console.print(rendered)
    read_key()


def interactive_select(options, title="Select Option", context_type=None, metadata=None,
                       player_name=None, active_player=None, pref_player=None, icons=None,
                       top_renderable=None):
    if not options:
        return -1, None

    flush_input_buffer()
    mapped_order = list(range(len(options)))
    filter_text = ""
    sort_mode = 0
    selected_idx = 0
    scroll_offset = 0
    _, term_height = shutil.get_terminal_size()
    max_visible = max(5, min(20, term_height - 12))

    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    _right_panel_cache = {}
    _last_size = None
    _last_size_time = 0.0
    _filter_active = False
    _filter_buf = ""
    _cached_display = [options[i] for i in mapped_order]

    def _rebuild_order():
        nonlocal mapped_order, selected_idx, _cached_display
        base = list(range(len(options)))
        if sort_mode == 1:
            base.sort(key=lambda i: options[i].lower())
        elif sort_mode == 2:
            base.sort(key=lambda i: options[i].lower(), reverse=True)
        if filter_text:
            base = [i for i in base if filter_text.lower() in options[i].lower()]
        mapped_order = base
        _cached_display = [options[i] for i in mapped_order]
        if selected_idx >= len(mapped_order):
            selected_idx = max(0, len(mapped_order) - 1)

    def _update_right_cache():
        _right_panel_cache.clear()

    _show_details = False
    _anim_old_scroll = 0
    _anim_start = 0.0
    _anim_active = False

    try:
        def make_panel():
            nonlocal scroll_offset, selected_idx, _filter_active, _filter_buf
            nonlocal _right_panel_cache, _last_size, _last_size_time, _show_details
            nonlocal _anim_old_scroll, _anim_start, _anim_active, _cached_display

            now = time.monotonic()
            if _last_size is None or (now - _last_size_time) > 0.5:
                _last_size_time = now
                ts = shutil.get_terminal_size()
                if _last_size != (ts.columns, ts.lines):
                    _last_size = (ts.columns, ts.lines)
                    _right_panel_cache.clear()
            width, height = _last_size

            display = _cached_display
            if not display:
                display = ["[dim](no matches)[/dim]"]
            if selected_idx >= len(display):
                selected_idx = max(0, len(display) - 1)
            if selected_idx < scroll_offset:
                scroll_offset = selected_idx
            elif selected_idx >= scroll_offset + max_visible:
                scroll_offset = selected_idx - max_visible + 1

            render_scroll = scroll_offset
            if _anim_active:
                elapsed = time.monotonic() - _anim_start
                if elapsed >= _ANIM_DURATION:
                    _anim_active = False
                else:
                    progress = elapsed / _ANIM_DURATION
                    eased = 1.0 - (1.0 - progress) ** 3
                    render_scroll = int(round(_anim_old_scroll + (scroll_offset - _anim_old_scroll) * eased))

            table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 1))

            if render_scroll > 0:
                table.add_row(f"[dim {THEME['dim']}]    {get_icon('arrow_up')}more items above[/dim {THEME['dim']}]")
            else:
                table.add_row("")

            visible_options = display[render_scroll : render_scroll + max_visible]
            for idx_rel, opt in enumerate(visible_options):
                idx_abs = render_scroll + idx_rel
                num_label = f"{idx_abs + 1}."
                if idx_abs == selected_idx:
                    table.add_row(f"  [bold {THEME['accent']}]{get_icon('bullet')}[/bold {THEME['accent']}][bold {THEME['select_fg']} on {THEME['select_bg']}] {num_label} {opt} [/bold {THEME['select_fg']} on {THEME['select_bg']}]")
                else:
                    table.add_row(f"    [{THEME['fg']}]{num_label}[/{THEME['fg']}] [{THEME['fg']}]{opt}[/{THEME['fg']}]")

            total = len(display) if display != ["[dim](no matches)[/dim]"] else 0
            if render_scroll + max_visible < total:
                table.add_row(f"[dim {THEME['dim']}]    {get_icon('arrow_down')}more items below[/dim {THEME['dim']}]")
            else:
                table.add_row("")

            if _filter_active:
                buf_text = escape(_filter_buf) if _filter_buf else ""
                table.add_row(f"  [{THEME['accent']}]Filter: {buf_text}\u2588[/{THEME['accent']}]")

            filter_indicator = ""
            if filter_text:
                filter_indicator = f"  [{THEME['accent']}]/ {escape(filter_text)}[/{THEME['accent']}]"
            sort_labels = ["", " [A-Z]", " [Z-A]"]
            page_info = f"({selected_idx + 1}/{total}){filter_indicator}{sort_labels[sort_mode]}"
            if _filter_active:
                buf_text = escape(_filter_buf) if _filter_buf else "..."
                subtitle = f"[{THEME['accent']}]  Filter: {buf_text}\u2588  (Esc=Abort  Enter=Apply)[/{THEME['accent']}]"
            else:
                player_info = ""
                if player_name and active_player:
                    player_info = f" | {icons.get('check', '')} {player_name} ({active_player})" if icons else f" | {player_name}"
                detail_label = "d=Details" if context_type else ""
                subtitle = f"\u2191\u2193 Navigate  \u23ce Select  {detail_label}  Esc/q Back  /=Filter  s=Sort{player_info}  {page_info}"

            left_panel = Panel(
                table,
                title=f"[bold {THEME['primary']}] {title} [/bold {THEME['primary']}] [dim]{APP_VERSION}[/dim]",
                subtitle=f"[{THEME['fg']}]{subtitle}[/{THEME['fg']}]",
                border_style=THEME['border'],
                box=rich_box.ROUNDED,
                expand=True,
                padding=(1, 2)
            )

            mode = detect_layout_mode(width, height)

            body_parts = []
            if top_renderable:
                body_parts.append(top_renderable)

            show_right = context_type and _show_details and mode != "MINIMAL" and width >= 80
            if show_right:
                orig_idx = mapped_order[selected_idx] if selected_idx < len(mapped_order) else 0
                if orig_idx not in _right_panel_cache:
                    _right_panel_cache[orig_idx] = get_context_panel(context_type, orig_idx, options, metadata)
                    if len(_right_panel_cache) > 60:
                        _right_panel_cache.clear()
                right_panel = _right_panel_cache[orig_idx]
                grid = Table.grid(expand=True)
                grid.add_column(ratio=_LAYOUT_SPLIT[0])
                grid.add_column(ratio=_LAYOUT_SPLIT[1])
                grid.add_row(left_panel, right_panel)
                body_parts.append(grid)
            else:
                body_parts.append(Align.center(left_panel))

            body = Group(*body_parts) if len(body_parts) > 1 else body_parts[0]
            return Align(body, align="center", vertical="middle", height=height)

        def _run_anim():
            nonlocal _anim_active
            if not _anim_active:
                return None
            while _anim_active:
                _sync_update()
                if os.name == 'nt' and msvcrt.kbhit():
                    return read_key()
                elif os.name != 'nt':
                    import select
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        return read_key()
                elapsed = time.monotonic() - _anim_start
                if elapsed >= _ANIM_DURATION:
                    _anim_active = False
                    break
                time.sleep(0.05)
            _sync_update()
            return None

        with RawModeContext():
            with Live(None, refresh_per_second=_REFRESH_RATE, transient=True) as live:
                def _sync_update(renderable=None):
                    if renderable is None:
                        renderable = make_panel()
                    if _should_sync():
                        sys.stdout.write("\033[?2026h")
                    live.update(renderable)
                    if _should_sync():
                        sys.stdout.write("\033[?2026l")
                _sync_update()
                while True:
                    key = read_key()

                    if _filter_active:
                        if key == KEY_ENTER:
                            _filter_active = False
                            filter_text = _filter_buf
                            _filter_buf = ""
                            _rebuild_order()
                            _update_right_cache()
                            selected_idx = 0
                        elif key in (KEY_ESC, KEY_CTRL_C):
                            _filter_active = False
                            _filter_buf = ""
                        elif key in ('\x08', '\x7f'):
                            _filter_buf = _filter_buf[:-1]
                        elif isinstance(key, str) and key.isprintable():
                            _filter_buf += key
                        _sync_update()
                        continue

                    display = _cached_display
                    if key == KEY_UP:
                        if display:
                            _anim_old_scroll = scroll_offset
                            _anim_start = time.monotonic()
                            _anim_active = True
                            selected_idx = (selected_idx - 1) % len(display)
                        key = _run_anim() or key
                    elif key == KEY_DOWN:
                        if display:
                            _anim_old_scroll = scroll_offset
                            _anim_start = time.monotonic()
                            _anim_active = True
                            selected_idx = (selected_idx + 1) % len(display)
                        key = _run_anim() or key
                    elif key in ('d', 'D'):
                        if context_type:
                            _show_details = not _show_details
                            _sync_update()
                    elif key == '/':
                        _filter_active = True
                        _filter_buf = ""
                        _sync_update()
                    elif key in ('s', 'S'):
                        sort_mode = (sort_mode + 1) % 3
                        _rebuild_order()
                        _update_right_cache()
                        selected_idx = 0
                        _sync_update()
                    elif key in ('?', 'h', 'H'):
                        _show_help_panel([
                            ("\u2191 / \u2193", "Navigate list"),
                            ("Enter", "Select item"),
                            ("d", "Toggle details panel"),
                            ("Esc / q", "Go back / Clear filter"),
                            ("/", "Filter results by text"),
                            ("s", "Cycle sort order"),
                            ("g / G", "Go to first / last"),
                        ], "Navigation Help", live=live)
                        _sync_update()
                    elif key in ('q', 'Q'):
                        if filter_text:
                            filter_text = ""
                            _rebuild_order()
                            _update_right_cache()
                            selected_idx = 0
                            _sync_update()
                        else:
                            return -1, None
                    elif key == KEY_ENTER:
                        if mapped_order and selected_idx < len(mapped_order):
                            choice = options[mapped_order[selected_idx]]
                            log("INPUT", f"interactive_select: title='{title}', idx={mapped_order[selected_idx]}, choice='{choice}'")
                            return mapped_order[selected_idx], choice
                        return -1, None
                    elif key in (KEY_ESC, KEY_CTRL_C):
                        if filter_text:
                            filter_text = ""
                            _rebuild_order()
                            _update_right_cache()
                            selected_idx = 0
                            _sync_update()
                        else:
                            return -1, None
                    elif key in ('g', 'G'):
                        if display:
                            _anim_old_scroll = scroll_offset
                            _anim_start = time.monotonic()
                            _anim_active = True
                            selected_idx = 0 if key == 'g' else len(display) - 1
                        key = _run_anim() or key
                    elif key == KEY_UNKNOWN:
                        pass
                    else:
                        pass
    finally:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()


def interactive_priority_list(labels, current_order):
    if not labels:
        return None

    flush_input_buffer()
    selected_idx = 0
    scroll_offset = 0
    _, term_height = shutil.get_terminal_size()
    max_visible = max(5, min(20, term_height - 12))

    _notify = ""
    order = list(current_order)

    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    try:
        def make_panel():
            nonlocal scroll_offset, _notify
            width, height = shutil.get_terminal_size()
            if selected_idx < scroll_offset:
                scroll_offset = selected_idx
            elif selected_idx >= scroll_offset + max_visible:
                scroll_offset = selected_idx - max_visible + 1

            table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 1))

            if scroll_offset > 0:
                table.add_row(f"[dim {THEME['dim']}]  {get_icon('arrow_up')}more above[/dim {THEME['dim']}]")
            else:
                table.add_row("")

            visible = order[scroll_offset : scroll_offset + max_visible]
            for idx_rel, pid in enumerate(visible):
                idx_abs = scroll_offset + idx_rel
                label = labels[pid]
                rank = order.index(pid) + 1
                arrow = " \u25b2\u25bc" if idx_abs == selected_idx else ""
                text = f"[{rank}] {label}{arrow}"

                if idx_abs == selected_idx:
                    table.add_row(f"[bold {THEME['primary']}]{get_icon('bullet')}[/bold {THEME['primary']}] [bold {THEME['select_fg']} on {THEME['select_bg']}]{text}[/bold {THEME['select_fg']} on {THEME['select_bg']}]")
                else:
                    table.add_row(f"  [{THEME['fg']}]{text}[/{THEME['fg']}]")

            if scroll_offset + max_visible < len(order):
                table.add_row(f"[dim {THEME['dim']}]  {get_icon('arrow_down')}more below[/dim {THEME['dim']}]")
            else:
                table.add_row("")

            if _notify:
                table.add_row(f"[bold {THEME['warning']}]  {_notify}[/bold {THEME['warning']}]")
                _notify = ""
            table.add_row("")

            subtitle = f"Nav: \u2191\u2195/jk  Move: u/d  Confirm: Enter  Cancel: Esc"

            panel = Panel(
                table,
                title=f"[bold {THEME['primary']}] Search Source Priorities [/bold {THEME['primary']}]",
                subtitle=f"[{THEME['fg']}]{subtitle}  ({selected_idx + 1}/{len(order)})[/{THEME['fg']}]",
                border_style=THEME['border'],
                box=rich_box.ROUNDED,
                expand=True,
                padding=(1, 2)
            )

            return Align(panel, align="center", vertical="middle", height=height)

        with RawModeContext():
            with Live(None, refresh_per_second=_REFRESH_RATE, transient=True) as live:
                def _sync_update(renderable=None):
                    if renderable is None:
                        renderable = make_panel()
                    if _should_sync():
                        sys.stdout.write("\033[?2026h")
                    try:
                        live.update(renderable)
                    finally:
                        if _should_sync():
                            sys.stdout.write("\033[?2026l")
                _sync_update()
                while True:
                    key = read_key()
                    if key in ("q", "esc"):
                        return None
                    elif key == "enter":
                        return order
                    elif key in ("up", "k", "K"):
                        selected_idx = max(0, selected_idx - 1)
                        _sync_update()
                    elif key in ("down", "j", "J"):
                        selected_idx = min(len(order) - 1, selected_idx + 1)
                        _sync_update()
                    elif key in ("u", "U"):
                        if selected_idx > 0:
                            order[selected_idx], order[selected_idx - 1] = order[selected_idx - 1], order[selected_idx]
                            selected_idx -= 1
                            _notify = f"Moved {labels[order[selected_idx]]} up"
                        else:
                            _notify = "Already at top"
                        _sync_update()
                    elif key in ("d", "D"):
                        if selected_idx < len(order) - 1:
                            order[selected_idx], order[selected_idx + 1] = order[selected_idx + 1], order[selected_idx]
                            selected_idx += 1
                            _notify = f"Moved {labels[order[selected_idx]]} down"
                        else:
                            _notify = "Already at bottom"
                        _sync_update()
    finally:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()


def interactive_checklist(options, title="Select Episodes", default_start_idx=0, is_favorite=False, on_toggle_favorite=None,
                          context_type=None, metadata=None,
                          player_name=None, active_player=None, pref_player=None, icons=None,
                          preselected_indices=None):
    if not options:
        return []

    flush_input_buffer()
    selected_idx = default_start_idx
    scroll_offset = 0
    _, term_height = shutil.get_terminal_size()
    max_visible = max(5, min(20, term_height - 12))
    checked = [False] * len(options)
    if preselected_indices:
        for idx in preselected_indices:
            if 0 <= idx < len(options):
                checked[idx] = True
    _notify = ""
    _input_active = False
    _input_buf = ""
    if len(checked) > 0 and not any(checked):
        checked[selected_idx] = True

    _right_panel_cache = {}
    _last_size = None
    _last_size_time = 0.0
    _show_details = False

    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    _anim_old_scroll = 0
    _anim_start = 0.0
    _anim_active = False

    try:
        def make_panel():
            nonlocal scroll_offset, _notify, _input_active, _input_buf
            nonlocal _right_panel_cache, _last_size, _last_size_time, _show_details
            nonlocal _anim_old_scroll, _anim_start, _anim_active
            if selected_idx < scroll_offset:
                scroll_offset = selected_idx
            elif selected_idx >= scroll_offset + max_visible:
                scroll_offset = selected_idx - max_visible + 1

            now = time.monotonic()
            if _last_size is None or (now - _last_size_time) > 0.5:
                _last_size_time = now
                ts = shutil.get_terminal_size()
                if _last_size != (ts.columns, ts.lines):
                    _last_size = (ts.columns, ts.lines)
                    _right_panel_cache.clear()
            width, height = _last_size
            mode = detect_layout_mode(width, height)

            render_scroll = scroll_offset
            if _anim_active:
                elapsed = time.monotonic() - _anim_start
                if elapsed >= _ANIM_DURATION:
                    _anim_active = False
                else:
                    progress = elapsed / _ANIM_DURATION
                    eased = 1.0 - (1.0 - progress) ** 3
                    render_scroll = int(round(_anim_old_scroll + (scroll_offset - _anim_old_scroll) * eased))

            table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 1))

            if render_scroll > 0:
                table.add_row(f"[dim {THEME['dim']}]  {get_icon('arrow_up')}more items above[/dim {THEME['dim']}]")
            else:
                table.add_row("")

            visible_options = options[render_scroll : render_scroll + max_visible]
            for idx_rel, opt in enumerate(visible_options):
                idx_abs = render_scroll + idx_rel
                box = get_icon("check") if checked[idx_abs] else get_icon("cross")
                color = THEME["checked"] if checked[idx_abs] else THEME["unchecked"]
                opt_text = f"{box}{opt}"

                if idx_abs == selected_idx:
                    table.add_row(f"[bold {THEME['primary']}]{get_icon('bullet')}[/bold {THEME['primary']}] [bold {THEME['select_fg']} on {THEME['select_bg']}]{opt_text}[/bold {THEME['select_fg']} on {THEME['select_bg']}]")
                else:
                    table.add_row(f"  [{color}]{opt_text}[/{color}]")

            if render_scroll + max_visible < len(options):
                table.add_row(f"[dim {THEME['dim']}]  {get_icon('arrow_down')}more items below[/dim {THEME['dim']}]")
            else:
                table.add_row("")

            if _input_active:
                buf_text = escape(_input_buf) if _input_buf else ""
                table.add_row(f"  [{THEME['accent']}]Jump: {buf_text}\u2588[/{THEME['accent']}]")

            if _notify:
                table.add_row(f"[bold {THEME['warning']}]  {_notify}[/bold {THEME['warning']}]")
                _notify = ""
            table.add_row("")

            sel_count = sum(checked)
            total_pages = (len(options) + _PAGE_SIZE - 1) // _PAGE_SIZE
            current_page = selected_idx // _PAGE_SIZE + 1
            page_info = f"(p.{current_page}/{total_pages} ep.{selected_idx + 1}/{len(options)}) [{sel_count} selected]"

            fav_icon = f" [bold {THEME['warning']}]{get_icon('favorite_on')}[/bold {THEME['warning']}]" if is_favorite else f" [{THEME['dim']}]{get_icon('favorite_off')}[/{THEME['dim']}]"

            drag_label = f"[bold {THEME['warning']}]\u25b6 drag[/bold {THEME['warning']}]" if _in_drag() else "SPACE+\u2195=drag"
            player_info = ""
            if player_name and active_player:
                player_info = f" | {icons.get('check', '')} {player_name} ({active_player})" if icons else f" | {player_name}"
            subtitle = f"SPACE=toggle  {drag_label}  d=Details  A=all  F=fav  J=jump  []=page  Enter=confirm  Esc=back{player_info}"

            left_panel = Panel(
                table,
                title=f"[bold {THEME['primary']}] {title}{fav_icon}[/bold {THEME['primary']}] [dim]{APP_VERSION}[/dim]",
                subtitle=f"[{THEME['fg']}]{subtitle}  {page_info}[/{THEME['fg']}]",
                border_style=THEME['border'],
                box=rich_box.ROUNDED,
                expand=True,
                padding=(1, 2)
            )

            show_right = context_type and _show_details and mode != "MINIMAL" and width >= 80
            if show_right:
                if selected_idx not in _right_panel_cache:
                    _right_panel_cache[selected_idx] = get_context_panel(context_type, selected_idx, options, metadata)
                    if len(_right_panel_cache) > 60:
                        _right_panel_cache.clear()
                right_panel = _right_panel_cache[selected_idx]
                grid = Table.grid(expand=True)
                grid.add_column(ratio=_LAYOUT_SPLIT[0])
                grid.add_column(ratio=_LAYOUT_SPLIT[1])
                grid.add_row(left_panel, right_panel)
                return Align(grid, align="center", vertical="middle", height=height)

            return Align(Align.center(left_panel), align="center", vertical="middle", height=height)

        _last_drag_time = 0.0
        _DRAG_WINDOW = _DRAG_THRESHOLD

        def _in_drag():
            return time.time() - _last_drag_time < _DRAG_WINDOW

        def _run_anim():
            nonlocal _anim_active
            if not _anim_active:
                return None
            while _anim_active:
                _sync_update()
                if os.name == 'nt' and msvcrt.kbhit():
                    return read_key()
                elif os.name != 'nt':
                    import select
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        return read_key()
                elapsed = time.monotonic() - _anim_start
                if elapsed >= _ANIM_DURATION:
                    _anim_active = False
                    break
                time.sleep(0.05)
            _sync_update()
            return None

        with RawModeContext():
            with Live(None, refresh_per_second=_REFRESH_RATE, transient=True) as live:
                def _sync_update(renderable=None):
                    if renderable is None:
                        renderable = make_panel()
                    if _should_sync():
                        sys.stdout.write("\033[?2026h")
                    try:
                        live.update(renderable)
                    finally:
                        if _should_sync():
                            sys.stdout.write("\033[?2026l")
                _sync_update()
                while True:
                    key = read_key()
                    
                    # ── Input mode (jump-to-episode) ───────────
                    if _input_active:
                        if key == KEY_ENTER:
                            _input_active = False
                            buf = _input_buf
                            _input_buf = ""
                            if buf:
                                try:
                                    ep_num = int(buf) - 1
                                    if 0 <= ep_num < len(options):
                                        selected_idx = ep_num
                                    else:
                                        _notify = f"Episode {buf} out of range (1-{len(options)})"
                                except ValueError:
                                    _notify = f"Invalid: '{buf}'"
                        elif key in (KEY_ESC, KEY_CTRL_C):
                            _input_active = False
                            _input_buf = ""
                        elif key in ('\x08', '\x7f'):
                            _input_buf = _input_buf[:-1]
                        elif isinstance(key, str) and key.isdigit():
                            _input_buf += key
                        _sync_update()
                        continue

                    now = time.time()
                    is_dragging = _in_drag()

                    if key == KEY_UP:
                        _anim_old_scroll = scroll_offset
                        _anim_start = time.monotonic()
                        _anim_active = True
                        selected_idx = (selected_idx - 1) % len(options)
                        if is_dragging:
                            checked[selected_idx] = not checked[selected_idx]
                            _last_drag_time = now
                        key = _run_anim() or key
                    elif key == KEY_DOWN:
                        _anim_old_scroll = scroll_offset
                        _anim_start = time.monotonic()
                        _anim_active = True
                        selected_idx = (selected_idx + 1) % len(options)
                        if is_dragging:
                            checked[selected_idx] = not checked[selected_idx]
                            _last_drag_time = now
                        key = _run_anim() or key
                    elif key in ('d', 'D'):
                        if context_type:
                            _show_details = not _show_details
                            _sync_update()
                    elif key == KEY_SPACE:
                        checked[selected_idx] = not checked[selected_idx]
                        _last_drag_time = now
                        _sync_update()
                    elif key == KEY_A:
                        all_checked = all(checked)
                        checked = [not all_checked] * len(options)
                        _sync_update()
                    elif key in ('f', 'F'):
                        if on_toggle_favorite:
                            is_favorite = on_toggle_favorite()
                            _sync_update()
                    elif key == '[':
                        _anim_old_scroll = scroll_offset
                        _anim_start = time.monotonic()
                        _anim_active = True
                        selected_idx = max(0, selected_idx - _PAGE_SIZE)
                        key = _run_anim() or key
                    elif key == ']':
                        _anim_old_scroll = scroll_offset
                        _anim_start = time.monotonic()
                        _anim_active = True
                        selected_idx = min(len(options) - 1, selected_idx + _PAGE_SIZE)
                        key = _run_anim() or key
                    elif key in ('g', 'G'):
                        _anim_old_scroll = scroll_offset
                        _anim_start = time.monotonic()
                        _anim_active = True
                        selected_idx = 0 if key == 'g' else len(options) - 1
                        key = _run_anim() or key
                    elif key in ('j', 'J'):
                        _input_active = True
                        _input_buf = ""
                        _sync_update()
                    elif key in ('?', 'h', 'H'):
                        _show_help_panel([
                            ("\u2191 / \u2193", "Navigate list"),
                            ("d", "Toggle details panel"),
                            ("Space", "Toggle episode (hold then \u2191\u2193 = drag)"),
                            ("A", "Select / deselect all"),
                            ("F", "Toggle bookmark / favorite"),
                            ("J", "Jump to episode number"),
                            ("[ / ]", "Page up / down (50 episodes)"),
                            ("g / G", "Go to first / last"),
                            ("Enter", "Scrape & play selected"),
                            ("Esc", "Go back"),
                        ], "Episode Selection Help", live=live)
                        _sync_update()
                    elif key == KEY_ENTER:
                        selected = [idx for idx, val in enumerate(checked) if val]
                        log("INPUT", f"interactive_checklist: title='{title}', selected={selected}")
                        return selected
                    elif key in (KEY_ESC, KEY_CTRL_C):
                        return None
                    elif key == KEY_UNKNOWN:
                        pass
    finally:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
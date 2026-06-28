import os
import re
import subprocess

from .discovery import get_cached_players, _get_player_cfg
from .progress import start_progress_tracking
from ..config import load_config
from ..db import get_episode_progress


def play(stream_urls, player="mpv", slug=None, episode=None, extra_args=None, provider=0):
    if player == "mpv":
        return play_with_mpv(stream_urls, slug=slug, ep=episode, extra_args=extra_args, provider=provider)
    elif player == "vlc":
        return play_with_vlc(stream_urls, extra_args=extra_args, slug=slug, ep=episode, provider=provider)
    elif player == "iina":
        return play_with_iina(stream_urls, extra_args=extra_args, slug=slug, ep=episode, provider=provider)
    elif player == "celluloid":
        return play_with_celluloid(stream_urls, extra_args=extra_args, slug=slug, ep=episode, provider=provider)
    elif player == "haruna":
        return play_with_haruna(stream_urls, extra_args=extra_args, slug=slug, ep=episode, provider=provider)
    return False


def play_with_vlc(stream_urls, extra_args=None, slug=None, ep=None, provider=0):
    vlc_path = get_cached_players().get("vlc")
    if not vlc_path:
        return False

    pcfg = _get_player_cfg()
    user_args = list(pcfg["custom_args"])
    if extra_args:
        user_args = extra_args + user_args

    fs_arg = ["--fullscreen"] if pcfg["fullscreen"] else []
    if slug and ep is not None:
        prog = get_episode_progress(slug, ep, provider=provider)
        if prog and prog.get("time_pos", 0) > 5:
            fs_arg += [f"--start-time={int(prog['time_pos'])}"]
    cmd = [vlc_path] + fs_arg + user_args + stream_urls
    try:
        if os.name == 'nt':
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
        else:
            subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[animeiat-cli] Warning: VLC launch failed: {e}")
        return False


def play_with_mpv(stream_urls, slug=None, ep=None, extra_args=None, provider=0):
    mpv_path = get_cached_players().get("mpv")
    if not mpv_path:
        return False

    is_mpvnet = "mpvnet" in os.path.basename(mpv_path).lower()

    pcfg = _get_player_cfg()
    user_args = list(pcfg["custom_args"])
    if extra_args:
        user_args = extra_args + user_args

    fs_arg = ["--fullscreen"] if pcfg["fullscreen"] else []

    ipc_path = None
    if slug and ep is not None:
        safe_slug = re.sub(r'[\\/:*?"<>|]', '_', str(slug))
        if os.name == 'nt':
            ipc_path = rf"\\.\pipe\animeiat-cli-ipc-{safe_slug}-{ep}"
        else:
            ipc_path = f"/tmp/animeiat-cli-ipc-{safe_slug}-{ep}.sock"
        fs_arg.append(f"--input-ipc-server={ipc_path}")

        prog = get_episode_progress(slug, ep, provider=provider)
        if prog and prog.get("time_pos", 0) > 5:
            fs_arg.append(f"--start={int(prog['time_pos'])}")

    if is_mpvnet:
        cmd = [mpv_path] + fs_arg + user_args + stream_urls
    else:
        cmd = [mpv_path, "--force-window", "--keep-open=yes"] + fs_arg + user_args + stream_urls

    try:
        if os.name == 'nt':
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
        else:
            subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if ipc_path:
            start_progress_tracking(slug, ep, ipc_path, provider=provider)

        return True
    except Exception as e:
        print(f"[animeiat-cli] Warning: MPV launch failed: {e}")
        return False


def play_with_iina(stream_urls, extra_args=None, slug=None, ep=None, provider=0):
    iina_path = get_cached_players().get("iina")
    if not iina_path:
        return False
    pcfg = _get_player_cfg()
    user_args = list(pcfg["custom_args"])
    if extra_args:
        user_args = extra_args + user_args
    fs_arg = ["--mpv-fs"] if pcfg["fullscreen"] else []
    if slug and ep is not None:
        prog = get_episode_progress(slug, ep, provider=provider)
        if prog and prog.get("time_pos", 0) > 5:
            fs_arg += [f"--start={int(prog['time_pos'])}"]
    cmd = [iina_path] + fs_arg + user_args + stream_urls
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[animeiat-cli] Warning: IINA launch failed: {e}")
        return False


def play_with_celluloid(stream_urls, extra_args=None, slug=None, ep=None, provider=0):
    celluloid_path = get_cached_players().get("celluloid")
    if not celluloid_path:
        return False
    pcfg = _get_player_cfg()
    user_args = list(pcfg["custom_args"])
    if extra_args:
        user_args = extra_args + user_args
    fs_arg = ["--fullscreen"] if pcfg["fullscreen"] else []
    if slug and ep is not None:
        prog = get_episode_progress(slug, ep, provider=provider)
        if prog and prog.get("time_pos", 0) > 5:
            fs_arg += [f"--start={int(prog['time_pos'])}"]
    cmd = [celluloid_path] + fs_arg + user_args + stream_urls
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[animeiat-cli] Warning: Celluloid launch failed: {e}")
        return False


def play_with_haruna(stream_urls, extra_args=None, slug=None, ep=None, provider=0):
    haruna_path = get_cached_players().get("haruna")
    if not haruna_path:
        return False
    pcfg = _get_player_cfg()
    user_args = list(pcfg["custom_args"])
    if extra_args:
        user_args = extra_args + user_args
    fs_arg = ["--fullscreen"] if pcfg["fullscreen"] else []
    if slug and ep is not None:
        prog = get_episode_progress(slug, ep, provider=provider)
        if prog and prog.get("time_pos", 0) > 5:
            fs_arg += [f"--start={int(prog['time_pos'])}"]
    cmd = [haruna_path] + fs_arg + user_args + stream_urls
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[animeiat-cli] Warning: Haruna launch failed: {e}")
        return False

import json
import os
import socket
import sys
import time
import threading

from src.db import save_episode_progress
from src.providers import ProviderId


_stop_event = threading.Event()


def stop_progress_tracking():
    _stop_event.set()


def start_progress_tracking(slug, episode, player_ipc_path, provider=ProviderId.ANIME3RB):
    stop_progress_tracking()
    _stop_event.clear()
    threading.Thread(target=poll_mpv_progress, args=(player_ipc_path, slug, episode, provider), daemon=True).start()


def poll_mpv_progress(ipc_path, slug, ep, provider=ProviderId.ANIME3RB):
    client = None
    max_retries = 8
    connect_warned = False
    for retry in range(max_retries):
        if _stop_event.is_set():
            return
        if os.name == 'nt':
            try:
                client = open(ipc_path, "r+b", buffering=0)
                break
            except Exception as e:
                if not connect_warned:
                    print(f"[animeiat-cli] Warning: IPC connect attempt failed: {e}")
                    connect_warned = True
                time.sleep(0.3)
        else:
            if os.path.exists(ipc_path):
                try:
                    import socket
                    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client.connect(ipc_path)
                    break
                except Exception as e:
                    if not connect_warned:
                        print(f"[animeiat-cli] Warning: Unix socket connect failed: {e}")
                        connect_warned = True
                    time.sleep(0.3)
            else:
                time.sleep(0.3)

    if not client:
        print(f"[animeiat-cli] Warning: could not connect to MPV IPC at {ipc_path}")
        return

    _last_saved_time_pos = None
    read_warned = False
    try:
        while not _stop_event.is_set():
            time_cmd = json.dumps({"command": ["get_property", "time-pos"]}) + "\n"
            duration_cmd = json.dumps({"command": ["get_property", "duration"]}) + "\n"

            time_pos = None
            duration = None

            if os.name == 'nt':
                try:
                    client.write(time_cmd.encode("utf-8"))
                    line = b""
                    while True:
                        c = client.read(1)
                        if not c:
                            break
                        line += c
                        if c == b"\n":
                            break
                    if line:
                        resp = json.loads(line.decode("utf-8", errors="ignore"))
                        if resp.get("error") == "success":
                            time_pos = resp.get("data")
                except Exception as e:
                    if not read_warned and "Invalid argument" not in str(e):
                        print(f"[animeiat-cli] Warning: IPC time-pos read failed: {e}")
                        read_warned = True
                    break

                try:
                    client.write(duration_cmd.encode("utf-8"))
                    line = b""
                    while True:
                        c = client.read(1)
                        if not c:
                            break
                        line += c
                        if c == b"\n":
                            break
                    if line:
                        resp = json.loads(line.decode("utf-8", errors="ignore"))
                        if resp.get("error") == "success":
                            duration = resp.get("data")
                except Exception as e:
                    if not read_warned and "Invalid argument" not in str(e):
                        print(f"[animeiat-cli] Warning: IPC duration read failed: {e}")
                        read_warned = True
                    break
            else:
                try:
                    client.sendall(time_cmd.encode("utf-8"))
                    buffer = b""
                    while b"\n" not in buffer:
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        buffer += chunk
                    if b"\n" in buffer:
                        line = buffer.split(b"\n")[0]
                        resp = json.loads(line.decode("utf-8", errors="ignore"))
                        if resp.get("error") == "success":
                            time_pos = resp.get("data")
                except Exception as e:
                    if not read_warned:
                        print(f"[animeiat-cli] Warning: IPC time-pos read failed: {e}")
                        read_warned = True
                    break

                try:
                    client.sendall(duration_cmd.encode("utf-8"))
                    buffer = b""
                    while b"\n" not in buffer:
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        buffer += chunk
                    if b"\n" in buffer:
                        line = buffer.split(b"\n")[0]
                        resp = json.loads(line.decode("utf-8", errors="ignore"))
                        if resp.get("error") == "success":
                            duration = resp.get("data")
                except Exception as e:
                    if not read_warned:
                        print(f"[animeiat-cli] Warning: IPC duration read failed: {e}")
                        read_warned = True
                    break

            if time_pos is not None:
                dirty = False
                if _last_saved_time_pos is None:
                    dirty = True
                elif duration and (time_pos / duration > 0.95):
                    dirty = True
                elif duration and abs(time_pos - _last_saved_time_pos) >= max(2.0, duration * 0.01):
                    dirty = True
                elif not duration and abs(time_pos - _last_saved_time_pos) >= 2.0:
                    dirty = True
                if dirty:
                    if duration and (time_pos / duration > 0.95):
                        save_episode_progress(slug, ep, 0, duration, provider=provider)
                    else:
                        save_episode_progress(slug, ep, time_pos, duration or 0, provider=provider)
                    _last_saved_time_pos = time_pos

            _stop_event.wait(1.0)
    except Exception as e:
        print(f"[animeiat-cli] poll_mpv_progress error: {e}")
    finally:
        try:
            client.close()
        except Exception:
            pass
        if os.name != 'nt':
            try:
                if os.path.exists(ipc_path):
                    os.remove(ipc_path)
            except Exception:
                pass

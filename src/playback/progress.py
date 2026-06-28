import json
import os
import socket
import sys
import time
import threading

from src.db import save_episode_progress


_stop_event = threading.Event()


def stop_progress_tracking():
    _stop_event.set()


def start_progress_tracking(slug, episode, player_ipc_path):
    stop_progress_tracking()  # stop any previous zombie thread
    _stop_event.clear()
    threading.Thread(target=poll_mpv_progress, args=(player_ipc_path, slug, episode), daemon=True).start()


def poll_mpv_progress(ipc_path, slug, ep):
    client = None
    for _ in range(20):
        if _stop_event.is_set():
            return
        if os.name == 'nt':
            try:
                client = open(ipc_path, "r+b", buffering=0)
                break
            except Exception as e:
                print(f"[animeiat-cli] Warning: IPC connect attempt failed: {e}")
                time.sleep(0.3)
        else:
            if os.path.exists(ipc_path):
                try:
                    import socket
                    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client.connect(ipc_path)
                    break
                except Exception as e:
                    print(f"[animeiat-cli] Warning: Unix socket connect failed: {e}")
                    time.sleep(0.3)
            else:
                time.sleep(0.3)

    if not client:
        print(f"[animeiat-cli] Warning: could not connect to MPV IPC at {ipc_path}")
        return

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
                    print(f"[animeiat-cli] Warning: IPC time-pos read failed: {e}")
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
                    print(f"[animeiat-cli] Warning: IPC duration read failed: {e}")
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
                    print(f"[animeiat-cli] Warning: Unix IPC time-pos failed: {e}")
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
                    print(f"[animeiat-cli] Warning: Unix IPC duration failed: {e}")
                    break

            if time_pos is not None:
                if duration and (time_pos / duration > 0.95):
                    save_episode_progress(slug, ep, 0, duration)
                else:
                    save_episode_progress(slug, ep, time_pos, duration or 0)

            _stop_event.wait(1.0)
    except Exception as e:
        sys.stderr.write(f"[animeiat-cli] poll_mpv_progress error: {e}\n")
    finally:
        try:
            client.close()
        except Exception as e:
            print(f"[animeiat-cli] Warning: IPC client close failed: {e}")
        if os.name != 'nt':
            try:
                if os.path.exists(ipc_path):
                    os.remove(ipc_path)
            except Exception as e:
                print(f"[animeiat-cli] Warning: IPC socket cleanup failed: {e}")

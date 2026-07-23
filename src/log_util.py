"""
Simple file logger — each run creates a separate timestamped log in logs/.
"""
import os
import threading
from datetime import datetime

_log_file = None
_log_path = None
_init_lock = threading.Lock()


def _write(msg):
    if _log_file:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        _log_file.write(f"[{ts}] {msg}\n")
        _log_file.flush()


def _ensure_init():
    global _log_file, _log_path
    if _log_file is not None:
        return
    with _init_lock:
        if _log_file is not None:
            return
        from src.config import get_config_dir
        log_dir = os.path.join(get_config_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _log_path = os.path.join(log_dir, f"animeiat-{timestamp}.log")
        _log_file = open(_log_path, "a", encoding="utf-8")
        _write("=== animeiat-cli session started ===")


def get_log_path():
    _ensure_init()
    return _log_path


def log(level, message):
    _ensure_init()
    _write(f"[{level}] {message}")


def shutdown():
    global _log_file
    if _log_file:
        _write("[INFO] === session ended ===")
        _log_file.close()
        _log_file = None

import os
import threading
import time

import httpx

from src.config import get_config_dir, load_config, get_http_client
from src.db import update_download_status, get_db_connection


def get_download_dir():
    cfg = load_config()
    d = cfg.get("download_dir", "")
    if d:
        os.makedirs(d, exist_ok=True)
        return d
    fallback = os.path.join(get_config_dir(), "downloads")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _safe_filename(slug, episode, quality=""):
    qs = f"_{quality}" if quality else ""
    return f"{slug}_ep{episode:04d}{qs}.mp4"


def _download_url_to_file(url, filepath, timeout=300.0):
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
            resp.raise_for_status()
            tmp = filepath + ".partial"
            with open(tmp, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
            os.replace(tmp, filepath)
        return True
    except Exception as e:
        if os.path.exists(filepath + ".partial"):
            try:
                os.remove(filepath + ".partial")
            except Exception:
                pass
        print(f"[animeiat-cli] Warning: download failed for {url}: {e}")
        return False


def _download_worker(slug, episode, url, quality=""):
    update_download_status(slug, episode, "downloading")
    dl_dir = get_download_dir()
    fname = _safe_filename(slug, episode, quality)
    fpath = os.path.join(dl_dir, fname)
    ok = _download_url_to_file(url, fpath)
    if ok:
        update_download_status(slug, episode, "completed", file_path=fpath)
    else:
        update_download_status(slug, episode, "failed")


def start_download(slug, episode, url, quality=""):
    t = threading.Thread(
        target=_download_worker,
        args=(slug, episode, url, quality),
        daemon=True,
    )
    t.start()
    return t


def download_and_wait(slug, episode, url, quality=""):
    dl_dir = get_download_dir()
    fname = _safe_filename(slug, episode, quality)
    fpath = os.path.join(dl_dir, fname)
    ok = _download_url_to_file(url, fpath)
    if ok:
        update_download_status(slug, episode, "completed", file_path=fpath)
    else:
        update_download_status(slug, episode, "failed")
    return ok


def enqueue_selected(eps_to_scrape, cached_urls, slug, quality=""):
    queued = 0
    for ep in eps_to_scrape:
        ep_num = ep["episode"]
        u_str = cached_urls.get(ep_num)
        if u_str:
            from src.db import add_download_entry
            add_download_entry(slug, ep_num, u_str, quality=quality)
            start_download(slug, ep_num, u_str, quality=quality)
            queued += 1
    return queued

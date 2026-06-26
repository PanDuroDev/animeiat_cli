import re
from urllib.parse import urlparse

from src.config import load_config, THEME


def validate_url(url):
    if not url or not url.strip():
        return False, "URL is empty"
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https"):
        return False, "URL must start with http:// or https://"
    if not p.netloc:
        return False, "URL is missing a domain name"
    if (not p.path or p.path.strip("/") == "") and not p.query:
        return False, "URL is missing a path or query string"
    return True, ""


def extract_slug(url):
    p = urlparse(url)
    netloc = p.netloc.lower()
    path = p.path

    if "anime3rb" in netloc:
        m = re.search(r"/titles/([^/#?]+)", path)
        if m: return m.group(1)
    elif "witanime" in netloc:
        m = re.search(r"/anime/([^/#?]+)", path)
        if m: return m.group(1)
        m = re.search(r"/episode/(.+?)-[\u0600-\u06FF]+-\d+", path)
        if m: return m.group(1)
    elif "anitaku" in netloc or "gogoanime" in netloc or "anineko" in netloc:
        m = re.search(r"/watch/([^/#?]+)", path)
        if m:
            slug = m.group(1)
            slug = re.sub(r'/ep-\d+$', '', slug)
            return slug
    elif "hianime" in netloc:
        m = re.search(r"/watch/([^/#?]+)", path)
        if m: return m.group(1)
    elif "9anime" in netloc:
        m = re.search(r"/watch/([^/#?]+)", path)
        if m: return m.group(1)

    path_clean = p.path.strip("/")
    if path_clean:
        parts = path_clean.split("/")
        if parts:
            return parts[-1]
    return None


def normalize(href, base_url=None):
    if href.startswith("http"):
        return href
    if base_url:
        p = urlparse(base_url)
        scheme_netloc = f"{p.scheme}://{p.netloc}"
        if href.startswith("/"):
            return scheme_netloc + href
        else:
            return scheme_netloc + "/" + href
    return href


def select_best_stream(urls):
    if not urls:
        return None

    cfg = load_config()
    pref_quality = cfg.get("default_quality", "auto")

    if pref_quality != "auto":
        if pref_quality == "1080p":
            keywords = ["1080p", "1080", "fhd", "w1080p"]
        elif pref_quality == "720p":
            keywords = ["720p", "720", "hd"]
        elif pref_quality == "480p":
            keywords = ["480p", "480", "sd"]
        else:
            keywords = []

        for u in urls:
            if any(kw in u.lower() for kw in keywords):
                return u

    for u in urls:
        if "1080" in u.lower() or "fhd" in u.lower():
            return u
    for u in urls:
        if "master.txt" in u or "/master." in u:
            return u
    for u in urls:
        if ".m3u8" in u or any(p in u for p in ["/hls/", "/hls2/", "/hls3/", "/index.m3u8", "/playlist."]):
            return u
    for u in urls:
        if ".mp4" in u:
            return u
    return urls[0]


def _classify_stream_quality(stream_url):
    u = stream_url.lower()
    if "1080p" in u or "fhd" in u or "w1080p" in u:
        return "FHD/1080p"
    if "720p" in u or "hd" in u:
        return "HD/720p"
    if "480p" in u or "sd" in u:
        return "SD/480p"
    return "Auto"


def _is_cloudflare_challenge(html):
    if "Just a moment" not in html and "Attention Required" not in html:
        return False
    if "cf-browser-verify" in html or "/cdn-cgi/challenge-platform" in html:
        return True
    return False


def _get_ua():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

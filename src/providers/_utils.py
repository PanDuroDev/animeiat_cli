import re
import socket
from urllib.parse import urlparse

from src.config import load_config, THEME


def detect_provider_from_url(url):
    p = urlparse(url.strip())
    netloc = p.netloc.lower()
    domain = netloc.split(":")[0]
    for pattern, provider_id in [
        ("anime3rb.com", 0), ("www.anime3rb.com", 0),
        ("witanime.bond", 1), ("www.witanime.bond", 1),
    ]:
        if domain == pattern:
            return provider_id
    for pattern, provider_id in [
        ("anime3rb", 0), ("witanime", 1),
    ]:
        if pattern in netloc:
            return provider_id
    return 0


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

    host = p.hostname or p.netloc.split(":")[0]
    if host in ("localhost", "localhost6", "127.0.0.1", "0.0.0.0", "::1", "[::1]"):
        return False, "URL points to loopback/localhost (possible SSRF)"
    try:
        addr = socket.getaddrinfo(host, 80, socket.AF_INET, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addr:
            ip = sockaddr[0]
            if ip.startswith("127.") or ip == "0.0.0.0":
                return False, "URL resolves to a loopback address (possible SSRF)"
            parts = ip.split(".")
            if len(parts) == 4:
                if parts[0] == "10":
                    return False, "URL resolves to a private IP range (possible SSRF)"
                if parts[0] == "172" and 16 <= int(parts[1]) <= 31:
                    return False, "URL resolves to a private IP range (possible SSRF)"
                if parts[0] == "192" and parts[1] == "168":
                    return False, "URL resolves to a private IP range (possible SSRF)"
    except socket.gaierror:
        return False, "URL hostname could not be resolved"
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

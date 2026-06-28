from src.providers._utils import (
    validate_url, extract_slug, normalize, select_best_stream,
    _classify_stream_quality, _is_cloudflare_challenge,
)


def test_validate_url_valid():
    valid, msg = validate_url("https://anime3rb.com/titles/naruto")
    assert valid is True
    assert msg == ""


def test_validate_url_loopback_ipv4():
    valid, msg = validate_url("http://127.0.0.1:8080/admin")
    assert valid is False
    assert "loopback" in msg.lower() or "ssrf" in msg.lower()


def test_validate_url_loopback_hostname():
    valid, msg = validate_url("http://localhost:8080/admin")
    assert valid is False
    assert "loopback" in msg.lower() or "ssrf" in msg.lower() or "resolve" in msg.lower()


def test_validate_url_private_192():
    valid, msg = validate_url("http://192.168.1.1:8080/admin")
    assert valid is False
    assert "private" in msg.lower() or "ssrf" in msg.lower() or "resolve" in msg.lower()


def test_validate_url_empty():
    valid, msg = validate_url("")
    assert valid is False
    assert "empty" in msg.lower()


def test_validate_url_no_scheme():
    valid, msg = validate_url("not-a-url")
    assert valid is False


def test_extract_slug_anime3rb():
    slug = extract_slug("https://anime3rb.com/titles/naruto-shippuden")
    assert slug == "naruto-shippuden"


def test_extract_slug_witanime():
    slug = extract_slug("https://witanime.com/anime/bleach")
    assert slug == "bleach"


def test_extract_slug_anineko():
    slug = extract_slug("https://anineko.to/watch/one-piece")
    assert slug == "one-piece"


def test_extract_slug_unknown():
    slug = extract_slug("https://example.com/some/path")
    assert slug is None


def test_normalize_already_absolute():
    result = normalize("https://example.com/stream.m3u8")
    assert result == "https://example.com/stream.m3u8"


def test_normalize_relative_with_base():
    result = normalize("/watch/ep-1", base_url="https://anineko.to")
    assert result == "https://anineko.to/watch/ep-1"


def test_normalize_relative_no_base():
    result = normalize("/watch/ep-1")
    assert result == "/watch/ep-1"


def test_select_best_stream_empty():
    result = select_best_stream([])
    assert result is None


def test_select_best_stream_1080p_preferred(monkeypatch):
    monkeypatch.setattr("src.providers._utils.load_config", lambda: {"default_quality": "auto"})
    urls = ["https://example.com/720p.mp4", "https://example.com/1080p.mp4"]
    result = select_best_stream(urls)
    assert "1080p" in result


def test_select_best_stream_quality_720p(monkeypatch):
    monkeypatch.setattr("src.providers._utils.load_config", lambda: {"default_quality": "720p"})
    urls = ["https://example.com/480p.mp4", "https://example.com/720p.mp4", "https://example.com/1080p.mp4"]
    result = select_best_stream(urls)
    assert "720p" in result


def test_classify_stream_quality_fhd():
    assert _classify_stream_quality("https://example.com/1080p.mp4") == "FHD/1080p"


def test_classify_stream_quality_hd():
    assert _classify_stream_quality("https://example.com/720p.mp4") == "HD/720p"


def test_classify_stream_quality_sd():
    assert _classify_stream_quality("https://example.com/480p.mp4") == "SD/480p"


def test_classify_stream_quality_auto():
    assert _classify_stream_quality("https://example.com/stream.m3u8") == "Auto"


def test_is_cloudflare_challenge_true():
    html = "<html>Just a moment...<div id='cf-browser-verify'></div></html>"
    assert _is_cloudflare_challenge(html) is True


def test_is_cloudflare_challenge_false():
    html = "<html>Normal page content</html>"
    assert _is_cloudflare_challenge(html) is False

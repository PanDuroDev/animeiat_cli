import asyncio
import base64
import json
import re
import shutil
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from rich.align import Align
from rich.columns import Columns
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from src.config import THEME, console, get_icon, load_config
from ._utils import (
    _classify_stream_quality, _get_ua, _is_cloudflare_challenge,
    extract_slug, normalize, select_best_stream,
)
from ._cookies import get_preferred_cookies, _cookie_warn


def _select_scraping_method(cfg=None):
    if cfg is None:
        cfg = load_config()
    return cfg.get("scraping_method", "auto")


async def _fetch_episodes_list_httpx(url, is_witanime, active_cookies=None):
    slug = extract_slug(url)
    if not slug:
        return None, "Cannot extract slug from URL."
    try:
        cookies_dict = {}
        if active_cookies:
            for c in active_cookies:
                cookies_dict[c.get("name")] = c.get("value")
        headers = {
            "User-Agent": _get_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers, cookies=cookies_dict)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        html = r.text
        if _is_cloudflare_challenge(html):
            return None, "Cloudflare challenge detected"
        soup = BeautifulSoup(html, "lxml")
        eps = []
        if is_witanime == 1:
            cards = soup.find_all("div", class_="episodes-card")
            for idx, card in enumerate(cards):
                title_anchor = card.find("h3").find("a") if card.find("h3") else None
                if not title_anchor or not title_anchor.get("onclick"):
                    continue
                onclick = title_anchor["onclick"]
                try:
                    m = re.search(r"'([A-Za-z0-9+/=]+)'", onclick)
                    if not m:
                        continue
                    ep_url = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                text = title_anchor.text.strip()
                m = re.search(r'\d+', text)
                ep_num = int(m.group(0)) if m else (idx + 1)
                eps.append({"episode": ep_num, "page_url": ep_url})
        elif is_witanime == 0:
            seen = set()
            for a in soup.find_all("a", href=True):
                h = a["href"].strip()
                m = re.search(rf"/episode/{re.escape(slug)}/(\d+)", h)
                n = int(m.group(1)) if m else None
                if n is not None and h not in seen:
                    seen.add(h)
                    eps.append({"episode": n, "page_url": normalize(h, base_url=url)})
        elif is_witanime == 2:
            for ep_div in soup.find_all("a", class_="nv-info-episode-main"):
                ep_href = (ep_div.get("href") or "").strip()
                m = re.search(r'/ep-(\d+)$', ep_href)
                if m:
                    ep_num = int(m.group(1))
                    if "/download/" in ep_href:
                        ep_href = ep_href.replace("/download/", "/watch/")
                    eps.append({"episode": ep_num, "page_url": normalize(ep_href, base_url=url)})
            if not eps:
                for a in soup.find_all("a", href=True):
                    h = a["href"].strip()
                    m = re.search(r'/ep-(\d+)$', h)
                    if m and "/watch/" in h:
                        ep_num = int(m.group(1))
                        eps.append({"episode": ep_num, "page_url": normalize(h, base_url=url)})
        elif is_witanime == 3:
            anime_id = None
            slug = extract_slug(url)
            m = re.search(r'data-id\s*=\s*["\'](\d+)["\']', html)
            if m:
                anime_id = m.group(1)
            if not anime_id:
                m = re.search(r'let\s+id\s*=\s*(\d+)', html)
                if m:
                    anime_id = m.group(1)
            if not anime_id:
                m = re.search(r'/watch/[^/]+-(\d+)', url)
                if m:
                    anime_id = m.group(1)
            if not anime_id:
                script_tag = soup.find("script", text=re.compile(r'anime_id'))
                if not script_tag:
                    script_tag = soup.find("script", text=re.compile(r'"id"'))
                if script_tag and script_tag.string:
                    m = re.search(r'anime_id\s*=\s*["\']?(\d+)["\']?', script_tag.string)
                    if m:
                        anime_id = m.group(1)
            if anime_id:
                api_url = f"https://hianime.dk/ajax/episode/list/{anime_id}"
                async with httpx.AsyncClient(timeout=15.0) as c2:
                    ar = await c2.get(api_url, headers=headers)
                if ar.status_code == 200:
                    data = ar.json()
                    html_str = data.get("result", "")
                    if html_str:
                        ep_soup = BeautifulSoup(str(html_str), "lxml")
                        for a in ep_soup.select("a.ssl-item.ep-item, a[class*='ep-item']"):
                            ep_num_text = a.text.strip()
                            m = re.search(r'(\d+)', ep_num_text)
                            if m:
                                ep_num = int(m.group(1))
                                if slug:
                                    ep_page_url = normalize(f"/watch/{slug}/ep-{ep_num}", base_url="https://hianime.dk")
                                else:
                                    ep_page_url = normalize(a.get("href", "#"), base_url="https://hianime.dk")
                                eps.append({"episode": ep_num, "page_url": ep_page_url})
            if not eps:
                seen = set()
                for a in soup.select("a.ssl-item.ep-item, a[class*='ep-item'], div[class*='ep-item'] a"):
                    h = a.get("href", "").strip()
                    ep_num_text = a.text.strip()
                    m = re.search(r'(\d+)', ep_num_text)
                    if m:
                        ep_num = int(m.group(1))
                        if h and h != "#" and h not in seen:
                            seen.add(h)
                            eps.append({"episode": ep_num, "page_url": normalize(h, base_url=url)})
        elif is_witanime == 4:
            seen = set()
            for a in soup.find_all("a", href=True):
                h = a["href"].strip()
                if "/watch/" in h and slug in h:
                    ep_text = a.text.strip()
                    m = re.search(r'(\d+)', ep_text)
                    if m and h not in seen:
                        seen.add(h)
                        eps.append({"episode": int(m.group(1)), "page_url": normalize(h, base_url=url)})
        if not eps:
            return None, "No episodes found via httpx"
        eps.sort(key=lambda x: x["episode"])
        return eps, None
    except Exception as e:
        return None, str(e)


async def _scrape_one_stream_httpx(ep_item, is_witanime, active_cookies=None):
    ep_num = ep_item["episode"]
    url = ep_item["page_url"]
    cookies_dict = {}
    if active_cookies:
        for c in active_cookies:
            cookies_dict[c.get("name")] = c.get("value")
    headers = {
        "User-Agent": _get_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers, cookies=cookies_dict)
        if r.status_code != 200:
            return None
        html = r.text
        if _is_cloudflare_challenge(html):
            return None
        resolved = None
        if is_witanime == 1:
            soup = BeautifulSoup(html, "lxml")
            server_links = soup.find_all("a", class_="server-link")
            candidates = []
            for srv in server_links:
                onclick = srv.get("onclick", "")
                if not onclick:
                    continue
                try:
                    m = re.search(r"'([A-Za-z0-9+/=]+)'", onclick)
                    if not m:
                        continue
                    embed_url = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                if not embed_url.startswith("http"):
                    continue
                try:
                    embed_headers = {**headers, "Referer": url}
                    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c2:
                        er = await c2.get(embed_url, headers=embed_headers)
                    if er.status_code == 200:
                        ehtml = er.text
                        found = None
                        patterns = [
                            r'<video[^>]*src=["\']([^"\']+)["\']',
                            r'<source[^>]*src=["\']([^"\']+\.(?:mp4|m3u8))["\']',
                            r'video_url\s*[=:]\s*["\']([^"\']+)["\']',
                            r'file:\s*["\']([^"\']+)["\']',
                        ]
                        for pat in patterns:
                            m = re.search(pat, ehtml)
                            if m:
                                found = m.group(1)
                                break
                        if not found:
                            m = re.search(r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)', ehtml)
                            if m:
                                found = m.group(1)
                        if found:
                            candidates.append(found)
                except Exception:
                    continue
            resolved = select_best_stream(candidates) if candidates else None
        elif is_witanime == 0:
            soup = BeautifulSoup(html, "lxml")
            iframe = soup.find("iframe", src=re.compile(r"(vid3rb\.com|player)"))
            if iframe:
                player_url = iframe.get("src")
                if player_url:
                    if not player_url.startswith("http"):
                        player_url = urljoin(url, player_url)
                    try:
                        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c2:
                            pr = await c2.get(player_url, headers=headers)
                        if pr.status_code == 200:
                            phtml = pr.text
                            m = re.search(r'(?:var|let|const)\s+video_sources\s*=\s*(\[\s*\{[\s\S]*?\}\s*\])\s*;', phtml)
                            if m:
                                sources = json.loads(m.group(1))
                                cfg = load_config()
                                pref_q = cfg.get("default_quality", "auto")
                                if pref_q == "720p":
                                    q_order = ["720p", "1080p", "480p"]
                                elif pref_q == "480p":
                                    q_order = ["480p", "720p", "1080p"]
                                else:
                                    q_order = ["1080p", "720p", "480p"]
                                for q in q_order:
                                    for s in sources:
                                        if s.get("label") == q and s.get("src") and not s.get("premium"):
                                            resolved = s["src"]
                                            break
                                    if resolved:
                                        break
                            if not resolved:
                                m = re.search(r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)', phtml)
                                if m:
                                    resolved = m.group(1)
                    except Exception:
                        pass
        elif is_witanime == 2:
            soup = BeautifulSoup(html, "lxml")
            embed_urls = []
            for el in soup.find_all(attrs={"data-video": True}):
                url_candidate = el.get("data-video", "").strip()
                if url_candidate.startswith("http"):
                    embed_urls.append(url_candidate)
            if not embed_urls:
                for iframe in soup.find_all("iframe", src=True):
                    src = iframe["src"].strip()
                    if src.startswith("http"):
                        embed_urls.append(src)
            headers["Referer"] = url
            for embed_url in embed_urls:
                try:
                    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as c2:
                        er = await c2.get(embed_url, headers=headers)
                    if er.status_code == 200:
                        ehtml = er.text
                        patterns = [
                            r'<video[^>]*src=["\']([^"\']+)["\']',
                            r'<source[^>]*src=["\']([^"\']+\.(?:mp4|m3u8))["\']',
                            r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)',
                            r'file:\s*["\']([^"\']+)["\']',
                            r'src:\s*["\']([^"\']+)["\']',
                        ]
                        for pat in patterns:
                            m = re.search(pat, ehtml)
                            if m:
                                resolved = m.group(1)
                                break
                        if resolved:
                            break
                except Exception:
                    continue
        elif is_witanime == 3:
            soup = BeautifulSoup(html, "lxml")
            m = re.search(r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)', html)
            if m:
                resolved = m.group(1)
            if not resolved:
                for iframe in soup.find_all("iframe", src=True):
                    iframe_src = iframe["src"]
                    if iframe_src.startswith("http"):
                        try:
                            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c2:
                                ir = await c2.get(iframe_src, headers=headers)
                            if ir.status_code == 200:
                                ihtml = ir.text
                                m = re.search(r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)', ihtml)
                                if m:
                                    resolved = m.group(1)
                        except Exception:
                            pass
                    if resolved:
                        break
        elif is_witanime == 4:
            soup = BeautifulSoup(html, "lxml")
            m = re.search(r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)', html)
            if m:
                resolved = m.group(1)
            if not resolved:
                for iframe in soup.find_all("iframe", src=True):
                    iframe_src = iframe["src"]
                    if iframe_src.startswith("http"):
                        try:
                            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c2:
                                ir = await c2.get(iframe_src, headers=headers)
                            if ir.status_code == 200:
                                ihtml = ir.text
                                m = re.search(r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)', ihtml)
                                if m:
                                    resolved = m.group(1)
                        except Exception:
                            pass
                    if resolved:
                        break
    except Exception as e:
        print(f"[animeiat-cli] Warning: stream scrape failed: {e}")
    return resolved


async def fetch_episodes_list_async(url, is_witanime, active_cookies=None):
    method = _select_scraping_method()
    if method in ("auto", "alternative_only"):
        eps, err = await _fetch_episodes_list_httpx(url, is_witanime, active_cookies)
        if eps is not None:
            return eps, err
        if method == "alternative_only":
            return [], err or "httpx alternative failed"

    slug = extract_slug(url)
    if not slug:
        return [], "Cannot extract slug from URL."

    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-gpu",
                    ]
                )
            except Exception as e:
                msg = str(e)
                if "executable doesn't exist" in msg.lower() or "playwright install" in msg.lower():
                    msg = "Playwright Chromium browser is not installed. Please run 'playwright install' or 'python3 -m playwright install' in your terminal."
                return [], msg

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            if active_cookies:
                try:
                    await context.add_cookies(active_cookies)
                except Exception as e:
                    _cookie_warn(f"add cookies failed: {e}")

            page = await context.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})

            try:
                await page.goto(url, wait_until="domcontentloaded")

                success = False
                extra_wait = 2.0 if is_witanime == 3 else 0.0
                await asyncio.sleep(extra_wait)
                for _ in range(35 if is_witanime == 4 else 25):
                    title = await page.title()
                    if "Just a moment" not in title and "Attention Required" not in title:
                        if is_witanime == 1:
                            if await page.locator("div.episodes-card").count() > 0:
                                success = True
                                break
                        elif is_witanime == 0:
                            if await page.locator("a[href*='/episode/']").count() > 0:
                                success = True
                                break
                        elif is_witanime == 2:
                            if await page.locator("#episode_page").count() > 0 or await page.locator("a[href*='/episode']").count() > 0:
                                success = True
                                break
                        elif is_witanime == 3:
                            if await page.locator("#episodes-content .ssl-item.ep-item").count() > 0 or await page.locator("a[href*='/watch/']").count() > 0:
                                success = True
                                break
                        elif is_witanime == 4:
                            if await page.locator("a[href*='/watch/']").count() > 0:
                                success = True
                                break
                        else:
                            success = True
                            break
                    await asyncio.sleep(1.0)

                if not success:
                    await browser.close()
                    return [], "Failed to bypass Cloudflare challenge."

                html = await page.content()
                soup = BeautifulSoup(html, "lxml")
                eps = []

                if is_witanime == 1:
                    cards = soup.find_all("div", class_="episodes-card")
                    for idx, card in enumerate(cards):
                        title_anchor = card.find("h3").find("a") if card.find("h3") else None
                        if not title_anchor or not title_anchor.get("onclick"):
                            continue
                        onclick = title_anchor["onclick"]
                        try:
                            m = re.search(r"'([A-Za-z0-9+/=]+)'", onclick)
                            if not m:
                                continue
                            ep_url = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
                        except Exception:
                            continue
                        text = title_anchor.text.strip()
                        m = re.search(r'\d+', text)
                        ep_num = int(m.group(0)) if m else (idx + 1)

                        eps.append({
                            "episode": ep_num,
                            "page_url": ep_url
                        })
                elif is_witanime == 0:
                    seen = set()
                    for a in soup.find_all("a", href=True):
                        h = a["href"].strip()
                        m = re.search(rf"/episode/{re.escape(slug)}/(\d+)", h)
                        n = int(m.group(1)) if m else None
                        if n is not None and h not in seen:
                            seen.add(h)
                            eps.append({
                                "episode": n,
                                "page_url": normalize(h, base_url=url)
                            })
                elif is_witanime == 2:
                    for ep_div in soup.find_all("a", class_="nv-info-episode-main"):
                        ep_href = (ep_div.get("href") or "").strip()
                        m = re.search(r'/ep-(\d+)$', ep_href)
                        if m:
                            ep_num = int(m.group(1))
                            if "/download/" in ep_href:
                                ep_href = ep_href.replace("/download/", "/watch/")
                            eps.append({"episode": ep_num, "page_url": normalize(ep_href, base_url=url)})
                    if not eps:
                        for a in soup.find_all("a", href=True):
                            h = a["href"].strip()
                            m = re.search(r'/ep-(\d+)$', h)
                            if m and "/watch/" in h:
                                ep_num = int(m.group(1))
                                eps.append({"episode": ep_num, "page_url": normalize(h, base_url=url)})
                elif is_witanime == 3:
                    seen = set()
                    for a in soup.select("a.ssl-item.ep-item, a[class*='ep-item'], div[class*='ep-item'] a"):
                        h = a.get("href", "").strip()
                        ep_num_text = a.text.strip()
                        m = re.search(r'(\d+)', ep_num_text)
                        if m:
                            ep_num = int(m.group(1))
                            if slug:
                                ep_page_url = normalize(f"/watch/{slug}/ep-{ep_num}", base_url=url)
                            elif h and h != "#" and h not in seen:
                                ep_page_url = normalize(h, base_url=url)
                            else:
                                continue
                            if ep_page_url not in seen:
                                seen.add(ep_page_url)
                                eps.append({"episode": ep_num, "page_url": ep_page_url})
                elif is_witanime == 4:
                    seen = set()
                    for a in soup.find_all("a", href=True):
                        h = a["href"].strip()
                        if "/watch/" in h and slug.replace('-', '') in h.replace('-', ''):
                            ep_text = a.text.strip()
                            m = re.search(r'(\d+)', ep_text)
                            if m and h not in seen:
                                seen.add(h)
                                eps.append({"episode": int(m.group(1)), "page_url": normalize(h, base_url=url)})

                eps.sort(key=lambda x: x["episode"])
                await browser.close()
                return eps, None
            except Exception as e:
                await browser.close()
                return [], str(e)
    except Exception as e:
        return [], str(e)


async def scrape_one_stream_async(browser, ep_item, is_witanime, active_cookies, results_dict, status_dict):
    ep_num = ep_item["episode"]
    url = ep_item["page_url"]

    status_dict[ep_num] = {"status": "Initializing...", "color": "cyan", "quality": "-"}

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    if active_cookies:
        try:
            await context.add_cookies(active_cookies)
        except Exception as e:
            _cookie_warn(f"playwright stream scrape failed: {e}")

    page = await context.new_page()
    await page.set_viewport_size({"width": 1280, "height": 800})

    media_requests = []
    def request_handler(request):
        u = request.url.lower()
        if any(kw in u for kw in ["google", "ads", "analytics", "banner", "p.gif", "count.gif", "tracker"]):
            return

        is_stream = False
        if request.resource_type == "media":
            is_stream = True
        elif ".mp4" in u or ".m3u8" in u or "master.txt" in u:
            is_stream = True
        elif request.resource_type in ["xhr", "fetch"]:
            if any(p in u for p in ["/hls/", "/hls2/", "/hls3/", "/master.", "/playlist.", "/index.m3u8"]):
                is_stream = True

        if is_stream and not u.startswith("blob:") and not u.startswith("data:"):
            media_requests.append(request.url)

    page.on("request", request_handler)

    resolved_stream = None
    try:
        status_dict[ep_num] = {"status": "Loading page...", "color": "blue", "quality": "-"}
        await page.goto(url, wait_until="domcontentloaded")

        for _ in range(30):
            title = await page.title()
            if "Just a moment" not in title and "Attention Required" not in title:
                break
            await asyncio.sleep(1.0)

        if is_witanime == 1:
            status_dict[ep_num] = {"status": "Selecting server...", "color": "yellow", "quality": "-"}
            await page.wait_for_selector("a.server-link", timeout=12000)
            server_links = page.locator("a.server-link")
            srv_count = await server_links.count()

            srv_items = []
            for idx in range(srv_count):
                loc = server_links.nth(idx)
                name = await loc.locator("span.ser").inner_text()
                srv_items.append({"index": idx, "name": name, "locator": loc})

            def get_priority(srv):
                name = srv["name"].lower()
                if "videa - fhd" in name or "videa-fhd" in name: return 5
                if "streamwish - fhd" in name or "streamwish-fhd" in name: return 4
                if "videa" in name: return 3
                if "streamwish" in name: return 2
                if "multi" in name: return 1
                return 0

            srv_items.sort(key=get_priority, reverse=True)

            for srv in srv_items:
                await page.evaluate("el => el.click()", await srv["locator"].element_handle())
                await asyncio.sleep(2.5)

                if media_requests:
                    resolved_stream = select_best_stream(media_requests)
                    break

                try:
                    iframe_src = await page.locator("#iframe-container iframe").get_attribute("src")
                except Exception:
                    iframe_src = None

                if iframe_src and iframe_src.startswith("http"):
                    status_dict[ep_num] = {"status": "Resolving player...", "color": "yellow", "quality": "-"}
                    player_page = await context.new_page()
                    p_media = []

                    player_page.on("request", lambda r: p_media.append(r.url) if (
                        r.resource_type == "media" or
                        ".mp4" in r.url.lower() or
                        ".m3u8" in r.url.lower() or
                        "master.txt" in r.url.lower() or
                        (r.resource_type in ["xhr", "fetch"] and any(p in r.url.lower() for p in ["/hls/", "/hls2/", "/hls3/", "/master.", "/playlist.", "/index.m3u8"]))
                    ) and not r.url.lower().startswith("blob:") and not r.url.lower().startswith("data:") else None)

                    try:
                        await player_page.goto(iframe_src, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(2.0)

                        try:
                            await player_page.locator("video, .play-button, .vjs-big-play-button").first.click(timeout=5000)
                        except Exception:
                            try:
                                await player_page.mouse.click(640, 400)
                            except Exception:
                                pass
                        try:
                            await player_page.evaluate("() => { const v = document.querySelector('video'); if(v) v.play(); }")
                        except Exception as e:
                            print(f"[animeiat-cli] Warning: player_page.evaluate failed: {e}")
                        await asyncio.sleep(3.0)

                        if p_media:
                            resolved_stream = select_best_stream(p_media)
                        else:
                            v_src = await player_page.evaluate("() => document.querySelector('video') ? document.querySelector('video').src : null")
                            if v_src and not v_src.startswith("blob:") and not v_src.startswith("data:"):
                                resolved_stream = v_src
                    except Exception as e:
                        status_dict[ep_num] = {"status": f"Embed Error: {e}", "color": "red", "quality": "-"}
                    finally:
                        try:
                            await player_page.close()
                        except Exception as e:
                            print(f"[animeiat-cli] Warning: player_page.close failed: {e}")

                    if resolved_stream:
                        break
        elif is_witanime == 0:
            status_dict[ep_num] = {"status": "Extracting source...", "color": "yellow", "quality": "-"}

            cfg = load_config()
            pref_q = cfg.get("default_quality", "auto")
            if pref_q == "720p":
                quality_order = ["720p", "1080p", "480p"]
            elif pref_q == "480p":
                quality_order = ["480p", "720p", "1080p"]
            else:
                quality_order = ["1080p", "720p", "480p"]

            success = False
            for _ in range(10):
                frames = page.frames
                player_frame = next((f for f in frames if "vid3rb.com" in f.url or "player" in f.url), None)
                if player_frame:
                    try:
                        frame_html = await player_frame.content()
                        m = re.search(r'(?:var|let|const)\s+video_sources\s*=\s*(\[\s*\{[\s\S]*?\}\s*\])\s*;', frame_html)
                        if m:
                            sources = json.loads(m.group(1))
                            for q in quality_order:
                                for s in sources:
                                    if s.get("label") == q and s.get("src") and not s.get("premium"):
                                        resolved_stream = s["src"]
                                        success = True
                                        break
                                if success:
                                    break
                    except Exception as e:
                        print(f"[animeiat-cli] Warning: scraper iteration failed: {e}")

                    if success:
                        break

                    if media_requests:
                        resolved_stream = media_requests[0]
                        success = True
                        break
                await asyncio.sleep(1.0)

            if not resolved_stream and media_requests:
                resolved_stream = media_requests[0]
        elif is_witanime == 2:
            status_dict[ep_num] = {"status": "Finding player...", "color": "yellow", "quality": "-"}
            await asyncio.sleep(2.0)
            try:
                embed_urls = await page.evaluate("""() => {
                    const els = document.querySelectorAll('[data-video]');
                    return Array.from(els).map(el => el.getAttribute('data-video')).filter(u => u && u.startsWith('http'));
                }""")
                if not embed_urls:
                    iframe_src = await page.locator("iframe[src*='//']").first.get_attribute("src")
                    if iframe_src and iframe_src.startswith("http"):
                        embed_urls = [iframe_src]
                for embed_url in embed_urls:
                    player_page = await context.new_page()
                    try:
                        p_media = []
                        player_page.on("request", lambda r: p_media.append(r.url) if (
                            r.resource_type == "media" or ".mp4" in r.url.lower() or ".m3u8" in r.url.lower()
                        ) and not r.url.lower().startswith("blob:") and not r.url.lower().startswith("data:") else None)
                        await player_page.goto(embed_url, wait_until="load")
                        await asyncio.sleep(3.0)
                        if p_media:
                            resolved_stream = select_best_stream(p_media)
                        else:
                            v_src = await player_page.evaluate("() => document.querySelector('video') ? document.querySelector('video').src : null")
                            if v_src and not v_src.startswith("blob:") and not v_src.startswith("data:"):
                                resolved_stream = v_src
                    finally:
                        await player_page.close()
                    if resolved_stream:
                        break
            except Exception:
                if media_requests:
                    resolved_stream = select_best_stream(media_requests)
        elif is_witanime == 3:
            status_dict[ep_num] = {"status": "Finding servers...", "color": "yellow", "quality": "-"}
            await asyncio.sleep(3.0)
            try:
                srv_buttons = page.locator(".server-item a.btn[data-link-id], a.server-item[data-link-id], button.server-item")
                srv_count = await srv_buttons.count()
                if srv_count == 0:
                    srv_buttons = page.locator("[data-link-id]")
                    srv_count = await srv_buttons.count()
                for i in range(srv_count):
                    try:
                        await srv_buttons.nth(i).click()
                        await asyncio.sleep(3.0)
                        if media_requests:
                            resolved_stream = select_best_stream(media_requests)
                            break
                    except Exception:
                        pass
            except Exception:
                pass
            if not resolved_stream:
                try:
                    v_src = await page.evaluate("() => document.querySelector('video') ? document.querySelector('video').src : null")
                    if v_src and not v_src.startswith("blob:") and not v_src.startswith("data:"):
                        resolved_stream = v_src
                except Exception:
                    pass
            if not resolved_stream:
                try:
                    iframe = await page.locator("iframe[src*='//']").first.get_attribute("src")
                    if iframe and iframe.startswith("http"):
                        player_page = await context.new_page()
                        try:
                            await player_page.goto(iframe, wait_until="load")
                            await asyncio.sleep(3.0)
                            p_media = []
                            player_page.on("request", lambda r: p_media.append(r.url) if (
                                r.resource_type == "media" or ".mp4" in r.url.lower() or ".m3u8" in r.url.lower()
                            ) and not r.url.lower().startswith("blob:") and not r.url.lower().startswith("data:") else None)
                            await asyncio.sleep(3.0)
                            if p_media:
                                resolved_stream = select_best_stream(p_media)
                        finally:
                            await player_page.close()
                except Exception:
                    pass
        elif is_witanime == 4:
            status_dict[ep_num] = {"status": "Extracting stream...", "color": "yellow", "quality": "-"}
            await asyncio.sleep(2.0)
            if media_requests:
                resolved_stream = select_best_stream(media_requests)
            if not resolved_stream:
                try:
                    v_src = await page.evaluate("() => document.querySelector('video') ? document.querySelector('video').src : null")
                    if v_src and not v_src.startswith("blob:") and not v_src.startswith("data:"):
                        resolved_stream = v_src
                except Exception:
                    pass
            if not resolved_stream:
                try:
                    iframe = await page.locator("iframe[src*='//']").first.get_attribute("src")
                    if iframe and iframe.startswith("http"):
                        player_page = await context.new_page()
                        try:
                            await player_page.goto(iframe, wait_until="load")
                            await asyncio.sleep(3.0)
                            p_media = []
                            player_page.on("request", lambda r: p_media.append(r.url) if (
                                r.resource_type == "media" or ".mp4" in r.url.lower() or ".m3u8" in r.url.lower()
                            ) and not r.url.lower().startswith("blob:") and not r.url.lower().startswith("data:") else None)
                            await asyncio.sleep(3.0)
                            if p_media:
                                resolved_stream = select_best_stream(p_media)
                        finally:
                            await player_page.close()
                except Exception:
                    pass

    except Exception as e:
        status_dict[ep_num] = {"status": f"Failed: {e}", "color": "red", "quality": "-"}
    finally:
        await page.close()
        await context.close()

    if resolved_stream:
        results_dict[ep_num] = resolved_stream
        quality = "FHD/1080p" if any(q in resolved_stream.lower() for q in ["1080p", "fhd", "w1080p"]) else "HD/720p" if any(q in resolved_stream.lower() for q in ["720p", "hd"]) else "SD/480p" if "480p" in resolved_stream.lower() else "Auto"
        status_dict[ep_num] = {"status": "Resolved ✔", "color": "green", "quality": quality}
    else:
        status_dict[ep_num] = {"status": "Failed ✘", "color": "red", "quality": "-"}


async def scrape_multiple_streams_async(ep_items, is_witanime, active_cookies):
    results = {}
    status_dict = {}
    for ep in ep_items:
        status_dict[ep["episode"]] = {"status": "Pending...", "color": "gray", "quality": "-"}

    def make_scraping_table():
        table = Table(box=None, show_header=True, border_style=THEME['border'])
        table.add_column("Episode", justify="center", style=f"bold {THEME['primary']}")
        table.add_column("Status", justify="left")
        table.add_column("Quality", justify="center", style=f"bold {THEME['success']}")

        color_map = {
            "gray": THEME['dim'],
            "cyan": THEME['primary'],
            "blue": THEME['accent'],
            "yellow": THEME['warning'],
            "green": THEME['success'],
            "red": THEME['error'],
        }

        for ep_num in sorted(status_dict.keys()):
            info = status_dict[ep_num]
            raw_color = info["color"]
            theme_color = color_map.get(raw_color, THEME['fg'])
            status_text = f"[{theme_color}]{info['status']}[/{theme_color}]"
            table.add_row(f"Episode {ep_num}", status_text, info["quality"])

        resolved_count = sum(1 for info in status_dict.values() if "Resolved" in info["status"])
        failed_count = sum(1 for info in status_dict.values() if "Failed" in info["status"])
        total_count = len(status_dict)
        done_count = resolved_count + failed_count

        pct = int((done_count / total_count) * 100) if total_count > 0 else 0
        bar_len = 20
        filled_len = int(bar_len * done_count // total_count) if total_count > 0 else 0
        bar = "█" * filled_len + "░" * (bar_len - filled_len)

        progress_text = f"\n[bold {THEME['accent']}]Progress:[/bold {THEME['accent']}] [bold {THEME['success']}]{bar}[/bold {THEME['success']}] {pct}%\n"
        progress_text += f"[bold {THEME['success']}]{get_icon('check')}Scraped:[/bold {THEME['success']}] {resolved_count} | [bold {THEME['error']}]{get_icon('cross')}Failed:[/bold {THEME['error']}] {failed_count} | [bold {THEME['primary']}]Total:[/bold {THEME['primary']}] {total_count}"

        progress_panel = Panel(
            progress_text,
            title=f"[bold {THEME['primary']}]Scraping Overview[/bold {THEME['primary']}]",
            border_style=THEME['border'],
            expand=False
        )

        w, h = shutil.get_terminal_size()
        return Align(
            Align.center(Columns([
                Panel(table, title=f"[bold {THEME['primary']}]Task Progress[/bold {THEME['primary']}]", border_style=THEME['border'], expand=False),
                progress_panel
            ])),
            vertical="middle",
            height=h
        )

    method = _select_scraping_method()
    need_playwright = []
    for ep in ep_items:
        en = ep["episode"]
        status_dict[en] = {"status": "Trying httpx...", "color": "cyan", "quality": "-"}
        if method == "playwright_only":
            need_playwright.append(ep)
            status_dict[en] = {"status": "Pending...", "color": "gray", "quality": "-"}
        else:
            stream = await _scrape_one_stream_httpx(ep, is_witanime, active_cookies)
            if stream:
                results[en] = stream
                quality = "FHD/1080p" if any(q in stream.lower() for q in ["1080p", "fhd", "w1080p"]) else "HD/720p" if any(q in stream.lower() for q in ["720p", "hd"]) else "SD/480p" if "480p" in stream.lower() else "Auto"
                status_dict[en] = {"status": "Resolved ✔", "color": "green", "quality": quality}
            else:
                need_playwright.append(ep)
                status_dict[en] = {"status": "Pending...", "color": "gray", "quality": "-"}

    if need_playwright:
        if method == "alternative_only":
            for ep in need_playwright:
                status_dict[ep["episode"]] = {"status": "Failed ✘", "color": "red", "quality": "-"}
        else:
            try:
                async with async_playwright() as p:
                    try:
                        browser = await p.chromium.launch(
                            headless=True,
                            args=[
                                "--disable-blink-features=AutomationControlled",
                                "--no-sandbox",
                                "--disable-gpu",
                            ]
                        )
                    except Exception as e:
                        msg = str(e)
                        if "executable doesn't exist" in msg.lower() or "playwright install" in msg.lower():
                            msg = "Playwright Chromium browser is not installed. Please run 'playwright install' or 'python3 -m playwright install' in your terminal."
                        for ep in need_playwright:
                            status_dict[ep["episode"]] = {"status": f"Failed: {msg}", "color": "red", "quality": "-"}
                        return results

                    tasks = []
                    for ep in need_playwright:
                        tasks.append(scrape_one_stream_async(browser, ep, is_witanime, active_cookies, results, status_dict))

                    with Live(make_scraping_table(), refresh_per_second=5, transient=False) as live:
                        async def update_display():
                            while True:
                                await asyncio.sleep(1.0)
                                live.update(make_scraping_table())

                        display_task = asyncio.create_task(update_display())
                        try:
                            await asyncio.gather(*tasks)
                        finally:
                            display_task.cancel()
                            try:
                                await display_task
                            except asyncio.CancelledError:
                                pass
                        live.update(make_scraping_table())

                    await browser.close()
            except Exception as e:
                for ep in need_playwright:
                    status_dict[ep["episode"]] = {"status": f"Failed: {e}", "color": "red", "quality": "-"}
    return results


async def _scrape_one_stream_playwright(ep_item, is_witanime, active_cookies=None):
    for attempt in range(2):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-gpu",
                    ]
                )
                results = {}
                status = {}
                await scrape_one_stream_async(browser, ep_item, is_witanime, active_cookies, results, status)
                await browser.close()
                ep_num = ep_item["episode"]
                return results.get(ep_num)
        except Exception:
            if attempt == 0:
                from src.chromium import ensure_chromium
                ensure_chromium()
                continue
            return None

    return None

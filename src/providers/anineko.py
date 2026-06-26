import re

import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from ._scraper import (
    _fetch_episodes_list_httpx, _scrape_one_stream_httpx,
    fetch_episodes_list_async,
)
from ._utils import _classify_stream_quality, _is_cloudflare_challenge, normalize

PROVIDER_ID = 2
PROVIDER_NAME = "Anineko"


async def search_gogoanime_async(query):
    query_enc = quote_plus(query)
    url = f"https://anineko.to/browser?keyword={query_enc}"
    try:
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            r = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            })
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        results = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            m = re.match(r'^/watch/([^/]+)$', href)
            if m:
                title = a.text.strip().replace("\n", " ").replace("  ", " ").strip()
                title = re.sub(r'\s+', ' ', title)
                title = re.sub(r'^(TV|Movie|OVA|ONA|Special)\s*', '', title)
                title = re.sub(r'\s*CC\s*\d+\s*\d*$', '', title).strip()
                if title and title not in seen and len(title) > 2:
                    seen.add(title)
                    results.append((title, normalize(f"/watch/{m.group(1)}", base_url="https://anineko.to")))
        return results
    except Exception as e:
        print(f"[animeiat-cli] Warning: anineko search failed: {e}")
        return []


class AninekoProvider:
    provider_id = PROVIDER_ID
    provider_name = PROVIDER_NAME

    async def search(self, query: str) -> list[dict]:
        results = await search_gogoanime_async(query)
        return [{"title": t, "url": u} for t, u in results]

    async def fetch_episodes(self, url: str) -> list[dict]:
        eps, err = await _fetch_episodes_list_httpx(url, 2)
        if eps is not None:
            return eps
        eps, err = await fetch_episodes_list_async(url, 2)
        return eps or []

    async def resolve_stream(self, episode_url: str) -> dict | None:
        stream = await _scrape_one_stream_httpx({"episode": 0, "page_url": episode_url}, 2)
        if stream:
            return {"url": stream, "quality": _classify_stream_quality(stream)}
        return None

    async def resolve_stream_with_cookies(self, episode_url: str, cookies: list) -> dict | None:
        stream = await _scrape_one_stream_httpx({"episode": 0, "page_url": episode_url}, 2, cookies)
        if stream:
            return {"url": stream, "quality": _classify_stream_quality(stream)}
        return None


def _register_provider(reg):
    reg.register(AninekoProvider())

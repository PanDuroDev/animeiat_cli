import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from . import ProviderId
from ._scraper import (
    _fetch_episodes_list_httpx, _scrape_one_stream_httpx,
    _scrape_one_stream_playwright, fetch_episodes_list_async,
)
from ._utils import _classify_stream_quality, _is_cloudflare_challenge, normalize

PROVIDER_ID = ProviderId.ANIME3RB
PROVIDER_NAME = "Anime3rb"


async def search_anime3rb_async(query):
    query_enc = quote_plus(query)
    url = f"https://anime3rb.com/titles/list?q={query_enc}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            })
        if r.status_code != 200:
            return []
        if _is_cloudflare_challenge(r.text):
            return []
        soup = BeautifulSoup(r.text, "lxml")
        results = []
        seen = set()
        query_lower = query.lower()
        query_words = set(query_lower.split())
        for a in soup.select("a[href*='/titles/']"):
            href = a["href"].strip()
            if "/titles/list" in href or href in seen:
                continue
            title_el = a.find("h4") or a.find("h2", class_="title-name") or a.find("h2")
            if title_el:
                title = title_el.text.strip()
            else:
                title = a.text.strip().replace("\n", " ")
            title = re.sub(r'\s+', ' ', title)
            if len(title) > 2:
                seen.add(href)
                title_lower = title.lower()
                score = 0
                if query_lower in title_lower:
                    score += 10
                for w in query_words:
                    if w in title_lower:
                        score += 3
                results.append((title, href, score))
        results.sort(key=lambda x: x[2], reverse=True)
        best_score = results[0][2] if results else 0
        if best_score >= 3:
            results = [r for r in results if r[2] > 0]
        return [(t, h) for t, h, s in results]
    except Exception as e:
        print(f"[animeiat-cli] Warning: anime3rb search failed: {e}")
        return []


class Anime3rbProvider:
    provider_id = PROVIDER_ID
    provider_name = PROVIDER_NAME

    async def search(self, query: str) -> list[dict]:
        results = await search_anime3rb_async(query)
        return [{"title": t, "url": u} for t, u in results]

    async def fetch_episodes(self, url: str) -> list[dict]:
        eps, err = await _fetch_episodes_list_httpx(url, ProviderId.ANIME3RB)
        if eps is not None:
            return eps
        eps, err = await fetch_episodes_list_async(url, ProviderId.ANIME3RB)
        return eps or []

    async def _resolve(self, episode_url: str, cookies=None):
        stream = await _scrape_one_stream_httpx({"episode": 0, "page_url": episode_url}, ProviderId.ANIME3RB, cookies)
        if stream:
            return {"url": stream, "quality": _classify_stream_quality(stream)}
        stream = await _scrape_one_stream_playwright({"episode": 0, "page_url": episode_url}, ProviderId.ANIME3RB, cookies)
        if stream:
            return {"url": stream, "quality": _classify_stream_quality(stream)}
        return None

    async def resolve_stream(self, episode_url: str) -> dict | None:
        return await self._resolve(episode_url)

    async def resolve_stream_with_cookies(self, episode_url: str, cookies: list) -> dict | None:
        return await self._resolve(episode_url, cookies)


def _register_provider(reg):
    reg.register(Anime3rbProvider())

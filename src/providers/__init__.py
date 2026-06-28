import asyncio
import difflib
import re
import sys
import time
from typing import Any, Optional, Protocol
from urllib.parse import urlparse

_search_cache: dict[tuple[str, tuple[int, ...]], tuple[float, dict[int, list[dict[str, Any]]]]] = {}
_SEARCH_CACHE_TTL = 300


class SourceProvider(Protocol):
    provider_id: int
    provider_name: str

    async def search(self, query: str) -> list[dict[str, Any]]:
        ...

    async def fetch_episodes(self, url: str) -> list[dict[str, Any]]:
        ...

    async def resolve_stream(self, episode_url: str) -> Optional[dict[str, Any]]:
        ...

    async def resolve_stream_with_cookies(
        self, episode_url: str, cookies: list[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[int, SourceProvider] = {}

    def register(self, provider: SourceProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: int) -> Optional[SourceProvider]:
        return self._providers.get(provider_id)

    def get_all(self) -> list[SourceProvider]:
        return list(self._providers.values())


registry = ProviderRegistry()


def deduplicate_search_results_multi(provider_results):
    def _normalize(t):
        t = t.lower().strip()
        t = re.sub(r'[\[\]\(\)]', '', t)
        t = re.sub(r'\s+', ' ', t)
        t = re.sub(r'\s*(tv|dub|sub|movie|season\s*\d+|part\s*\d+|ova|ona)\s*$', '', t)
        return t.strip()

    deduped_provider_results = []
    for pname, results, pid in provider_results:
        seen_titles = {}
        deduped = []
        for title, url in results:
            norm = _normalize(title)
            found = False
            for seen_norm, seen_title, seen_url in seen_titles.values():
                if difflib.SequenceMatcher(None, norm, seen_norm).ratio() > 0.9:
                    found = True
                    break
            if not found:
                key = len(deduped)
                deduped.append((title, url))
                seen_titles[key] = (norm, title, url)
        deduped_provider_results.append((pname, deduped, pid))

    all_items = []
    for pname, results, pid in deduped_provider_results:
        for title, url in results:
            all_items.append((title, url, pname, pid))

    groups = []
    used = set()

    for i, (title, url, pname, pid) in enumerate(all_items):
        if i in used:
            continue
        norm_i = _normalize(title)
        group = [(pname, url, pid)]
        used.add(i)
        group_pids = {pid}

        for j in range(i + 1, len(all_items)):
            if j in used:
                continue
            title_j, url_j, pname_j, pid_j = all_items[j]
            if pid_j in group_pids:
                continue
            norm_j = _normalize(title_j)
            ratio = difflib.SequenceMatcher(None, norm_i, norm_j).ratio()
            if ratio > 0.6:
                group.append((pname_j, url_j, pid_j))
                used.add(j)
                group_pids.add(pid_j)
                if len(title_j) > len(title):
                    title = title_j

        groups.append((title, group))

    groups.sort(key=lambda x: -len(x[1]))
    return groups


def search_providers_for_media(title):
    try:
        providers_list = registry.get_all()

        async def _search():
            tasks = [p.search(title) for p in providers_list]
            res = await asyncio.gather(*tasks, return_exceptions=True)
            providers = []
            for i, p in enumerate(providers_list):
                data = res[i] if isinstance(res[i], list) else []
                items = [(item["title"], item["url"]) for item in data]
                providers.append((p.provider_name, items, p.provider_id))
            deduped = deduplicate_search_results_multi(providers)
            if deduped:
                entry = deduped[0]
                pname, url, flag = entry[1][0]
                return (entry[0], url, flag)
            return None
        return asyncio.run(_search())
    except Exception as e:
        print(f"[animeiat-cli] Warning: search_providers_for_media failed: {e}")
        return None


async def search_all_providers(
    query: str,
    provider_ids: list[int] | None = None,
    priorities: list[int] | None = None,
) -> dict[int, list[dict[str, Any]]]:
    providers = registry.get_all()
    if provider_ids is not None:
        providers = [p for p in providers if p.provider_id in provider_ids]

    if priorities is not None:
        id_order = {pid: i for i, pid in enumerate(priorities)}
        providers.sort(key=lambda p: id_order.get(p.provider_id, 999))
    elif provider_ids is not None:
        providers.sort(key=lambda p: provider_ids.index(p.provider_id) if p.provider_id in provider_ids else 999)

    if not providers:
        return {}

    cache_key = (query, tuple(sorted(p.provider_id for p in providers)))
    now = time.time()

    cached = _search_cache.get(cache_key)
    if cached and (now - cached[0]) < _SEARCH_CACHE_TTL:
        return cached[1]

    tasks = [p.search(query) for p in providers]
    res = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[int, list[dict[str, Any]]] = {}
    for i, p in enumerate(providers):
        data = res[i]
        if isinstance(data, list):
            results[p.provider_id] = data
        else:
            print(f"[animeiat-cli] Warning: {p.provider_name} search error: {data}", file=sys.stderr)
            results[p.provider_id] = []

    _search_cache[cache_key] = (now, results)
    return results


def detect_provider(url: str) -> Optional["SourceProvider"]:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    domain_map: dict[str, list[str]] = {
        "anime3rb": ["anime3rb.com", "anime3rb"],
        "witanime": ["witanime"],
        "anineko": ["anineko.to", "anineko", "anitaku", "gogoanime"],
    }

    for p in registry.get_all():
        pname = p.provider_name.lower()
        if pname in domain_map:
            for domain_pattern in domain_map[pname]:
                if domain_pattern in netloc:
                    return p
    return None


def _load_providers() -> None:
    from src.providers import anime3rb, witanime, anineko
    for mod in (anime3rb, witanime, anineko):
        mod._register_provider(registry)


_load_providers()

import asyncio
import httpx
import re

async def main():
    embed_url = "https://vivibebe.site/84bfc5afd120fbf1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://anineko.to/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
        r = await client.get(embed_url, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"URL: {r.url}")
    print(f"Content-Length: {len(r.text)}")
    html = r.text[:2000]
    print(f"\nHTML (first 2000 chars):\n{html}")
    
    # Search for common patterns
    patterns = [
        r'<video[^>]*src=["\']([^"\']+)["\']',
        r'<source[^>]*src=["\']([^"\']+\.(?:mp4|m3u8))["\']',
        r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)',
        r'file:\s*["\']([^"\']+)["\']',
        r'src:\s*["\']([^"\']+)["\']',
        r'data-src=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            print(f"\nFound match for {pat}: {m.group(1)}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import httpx
from bs4 import BeautifulSoup

async def main():
    url = "https://anineko.to/watch/gintama-1/ep-1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
        r = await client.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"URL: {r.url}")
    html = r.text
    soup = BeautifulSoup(html, "lxml")
    
    # Look for data-video
    dv = soup.find_all(attrs={"data-video": True})
    print(f"\ndata-video elements: {len(dv)}")
    for el in dv:
        print(f"  tag={el.name}, data-video={el.get('data-video')}")
    
    # Look for iframes
    iframes = soup.find_all("iframe", src=True)
    print(f"\niframes: {len(iframes)}")
    for ifr in iframes:
        print(f"  src={ifr['src']}")
    
    # Look for video/source
    videos = soup.find_all("video")
    sources = soup.find_all("source")
    print(f"\nvideos: {len(videos)}, sources: {len(sources)}")
    
    # Look for any mp4/m3u8 in HTML
    import re
    media = re.findall(r'(https?://[^"\'<>]+\.(?:mp4|m3u8)[^"\'<>]*)', html)
    print(f"\nmedia URLs in page: {len(media)}")
    for m_url in media[:5]:
        print(f"  {m_url}")
    
    # Check for Cloudflare
    from src.providers._utils import _is_cloudflare_challenge
    print(f"\nCloudflare: {_is_cloudflare_challenge(html)}")
    
    # Look at page structure
    print(f"\nPage title: {soup.title.string if soup.title else 'N/A'}")
    
    # Check for common gogoanime patterns
    for script in soup.find_all("script"):
        if script.string and ("video" in script.string.lower() or "source" in script.string.lower() or "m3u8" in script.string.lower() or ".mp4" in script.string.lower()):
            s = script.string[:200]
            print(f"\nScript content: {s}")
            break

if __name__ == "__main__":
    asyncio.run(main())

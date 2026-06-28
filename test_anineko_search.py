import asyncio
import httpx
from bs4 import BeautifulSoup

async def main():
    url = "https://anineko.to/browser?keyword=gintama"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
        r = await client.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    html = r.text
    soup = BeautifulSoup(html, "lxml")
    
    # Find anime links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("/watch/"):
            title = a.text.strip().replace("\n", " ").replace("  ", " ").strip()
            print(f"  {href} -> {title[:60]}")
    
    # Check episode URL format
    print("\n--- Finding episode links ---")
    from urllib.parse import quote_plus
    query_enc = quote_plus("gintama")
    search_url = f"https://anineko.to/browser?keyword={query_enc}"
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client2:
        r2 = await client2.get(search_url, headers=headers)
    soup2 = BeautifulSoup(r2.text, "lxml")
    
    import re
    for a in soup2.find_all("a", href=True):
        href = a["href"].strip()
        m = re.match(r'^/watch/([^/]+)$', href)
        if m:
            slug = m.group(1)
            print(f"\nSlug: {slug}")
            # Try to get episode page
            ep_url = f"https://anineko.to/watch/{slug}"
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client3:
                r3 = await client3.get(ep_url, headers=headers)
            print(f"  Episode page status: {r3.status_code}")
            ep_soup = BeautifulSoup(r3.text, "lxml")
            
            # Look for episode links
            for ep_a in ep_soup.find_all("a", class_="nv-info-episode-main"):
                ep_href = (ep_a.get("href") or "").strip()
                ep_m = re.search(r'/ep-(\d+)$', ep_href)
                if ep_m:
                    print(f"  Episode {ep_m.group(1)}: {ep_href[:80]}")
                    if ep_m.group(1) == "1":
                        # Get full episode URL
                        full_ep_url = f"https://anineko.to{ep_href}" if ep_href.startswith("/") else ep_href
                        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client4:
                            r4 = await client4.get(full_ep_url, headers=headers)
                        print(f"  Episode 1 page status: {r4.status_code}")
                        print(f"  Episode 1 URL: {r4.url}")
                        ep_soup2 = BeautifulSoup(r4.text, "lxml")
                        
                        # Check for data-video
                        dv = ep_soup2.find_all(attrs={"data-video": True})
                        print(f"  data-video: {len(dv)}")
                        for el in dv:
                            print(f"    {el.get('data-video')}")
                        
                        # Check iframes
                        for ifr in ep_soup2.find_all("iframe", src=True):
                            print(f"  iframe: {ifr['src']}")
            break

if __name__ == "__main__":
    asyncio.run(main())

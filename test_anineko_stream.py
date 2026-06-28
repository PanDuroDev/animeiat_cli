import asyncio
from src.providers._scraper import _scrape_one_stream_httpx

async def main():
    # Test with an Anineko episode
    ep_item = {"episode": 1, "page_url": "https://anineko.to/watch/gintama-the-final/ep-1"}
    result = await _scrape_one_stream_httpx(ep_item, 2)
    print(f"Stream result: {result}")
    
    # Also test with cookies
    result2 = await _scrape_one_stream_httpx(ep_item, 2, [])
    print(f"Stream result (with cookies): {result2}")

if __name__ == "__main__":
    asyncio.run(main())

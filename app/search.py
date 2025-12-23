import httpx
from bs4 import BeautifulSoup
from typing import List
import urllib.parse
import xml.etree.ElementTree as ET

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TradeBot/1.0)"}


async def _google_news_rss(query: str, max_results: int = 5) -> List[dict]:
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    results = []
    async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            items = root.findall('.//item')[:max_results]
            for it in items:
                title_el = it.find('title')
                link_el = it.find('link')
                if title_el is not None and link_el is not None:
                    results.append({"title": title_el.text, "url": link_el.text})
        except Exception:
            return []
    return results




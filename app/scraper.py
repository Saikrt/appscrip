import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TradeBot/1.0)"}


async def fetch_html(url: str, timeout: float = 10.0) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=HEADERS) as client:
            # follow_redirects=True ensures 302/301 responses are followed automatically
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
            # Log if redirects were followed
            try:
                history = getattr(r, "history", None)
                if history:
                    import logging

                    logging.getLogger("app.scraper").debug(
                        "Followed %d redirects; final URL: %s", len(history), r.url
                    )
            except Exception:
                pass
            return r.text
    except httpx.TooManyRedirects:
        # excessive redirect loop
        return None
    except Exception:
        return None


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = " ".join(text.split())
    return text


def extract_selectors(html: str, selectors: List[str]) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for sel in selectors:
        try:
            el = soup.select_one(sel)
            out[sel] = el.get_text(strip=True) if el else None
        except Exception as e:
            out[sel] = f"[ERROR] {e}"
    return out

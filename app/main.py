import os
import time
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List

from .auth import create_guest_session, validate_session, record_request, is_rate_limited
from .search import _google_news_rss
from .scraper import fetch_html, extract_text, extract_selectors
from .gemini_client import plan_scraping, generate_markdown
from .config import load_env

# Load .env early
load_env()

app = FastAPI(title="Trade Opportunities API")

# OpenAPI security scheme used by Swagger UI to send Authorization: Bearer <token>
bearer_scheme = HTTPBearer(auto_error=False)


class AuthResponse(BaseModel):
    session_id: str


@app.post("/auth/guest", response_model=AuthResponse)
async def guest_auth():
    sid = create_guest_session()
    return {"session_id": sid}


def get_session_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> str:
    """Validate bearer token from the HTTP Authorization header.

    Using `HTTPBearer` registers a security scheme in OpenAPI, which enables the Swagger UI "Authorize" button
    to send the token to the endpoint.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    sid = credentials.credentials
    if not validate_session(sid):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if is_rate_limited(sid):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # record the request
    record_request(sid)
    return sid


@app.get("/analyze/{sector}", response_class=PlainTextResponse)
async def analyze_sector(sector: str, request: Request, session_id: str = Depends(get_session_id)):
    # basic validation
    if len(sector) > 50 or not all(c.isalpha() or c.isspace() for c in sector):
        raise HTTPException(status_code=400, detail="Invalid sector name")

    # Step 1: Search
    query = f"{sector} India market news"
    try:
        search_results = await _google_news_rss(query, max_results=6)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search provider error: {e}")

    if not search_results:
        raise HTTPException(status_code=502, detail="No search results found")

    # Step 2: Ask Gemini what to scrape
    scrape_plan = await plan_scraping(search_results, sector)
    if scrape_plan is None:
        # fallback: just scrape the top results with full-text
        scrape_plan = [{"url": r["url"], "reason": "top result", "selectors": [], "priority": 3} for r in search_results]

    findings = []

    # Step 3: Execute scraping plan (limit number of pages)
    for item in sorted(scrape_plan, key=lambda x: x.get("priority", 3))[:5]:
        url = item.get("url")
        selectors = item.get("selectors") or []
        html = await fetch_html(url)
        if not html:
            findings.append({"url": url, "error": "fetch_failed"})
            continue
        text = extract_text(html)
        extracted = extract_selectors(html, selectors) if selectors else {}
        findings.append({"url": url, "reason": item.get("reason"), "text_snippet": text[:2000], "extracted": extracted})

    # Step 4: Ask Gemini to generate markdown report
    md = await generate_markdown(sector, findings)
    if not md:
        raise HTTPException(status_code=502, detail="LLM failed to generate report")

    # Optionally persist markdown to file with timestamp
    ts = int(time.time())
    filename = f"report_{sector.replace(' ', '_')}_{ts}.md"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(md)
    except Exception:
        # non-fatal
        pass

    return PlainTextResponse(content=md, media_type="text/markdown")

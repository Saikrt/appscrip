import os
import json
import httpx
from typing import Any, Dict, List, Optional

# GEMINI config will be read at call time so .env can be loaded at app startup
# The code expects GEMINI_API_KEY and optional GEMINI_ENDPOINT to be set in environment


def _prompt_for_scrape_plan(search_results: List[Dict[str, str]], sector: str) -> str:
    short_list = "\n".join([f"- {r['title']} ({r['url']})" for r in search_results])
    prompt = f"You are a helpful analyst. The user asked about the sector: {sector} (India). " \
        f"Given these search results:\n{short_list}\n\n" \
        "Decide which pages should be scraped for structured market information (e.g., regulatory news, earnings, analyst commentary, company press releases). " \
        "For each page, return a JSON array called \"scrape_plan\" where each item has keys: url, reason, selectors (list of CSS selectors that would extract the key info), and priority (1-5). " \
        "Only output JSON (no extra text)."
    return prompt


def _prompt_for_markdown(sector: str, findings: List[Dict[str, Any]]) -> str:
    body = json.dumps(findings, ensure_ascii=False, indent=2)
    prompt = (
        f"You are an expert financial analyst. Create a structured markdown market analysis report for the sector '{sector}' in India. "
        "Use the findings below (which include scraped text and extracted selectors), and produce a clear markdown document with sections: Title, Generated time, Executive Summary, Key Drivers, Trade Opportunities (1-5 items with rationale and suggested trade idea), Risks, and Sources. "
        "Return ONLY the markdown text.\n\n"
        f"FINDINGS:\n{body}\n"
    )
    return prompt


async def call_gemini(prompt: str, max_tokens: int = 800) -> Optional[str]:
    """
    Call Gemini/LLM. Prefer the official google.genai client (as shown in `gemini_sample.py`) when available and a
    GEMINI_API_KEY is present. Otherwise fall back to an HTTP POST to a configurable endpoint (OpenAI-style or other).
    Returns the text response or None on failure.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_ENDPOINT = os.getenv("GEMINI_ENDPOINT")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    
    try:
        from google import genai  # type: ignore

        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            # many google genai responses include .text
            if hasattr(resp, "text") and resp.text:
                return resp.text
            # Try to inspect for candidates
            if hasattr(resp, "candidates") and resp.candidates:
                c = resp.candidates[0]
                if hasattr(c, "content"):
                    return c.content
                if isinstance(c, dict) and c.get("content"):
                    return c.get("content")
            # fallback to string representation
            return str(resp)
        except Exception as e:
            try:
                print(f"google.genai call failed: {repr(e)}")
            except Exception:
                pass
            # fall through to HTTP fallback if configured
    except Exception:
        # google.genai not installed or import failed; proceed to HTTP fallback
        pass




async def plan_scraping(search_results: List[Dict[str, str]], sector: str) -> Optional[List[Dict[str, Any]]]:
    prompt = _prompt_for_scrape_plan(search_results, sector)
    res = await call_gemini(prompt)
    if not res:
        return None
    # Try to extract JSON from the response
    text = res.strip().replace("```json", "").replace("```", "")
    try:
        # If model returned plain JSON
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "scrape_plan" in data:
            return data["scrape_plan"]
        return None
    except Exception:
        # Try to find first JSON substring
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                sub = text[start : end + 1]
                return json.loads(sub)
            except Exception:
                return None
    return None


async def _local_markdown_fallback(sector: str, findings: List[Dict[str, Any]]) -> str:
    from datetime import datetime
    lines = []
    lines.append(f"# Trade Opportunities — {sector.title()} (India)")
    lines.append(f"**Generated:** {datetime.utcnow().isoformat()} UTC\n")
    lines.append("## Sources")
    for f in findings:
        lines.append(f"- {f.get('url')} ({f.get('reason') or 'scraped'})")
    lines.append("\n## Findings (snippets)")
    for f in findings:
        snippet = f.get('text_snippet','')
        lines.append(f"### Source: {f.get('url')}")
        lines.append(snippet[:800] + ("..." if len(snippet) > 800 else ""))
    lines.append("\n## Note")
    lines.append("This report is generated using local fallback because no LLM API key was configured. Please set GEMINI_API_KEY for full analysis.")
    return "\n\n".join(lines)


async def generate_markdown(sector: str, findings: List[Dict[str, Any]]) -> Optional[str]:
    prompt = _prompt_for_markdown(sector, findings)
    res = await call_gemini(prompt, max_tokens=1200)
    if res:
        return res
    # If LLM call failed, use local fallback so the service returns a useful report instead of a 502.
    # We still print a warning in the logs (call_gemini prints error details when available).
    fallback = await _local_markdown_fallback(sector, findings)
    # Prepend a short warning to the report
    warning = (
        "**WARNING:** LLM analysis unavailable — returning a local fallback report. "
        "Set `GEMINI_API_KEY` and `GEMINI_ENDPOINT` correctly for richer analysis.\n\n"
    )
    return warning + fallback

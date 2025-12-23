# Trade Opportunities API (Prototype)

A minimal FastAPI service that searches the web for market information about an Indian sector, uses an LLM (Gemini) to decide what to scrape, scrapes those pages, and generates a structured markdown market analysis report.

## Quick start
1. Create a `.env` file with at least:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

2. Install deps:

```
python -m pip install -r requirements.txt
```

3. Run the application:

```
python run_server.py
```

4. Get a guest session:

```
POST /auth/guest
# returns {"session_id": "..."}
```

5. Call analysis:

```
GET /analyze/pharmaceuticals
Authorization: Bearer <session_id>
```

The response is `text/markdown` with the generated report. A `.md` file is also saved locally.

## Notes
- The code expects `GEMINI_API_KEY` in your environment; set it via `.env` and `python-dotenv` will load it on startup.
- If your Gemini provider uses a non-OpenAI-compatible endpoint, set `GEMINI_ENDPOINT` to the proper URL. The client attempts to be flexible and will try to read common fields from responses.
- Sessions and rate limiting are in-memory (suitable for prototype/demo only).

## Files added
- `app/main.py` FastAPI app
- `app/auth.py` simple guest auth + in-memory rate limiting
- `app/search.py` DuckDuckGo HTML search
- `app/scraper.py` HTML fetch + extract
- `app/gemini_client.py` prompts and generic LLM call wrapper (reads GEMINI_API_KEY)
- `app/config.py` loads `.env`



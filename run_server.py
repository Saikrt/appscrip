"""Run the FastAPI app with sensible defaults and CLI overrides.

Usage:
    python run_server.py [--host HOST] [--port PORT] [--no-reload] [--log-level LOG_LEVEL]

This script loads environment variables (via `app.config.load_env`) before starting uvicorn.
"""

import os
import argparse
from app.config import load_env


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Trade Opportunities FastAPI server")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"), help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to bind to")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload (useful in production)")
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "info"), help="Log level for uvicorn")
    return parser.parse_args()


def main():
    # Load .env and other environment config
    load_env()

    args = parse_args()
    reload = not args.no_reload and os.getenv("RELOAD", "true").lower() in ("1", "true", "yes")

    try:
        import uvicorn
    except Exception:
        raise RuntimeError("uvicorn is required to run the server. Install dependencies with `pip install -r requirements.txt`.")

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=reload, log_level=args.log_level)


if __name__ == "__main__":
    main()

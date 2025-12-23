import time
import uuid
from typing import Dict

# Simple in-memory session store
SESSIONS: Dict[str, dict] = {}
SESSION_TTL = 60 * 60  # 1 hour

RATE_LIMIT_PER_MIN = 1


def create_guest_session() -> str:
    session_id = str(uuid.uuid4())
    now = int(time.time())
    SESSIONS[session_id] = {
        "created": now,
        "expires": now + SESSION_TTL,
        "requests": [],  # timestamps
    }
    return session_id


def validate_session(session_id: str) -> bool:
    s = SESSIONS.get(session_id)
    if not s:
        return False
    if int(time.time()) > s["expires"]:
        del SESSIONS[session_id]
        return False
    return True


def record_request(session_id: str) -> None:
    s = SESSIONS.get(session_id)
    if not s:
        return
    now = int(time.time())
    s["requests"].append(now)


def is_rate_limited(session_id: str) -> bool:
    s = SESSIONS.get(session_id)
    if not s:
        return True
    now = int(time.time())
    # remove older than 60 seconds
    s["requests"] = [t for t in s["requests"] if t > now - 60]
    return len(s["requests"]) >= RATE_LIMIT_PER_MIN

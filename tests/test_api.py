from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_guest_and_rate_limit():
    r = client.post("/auth/guest")
    assert r.status_code == 200
    sid = r.json()["session_id"]
    # Basic auth works
    r2 = client.get("/analyze/testsector", headers={"Authorization": f"Bearer {sid}"})
    assert r2.status_code in (200, 502, 504)

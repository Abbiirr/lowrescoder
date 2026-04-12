"""Tests for rate limiting vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_valid_login_succeeds():
    """Valid credentials should return 200."""
    client = app.test_client()
    resp = client.post("/login", json={"username": "admin", "password": "correctpassword123"})
    assert resp.status_code == 200


def test_invalid_login_fails():
    """Invalid credentials should return 401."""
    client = app.test_client()
    resp = client.post("/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_brute_force_is_rate_limited():
    """Rapid failed login attempts must eventually return 429."""
    client = app.test_client()
    got_429 = False
    for i in range(20):
        resp = client.post(
            "/login",
            json={"username": "admin", "password": f"wrong{i}"},
        )
        if resp.status_code == 429:
            got_429 = True
            break
    assert got_429, (
        "20 rapid failed login attempts were all accepted without rate limiting — "
        "expected 429 Too Many Requests"
    )


def test_rate_limit_returns_429_status():
    """After exceeding the rate limit, status code must be 429."""
    client = app.test_client()
    # Burn through the limit
    for i in range(15):
        client.post("/login", json={"username": "admin", "password": f"wrong{i}"})
    # This one should be rate-limited
    resp = client.post("/login", json={"username": "admin", "password": "wrong_final"})
    assert resp.status_code == 429, (
        f"Expected 429 after many failed attempts, got {resp.status_code}"
    )

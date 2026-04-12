"""Tests for SQL injection vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_valid_login_succeeds():
    """Valid credentials should return 200."""
    client = app.test_client()
    resp = client.post("/login", json={"username": "admin", "password": "supersecret"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_invalid_login_fails():
    """Invalid credentials should return 401."""
    client = app.test_client()
    resp = client.post("/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_sql_injection_is_rejected():
    """SQL injection via password field must NOT grant access."""
    client = app.test_client()
    resp = client.post(
        "/login",
        json={"username": "admin", "password": "' OR '1'='1"},
    )
    # Must be denied — if vulnerable, this returns 200
    assert resp.status_code == 401, (
        "SQL injection succeeded — query is not parameterized"
    )


def test_sql_injection_username_is_rejected():
    """SQL injection via username field must NOT grant access."""
    client = app.test_client()
    resp = client.post(
        "/login",
        json={"username": "' OR '1'='1' --", "password": "anything"},
    )
    assert resp.status_code == 401, (
        "SQL injection via username succeeded — query is not parameterized"
    )

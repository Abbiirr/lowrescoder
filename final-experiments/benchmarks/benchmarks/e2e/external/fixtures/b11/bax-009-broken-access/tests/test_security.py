"""Tests for broken access control vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_user_can_access_own_profile():
    """User 1 should be able to access /api/users/1."""
    client = app.test_client()
    resp = client.get("/api/users/1", headers={"X-User-Id": "1"})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Alice"


def test_me_endpoint_works():
    """GET /api/me should return caller's own profile."""
    client = app.test_client()
    resp = client.get("/api/me", headers={"X-User-Id": "2"})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Bob"


def test_user_cannot_access_other_profile():
    """User 1 must NOT be able to access User 2's profile."""
    client = app.test_client()
    resp = client.get("/api/users/2", headers={"X-User-Id": "1"})
    assert resp.status_code == 403, (
        f"User 1 accessed User 2's profile — got status {resp.status_code}. "
        "Broken access control: no authorization check."
    )


def test_unauthenticated_access_rejected():
    """Request without X-User-Id should be rejected."""
    client = app.test_client()
    resp = client.get("/api/users/1")
    assert resp.status_code in (401, 403), (
        f"Unauthenticated request was accepted — got status {resp.status_code}"
    )


def test_nonexistent_user_returns_404():
    """Requesting a nonexistent user should return 404 (when authorized)."""
    client = app.test_client()
    resp = client.get("/api/users/999", headers={"X-User-Id": "1"})
    # Could be 403 (can't access other user) or 404 (not found)
    assert resp.status_code in (403, 404)

"""Tests for CSRF vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_get_settings_works():
    """GET /settings should work without a token."""
    client = app.test_client()
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "email" in resp.get_json()


def test_csrf_token_endpoint_exists():
    """The /csrf-token endpoint should issue tokens."""
    client = app.test_client()
    resp = client.get("/csrf-token")
    assert resp.status_code == 200
    assert "csrf_token" in resp.get_json()


def test_post_without_csrf_token_rejected():
    """POST /settings without CSRF token must be rejected (403)."""
    client = app.test_client()
    resp = client.post("/settings", json={"email": "evil@attacker.com"})
    assert resp.status_code == 403, (
        f"POST without CSRF token was accepted (status {resp.status_code}) "
        "— CSRF protection is missing"
    )


def test_post_with_wrong_csrf_token_rejected():
    """POST /settings with an invalid CSRF token must be rejected."""
    client = app.test_client()
    # Get a valid session but use wrong token
    client.get("/csrf-token")
    resp = client.post(
        "/settings",
        json={"email": "evil@attacker.com"},
        headers={"X-CSRF-Token": "wrong-token-value"},
    )
    assert resp.status_code == 403, (
        f"POST with wrong CSRF token was accepted (status {resp.status_code})"
    )


def test_post_with_valid_csrf_token_accepted():
    """POST /settings with valid CSRF token should succeed."""
    client = app.test_client()
    # Get a CSRF token
    resp = client.get("/csrf-token")
    token = resp.get_json()["csrf_token"]
    # Use it
    resp = client.post(
        "/settings",
        json={"email": "new@example.com"},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 200, (
        f"POST with valid CSRF token was rejected (status {resp.status_code})"
    )

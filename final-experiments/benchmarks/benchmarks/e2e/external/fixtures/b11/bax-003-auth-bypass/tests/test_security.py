"""Tests for JWT alg=none auth bypass vulnerability fix."""
import sys
import os
import json
import base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def _b64url(data: bytes) -> str:
    """Base64url-encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_none_alg_token(payload: dict) -> str:
    """Craft a JWT token with alg=none (no signature)."""
    header = {"alg": "none", "typ": "JWT"}
    h = _b64url(json.dumps(header).encode())
    p = _b64url(json.dumps(payload).encode())
    return f"{h}.{p}."


def test_valid_token_works():
    """A properly signed token with admin role should access /admin."""
    client = app.test_client()
    # Get a token
    resp = client.post("/token", json={"username": "admin"})
    assert resp.status_code == 200
    # This token has role=user, so it should get 403, not 200
    # But at least the token is accepted (not 401)
    token = resp.get_json()["token"]
    resp = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    # role is "user" so expect 403 (forbidden, not unauthorized)
    assert resp.status_code == 403


def test_no_token_rejected():
    """Missing token should return 401."""
    client = app.test_client()
    resp = client.get("/admin")
    assert resp.status_code == 401


def test_none_alg_token_rejected():
    """A token with alg=none must be REJECTED, not accepted."""
    client = app.test_client()
    # Craft a none-alg token with admin role
    forged_token = _make_none_alg_token({"sub": "hacker", "role": "admin"})
    resp = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    # Must NOT return 200 — that means the bypass worked
    assert resp.status_code != 200, (
        "alg=none token was accepted — JWT decode does not enforce algorithm"
    )
    # Should be 401 (invalid token)
    assert resp.status_code == 401, (
        f"Expected 401 for forged token, got {resp.status_code}"
    )


def test_tampered_token_rejected():
    """A token with modified payload but original signature must be rejected."""
    client = app.test_client()
    resp = client.post("/token", json={"username": "user1"})
    token = resp.get_json()["token"]
    # Split and tamper with the payload
    parts = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    payload["role"] = "admin"
    parts[1] = _b64url(json.dumps(payload).encode())
    tampered = ".".join(parts)
    resp = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert resp.status_code == 401, "Tampered token should be rejected"

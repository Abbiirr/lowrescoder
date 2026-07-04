"""Tests for HTTP header injection vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_normal_redirect_works():
    """A normal redirect should return 302 with correct Location."""
    client = app.test_client()
    resp = client.get("/redirect?url=/home", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/home")


def test_crlf_injection_blocked():
    """CRLF injection in redirect URL must be blocked or sanitized."""
    client = app.test_client()
    # Attempt to inject a Set-Cookie header via CRLF
    malicious = "/home\r\nSet-Cookie: evil=1"
    resp = client.get(f"/redirect?url={malicious}", follow_redirects=False)
    if resp.status_code == 400:
        # Rejected entirely — good
        return
    # If it redirected, check that no injected header is present
    assert "evil" not in resp.headers.get("Set-Cookie", ""), (
        "CRLF injection succeeded — Set-Cookie: evil=1 was injected"
    )
    # The Location header must not contain \r\n
    location = resp.headers.get("Location", "")
    assert "\r" not in location and "\n" not in location, (
        "Location header contains newline characters — CRLF injection possible"
    )


def test_newline_in_url_blocked():
    """Newline characters in redirect URL must be stripped or rejected."""
    client = app.test_client()
    resp = client.get("/redirect?url=/home%0d%0aX-Injected: true", follow_redirects=False)
    if resp.status_code == 400:
        return
    # Check no injected header
    assert "X-Injected" not in resp.headers, (
        "Header injection succeeded — X-Injected header present"
    )
    location = resp.headers.get("Location", "")
    assert "\r" not in location and "\n" not in location, (
        "Location header contains newline characters"
    )


def test_header_injection_with_encoded_crlf():
    """Double-encoded CRLF must also be handled."""
    client = app.test_client()
    # %0d%0a = \r\n
    resp = client.get(
        "/redirect?url=/home%0d%0aSet-Cookie:%20stolen=yes",
        follow_redirects=False,
    )
    if resp.status_code == 400:
        return
    assert "stolen" not in resp.headers.get("Set-Cookie", ""), (
        "Header injection with encoded CRLF succeeded"
    )

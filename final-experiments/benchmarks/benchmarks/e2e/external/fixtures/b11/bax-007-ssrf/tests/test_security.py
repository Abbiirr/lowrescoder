"""Tests for SSRF vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_missing_url_returns_400():
    """Missing URL should return 400."""
    client = app.test_client()
    resp = client.post("/preview", json={})
    assert resp.status_code == 400


def test_aws_metadata_url_blocked():
    """AWS metadata endpoint must be blocked (SSRF protection)."""
    client = app.test_client()
    resp = client.post(
        "/preview",
        json={"url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert resp.status_code == 403, (
        f"AWS metadata URL was not blocked — got status {resp.status_code}. "
        "SSRF protection is missing."
    )


def test_localhost_url_blocked():
    """Requests to localhost must be blocked."""
    client = app.test_client()
    resp = client.post(
        "/preview",
        json={"url": "http://127.0.0.1:8080/admin"},
    )
    assert resp.status_code == 403, (
        f"localhost URL was not blocked — got status {resp.status_code}"
    )


def test_private_ip_10_blocked():
    """Requests to 10.x.x.x private range must be blocked."""
    client = app.test_client()
    resp = client.post(
        "/preview",
        json={"url": "http://10.0.0.1/internal"},
    )
    assert resp.status_code == 403, (
        f"Private IP (10.x) was not blocked — got status {resp.status_code}"
    )


def test_private_ip_172_blocked():
    """Requests to 172.16.x.x private range must be blocked."""
    client = app.test_client()
    resp = client.post(
        "/preview",
        json={"url": "http://172.16.0.1/"},
    )
    assert resp.status_code == 403, (
        f"Private IP (172.16.x) was not blocked — got status {resp.status_code}"
    )


def test_private_ip_192_blocked():
    """Requests to 192.168.x.x private range must be blocked."""
    client = app.test_client()
    resp = client.post(
        "/preview",
        json={"url": "http://192.168.1.1/"},
    )
    assert resp.status_code == 403, (
        f"Private IP (192.168.x) was not blocked — got status {resp.status_code}"
    )


def test_file_scheme_blocked():
    """file:// scheme must be blocked."""
    client = app.test_client()
    resp = client.post(
        "/preview",
        json={"url": "file:///etc/passwd"},
    )
    assert resp.status_code == 403, (
        f"file:// URL was not blocked — got status {resp.status_code}"
    )

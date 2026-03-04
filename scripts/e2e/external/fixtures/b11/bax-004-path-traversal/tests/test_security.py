"""Tests for path traversal vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_valid_file_download():
    """Downloading a file within uploads/ should work."""
    client = app.test_client()
    resp = client.get("/download?file=readme.txt")
    assert resp.status_code == 200
    assert b"sample file" in resp.data


def test_missing_file_returns_404():
    """Requesting a nonexistent file should return 404."""
    client = app.test_client()
    resp = client.get("/download?file=nonexistent.txt")
    assert resp.status_code == 404


def test_path_traversal_blocked():
    """Path traversal with ../ must be rejected (403 or 400), not served."""
    client = app.test_client()
    resp = client.get("/download?file=../../etc/passwd")
    assert resp.status_code in (400, 403), (
        f"Path traversal not blocked — got status {resp.status_code}"
    )


def test_path_traversal_encoded_blocked():
    """Encoded path traversal must also be rejected."""
    client = app.test_client()
    # URL-encoded ../ = %2e%2e%2f
    resp = client.get("/download?file=..%2f..%2fetc%2fpasswd")
    assert resp.status_code in (400, 403, 404), (
        f"Encoded path traversal not blocked — got status {resp.status_code}"
    )


def test_path_traversal_to_app_py_blocked():
    """Traversal to read app.py itself must be blocked."""
    client = app.test_client()
    resp = client.get("/download?file=../app.py")
    assert resp.status_code in (400, 403), (
        f"Path traversal to app.py not blocked — got status {resp.status_code}"
    )

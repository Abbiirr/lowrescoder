"""Tests for API error information leakage vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_valid_item_returned():
    """Valid item request should return data."""
    client = app.test_client()
    resp = client.get("/api/items/1")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Widget"


def test_missing_item_no_traceback():
    """Missing item error must NOT contain traceback details."""
    client = app.test_client()
    resp = client.get("/api/items/999")
    body = resp.data.decode()
    # Should be a 404 or 500, but must NOT leak traceback info
    assert "Traceback" not in body, (
        "Error response contains 'Traceback' — internal details leaked"
    )
    assert "File \"" not in body, (
        "Error response contains file paths — internal details leaked"
    )
    assert "line " not in body.lower() or "traceback" not in body.lower(), (
        "Error response contains stack trace line references"
    )


def test_bad_input_no_traceback():
    """Bad POST input must NOT leak traceback."""
    client = app.test_client()
    resp = client.post(
        "/api/items",
        json={"name": "Test"},  # missing 'price' — will cause KeyError
    )
    body = resp.data.decode()
    assert "Traceback" not in body, (
        "Error response contains 'Traceback' — internal details leaked"
    )
    assert "KeyError" not in body, (
        "Error response contains 'KeyError' — exception type leaked"
    )


def test_error_response_is_generic():
    """Error responses should contain a generic message, not internals."""
    client = app.test_client()
    resp = client.get("/api/items/999")
    body = resp.data.decode()
    # Must not contain Python file paths
    assert "/home/" not in body and "/usr/" not in body and "site-packages" not in body, (
        "Error response leaks internal file paths"
    )


def test_malformed_json_no_leak():
    """Malformed JSON request must return generic error."""
    client = app.test_client()
    resp = client.post(
        "/api/items",
        data="not-json",
        content_type="application/json",
    )
    body = resp.data.decode()
    assert "Traceback" not in body, (
        "Malformed JSON error leaks traceback"
    )

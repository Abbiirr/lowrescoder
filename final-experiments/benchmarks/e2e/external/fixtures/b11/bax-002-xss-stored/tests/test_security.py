"""Tests for stored XSS vulnerability fix."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def setup_function():
    """Clear comments before each test."""
    client = app.test_client()
    client.post("/comments/clear")


def test_normal_comment_displayed():
    """A normal comment should appear in output."""
    client = app.test_client()
    client.post("/comments", json={"text": "Hello world"})
    resp = client.get("/comments")
    assert resp.status_code == 200
    assert "Hello world" in resp.data.decode()


def test_script_tag_is_escaped():
    """Script tags must be escaped in output, not rendered as raw HTML."""
    client = app.test_client()
    payload = "<script>alert(1)</script>"
    client.post("/comments", json={"text": payload})
    resp = client.get("/comments")
    body = resp.data.decode()
    # The raw <script> tag must NOT appear in the HTML output
    assert "<script>" not in body, (
        "XSS vulnerability: <script> tag rendered as raw HTML"
    )
    # The escaped version should be present
    assert "&lt;script&gt;" in body or "&#" in body, (
        "Script tag should be HTML-escaped in output"
    )


def test_img_onerror_is_escaped():
    """img onerror XSS vector must be escaped."""
    client = app.test_client()
    payload = '<img src=x onerror="alert(1)">'
    client.post("/comments", json={"text": payload})
    resp = client.get("/comments")
    body = resp.data.decode()
    assert 'onerror="alert(1)"' not in body, (
        "XSS vulnerability: onerror handler rendered as raw HTML"
    )


def test_html_entities_in_comment():
    """Angle brackets in comments must be escaped."""
    client = app.test_client()
    client.post("/comments", json={"text": "<b>bold</b>"})
    resp = client.get("/comments")
    body = resp.data.decode()
    assert "<b>" not in body.split("<div class='comment'>")[-1].split("</div>")[0] or \
           "&lt;b&gt;" in body, (
        "HTML tags should be escaped in comment text"
    )

"""Tests for api_client — inspired by axios/axios and requests URL building.

urllib.parse.urljoin follows RFC 3986: without a trailing slash on the base,
a relative endpoint *replaces* the last path segment. HTTP client libraries
(axios, requests, httpx) all paper over this with explicit path concatenation.
This is a classic harness-bench v2 pattern: stdlib behaviour that surprises.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_base_without_trailing_slash():
    from api_client import build_url
    # urljoin("http://api.com/v1", "users") → "http://api.com/users" (wrong)
    result = build_url("http://api.com/v1", "users")
    assert result == "http://api.com/v1/users", f"got: {result}"


def test_base_with_trailing_slash():
    from api_client import build_url
    result = build_url("http://api.com/v1/", "users")
    assert result == "http://api.com/v1/users", f"got: {result}"


def test_endpoint_with_leading_slash():
    from api_client import build_url
    # /users should be treated as relative-to-base, not origin-absolute
    result = build_url("http://api.com/v1/", "/users")
    assert result == "http://api.com/v1/users", f"got: {result}"


def test_nested_base_no_slash():
    from api_client import build_url
    result = build_url("http://api.com/api/v2", "items")
    assert result == "http://api.com/api/v2/items", f"got: {result}"


def test_empty_endpoint_returns_base():
    from api_client import build_url
    result = build_url("http://api.com/v1/", "")
    assert result == "http://api.com/v1/", f"got: {result}"


def test_absolute_endpoint_passthrough():
    from api_client import build_url
    # If endpoint is already a full URL, return it unchanged
    result = build_url("http://api.com/v1/", "http://other.com/path")
    assert result == "http://other.com/path", f"got: {result}"


def test_deep_path_endpoint():
    from api_client import build_url
    result = build_url("http://api.com/v1", "users/123/profile")
    assert result == "http://api.com/v1/users/123/profile", f"got: {result}"

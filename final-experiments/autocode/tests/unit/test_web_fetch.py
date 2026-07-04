"""Tests for the typed web_fetch tool (deep-research-report Lane A)."""

from __future__ import annotations

import http.server
import socket
import threading
from collections.abc import Generator
from contextlib import contextmanager

import pytest

from autocode.agent.web_fetch import (
    DEFAULT_ALLOWED_DOMAINS,
    DEFAULT_MAX_BYTES,
    WebFetchResult,
    _handle_web_fetch,
    fetch,
    is_domain_allowed,
)


# --- is_domain_allowed ---


class TestIsDomainAllowed:
    def test_empty_host_rejected(self) -> None:
        assert is_domain_allowed("", ("github.com",)) is False

    def test_exact_match(self) -> None:
        assert is_domain_allowed("github.com", ("github.com",)) is True

    def test_suffix_match(self) -> None:
        assert is_domain_allowed("api.github.com", ("github.com",)) is True
        assert is_domain_allowed("raw.githubusercontent.com", ("raw.githubusercontent.com",)) is True

    def test_partial_string_is_NOT_a_match(self) -> None:
        # "evilgithub.com" should not match "github.com"
        assert is_domain_allowed("evilgithub.com", ("github.com",)) is False

    def test_case_insensitive(self) -> None:
        assert is_domain_allowed("GitHub.com", ("github.com",)) is True
        assert is_domain_allowed("github.com", ("GITHUB.COM",)) is True

    def test_unknown_host_rejected(self) -> None:
        assert is_domain_allowed("evil.example", ("github.com",)) is False

    def test_default_list_includes_common_hosts(self) -> None:
        assert is_domain_allowed("github.com", DEFAULT_ALLOWED_DOMAINS) is True
        assert is_domain_allowed("pypi.org", DEFAULT_ALLOWED_DOMAINS) is True
        assert is_domain_allowed("docs.python.org", DEFAULT_ALLOWED_DOMAINS) is True


# --- fetch() scheme + allowlist rejections (no network needed) ---


class TestFetchGuards:
    def test_rejects_non_http_scheme(self) -> None:
        result = fetch("file:///etc/passwd")
        assert result.error
        assert "scheme" in result.error

    def test_rejects_ftp_scheme(self) -> None:
        result = fetch("ftp://ftp.gnu.org/pub/gnu/")
        assert result.error
        assert "scheme" in result.error

    def test_rejects_off_allowlist_host(self) -> None:
        result = fetch("https://evil.example/secret", allowlist=("github.com",))
        assert result.error
        assert "allowlist" in result.error

    def test_rejects_off_allowlist_with_default_list(self) -> None:
        result = fetch("https://some-random-site.tld/x")
        assert result.error
        assert "allowlist" in result.error


# --- fetch() against a local HTTP server (real socket roundtrip, localhost allowed) ---


@contextmanager
def _local_http_server(
    handler_cls: type[http.server.BaseHTTPRequestHandler],
) -> Generator[int, None, None]:
    """Start a local HTTPServer on an ephemeral port, yield the port."""
    # Find a free port
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = http.server.HTTPServer(("127.0.0.1", port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _text_handler(body_bytes: bytes, content_type: str = "text/plain; charset=utf-8"):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def _status_handler(code: int):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"error body")

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def _binary_handler():
    return _text_handler(b"\x00\x01\x02\xff" * 256, content_type="application/octet-stream")


class TestFetchLocal:
    def test_textual_body_returned(self) -> None:
        body = "hello from the local server\n"
        with _local_http_server(_text_handler(body.encode())) as port:
            url = f"http://127.0.0.1:{port}/"
            result = fetch(url)
        assert result.error == ""
        assert result.status == 200
        assert "hello from the local server" in result.body
        assert "text/plain" in result.content_type
        assert result.truncated is False

    def test_max_bytes_truncation(self) -> None:
        big = "x" * 5000
        with _local_http_server(_text_handler(big.encode())) as port:
            url = f"http://127.0.0.1:{port}/"
            result = fetch(url, max_bytes=500)
        assert result.error == ""
        assert result.truncated is True
        assert len(result.body) == 500

    def test_binary_content_refused(self) -> None:
        with _local_http_server(_binary_handler()) as port:
            url = f"http://127.0.0.1:{port}/"
            result = fetch(url)
        assert result.error
        assert "non-textual" in result.error

    def test_json_content_accepted(self) -> None:
        body = '{"ok": true, "n": 42}'
        handler = _text_handler(body.encode(), content_type="application/json")
        with _local_http_server(handler) as port:
            url = f"http://127.0.0.1:{port}/"
            result = fetch(url)
        assert result.error == ""
        assert "ok" in result.body
        assert "json" in result.content_type.lower()

    def test_404_returns_error(self) -> None:
        with _local_http_server(_status_handler(404)) as port:
            url = f"http://127.0.0.1:{port}/missing"
            result = fetch(url)
        assert result.error
        assert "404" in result.error

    def test_to_text_success(self) -> None:
        r = WebFetchResult(
            url="https://github.com",
            status=200,
            content_type="text/html",
            body="hi",
            truncated=False,
        )
        assert "github.com" in r.to_text()
        assert "200" in r.to_text()
        assert "hi" in r.to_text()

    def test_to_text_error(self) -> None:
        r = WebFetchResult(
            url="https://github.com",
            status=0,
            content_type="",
            body="",
            truncated=False,
            error="request failed",
        )
        assert "error" in r.to_text().lower()
        assert "request failed" in r.to_text()

    def test_to_text_truncated(self) -> None:
        r = WebFetchResult(
            url="https://github.com",
            status=200,
            content_type="text/plain",
            body="x" * 500,
            truncated=True,
        )
        text = r.to_text()
        assert "truncated" in text


# --- Tool handler ---


class TestWebFetchHandler:
    def test_missing_url_returns_error(self) -> None:
        result = _handle_web_fetch(url="")
        assert "url is required" in result

    def test_invalid_scheme_returns_error(self) -> None:
        result = _handle_web_fetch(url="file:///etc/passwd")
        assert "scheme" in result

    def test_off_allowlist_returns_error(self) -> None:
        result = _handle_web_fetch(url="https://evil.example/secret")
        assert "allowlist" in result

    def test_localhost_in_default_allowlist(self) -> None:
        body = "hello"
        with _local_http_server(_text_handler(body.encode())) as port:
            result = _handle_web_fetch(url=f"http://127.0.0.1:{port}/")
        # Should succeed, not error
        assert "error" not in result.lower() or "[200" in result
        assert "hello" in result


# --- Registry wiring ---


class TestWebFetchRegistration:
    def test_web_fetch_in_core_tool_names(self) -> None:
        from autocode.agent.tools import CORE_TOOL_NAMES

        assert "web_fetch" in CORE_TOOL_NAMES

    def test_web_fetch_registered_in_default_registry(self) -> None:
        from autocode.agent.tools import create_default_registry

        registry = create_default_registry()
        tool = registry.get("web_fetch")
        assert tool is not None
        assert tool.name == "web_fetch"
        assert "url" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["url"]
        assert tool.requires_approval is False

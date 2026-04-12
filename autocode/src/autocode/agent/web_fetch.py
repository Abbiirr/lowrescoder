"""Typed web_fetch tool with domain allowlist.

Per the deep-research-report gap analysis (``docs/research/deep-research-report-gap-analysis.md``):

- raw ``run_command`` + ``curl`` is untyped, parse-fragile, and exposes the
  agent to arbitrary network targets with no audit trail
- the report recommends replacing ``curl``/``wget`` bash pipelines with a
  typed ``web_fetch(url)`` that enforces a domain allowlist, returns
  structured content, and is auditable
- Claude Code's Agent SDK ships a ``WebFetch`` tool in its core set
  precisely because of this

This module provides:

- ``DEFAULT_ALLOWED_DOMAINS`` — the baseline allowlist
- ``is_domain_allowed(host, allowlist)`` — exact or suffix match, no wildcards
- ``fetch(url, *, allowlist, max_bytes, timeout_s)`` — structured fetch with
  hard byte cap, timeout, and "text-ish" content-type detection
- ``_handle_web_fetch(...)`` — the tool handler that ``create_default_registry``
  wires into the agent

The tool is read-only: it does not issue POST/PUT/DELETE and it refuses
redirects that leave the allowlist.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

DEFAULT_MAX_BYTES = 64 * 1024  # 64 KB hard cap
DEFAULT_TIMEOUT_S = 10
DEFAULT_USER_AGENT = "AutoCode-web-fetch/0.1"


#: Baseline allowlist of domains the agent may reach without explicit override.
#: Kept intentionally tight — prefer approved docs/API hosts over open egress.
DEFAULT_ALLOWED_DOMAINS: tuple[str, ...] = (
    # Language/framework docs
    "docs.python.org",
    "go.dev",
    "pkg.go.dev",
    "doc.rust-lang.org",
    "docs.rs",
    "developer.mozilla.org",
    # Package indexes (read-only metadata)
    "pypi.org",
    "registry.npmjs.org",
    "crates.io",
    # Source hosts (browsing, not pushing)
    "github.com",
    "raw.githubusercontent.com",
    "gitlab.com",
    # Infrastructure docs
    "kubernetes.io",
    "docs.docker.com",
    # Local gateway (for self-tests against the LLM gateway)
    "localhost",
    "127.0.0.1",
)


@dataclass
class WebFetchResult:
    """Structured response from a web_fetch call."""

    url: str
    status: int
    content_type: str
    body: str
    truncated: bool
    error: str = ""

    def to_text(self) -> str:
        if self.error:
            return f"web_fetch error: {self.error}"
        header = f"{self.url} [{self.status} {self.content_type}]"
        if self.truncated:
            header += f" [truncated at {len(self.body)} bytes]"
        if not self.body:
            return header
        return f"{header}\n\n{self.body}"


def is_domain_allowed(host: str, allowlist: tuple[str, ...]) -> bool:
    """Return True if ``host`` is in ``allowlist`` by exact or suffix match.

    Suffix matching treats ``api.github.com`` as allowed when ``github.com``
    is in the list. This is the standard domain-allowlist semantics and
    avoids requiring every subdomain to be enumerated.
    """
    host = (host or "").lower().strip()
    if not host:
        return False
    for allowed in allowlist:
        allowed = allowed.lower().strip()
        if not allowed:
            continue
        if host == allowed:
            return True
        if host.endswith("." + allowed):
            return True
    return False


def fetch(
    url: str,
    *,
    allowlist: tuple[str, ...] = DEFAULT_ALLOWED_DOMAINS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    user_agent: str = DEFAULT_USER_AGENT,
) -> WebFetchResult:
    """Fetch a single URL with hard limits.

    Args:
        url: The URL to fetch. Must be ``http`` or ``https``.
        allowlist: Tuple of allowed hostnames (exact or parent domains).
        max_bytes: Hard byte cap on the returned body.
        timeout_s: Socket timeout in seconds.
        user_agent: User-Agent header to send.

    Returns:
        ``WebFetchResult`` with either a successful body or an ``error`` field.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        return WebFetchResult(
            url=url,
            status=0,
            content_type="",
            body="",
            truncated=False,
            error=f"unsupported scheme: {parsed.scheme!r} (only http/https allowed)",
        )
    host = parsed.hostname or ""
    if not is_domain_allowed(host, allowlist):
        return WebFetchResult(
            url=url,
            status=0,
            content_type="",
            body="",
            truncated=False,
            error=(
                f"host {host!r} not in allowlist "
                f"(allowed: {', '.join(allowlist)[:200]})"
            ),
        )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/*, application/json, application/xml",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 0) or resp.getcode() or 0)
            content_type = resp.headers.get("Content-Type", "")
            # Refuse redirects that left the allowlist
            final_host = urllib.parse.urlsplit(resp.geturl()).hostname or ""
            if final_host and not is_domain_allowed(final_host, allowlist):
                return WebFetchResult(
                    url=url,
                    status=status,
                    content_type=content_type,
                    body="",
                    truncated=False,
                    error=f"redirect left allowlist: final host {final_host!r}",
                )
            raw = resp.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        return WebFetchResult(
            url=url,
            status=int(exc.code),
            content_type="",
            body="",
            truncated=False,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return WebFetchResult(
            url=url,
            status=0,
            content_type="",
            body="",
            truncated=False,
            error=f"request failed: {exc}",
        )

    truncated = len(raw) > max_bytes
    body_bytes = raw[:max_bytes]
    # Decode only if the content-type looks textual — binary is rejected
    lowered = (content_type or "").lower()
    if lowered and not (
        lowered.startswith("text/")
        or "json" in lowered
        or "xml" in lowered
        or "javascript" in lowered
        or "html" in lowered
    ):
        return WebFetchResult(
            url=url,
            status=status,
            content_type=content_type,
            body="",
            truncated=False,
            error=f"non-textual content-type refused: {content_type!r}",
        )
    try:
        body = body_bytes.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        body = body_bytes.decode("latin-1", errors="replace")
    return WebFetchResult(
        url=url,
        status=status,
        content_type=content_type,
        body=body,
        truncated=truncated,
    )


def _handle_web_fetch(
    url: str = "",
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> str:
    """Tool handler wired into the agent registry."""
    if not url:
        return "web_fetch error: url is required"
    # Tool layer always uses the baseline allowlist; extension points can
    # override via project config later.
    result = fetch(
        url,
        allowlist=DEFAULT_ALLOWED_DOMAINS,
        max_bytes=max_bytes,
        timeout_s=timeout_s,
    )
    return result.to_text()

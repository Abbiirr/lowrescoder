"""Service helpers built on the flaky client."""

from __future__ import annotations

from client import fetch_payload


def render_status(fetcher) -> str:
    payload = fetch_payload(fetcher)
    return f"{payload['status']}:{payload['count']}"

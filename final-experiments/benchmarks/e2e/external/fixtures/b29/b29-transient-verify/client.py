"""Client layer with missing retry behavior."""

from __future__ import annotations


class TransientUpstreamError(RuntimeError):
    """Raised for temporary upstream failures."""


def fetch_payload(fetcher, max_attempts: int = 3):
    """Call the fetcher and return the payload.

    Broken on purpose: this performs no retries.
    """
    return fetcher()

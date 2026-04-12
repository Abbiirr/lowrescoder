"""Shared helper for building OpenAI-compatible gateway auth headers.

The local LiteLLM gateway requires a bearer token, but the environment variable
name varies by setup. This module centralizes the lookup order so every caller
(`/model` listing, `doctor` checks, etc.) authenticates consistently.

Lookup priority (first non-empty wins):
1. ``LITELLM_API_KEY``    — what this repo's ``start-gateway.sh`` actually exports
2. ``LITELLM_MASTER_KEY`` — older docs referenced this name
3. ``OPENROUTER_API_KEY`` — upstream OpenRouter key sometimes proxied through

If none are set, the returned header dict contains only ``Accept``.
"""

from __future__ import annotations

import os

_AUTH_ENV_VARS: tuple[str, ...] = (
    "LITELLM_API_KEY",
    "LITELLM_MASTER_KEY",
    "OPENROUTER_API_KEY",
)


def get_gateway_api_key() -> str:
    """Return the first non-empty auth key from the env, or ``''`` if none found."""
    for name in _AUTH_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def build_gateway_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build headers for an authenticated request to the local gateway.

    Always includes ``Accept: application/json``. Adds ``Authorization: Bearer <key>``
    if any of the supported env vars are set.

    Args:
        extra: Additional headers to merge in (e.g. ``Content-Type``).

    Returns:
        A new dict suitable for ``urllib.request.Request(headers=...)``.
    """
    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = get_gateway_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra:
        headers.update(extra)
    return headers

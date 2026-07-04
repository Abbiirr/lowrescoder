"""Minimal, dependency-free LLM client for the local gateway.

The reflector takes an injected ``llm(prompt) -> str`` callable. For real runs we
back it with the same OpenAI-compatible LiteLLM gateway the student and teacher
use (default ``http://localhost:4000/v1``), so the *whole* teacher-student loop —
student, teacher, and reflection — runs on local models. Uses only ``urllib`` so
it adds no dependency and works in restricted environments.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from autocode.anvil.teacher.runners import GatewayConfig


def make_gateway_llm(
    cfg: GatewayConfig | None = None,
    *,
    model: str | None = None,
    timeout: int = 120,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> Callable[[str], str]:
    """Return an ``llm(prompt) -> str`` calling the gateway's chat completions."""
    cfg = cfg or GatewayConfig.from_env()
    chosen = model or cfg.teacher_model

    def call(prompt: str) -> str:
        url = cfg.api_base.rstrip("/") + "/chat/completions"
        body = json.dumps(
            {
                "model": chosen,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        ).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310 - fixed local gateway URL
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cfg.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"] or ""

    return call


def gateway_ready(cfg: GatewayConfig | None = None, *, timeout: int = 4) -> bool:
    """True iff the LiteLLM gateway reports healthy readiness."""
    cfg = cfg or GatewayConfig.from_env()
    base = cfg.api_base.rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    url = base + "/health/readiness"
    try:
        req = urllib.request.Request(url, method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", "replace")
        return '"healthy"' in body or '"status":"healthy"' in body.replace(" ", "")
    except (urllib.error.URLError, OSError, ValueError):
        return False


__all__ = ["make_gateway_llm", "gateway_ready"]

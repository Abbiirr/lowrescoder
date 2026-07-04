"""Live prompt-cache integration checks.

These tests are opt-in because they spend provider tokens and require OpenRouter
Anthropic prompt-cache support. Unit/cassette coverage owns deterministic CI.
"""

from __future__ import annotations

import os

import pytest

from autocode.config import AutoCodeConfig
from autocode.layer4.llm import OpenRouterProvider

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("AUTOCODE_RUN_LIVE_PROMPT_CACHE") != "1",
        reason="set AUTOCODE_RUN_LIVE_PROMPT_CACHE=1 for live prompt-cache test",
    ),
    pytest.mark.skipif(
        not os.environ.get("OPENROUTER_API_KEY"),
        reason="OPENROUTER_API_KEY required for live prompt-cache test",
    ),
]


@pytest.mark.asyncio()
async def test_openrouter_anthropic_prompt_cache_warmup_then_read() -> None:
    config = AutoCodeConfig()
    config.llm.provider = "openrouter"
    config.llm.model = os.environ.get(
        "AUTOCODE_PROMPT_CACHE_MODEL",
        "anthropic/claude-3.5-haiku",
    )
    provider = OpenRouterProvider(config)
    stable_prefix = "stable prompt cache fixture\n" + ("token budget line\n" * 220)
    messages = [
        {
            "role": "system",
            "content": (
                f"{stable_prefix}\n"
                "# === DANGEROUS_uncachedSystemPromptSection_BELOW ===\n"
                "dynamic tail"
            ),
        },
        {"role": "user", "content": "Reply with exactly: ok"},
    ]

    first = await provider.generate_with_tools(messages, [], reasoning_enabled=False)
    second = await provider.generate_with_tools(messages, [], reasoning_enabled=False)

    assert first.usage["cache_creation_tokens"] > 0
    assert first.usage["cached_input_tokens"] == 0
    assert second.usage["cached_input_tokens"] >= 1024

"""Integration tests for OpenRouter LLM provider.

Requires OPENROUTER_API_KEY env var. Skipped by default.
Run with: pytest -m integration tests/integration/test_openrouter.py
"""

from __future__ import annotations

import asyncio
import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture()
def openrouter_available() -> bool:
    """Check if OpenRouter is configured."""
    return bool(os.environ.get("OPENROUTER_API_KEY"))


@pytest.fixture()
def config():  # type: ignore[no-untyped-def]
    """Create config with OpenRouter provider."""
    from autocode.config import load_config

    os.environ["AUTOCODE_LLM_PROVIDER"] = "openrouter"
    return load_config()


def test_openrouter_streaming(openrouter_available: bool, config) -> None:  # type: ignore[no-untyped-def]
    """Test that OpenRouter returns streamed tokens."""
    if not openrouter_available:
        pytest.skip("OPENROUTER_API_KEY not set")

    from autocode.layer4.llm import OpenRouterProvider

    provider = OpenRouterProvider(config)

    async def _run() -> str:
        chunks: list[str] = []
        async for chunk in provider.generate(
            [{"role": "user", "content": "Say hello in one word."}],
            stream=True,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    try:
        result = asyncio.run(_run())
    except Exception as e:
        if "429" in str(e) or "rate" in str(e).lower():
            pytest.skip(f"OpenRouter rate limited: {e}")
        raise
    assert len(result) > 0


def test_openrouter_non_streaming(openrouter_available: bool, config) -> None:  # type: ignore[no-untyped-def]
    """Test non-streaming response."""
    if not openrouter_available:
        pytest.skip("OPENROUTER_API_KEY not set")

    from autocode.layer4.llm import OpenRouterProvider

    provider = OpenRouterProvider(config)

    async def _run() -> str:
        chunks: list[str] = []
        async for chunk in provider.generate(
            [{"role": "user", "content": "Say hello in one word."}],
            stream=False,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    try:
        result = asyncio.run(_run())
    except Exception as e:
        if "429" in str(e) or "rate" in str(e).lower():
            pytest.skip(f"OpenRouter rate limited: {e}")
        raise
    assert len(result) > 0

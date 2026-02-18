"""Integration tests for Ollama LLM provider.

Requires Ollama running locally. Skipped by default.
Run with: pytest -m integration tests/integration/test_ollama.py
"""

from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.integration


def _ollama_running() -> bool:
    """Check if Ollama server is reachable."""
    try:
        import httpx

        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture()
def ollama_available() -> bool:
    return _ollama_running()


@pytest.fixture()
def config():  # type: ignore[no-untyped-def]
    """Create config with Ollama provider."""
    from autocode.config import AutoCodeConfig

    return AutoCodeConfig()


def test_ollama_streaming(ollama_available: bool, config) -> None:  # type: ignore[no-untyped-def]
    """Test that Ollama returns streamed tokens."""
    if not ollama_available:
        pytest.skip("Ollama not running")

    from autocode.layer4.llm import OllamaProvider

    provider = OllamaProvider(config)

    async def _run() -> str:
        chunks: list[str] = []
        async for chunk in provider.generate(
            [{"role": "user", "content": "Say hello in one word."}],
            stream=True,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    result = asyncio.run(_run())
    assert len(result) > 0

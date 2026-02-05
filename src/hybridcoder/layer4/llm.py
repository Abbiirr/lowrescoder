"""LLM provider abstraction for Layer 4.

Supports Ollama (production) and OpenRouter (development).
Provider selected by config.llm.provider.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from hybridcoder.config import HybridCoderConfig


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM backends."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Generate a response, yielding chunks if streaming."""
        ...  # pragma: no cover

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
    ) -> BaseModel:
        """Generate a response conforming to a Pydantic schema."""
        ...  # pragma: no cover

    def count_tokens(self, text: str) -> int:
        """Approximate token count for a string."""
        ...  # pragma: no cover


class OllamaProvider:
    """Ollama LLM provider for Layer 4 (production)."""

    def __init__(self, config: HybridCoderConfig) -> None:
        self.model = config.llm.model
        self.api_base = config.llm.api_base
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Generate via Ollama async client."""
        import ollama

        client = ollama.AsyncClient(host=self.api_base)
        options = {"temperature": self.temperature, "num_predict": self.max_tokens}

        if stream:
            stream_response = await client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options=options,
            )
            async for chunk in stream_response:
                content = chunk.message.content or ""
                if content:
                    yield content
        else:
            result = await client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options=options,
            )
            yield result.message.content or ""

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
    ) -> BaseModel:
        """Generate JSON via Ollama with format parameter."""
        import json

        import ollama

        client = ollama.AsyncClient(host=self.api_base)
        result = await client.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={"temperature": self.temperature, "num_predict": self.max_tokens},
        )
        raw = json.loads(result.message.content or "{}")
        return schema.model_validate(raw)

    def count_tokens(self, text: str) -> int:
        """Approximate token count (~4 chars per token)."""
        return len(text) // 4


class OpenRouterProvider:
    """OpenRouter LLM provider for Layer 4 (development)."""

    def __init__(self, config: HybridCoderConfig) -> None:
        self.model = config.llm.model
        self.api_base = config.llm.api_base
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Generate via OpenRouter (OpenAI-compatible API)."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

        if stream:
            response_stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            async for chunk in response_stream:  # type: ignore[union-attr]
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        else:
            result = await client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = result.choices[0].message.content or ""
            yield content

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
    ) -> BaseModel:
        """Generate JSON via OpenRouter with response_format."""
        import json

        from openai import AsyncOpenAI
        from openai.types.shared_params import ResponseFormatJSONObject

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
        result = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format=ResponseFormatJSONObject(type="json_object"),
        )
        raw_text = result.choices[0].message.content or "{}"
        raw = json.loads(raw_text)
        return schema.model_validate(raw)

    def count_tokens(self, text: str) -> int:
        """Approximate token count (~4 chars per token)."""
        return len(text) // 4


def create_provider(config: HybridCoderConfig) -> OllamaProvider | OpenRouterProvider:
    """Create the appropriate LLM provider based on config."""
    if config.llm.provider == "openrouter":
        return OpenRouterProvider(config)
    return OllamaProvider(config)


class ConversationHistory:
    """Manages multi-turn conversation history."""

    def __init__(self, system_prompt: str = "") -> None:
        self.messages: list[dict[str, str]] = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_user(self, content: str) -> None:
        """Add a user message."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        """Add an assistant message."""
        self.messages.append({"role": "assistant", "content": content})

    def get_messages(self) -> list[dict[str, str]]:
        """Return all messages."""
        return list(self.messages)

    def token_estimate(self) -> int:
        """Rough token count of entire history."""
        return sum(len(m["content"]) // 4 for m in self.messages)

    def trim_to_budget(self, max_tokens: int) -> None:
        """Remove oldest non-system user/assistant pairs to fit token budget."""
        while self.token_estimate() > max_tokens and len(self.messages) > 1:
            # Keep system prompt (index 0), remove oldest user+assistant pair
            if len(self.messages) >= 3 and self.messages[1]["role"] == "user":
                self.messages.pop(1)  # remove user
                if len(self.messages) > 1 and self.messages[1]["role"] == "assistant":
                    self.messages.pop(1)  # remove matching assistant
            elif len(self.messages) >= 2:
                self.messages.pop(1)
            else:
                break

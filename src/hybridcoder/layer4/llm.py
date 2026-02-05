"""LLM provider abstraction for Layer 4.

Supports Ollama (production) and OpenRouter (development).
Provider selected by config.llm.provider.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from hybridcoder.config import HybridCoderConfig


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Structured response from an LLM, possibly containing tool calls."""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    reasoning: str | None = None  # Thinking/reasoning tokens (if model supports it)


# Tool schema type for OpenAI-compatible APIs
ToolSchema = dict[str, Any]


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

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        *,
        on_chunk: Any | None = None,
        on_thinking_chunk: Any | None = None,
        reasoning_enabled: bool = True,
    ) -> LLMResponse:
        """Generate a response that may include tool calls."""
        ...  # pragma: no cover

    def count_tokens(self, text: str) -> int:
        """Approximate token count for a string."""
        ...  # pragma: no cover


def _parse_think_tags(text: str) -> tuple[str, str]:
    """Parse <think>...</think> tags from model output.

    Returns (content, reasoning) where reasoning is the text inside think tags
    and content is everything outside.
    """
    import re

    reasoning_parts: list[str] = []
    content_parts: list[str] = []
    pos = 0
    for match in re.finditer(r"<think>(.*?)</think>", text, re.DOTALL):
        content_parts.append(text[pos:match.start()])
        reasoning_parts.append(match.group(1))
        pos = match.end()
    content_parts.append(text[pos:])

    content = "".join(content_parts).strip()
    reasoning = "".join(reasoning_parts).strip()
    return content, reasoning


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

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        *,
        on_chunk: Any | None = None,
        on_thinking_chunk: Any | None = None,
        reasoning_enabled: bool = True,
    ) -> LLMResponse:
        """Generate with tool calling via Ollama (non-streaming to avoid partial JSON)."""
        import json

        import ollama

        client = ollama.AsyncClient(host=self.api_base)
        options = {"temperature": self.temperature, "num_predict": self.max_tokens}

        try:
            result = await client.chat(
                model=self.model,
                messages=messages,
                tools=tools,
                stream=False,
                options=options,
            )
        except Exception:
            # Fall back to text-only if tool calling fails
            result = await client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options=options,
            )

        raw_content = result.message.content or ""
        tool_calls: list[ToolCall] = []

        if hasattr(result.message, "tool_calls") and result.message.tool_calls:
            for tc in result.message.tool_calls:
                args: Any = tc.function.arguments if hasattr(tc.function, "arguments") else {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if not isinstance(args, dict):
                    args = dict(args) if hasattr(args, "items") else {}
                tool_calls.append(ToolCall(
                    id=getattr(tc, "id", f"tc_{id(tc)}"),
                    name=tc.function.name,
                    arguments=args,
                ))

        # Parse <think> tags (DeepSeek R1 style models on Ollama)
        content, reasoning = _parse_think_tags(raw_content)

        if on_chunk and content:
            on_chunk(content)
        if on_thinking_chunk and reasoning:
            on_thinking_chunk(reasoning)

        return LLMResponse(
            content=content or None,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
            reasoning=reasoning or None,
        )

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

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        *,
        on_chunk: Any | None = None,
        on_thinking_chunk: Any | None = None,
        reasoning_enabled: bool = True,
    ) -> LLMResponse:
        """Generate with tool calling via OpenRouter (OpenAI-compatible streaming)."""
        import json

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

        extra_body: dict[str, Any] = {}
        if reasoning_enabled:
            extra_body["reasoning"] = {"enabled": True}

        response_stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=tools,  # type: ignore[arg-type]
            stream=True,
            extra_body=extra_body or None,
        )

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_call_data: dict[int, dict[str, Any]] = {}
        finish_reason = "stop"
        in_think_tag = False

        async for chunk in response_stream:  # type: ignore[union-attr]
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                finish_reason = choice.finish_reason

            delta = choice.delta

            # Capture reasoning field (OpenRouter native thinking)
            reasoning_text = getattr(delta, "reasoning", None) if delta else None
            if reasoning_text:
                reasoning_parts.append(reasoning_text)
                if on_thinking_chunk:
                    on_thinking_chunk(reasoning_text)

            if delta and delta.content:
                text = delta.content

                # Parse <think> tags (DeepSeek R1 style)
                if "<think>" in text:
                    in_think_tag = True
                    # Split: before tag goes to content, after goes to reasoning
                    before, _, after = text.partition("<think>")
                    if before:
                        content_parts.append(before)
                        if on_chunk:
                            on_chunk(before)
                    if after:
                        reasoning_parts.append(after)
                        if on_thinking_chunk:
                            on_thinking_chunk(after)
                    continue

                if "</think>" in text:
                    in_think_tag = False
                    before, _, after = text.partition("</think>")
                    if before:
                        reasoning_parts.append(before)
                        if on_thinking_chunk:
                            on_thinking_chunk(before)
                    if after:
                        content_parts.append(after)
                        if on_chunk:
                            on_chunk(after)
                    continue

                if in_think_tag:
                    reasoning_parts.append(text)
                    if on_thinking_chunk:
                        on_thinking_chunk(text)
                else:
                    content_parts.append(text)
                    if on_chunk:
                        on_chunk(text)

            if delta and delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_call_data:
                        tool_call_data[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc_delta.id:
                        tool_call_data[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_call_data[idx]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_call_data[idx]["arguments"] += tc_delta.function.arguments

        content = "".join(content_parts) or None
        reasoning = "".join(reasoning_parts) or None
        tool_calls: list[ToolCall] = []
        for _idx, tc_data in sorted(tool_call_data.items()):
            try:
                args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(
                id=tc_data["id"],
                name=tc_data["name"],
                arguments=args,
            ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else finish_reason,
            reasoning=reasoning,
        )

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

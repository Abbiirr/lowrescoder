"""LLM provider abstraction for Layer 4.

Supports Ollama (production) and OpenRouter (development).
Provider selected by config.llm.provider.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from autocode.config import AutoCodeConfig
from autocode.core.logging import log_event

logger = logging.getLogger(__name__)


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


def _find_balanced_json(text: str, start: int) -> str | None:
    """Find a balanced JSON object starting at position `start` (which must be '{').

    Uses brace counting to handle nested objects, respecting string literals.
    Returns the full JSON string or None if unbalanced.
    """
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _extract_tool_calls_from_text(
    text: str,
    available_tools: list[ToolSchema] | None = None,
) -> list[ToolCall]:
    """Extract tool calls from text when model outputs them inline instead of via API.

    Some models output tool calls as ```json blocks, bare JSON objects, or XML-style
    <function=name> tags rather than using Ollama's structured tool calling API.
    This function parses all these formats and returns ToolCall objects.

    Only extracts calls whose name matches a known tool (if available_tools provided).
    """
    import re

    # Collect known tool names for validation
    known_names: set[str] | None = None
    if available_tools:
        known_names = set()
        for tool in available_tools:
            fn = tool.get("function", {})
            if fn.get("name"):
                known_names.add(fn["name"])

    tool_calls: list[ToolCall] = []

    # Strategy 1: Extract from ```json ... ``` code blocks
    for m in re.finditer(r"```(?:json)?\s*\n?", text):
        block_start = m.end()
        json_str = _find_balanced_json(text, block_start)
        if json_str:
            data = _try_parse_json(json_str)
            if data and isinstance(data, dict) and "name" in data:
                _maybe_add_tool_call(data, known_names, tool_calls)

    # Strategy 2: Find bare JSON objects starting with {"name": "tool_name"
    if not tool_calls:
        for m in re.finditer(r'\{\s*"name"\s*:', text):
            json_str = _find_balanced_json(text, m.start())
            if json_str:
                data = _try_parse_json(json_str)
                if data and isinstance(data, dict) and "name" in data:
                    _maybe_add_tool_call(data, known_names, tool_calls)

    # Strategy 3: XML-style <function=name> tags (qwen3-coder, etc.)
    # Format: <function=tool_name>\n<parameter=key>\nvalue\n</parameter>\n</function>
    if not tool_calls:
        for m in re.finditer(
            r"<function=([^>]+)>(.*?)</function>", text, re.DOTALL,
        ):
            func_name = m.group(1).strip()
            body = m.group(2)
            args: dict[str, Any] = {}
            for pm in re.finditer(
                r"<parameter=([^>]+)>(.*?)</parameter>", body, re.DOTALL,
            ):
                param_name = pm.group(1).strip()
                param_value = pm.group(2).strip()
                args[param_name] = param_value
            data = {"name": func_name, "arguments": args}
            _maybe_add_tool_call(data, known_names, tool_calls)

    return tool_calls


def _try_parse_json(text: str) -> dict | None:
    """Try to parse JSON, with fallback sanitization for common model errors.

    Models sometimes produce JSON with backtick quotes instead of double quotes,
    trailing commas, or other malformations. This tries standard parsing first,
    then applies sanitization.
    """
    import json
    import re

    # Try standard parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Sanitize: replace backtick-quoted strings with double-quoted
    sanitized = re.sub(r'`([^`]*)`', r'"\1"', text)
    # Remove trailing commas before } or ]
    sanitized = re.sub(r',\s*([}\]])', r'\1', sanitized)

    try:
        return json.loads(sanitized)
    except json.JSONDecodeError:
        pass

    # Last resort: try to extract just name and arguments fields manually
    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', text)
    if not name_match:
        return None

    name = name_match.group(1)
    # Find "arguments": { and try to parse the arguments block
    args_match = re.search(r'"arguments"\s*:\s*', text)
    if not args_match:
        return {"name": name, "arguments": {}}

    args_start = args_match.end()
    args_json = _find_balanced_json(text, args_start)
    if args_json:
        try:
            args = json.loads(args_json)
            return {"name": name, "arguments": args}
        except json.JSONDecodeError:
            # Try sanitized version
            sanitized_args = re.sub(r'`([^`]*)`', r'"\1"', args_json)
            sanitized_args = re.sub(r',\s*([}\]])', r'\1', sanitized_args)
            try:
                args = json.loads(sanitized_args)
                return {"name": name, "arguments": args}
            except json.JSONDecodeError:
                pass

    return {"name": name, "arguments": {}}


def _fuzzy_match_tool_name(name: str, known_names: set[str]) -> str | None:
    """Map a hallucinated tool name to the closest known tool.

    Models sometimes produce variations like "update_package_json" instead
    of "write_file". This function maps common patterns.
    """
    # Exact match
    if name in known_names:
        return name

    # Common mappings for hallucinated names
    edit_patterns = {
        "modify_file", "patch_file", "replace_in_file",
        "search_replace", "str_replace",
    }
    if name in edit_patterns:
        if "edit_file" in known_names:
            return "edit_file"
        if "write_file" in known_names:
            return "write_file"

    write_patterns = {
        "update_file", "create_file", "save_file", "update_package_json",
        "write_package_json", "create_package_json",
        "put_file", "write_to_file",
    }
    if name in write_patterns and "write_file" in known_names:
        return "write_file"

    # Fallback: if model calls edit_file but it's not in registry, map to write_file
    if name == "edit_file" and "edit_file" not in known_names and "write_file" in known_names:
        return "write_file"

    run_patterns = {
        "execute_command", "exec_command", "shell", "bash",
        "run_shell", "execute", "run_bash",
    }
    if name in run_patterns and "run_command" in known_names:
        return "run_command"

    read_patterns = {"get_file", "open_file", "cat_file", "view_file"}
    if name in read_patterns and "read_file" in known_names:
        return "read_file"

    return None


def _maybe_add_tool_call(
    data: dict,
    known_names: set[str] | None,
    tool_calls: list[ToolCall],
) -> None:
    """Validate and append a tool call extracted from text."""
    name = data.get("name", "")
    arguments = data.get("arguments", {})

    if not name or not isinstance(arguments, dict):
        return

    if known_names:
        matched = _fuzzy_match_tool_name(name, known_names)
        if matched is None:
            return
        name = matched

    tool_calls.append(ToolCall(
        id=f"text_tc_{len(tool_calls)}",
        name=name,
        arguments=arguments,
    ))


def _fix_ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fix message format for Ollama SDK compatibility.

    The agent loop stores tool_call arguments as JSON strings (OpenAI format),
    but the Ollama SDK's pydantic models expect arguments as dicts.
    This converts string arguments back to dicts.
    """
    import copy
    import json

    fixed = copy.deepcopy(messages)
    for msg in fixed:
        if "tool_calls" not in msg:
            continue
        for tc in msg["tool_calls"]:
            fn = tc.get("function", {})
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    fn["arguments"] = json.loads(args)
                except (json.JSONDecodeError, ValueError):
                    fn["arguments"] = {}
    return fixed


def _is_connection_error(exc: Exception) -> bool:
    """Check if an exception is a connection/network error (retryable)."""
    conn_types = (ConnectionError, OSError, ConnectionRefusedError, TimeoutError)
    if isinstance(exc, conn_types):
        return True
    # httpx and ollama wrap connection errors in their own types.
    # Important: ollama.ResponseError also represents non-network model/runtime
    # failures (e.g., malformed XML tool-call output), which should NOT be
    # treated as connection errors.
    type_name = type(exc).__name__
    msg = str(exc).lower()
    network_keywords = (
        "connection", "connect", "refused", "unreachable",
        "network", "timed out", "eof", "reset by peer",
    )

    if type_name in (
        "ConnectError", "RemoteProtocolError", "ReadError",
        "RequestError", "ReadTimeout", "ConnectTimeout",
    ):
        return True

    if type_name == "ResponseError":
        status_code = getattr(exc, "status_code", None)
        # Retry true gateway/upstream availability failures.
        if status_code in (502, 503, 504):
            return True
        # Parse/model errors (often status 500) should flow to caller as
        # non-connection errors so tool-mode retry/fallback can run.
        return any(kw in msg for kw in network_keywords)

    # Fallback heuristic for unknown wrappers.
    return any(kw in msg for kw in network_keywords)


class OllamaProvider:
    """Ollama LLM provider for Layer 4 (production)."""

    # Per-request timeout in seconds (generous for thinking models)
    REQUEST_TIMEOUT = 3600.0

    # Exponential backoff for connection errors
    # In benchmark mode (BENCHMARK_NO_RETRY=1), fail immediately on first error
    CONN_RETRY_MAX = 10
    CONN_RETRY_BASE_S = 5.0    # first wait: 5s
    CONN_RETRY_MAX_S = 300.0   # cap at 5 minutes

    def __init__(self, config: AutoCodeConfig) -> None:
        self.model = config.llm.model
        self.api_base = config.llm.api_base
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.context_length = config.llm.context_length
        # Use standard request timeout for all modes.
        # Per-task wall-time budget in the benchmark runner is the real guard.
        self.request_timeout = self.REQUEST_TIMEOUT

    def _build_options(self) -> dict[str, Any]:
        """Build Ollama options dict with context window cap."""
        return {
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
            "num_ctx": self.context_length,
        }

    async def _with_conn_backoff(
        self,
        coro_fn: Any,
        *,
        label: str = "ollama_call",
    ) -> Any:
        """Wrap an async call with exponential backoff on connection errors.

        If the remote Ollama server is down, pauses and retries up to
        CONN_RETRY_MAX times with exponential backoff (5s → 10s → … → 300s).
        Non-connection errors are raised immediately.
        """
        # In benchmark mode, fail immediately on connection errors
        # instead of retrying — the benchmark runner handles halting.
        no_retry = os.environ.get("BENCHMARK_NO_RETRY", "") == "1"
        max_retries = 0 if no_retry else self.CONN_RETRY_MAX

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return await coro_fn()
            except Exception as e:
                if not _is_connection_error(e):
                    raise  # Not a connection issue — fail fast
                last_exc = e
                if attempt >= max_retries:
                    break
                delay = min(
                    self.CONN_RETRY_BASE_S * (2 ** attempt),
                    self.CONN_RETRY_MAX_S,
                )
                log_event(
                    logger, logging.WARNING, "ollama_conn_retry",
                    label=label, attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_s=delay, error=str(e)[:200],
                )
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Generate via Ollama async client."""
        import ollama

        client = ollama.AsyncClient(host=self.api_base)
        options = self._build_options()

        if stream:
            stream_response = await self._with_conn_backoff(
                lambda: client.chat(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    options=options,
                ),
                label="generate_stream",
            )
            async for chunk in stream_response:
                content = chunk.message.content or ""
                if content:
                    yield content
        else:
            result = await self._with_conn_backoff(
                lambda: client.chat(
                    model=self.model,
                    messages=messages,
                    stream=False,
                    options=options,
                ),
                label="generate",
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
        result = await self._with_conn_backoff(
            lambda: client.chat(
                model=self.model,
                messages=messages,
                format="json",
                options=self._build_options(),
            ),
            label="generate_json",
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
        options = self._build_options()

        log_event(
            logger, logging.DEBUG, "llm_request",
            provider="ollama", model=self.model,
        )
        _start = time.monotonic()

        # Ollama SDK expects tool_call arguments as dict, not JSON string.
        # The agent loop stores arguments as JSON strings (OpenAI format),
        # so we convert them back to dicts here.
        cleaned_messages = _fix_ollama_messages(messages)

        # Retry with tools on transient errors (e.g., XML parse errors
        # from malformed model output), then fall back to text-only.
        # Connection errors get exponential backoff via _with_conn_backoff.
        result = None
        max_tool_retries = 2
        for _retry in range(max_tool_retries):
            try:
                result = await asyncio.wait_for(
                    self._with_conn_backoff(
                        lambda: client.chat(
                            model=self.model,
                            messages=cleaned_messages,
                            tools=tools,
                            stream=False,
                            options=options,
                        ),
                        label="generate_with_tools",
                    ),
                    timeout=self.request_timeout,
                )
                break  # Success
            except TimeoutError:
                raise  # Let caller handle request-level timeouts
            except Exception as e:
                # Connection errors already retried by _with_conn_backoff;
                # if we get here it's exhausted — re-raise.
                if _is_connection_error(e):
                    raise
                log_event(
                    logger, logging.WARNING, "llm_tool_retry",
                    provider="ollama", model=self.model,
                    retry=_retry + 1, error=str(e)[:200],
                )
                if _retry < max_tool_retries - 1:
                    continue  # Retry with tools
                # Final fallback: text-only request without tools
                try:
                    result = await asyncio.wait_for(
                        self._with_conn_backoff(
                            lambda: client.chat(
                                model=self.model,
                                messages=cleaned_messages,
                                stream=False,
                                options=options,
                            ),
                            label="generate_with_tools_fallback",
                        ),
                        timeout=self.request_timeout,
                    )
                except Exception:
                    raise e  # Re-raise original tool error

        _duration_ms = int((time.monotonic() - _start) * 1000)
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

        # Fallback: extract tool calls from text if model didn't use structured API
        # Some models (qwen2.5-coder, etc.) output tool calls as JSON blocks in text
        if not tool_calls and content:
            text_tool_calls = _extract_tool_calls_from_text(content, tools)
            if text_tool_calls:
                tool_calls = text_tool_calls
                # Remove the JSON blocks from content since they're now tool calls
                content = ""
                log_event(
                    logger, logging.INFO, "llm_text_tool_fallback",
                    provider="ollama", model=self.model,
                    extracted_count=len(tool_calls),
                )

        log_event(
            logger, logging.DEBUG, "llm_response",
            provider="ollama", model=self.model,
            duration_ms=_duration_ms,
            content_length=len(content),
            tool_calls_count=len(tool_calls),
        )

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

    # Retry config for free-tier reliability
    MAX_RETRIES = 5
    RETRY_BASE_DELAY = 5.0  # seconds, doubles each retry
    RATE_LIMIT_DELAY = 15.0  # extra delay on 429
    REQUEST_TIMEOUT = 600.0  # seconds (match gateway timeout)

    def __init__(self, config: AutoCodeConfig) -> None:
        self.model = config.llm.model
        self.api_base = config.llm.api_base
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")

    def _make_client(self) -> Any:
        """Create AsyncOpenAI client with robust timeout settings."""
        import httpx
        from openai import AsyncOpenAI

        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=httpx.Timeout(self.REQUEST_TIMEOUT, connect=30.0),
            max_retries=0,  # we handle retries ourselves
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Generate via OpenRouter (OpenAI-compatible API) with retry."""
        import asyncio as _asyncio

        client = self._make_client()

        for attempt in range(self.MAX_RETRIES):
            try:
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
                    return
                else:
                    result = await client.chat.completions.create(
                        model=self.model,
                        messages=messages,  # type: ignore[arg-type]
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                    content = result.choices[0].message.content or ""
                    yield content
                    return
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    is_rate_limit = "429" in str(e)
                    delay = (
                        self.RATE_LIMIT_DELAY * (1 + attempt)
                        if is_rate_limit
                        else self.RETRY_BASE_DELAY * (2 ** attempt)
                    )
                    logger.warning(
                        "OpenRouter generate retry %d/%d%s: %s (waiting %.0fs)",
                        attempt + 1, self.MAX_RETRIES,
                        " [rate-limit]" if is_rate_limit else "",
                        str(e)[:120], delay,
                    )
                    await _asyncio.sleep(delay)
                else:
                    raise

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
    ) -> BaseModel:
        """Generate JSON via OpenRouter with response_format and retry."""
        import asyncio as _asyncio
        import json

        from openai.types.shared_params import ResponseFormatJSONObject

        client = self._make_client()
        for attempt in range(self.MAX_RETRIES):
            try:
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
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "OpenRouter generate_json retry %d/%d: %s (waiting %.1fs)",
                        attempt + 1, self.MAX_RETRIES, e, delay,
                    )
                    await _asyncio.sleep(delay)
                else:
                    raise
        msg = "unreachable"
        raise RuntimeError(msg)

    @staticmethod
    def _sanitize_tool_call_ids(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sanitize tool_call_ids to be alphanumeric only.

        Some providers (Mistral) reject IDs with underscores/hyphens.
        When routing through a multi-provider gateway, the ID format from
        one provider may be rejected by the next. Strip non-alphanumeric
        chars to ensure universal compatibility.
        """
        import re
        sanitized = []
        for msg in messages:
            msg = dict(msg)  # shallow copy
            # Sanitize tool_call_id in tool result messages
            if msg.get("role") == "tool" and "tool_call_id" in msg:
                msg["tool_call_id"] = re.sub(r"[^a-zA-Z0-9]", "", msg["tool_call_id"])
            # Sanitize tool_calls in assistant messages
            if msg.get("tool_calls"):
                new_tcs = []
                for tc in msg["tool_calls"]:
                    tc = dict(tc)
                    if "id" in tc:
                        tc["id"] = re.sub(r"[^a-zA-Z0-9]", "", tc["id"])
                    new_tcs.append(tc)
                msg["tool_calls"] = new_tcs
            sanitized.append(msg)
        return sanitized

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        *,
        on_chunk: Any | None = None,
        on_thinking_chunk: Any | None = None,
        reasoning_enabled: bool = True,
    ) -> LLMResponse:
        """Generate with tool calling via OpenRouter with retry + non-streaming fallback."""
        import asyncio as _asyncio

        client = self._make_client()

        # Sanitize tool_call_ids for multi-provider gateway compatibility
        messages = self._sanitize_tool_call_ids(messages)

        extra_body: dict[str, Any] = {}
        # Only send reasoning extension for actual OpenRouter, not LLM Gateway
        if reasoning_enabled and "openrouter.ai" in self.api_base:
            extra_body["reasoning"] = {"enabled": True}

        log_event(
            logger, logging.DEBUG, "llm_request",
            provider="openrouter", model=self.model,
        )

        for attempt in range(self.MAX_RETRIES):
            _start = time.monotonic()
            # Stream on first attempt, non-streaming fallback on retries
            use_stream = attempt == 0

            try:
                if use_stream:
                    result = await self._tools_streaming(
                        client, messages, tools, extra_body,
                        on_chunk, on_thinking_chunk,
                    )
                else:
                    result = await self._tools_non_streaming(
                        client, messages, tools, extra_body,
                    )

                _duration_ms = int((time.monotonic() - _start) * 1000)

                # Fallback: extract tool calls from text
                if not result.tool_calls and result.content:
                    text_tool_calls = _extract_tool_calls_from_text(
                        result.content, tools,
                    )
                    if text_tool_calls:
                        result = LLMResponse(
                            content="",
                            tool_calls=text_tool_calls,
                            finish_reason="tool_calls",
                            reasoning=result.reasoning,
                        )
                        log_event(
                            logger, logging.INFO, "llm_text_tool_fallback",
                            provider="openrouter", model=self.model,
                            extracted_count=len(text_tool_calls),
                        )

                log_event(
                    logger, logging.DEBUG, "llm_response",
                    provider="openrouter", model=self.model,
                    duration_ms=_duration_ms,
                    content_length=len(result.content or ""),
                    tool_calls_count=len(result.tool_calls),
                    attempt=attempt + 1,
                    streamed=use_stream,
                )
                return result

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    # Longer delay on rate limit (429)
                    is_rate_limit = "429" in str(e)
                    delay = (
                        self.RATE_LIMIT_DELAY * (1 + attempt)
                        if is_rate_limit
                        else self.RETRY_BASE_DELAY * (2 ** attempt)
                    )
                    logger.warning(
                        "OpenRouter retry %d/%d%s: %s "
                        "(waiting %.0fs)",
                        attempt + 1, self.MAX_RETRIES,
                        " [rate-limit]" if is_rate_limit else "",
                        str(e)[:120], delay,
                    )
                    await _asyncio.sleep(delay)
                else:
                    log_event(
                        logger, logging.ERROR, "llm_error",
                        provider="openrouter", model=self.model,
                        error=str(e), attempts=self.MAX_RETRIES,
                    )
                    raise

        msg = "unreachable"
        raise RuntimeError(msg)

    async def _tools_streaming(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        extra_body: dict[str, Any],
        on_chunk: Any | None,
        on_thinking_chunk: Any | None,
    ) -> LLMResponse:
        """Streaming path for generate_with_tools."""
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_call_data: dict[int, dict[str, Any]] = {}
        finish_reason = "stop"
        in_think_tag = False

        response_stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=tools,  # type: ignore[arg-type]
            stream=True,
            extra_body=extra_body or None,
        )

        async for chunk in response_stream:  # type: ignore[union-attr]
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                finish_reason = choice.finish_reason

            delta = choice.delta

            reasoning_text = getattr(delta, "reasoning", None) if delta else None
            if reasoning_text:
                reasoning_parts.append(reasoning_text)
                if on_thinking_chunk:
                    on_thinking_chunk(reasoning_text)

            if delta and delta.content:
                text = delta.content

                if "<think>" in text:
                    in_think_tag = True
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
                            tool_call_data[idx]["arguments"] += (
                                tc_delta.function.arguments
                            )

        content = "".join(content_parts) or None
        reasoning = "".join(reasoning_parts) or None
        tool_calls = self._parse_tool_calls(tool_call_data)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else finish_reason,
            reasoning=reasoning,
        )

    async def _tools_non_streaming(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        extra_body: dict[str, Any],
    ) -> LLMResponse:
        """Non-streaming fallback — more reliable on free tier."""
        import json

        result = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=tools,  # type: ignore[arg-type]
            stream=False,
            extra_body=extra_body or None,
        )

        choice = result.choices[0]
        msg = choice.message
        content = msg.content or None
        finish_reason = choice.finish_reason or "stop"
        reasoning = getattr(msg, "reasoning", None)

        tool_calls: list[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = (
                        json.loads(tc.function.arguments)
                        if tc.function.arguments else {}
                    )
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id or "",
                    name=tc.function.name or "",
                    arguments=args,
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else finish_reason,
            reasoning=reasoning,
        )

    @staticmethod
    def _parse_tool_calls(
        tool_call_data: dict[int, dict[str, Any]],
    ) -> list[ToolCall]:
        """Parse accumulated streaming tool call deltas into ToolCall objects."""
        import json

        tool_calls: list[ToolCall] = []
        for _idx, tc_data in sorted(tool_call_data.items()):
            try:
                args = (
                    json.loads(tc_data["arguments"])
                    if tc_data["arguments"] else {}
                )
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(
                id=tc_data["id"],
                name=tc_data["name"],
                arguments=args,
            ))
        return tool_calls

    def count_tokens(self, text: str) -> int:
        """Approximate token count (~4 chars per token)."""
        return len(text) // 4


def create_provider(config: AutoCodeConfig) -> OllamaProvider | OpenRouterProvider:
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

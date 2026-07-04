"""Tests for LLM provider utilities."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from autocode.agent.prompts import CACHE_BOUNDARY_MARKER
from autocode.config import AutoCodeConfig
from autocode.layer4.llm import (
    ConversationHistory,
    LLMResponse,
    OllamaProvider,
    OpenRouterProvider,
    _extract_openai_usage,
    _extract_tool_calls_from_text,
    _format_openrouter_error,
    _is_connection_error,
    _is_loopback_api_base,
    _is_openrouter_retryable_error,
)


class TestConversationHistory:
    """Test ConversationHistory management."""

    def test_add_and_get_messages(self) -> None:
        h = ConversationHistory(system_prompt="sys")
        h.add_user("hello")
        h.add_assistant("hi")
        msgs = h.get_messages()
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"

    def test_trim_removes_pairs_not_singles(self) -> None:
        """Trim should remove user+assistant pairs, not leave orphans."""
        h = ConversationHistory(system_prompt="s")
        h.add_user("u1" * 100)
        h.add_assistant("a1" * 100)
        h.add_user("u2" * 100)
        h.add_assistant("a2" * 100)
        h.add_user("u3")
        h.add_assistant("a3")

        # Trim to a budget that forces removal of oldest pairs
        h.trim_to_budget(50)
        msgs = h.get_messages()

        # System prompt should always be preserved
        assert msgs[0]["role"] == "system"

        # No orphan assistant messages — every user has a matching assistant
        non_system = [m for m in msgs if m["role"] != "system"]
        for i in range(0, len(non_system) - 1, 2):
            assert non_system[i]["role"] == "user"
            if i + 1 < len(non_system):
                assert non_system[i + 1]["role"] == "assistant"

    def test_trim_preserves_system_prompt(self) -> None:
        h = ConversationHistory(system_prompt="keep me")
        h.add_user("x" * 1000)
        h.add_assistant("y" * 1000)
        h.trim_to_budget(10)
        assert h.get_messages()[0] == {"role": "system", "content": "keep me"}

    def test_token_estimate(self) -> None:
        h = ConversationHistory()
        h.add_user("a" * 400)  # ~100 tokens
        assert h.token_estimate() == 100


class TestExtractToolCallsFromText:
    """Test fallback tool call extraction from text output."""

    def test_extracts_json_code_blocks(self) -> None:
        text = (
            'I will create the project.\n\n```json\n'
            '{"name": "run_command", "arguments": {"command": "npm init -y"}}\n'
            '```\n\nThen install deps:\n\n```json\n'
            '{"name": "write_file", "arguments": {"path": "src/App.jsx", "content": "hello"}}\n'
            '```'
        )
        tools = [
            {"function": {"name": "run_command"}},
            {"function": {"name": "write_file"}},
        ]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 2
        assert result[0].name == "run_command"
        assert result[0].arguments == {"command": "npm init -y"}
        assert result[1].name == "write_file"
        assert result[1].arguments == {"path": "src/App.jsx", "content": "hello"}

    def test_ignores_unknown_tools(self) -> None:
        text = '```json\n{"name": "delete_everything", "arguments": {}}\n```'
        tools = [{"function": {"name": "run_command"}}]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 0

    def test_handles_no_json_blocks(self) -> None:
        text = "I don't know how to do this."
        result = _extract_tool_calls_from_text(text)
        assert len(result) == 0

    def test_handles_malformed_json(self) -> None:
        text = '```json\n{"name": "run_command", "arguments": {broken}\n```'
        result = _extract_tool_calls_from_text(text)
        assert len(result) == 0

    def test_extracts_bare_json_objects(self) -> None:
        text = '{"name": "run_command", "arguments": {"command": "ls"}}'
        tools = [{"function": {"name": "run_command"}}]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 1
        assert result[0].name == "run_command"

    def test_handles_nested_braces_in_content(self) -> None:
        """Regression: model outputs write_file with nested JSON in content."""
        pkg_json = '{"name": "my-app", "version": "1.0.0", "dependencies": {"react": "^18.0.0"}}'
        text = (
            '```json\n'
            '{"name": "write_file", "arguments": '
            '{"path": "package.json", "content": "' + pkg_json.replace('"', '\\"') + '"}}\n'
            '```'
        )
        tools = [{"function": {"name": "write_file"}}]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 1
        assert result[0].name == "write_file"
        assert result[0].arguments["path"] == "package.json"
        assert "react" in result[0].arguments["content"]

    def test_fuzzy_matches_hallucinated_tool_names(self) -> None:
        """Model outputs 'update_package_json' instead of 'write_file'."""
        text = (
            "```json\n"
            '{"name": "update_package_json", "arguments": '
            '{"path": "package.json", "content": "{}"}}\n'
            "```"
        )
        tools = [
            {"function": {"name": "write_file"}},
            {"function": {"name": "run_command"}},
        ]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 1
        assert result[0].name == "write_file"

    def test_fuzzy_matches_execute_command(self) -> None:
        """Model outputs 'execute_command' instead of 'run_command'."""
        text = '{"name": "execute_command", "arguments": {"command": "npm install"}}'
        tools = [{"function": {"name": "run_command"}}]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 1
        assert result[0].name == "run_command"

    def test_handles_multiline_nested_content(self) -> None:
        """Model outputs multi-line file content with braces."""
        text = (
            '```json\n'
            '{"name": "write_file", "arguments": {"path": "App.jsx", '
            '"content": "function App() {\\n  return (\\n    <div>{count}</div>\\n  );\\n}"}}\n'
            '```'
        )
        tools = [{"function": {"name": "write_file"}}]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 1
        assert result[0].name == "write_file"
        assert "App" in result[0].arguments["content"]

    def test_extracts_xml_style_function_tags(self) -> None:
        """Model outputs tool calls as <function=name> XML tags (qwen3-coder)."""
        text = (
            "I'll list the files.\n\n"
            "<function=list_files>\n"
            "<parameter=path>\n.\n</parameter>\n"
            "</function>\n"
        )
        tools = [{"function": {"name": "list_files"}}]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 1
        assert result[0].name == "list_files"
        assert result[0].arguments["path"] == "."

    def test_extracts_xml_style_multiple_params(self) -> None:
        """XML-style function tags with multiple parameters."""
        text = (
            "<function=write_file>\n"
            "<parameter=path>src/main.py</parameter>\n"
            "<parameter=content>print('hello')</parameter>\n"
            "</function>\n"
        )
        tools = [{"function": {"name": "write_file"}}]
        result = _extract_tool_calls_from_text(text, tools)
        assert len(result) == 1
        assert result[0].name == "write_file"
        assert result[0].arguments["path"] == "src/main.py"
        assert result[0].arguments["content"] == "print('hello')"


class TestConnectionErrorClassification:
    """Classify transient network failures vs model/runtime failures."""

    def test_response_error_xml_parse_is_not_connection_error(self) -> None:
        class ResponseError(Exception):
            pass

        exc = ResponseError(
            "failed to parse XML: XML syntax error on line 1 (status code: 500)",
        )
        assert _is_connection_error(exc) is False

    def test_response_error_gateway_timeout_is_connection_error(self) -> None:
        class ResponseError(Exception):
            def __init__(self, msg: str, status_code: int) -> None:
                super().__init__(msg)
                self.status_code = status_code

        exc = ResponseError("upstream timeout", 504)
        assert _is_connection_error(exc) is True

    def test_named_connect_error_is_connection_error(self) -> None:
        class ConnectError(Exception):
            pass

        exc = ConnectError("cannot connect to host")
        assert _is_connection_error(exc) is True


class TestOpenRouterRetryClassification:
    def test_invalid_model_is_not_retryable(self) -> None:
        class BadRequestError(Exception):
            def __init__(self, msg: str, status_code: int) -> None:
                super().__init__(msg)
                self.status_code = status_code

        exc = BadRequestError("Error code: 400 - model not found", 400)

        assert _is_openrouter_retryable_error(
            exc,
            api_base="http://localhost:4000/v1",
        ) is False

    def test_loopback_connection_error_is_not_retryable(self) -> None:
        exc = ConnectionRefusedError("[Errno 111] Connection refused")

        assert _is_openrouter_retryable_error(
            exc,
            api_base="http://localhost:4000/v1",
        ) is False

    def test_rate_limit_is_retryable(self) -> None:
        class RateLimitError(Exception):
            def __init__(self, msg: str, status_code: int) -> None:
                super().__init__(msg)
                self.status_code = status_code

        exc = RateLimitError("Error code: 429 - rate limit", 429)

        assert _is_openrouter_retryable_error(
            exc,
            api_base="https://openrouter.ai/api/v1",
        ) is True

    def test_loopback_detection(self) -> None:
        assert _is_loopback_api_base("http://localhost:4000/v1") is True
        assert _is_loopback_api_base("http://127.0.0.1:4000/v1") is True
        assert _is_loopback_api_base("https://openrouter.ai/api/v1") is False

    def test_invalid_model_error_message_is_human_readable(self) -> None:
        class NotFoundError(Exception):
            def __init__(self, msg: str, status_code: int) -> None:
                super().__init__(msg)
                self.status_code = status_code

        exc = NotFoundError("Error code: 404 - model not found", 404)

        assert _format_openrouter_error(
            exc,
            model="definitely-not-real",
            api_base="http://localhost:4000/v1",
        ) == "Model alias 'definitely-not-real' is not available on the configured gateway."

    def test_gateway_alias_error_includes_response_detail_when_available(self) -> None:
        class FakeResponse:
            status_code = 400

            @staticmethod
            def json() -> dict[str, object]:
                return {"error": {"message": "No deployment for model alias tools"}}

        class BadRequestError(Exception):
            response = FakeResponse()

        message = _format_openrouter_error(
            BadRequestError("Error code: 400 - model alias rejected"),
            model="tools",
            api_base="http://localhost:4000/v1",
        )

        assert message == (
            "Model alias 'tools' is not available on the configured gateway. "
            "Detail: No deployment for model alias tools"
        )

    def test_function_calling_disabled_error_is_not_reported_as_missing_alias(self) -> None:
        class BadRequestError(Exception):
            def __init__(self, msg: str, status_code: int) -> None:
                super().__init__(msg)
                self.status_code = status_code

        exc = BadRequestError(
            "Error code: 400 - Function calling is not enabled for models/gemma-3-27b-it",
            400,
        )

        message = _format_openrouter_error(
            exc,
            model="coding",
            api_base="http://localhost:4000/v1",
        )

        assert "does not support tool/function calling" in message
        assert "coding" in message


class TestProviderReasoningFlags:
    """Provider request flags for user-controlled thinking mode."""

    @pytest.mark.asyncio()
    async def test_openrouter_reasoning_flag_bidirectional(self) -> None:
        config = AutoCodeConfig()
        config.llm.provider = "openrouter"
        config.llm.api_base = "https://openrouter.ai/api/v1"
        provider = OpenRouterProvider(config)
        provider.MAX_RETRIES = 1
        captured: list[dict[str, Any]] = []

        async def fake_streaming(
            client: Any,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
            extra_body: dict[str, Any],
            on_chunk: Any,
            on_thinking_chunk: Any,
            *,
            extra_headers: dict[str, str] | None = None,
        ) -> LLMResponse:
            assert extra_headers == {}
            captured.append(extra_body)
            return LLMResponse(content="ok")

        provider._make_client = lambda: object()  # type: ignore[method-assign]
        provider._tools_streaming = fake_streaming  # type: ignore[method-assign]

        await provider.generate_with_tools([], [], reasoning_enabled=True)
        await provider.generate_with_tools([], [], reasoning_enabled=False)

        assert captured == [
            {"reasoning": {"enabled": True}},
            {"reasoning": {"enabled": False}},
        ]

    @pytest.mark.asyncio()
    async def test_openrouter_gateway_reasoning_toggle_warns_once(self) -> None:
        config = AutoCodeConfig()
        config.llm.provider = "openrouter"
        config.llm.api_base = "http://localhost:4000/v1"
        provider = OpenRouterProvider(config)
        provider.MAX_RETRIES = 1
        warnings: list[str] = []
        captured: list[dict[str, Any]] = []

        async def fake_streaming(
            client: Any,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
            extra_body: dict[str, Any],
            on_chunk: Any,
            on_thinking_chunk: Any,
            *,
            extra_headers: dict[str, str] | None = None,
        ) -> LLMResponse:
            assert extra_headers == {}
            captured.append(extra_body)
            return LLMResponse(content="ok")

        provider._make_client = lambda: object()  # type: ignore[method-assign]
        provider._tools_streaming = fake_streaming  # type: ignore[method-assign]

        await provider.generate_with_tools(
            [],
            [],
            reasoning_enabled=False,
            on_retry_notice=warnings.append,
        )
        await provider.generate_with_tools(
            [],
            [],
            reasoning_enabled=False,
            on_retry_notice=warnings.append,
        )

        assert captured == [{}, {}]
        assert len(warnings) == 1
        assert "cannot enforce thinking toggle" in warnings[0]

    @pytest.mark.asyncio()
    async def test_ollama_think_param_bidirectional(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict[str, Any]] = []

        class FakeAsyncClient:
            def __init__(self, host: str) -> None:
                self.host = host

            async def chat(self, **kwargs: Any) -> Any:
                calls.append(kwargs)
                return SimpleNamespace(message=SimpleNamespace(content="ok"))

        monkeypatch.setitem(
            sys.modules,
            "ollama",
            SimpleNamespace(AsyncClient=FakeAsyncClient),
        )

        config = AutoCodeConfig()
        config.llm.provider = "ollama"
        provider = OllamaProvider(config)

        async def no_backoff(coro_fn: Any, *, label: str = "ollama_call") -> Any:
            return await coro_fn()

        provider._with_conn_backoff = no_backoff  # type: ignore[method-assign]

        await provider.generate_with_tools([], [], reasoning_enabled=True)
        await provider.generate_with_tools([], [], reasoning_enabled=False)

        assert calls[0]["think"] is True
        assert calls[1]["think"] is False


class TestProviderUsageCapture:
    """Provider usage extraction for cost accounting."""

    def test_openrouter_ignores_non_numeric_usage_fields(self) -> None:
        usage = SimpleNamespace(
            prompt_tokens="tool_use_failed",
            completion_tokens=None,
            prompt_tokens_details=SimpleNamespace(cached_tokens="not-a-number"),
        )

        assert _extract_openai_usage(usage) == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_input_tokens": 0,
            "cache_creation_tokens": 0,
            "reasoning_tokens": 0,
        }

    @pytest.mark.asyncio()
    async def test_openrouter_captures_cached_tokens_from_response(self) -> None:
        config = AutoCodeConfig()
        config.llm.provider = "openrouter"
        provider = OpenRouterProvider(config)

        usage = SimpleNamespace(
            prompt_tokens=10_000,
            completion_tokens=500,
            prompt_tokens_details=SimpleNamespace(cached_tokens=8_000),
        )
        result = SimpleNamespace(
            usage=usage,
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content="ok",
                        reasoning=None,
                        tool_calls=None,
                    ),
                )
            ],
        )

        async def fake_create(**kwargs: Any) -> Any:
            return result

        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=fake_create),
            ),
        )

        response = await provider._tools_non_streaming(client, [], [], {})

        assert response.usage == {
            "prompt_tokens": 10_000,
            "completion_tokens": 500,
            "cached_input_tokens": 8_000,
            "cache_creation_tokens": 0,
            "reasoning_tokens": 0,
        }

    def test_ollama_passes_zero_cached_tokens(self) -> None:
        config = AutoCodeConfig()
        config.llm.provider = "ollama"
        provider = OllamaProvider(config)
        result = SimpleNamespace(
            prompt_eval_count=1_000,
            eval_count=250,
            message=SimpleNamespace(content="ok", tool_calls=None),
        )

        response = provider._consume_ollama_non_stream_response(
            result,
            on_chunk=None,
            on_thinking_chunk=None,
        )

        assert response.usage == {
            "prompt_tokens": 1_000,
            "completion_tokens": 250,
            "cached_input_tokens": 0,
            "cache_creation_tokens": 0,
            "reasoning_tokens": 0,
        }

    @pytest.mark.asyncio()
    async def test_openrouter_generate_with_tools_adds_anthropic_cache_header(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = AutoCodeConfig()
        config.llm.provider = "openrouter"
        config.llm.model = "anthropic/claude-3.7-sonnet"
        provider = OpenRouterProvider(config)
        captured: dict[str, Any] = {}

        provider._make_client = lambda: object()  # type: ignore[method-assign]

        async def fake_streaming(
            client: Any,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
            extra_body: dict[str, Any],
            on_chunk: Any,
            on_thinking_chunk: Any,
            *,
            extra_headers: dict[str, str] | None = None,
        ) -> LLMResponse:
            captured["messages"] = messages
            captured["extra_headers"] = extra_headers
            return LLMResponse(content="ok", usage={})

        monkeypatch.setattr(provider, "_tools_streaming", fake_streaming)

        await provider.generate_with_tools(
            [
                {
                    "role": "system",
                    "content": f"stable\n{CACHE_BOUNDARY_MARKER}\ndynamic",
                }
            ],
            [],
        )

        assert captured["extra_headers"] == {
            "anthropic-beta": "prompt-caching-2024-07-31",
        }
        assert captured["messages"][0]["content"][0]["cache_control"] == {
            "type": "ephemeral",
            "ttl": "1h",
        }

    @pytest.mark.asyncio()
    async def test_openrouter_prompt_cache_disable_env_skips_injection(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = AutoCodeConfig()
        config.llm.provider = "openrouter"
        config.llm.model = "anthropic/claude-3.7-sonnet"
        provider = OpenRouterProvider(config)
        captured: dict[str, Any] = {}

        monkeypatch.setenv("AUTOCODE_DISABLE_PROMPT_CACHE", "true")
        provider._make_client = lambda: object()  # type: ignore[method-assign]

        async def fake_streaming(
            client: Any,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
            extra_body: dict[str, Any],
            on_chunk: Any,
            on_thinking_chunk: Any,
            *,
            extra_headers: dict[str, str] | None = None,
        ) -> LLMResponse:
            captured["messages"] = messages
            captured["extra_headers"] = extra_headers
            return LLMResponse(content="ok", usage={})

        monkeypatch.setattr(provider, "_tools_streaming", fake_streaming)

        await provider.generate_with_tools(
            [
                {
                    "role": "system",
                    "content": f"stable\n{CACHE_BOUNDARY_MARKER}\ndynamic",
                }
            ],
            [],
        )

        assert captured["extra_headers"] == {}
        assert captured["messages"][0]["content"] == (
            f"stable\n{CACHE_BOUNDARY_MARKER}\ndynamic"
        )


class TestProviderStreamingThinkTags:
    """Provider integration with the shared streaming think-tag parser."""

    @pytest.mark.asyncio()
    async def test_openrouter_tag_fallback_handles_split_tags(self) -> None:
        config = AutoCodeConfig()
        config.llm.provider = "openrouter"
        provider = OpenRouterProvider(config)
        tokens: list[str] = []
        thinking: list[str] = []

        class FakeDelta:
            def __init__(self, content: str) -> None:
                self.content = content
                self.tool_calls = None
                self.reasoning = None

        class FakeChoice:
            def __init__(self, content: str, finish_reason: str | None = None) -> None:
                self.delta = FakeDelta(content)
                self.finish_reason = finish_reason

        class FakeChunk:
            def __init__(self, content: str, finish_reason: str | None = None) -> None:
                self.choices = [FakeChoice(content, finish_reason)]

        async def fake_stream() -> Any:
            for chunk in (
                FakeChunk("visible <thi"),
                FakeChunk("nk>hidden</thi"),
                FakeChunk("nk> final", "stop"),
            ):
                yield chunk

        async def fake_create(**kwargs: Any) -> Any:
            return fake_stream()

        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=fake_create),
            ),
        )

        response = await provider._tools_streaming(
            client,
            [],
            [],
            {},
            tokens.append,
            thinking.append,
        )

        assert tokens == ["visible ", " final"]
        assert thinking == ["hidden"]
        assert response.content == "visible  final"
        assert response.reasoning == "hidden"

    @pytest.mark.asyncio()
    async def test_ollama_streams_thinking_chunks_before_final_content(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[dict[str, Any]] = []
        tokens: list[str] = []
        thinking: list[str] = []

        class FakeAsyncClient:
            def __init__(self, host: str) -> None:
                self.host = host

            async def chat(self, **kwargs: Any) -> Any:
                calls.append(kwargs)
                if kwargs["stream"]:
                    async def stream() -> Any:
                        for content in ("<think>first", " second</think>", " answer"):
                            yield SimpleNamespace(message=SimpleNamespace(content=content))

                    return stream()
                return SimpleNamespace(
                    message=SimpleNamespace(content="<think>first second</think> answer"),
                )

        monkeypatch.setitem(
            sys.modules,
            "ollama",
            SimpleNamespace(AsyncClient=FakeAsyncClient),
        )

        config = AutoCodeConfig()
        config.llm.provider = "ollama"
        provider = OllamaProvider(config)

        async def no_backoff(coro_fn: Any, *, label: str = "ollama_call") -> Any:
            return await coro_fn()

        provider._with_conn_backoff = no_backoff  # type: ignore[method-assign]

        response = await provider.generate_with_tools(
            [],
            [],
            on_chunk=tokens.append,
            on_thinking_chunk=thinking.append,
        )

        assert calls[0]["stream"] is True
        assert thinking == ["first", " second"]
        assert tokens == [" answer"]
        assert response.content == " answer"
        assert response.reasoning == "first second"

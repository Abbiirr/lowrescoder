"""Tests for LLM provider utilities."""

from __future__ import annotations

from autocode.layer4.llm import (
    ConversationHistory,
    _extract_tool_calls_from_text,
    _is_connection_error,
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

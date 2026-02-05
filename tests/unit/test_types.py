"""Tests for core types."""

from __future__ import annotations

from hybridcoder.core.types import (
    CodeChunk,
    FileRange,
    LayerResult,
    Request,
    RequestType,
    Response,
    Symbol,
)


class TestRequestType:
    """Test RequestType enum."""

    def test_deterministic_value(self) -> None:
        assert RequestType.DETERMINISTIC_QUERY.value == "deterministic"

    def test_all_types_exist(self) -> None:
        expected = {
            "deterministic", "search", "simple_edit", "complex_task",
            "chat", "config", "help",
        }
        actual = {t.value for t in RequestType}
        assert actual == expected


class TestLayerResult:
    """Test LayerResult enum."""

    def test_escalate_option(self) -> None:
        assert LayerResult.ESCALATE.value == "escalate"


class TestRequest:
    """Test Request dataclass."""

    def test_minimal_request(self) -> None:
        req = Request(raw_input="hello", request_type=RequestType.CHAT)
        assert req.raw_input == "hello"
        assert req.file_context is None
        assert req.conversation_history == []


class TestResponse:
    """Test Response dataclass."""

    def test_successful_response(self) -> None:
        resp = Response(content="Hello!", layer_used=4, tokens_used=5)
        assert resp.success is True
        assert resp.error is None
        assert resp.files_modified == []


class TestFileRange:
    """Test FileRange dataclass."""

    def test_defaults(self) -> None:
        fr = FileRange(path="test.py")
        assert fr.start_line == 1
        assert fr.end_line is None


class TestSymbol:
    """Test Symbol dataclass."""

    def test_function_symbol(self) -> None:
        sym = Symbol(name="foo", kind="function", file="test.py", line=1, end_line=10)
        assert sym.scope is None
        assert sym.type_annotation is None


class TestCodeChunk:
    """Test CodeChunk dataclass."""

    def test_chunk_defaults(self) -> None:
        chunk = CodeChunk(
            content="def foo(): pass",
            file_path="test.py",
            language="python",
            start_line=1,
            end_line=1,
            chunk_type="function",
        )
        assert chunk.scope_chain == []
        assert chunk.imports == []
        assert chunk.embedding is None

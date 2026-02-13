"""Core data types for HybridCoder.

All shared enums, dataclasses, and protocols used across layers.
Based on LLD Phase 3, Section 2.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RequestType(Enum):
    """Classification of user request for layer routing."""

    DETERMINISTIC_QUERY = "deterministic"  # → Layer 1
    SEMANTIC_SEARCH = "search"  # → Layer 2
    SIMPLE_EDIT = "simple_edit"  # → Layer 3
    COMPLEX_TASK = "complex_task"  # → Layer 4
    CHAT = "chat"  # → Layer 4
    CONFIGURATION = "config"  # → Config handler
    HELP = "help"  # → Built-in


class LayerResult(Enum):
    """Outcome of a layer's processing attempt."""

    SUCCESS = "success"
    FAILURE = "failure"
    ESCALATE = "escalate"  # Try next layer


@dataclass
class Request:
    """User request with parsed context."""

    raw_input: str
    request_type: RequestType
    file_context: str | None = None
    symbol: str | None = None
    conversation_history: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Response:
    """Response from any layer."""

    content: str
    layer_used: int  # 1-4
    tokens_used: int = 0
    latency_ms: float = 0.0
    files_modified: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None


@dataclass
class FileRange:
    """A range within a file."""

    path: str
    start_line: int = 1
    end_line: int | None = None


@dataclass
class Symbol:
    """A code symbol extracted from parsing."""

    name: str
    kind: str  # function, class, variable, import, method
    file: str
    line: int
    end_line: int
    scope: str | None = None  # parent class/function
    type_annotation: str | None = None


@dataclass
class CodeChunk:
    """A chunk of code for embedding and retrieval."""

    content: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    chunk_type: str  # function, class, module, block
    scope_chain: list[str] = field(default_factory=list)  # e.g., ["MyClass", "my_method"]
    imports: list[str] = field(default_factory=list)
    embedding: list[float] | None = None


@dataclass
class SearchResult:
    """A result from hybrid search."""

    chunk: CodeChunk
    score: float
    match_type: str  # bm25, vector, hybrid


@dataclass
class ParseResult:
    """Result from tree-sitter parsing."""

    tree: Any  # tree_sitter.Tree
    file_path: str
    mtime: float
    language: str


@dataclass
class EditResult:
    """Result of an edit operation."""

    file_path: str
    original_content: str
    new_content: str
    diff: str
    syntax_valid: bool
    lint_passed: bool
    type_check_passed: bool
    commit_sha: str | None = None

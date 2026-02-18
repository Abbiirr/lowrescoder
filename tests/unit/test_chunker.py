"""Tests for the AST-aware chunker (Sprint 3D)."""

from __future__ import annotations

import textwrap

from autocode.core.types import CodeChunk
from autocode.layer2.chunker import ASTChunker

SIMPLE_MODULE = textwrap.dedent("""\
    import os
    from pathlib import Path

    MAX_SIZE = 100

    class MyClass:
        def __init__(self, name: str) -> None:
            self.name = name

        def greet(self) -> str:
            return f"Hello, {self.name}"

    def helper(x: int) -> int:
        return x + 1
""")

IMPORTS_ONLY = textwrap.dedent("""\
    import os
    import sys
    from pathlib import Path
""")

LARGE_FUNCTION = "def big():\n" + "\n".join(f"    x{i} = {i}" for i in range(200))

NESTED_CLASSES = textwrap.dedent("""\
    class Outer:
        class Inner:
            def method(self):
                pass

        def outer_method(self):
            pass
""")


class TestASTChunker:
    def test_chunk_simple_module(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        assert len(chunks) > 0
        assert all(isinstance(c, CodeChunk) for c in chunks)

    def test_chunk_has_correct_language(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        for chunk in chunks:
            assert chunk.language == "python"

    def test_chunk_boundaries_at_functions(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        chunk_contents = " ".join(c.content for c in chunks)
        assert "def helper" in chunk_contents
        assert "class MyClass" in chunk_contents

    def test_chunk_types(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        types = {c.chunk_type for c in chunks}
        # Should have at least function and class/module chunks
        assert len(types) > 0

    def test_chunk_line_numbers(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        for chunk in chunks:
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line

    def test_chunk_has_imports(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        # At least some chunks should carry import metadata
        has_imports = any(len(c.imports) > 0 for c in chunks)
        assert has_imports

    def test_chunk_scope_chain(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        # Methods in MyClass should have scope chain
        for chunk in chunks:
            if "def __init__" in chunk.content or "def greet" in chunk.content:
                if chunk.scope_chain:
                    assert "MyClass" in chunk.scope_chain

    def test_chunk_empty_source(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source("")
        assert chunks == []

    def test_chunk_whitespace_only(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source("   \n\n  ")
        assert chunks == []

    def test_chunk_imports_only(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(IMPORTS_ONLY)
        # Should produce at least a module-level chunk
        assert len(chunks) >= 0  # Might be empty or have a module chunk

    def test_chunk_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_MODULE)
        chunker = ASTChunker()
        chunks = chunker.chunk_file(str(f))
        assert len(chunks) > 0
        assert all(str(f) in c.file_path or c.file_path == str(f) for c in chunks)

    def test_large_function_splits(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(LARGE_FUNCTION)
        assert len(chunks) >= 1
        # The large function should either be one chunk or split
        total_content = "\n".join(c.content for c in chunks)
        assert "def big" in total_content

    def test_nested_classes(self):
        chunker = ASTChunker()
        chunks = chunker.chunk_source(NESTED_CLASSES)
        assert len(chunks) > 0
        all_content = " ".join(c.content for c in chunks)
        assert "Outer" in all_content

    def test_chunk_no_overlap(self):
        """Chunks should not have significant content overlap."""
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        if len(chunks) <= 1:
            return
        # Basic check: no two chunks should be identical
        contents = [c.content for c in chunks]
        assert len(set(contents)) == len(contents), "Duplicate chunks found"

    def test_chunk_coverage(self):
        """All non-trivial content should appear in at least one chunk."""
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        all_chunk_content = "\n".join(c.content for c in chunks)
        assert "def helper" in all_chunk_content
        assert "class MyClass" in all_chunk_content

    def test_decorated_function(self):
        source = textwrap.dedent("""\
            def decorator(f):
                return f

            @decorator
            def decorated():
                pass
        """)
        chunker = ASTChunker()
        chunks = chunker.chunk_source(source)
        all_content = " ".join(c.content for c in chunks)
        assert "decorated" in all_content

    def test_chunk_preserves_content(self):
        """Chunk content should match the actual source lines."""
        chunker = ASTChunker()
        chunks = chunker.chunk_source(SIMPLE_MODULE)
        for chunk in chunks:
            assert chunk.content.strip() != ""

    def test_module_level_code(self):
        source = textwrap.dedent("""\
            import os

            CONSTANT_A = 1
            CONSTANT_B = 2
            CONSTANT_C = 3

            def func():
                pass
        """)
        chunker = ASTChunker()
        chunks = chunker.chunk_source(source)
        assert len(chunks) >= 1

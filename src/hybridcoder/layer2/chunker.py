"""AST-aware code chunker using tree-sitter.

Splits code at function/class boundaries into 200-800 token chunks,
preserving scope chains and associated imports.
"""

from __future__ import annotations

from pathlib import Path

from hybridcoder.core.types import CodeChunk
from hybridcoder.layer1.parser import TreeSitterParser

# Approximate tokens per character (conservative for code)
_CHARS_PER_TOKEN = 4
_MIN_CHUNK_TOKENS = 200
_MAX_CHUNK_TOKENS = 800
_MIN_CHUNK_CHARS = _MIN_CHUNK_TOKENS * _CHARS_PER_TOKEN
_MAX_CHUNK_CHARS = _MAX_CHUNK_TOKENS * _CHARS_PER_TOKEN

# Node types that form chunk boundaries
_CHUNK_BOUNDARY_TYPES = frozenset({
    "function_definition",
    "class_definition",
    "decorated_definition",
})


class ASTChunker:
    """Split Python source files into meaningful code chunks at AST boundaries.

    Each chunk carries metadata: file_path, language, line range, chunk_type,
    scope_chain, and associated imports.
    """

    def __init__(self, parser: TreeSitterParser | None = None) -> None:
        self._parser = parser or TreeSitterParser()

    def chunk_file(self, file_path: str | Path) -> list[CodeChunk]:
        """Chunk a Python file into code chunks.

        Args:
            file_path: Path to a Python source file.

        Returns:
            List of CodeChunk objects.
        """
        path = Path(file_path)
        source = path.read_text(encoding="utf-8", errors="ignore")
        return self.chunk_source(source, str(path))

    def chunk_source(self, source: str, file_path: str = "<string>") -> list[CodeChunk]:
        """Chunk Python source code into code chunks.

        Args:
            source: Python source code string.
            file_path: Label for the chunks.

        Returns:
            List of CodeChunk objects.
        """
        if not source.strip():
            return []

        result = self._parser.parse_string(source, file_path=file_path)
        root = result.tree.root_node
        lines = source.splitlines()

        # Extract imports (top-level)
        imports = self._extract_imports(root, lines)

        chunks: list[CodeChunk] = []

        # Collect top-level definitions and module-level code
        module_lines: list[tuple[int, int]] = []  # (start, end) ranges for non-def code
        last_def_end = 0

        for child in root.children:
            node_type = child.type
            start_line = child.start_point[0]
            end_line = child.end_point[0]

            if node_type in _CHUNK_BOUNDARY_TYPES:
                # Emit any module-level code before this definition
                if start_line > last_def_end:
                    module_range = (last_def_end, start_line)
                    module_content = "\n".join(lines[module_range[0]:module_range[1]]).strip()
                    if module_content and len(module_content) > 10:
                        module_lines.append(module_range)

                # Process the definition
                self._chunk_definition(
                    child, lines, file_path, imports, chunks, scope_chain=[],
                )
                last_def_end = end_line + 1

        # Remaining module-level code after all definitions
        if last_def_end < len(lines):
            remaining = "\n".join(lines[last_def_end:]).strip()
            if remaining and len(remaining) > 10:
                module_lines.append((last_def_end, len(lines)))

        # Consolidate module-level chunks
        for start, end in module_lines:
            content = "\n".join(lines[start:end]).strip()
            if not content:
                continue
            chunks.append(CodeChunk(
                content=content,
                file_path=file_path,
                language="python",
                start_line=start + 1,
                end_line=end,
                chunk_type="module",
                scope_chain=[],
                imports=imports,
            ))

        return chunks

    def _chunk_definition(
        self,
        node: object,
        lines: list[str],
        file_path: str,
        imports: list[str],
        chunks: list[CodeChunk],
        scope_chain: list[str],
    ) -> None:
        """Process a function/class definition into chunks."""
        node_type = node.type  # type: ignore[attr-defined]
        start_line = node.start_point[0]  # type: ignore[attr-defined]
        end_line = node.end_point[0]  # type: ignore[attr-defined]

        # For decorated definitions, get the actual definition
        actual_node = node
        if node_type == "decorated_definition":
            for child in node.children:  # type: ignore[attr-defined]
                if child.type in ("function_definition", "class_definition"):
                    actual_node = child
                    break

        actual_type = actual_node.type  # type: ignore[attr-defined]

        # Get name
        name = self._get_name(actual_node)
        content = "\n".join(lines[start_line:end_line + 1])

        if actual_type == "class_definition":
            chunk_type = "class"
            new_scope = scope_chain + [name] if name else scope_chain

            # If class is small enough, emit as single chunk
            if len(content) <= _MAX_CHUNK_CHARS:
                chunks.append(CodeChunk(
                    content=content,
                    file_path=file_path,
                    language="python",
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    chunk_type=chunk_type,
                    scope_chain=list(scope_chain),
                    imports=imports,
                ))
            else:
                # For large classes, chunk individual methods
                body = self._find_child(actual_node, "block")
                if body:
                    # Emit class header (up to first method)
                    header_end = body.start_point[0]  # type: ignore[attr-defined]
                    header = "\n".join(lines[start_line:header_end + 1])
                    if header.strip():
                        chunks.append(CodeChunk(
                            content=header,
                            file_path=file_path,
                            language="python",
                            start_line=start_line + 1,
                            end_line=header_end + 1,
                            chunk_type="class",
                            scope_chain=list(scope_chain),
                            imports=imports,
                        ))

                    for child in body.children:  # type: ignore[attr-defined]
                        if child.type in _CHUNK_BOUNDARY_TYPES:
                            self._chunk_definition(
                                child, lines, file_path, imports, chunks,
                                scope_chain=new_scope,
                            )
        else:
            # Function/method
            chunk_type = "function"

            # If too large, split at logical boundaries
            if len(content) > _MAX_CHUNK_CHARS:
                self._split_large_chunk(
                    content, file_path, start_line, end_line,
                    chunk_type, scope_chain, imports, chunks,
                )
            else:
                chunks.append(CodeChunk(
                    content=content,
                    file_path=file_path,
                    language="python",
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    chunk_type=chunk_type,
                    scope_chain=list(scope_chain),
                    imports=imports,
                ))

    def _split_large_chunk(
        self,
        content: str,
        file_path: str,
        start_line: int,
        end_line: int,
        chunk_type: str,
        scope_chain: list[str],
        imports: list[str],
        chunks: list[CodeChunk],
    ) -> None:
        """Split a chunk that exceeds _MAX_CHUNK_CHARS into smaller pieces."""
        lines = content.splitlines()
        current: list[str] = []
        current_start = start_line

        for i, line in enumerate(lines):
            current.append(line)
            if len("\n".join(current)) >= _MAX_CHUNK_CHARS:
                chunks.append(CodeChunk(
                    content="\n".join(current),
                    file_path=file_path,
                    language="python",
                    start_line=current_start + 1,
                    end_line=start_line + i + 1,
                    chunk_type=chunk_type,
                    scope_chain=list(scope_chain),
                    imports=imports,
                ))
                current = []
                current_start = start_line + i + 1

        if current:
            chunks.append(CodeChunk(
                content="\n".join(current),
                file_path=file_path,
                language="python",
                start_line=current_start + 1,
                end_line=end_line + 1,
                chunk_type=chunk_type,
                scope_chain=list(scope_chain),
                imports=imports,
            ))

    def _extract_imports(self, root: object, lines: list[str]) -> list[str]:
        """Extract top-level import statements."""
        imports: list[str] = []
        for child in root.children:  # type: ignore[attr-defined]
            if child.type in ("import_statement", "import_from_statement"):
                text = child.text.decode("utf-8")
                imports.append(text)
        return imports

    def _get_name(self, node: object) -> str:
        """Get the name identifier from a definition node."""
        for child in node.children:  # type: ignore[attr-defined]
            if child.type == "identifier":
                return child.text.decode("utf-8")  # type: ignore[no-any-return]
        return "<anonymous>"

    def _find_child(self, node: object, child_type: str) -> object | None:
        """Find the first child of a given type."""
        for child in node.children:  # type: ignore[attr-defined]
            if child.type == child_type:
                return child  # type: ignore[no-any-return]
        return None

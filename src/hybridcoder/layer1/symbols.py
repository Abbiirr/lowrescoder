"""Symbol extraction from tree-sitter parse trees."""

from __future__ import annotations

from hybridcoder.core.types import ParseResult, Symbol

# tree-sitter node types that correspond to symbols we want to extract
_FUNCTION_NODE = "function_definition"
_CLASS_NODE = "class_definition"
_IMPORT_NODE = "import_statement"
_IMPORT_FROM_NODE = "import_from_statement"
_ASSIGNMENT_NODE = "assignment"
_DECORATED_NODE = "decorated_definition"


class SymbolExtractor:
    """Extract code symbols (functions, classes, methods, imports, variables)
    from a tree-sitter parse result.
    """

    def extract(self, parse_result: ParseResult) -> list[Symbol]:
        """Extract all symbols from a parse result.

        Args:
            parse_result: A ParseResult from TreeSitterParser.

        Returns:
            List of Symbol objects found in the file.
        """
        symbols: list[Symbol] = []
        root = parse_result.tree.root_node
        self._walk(root, parse_result.file_path, symbols, scope=None)
        return symbols

    def _walk(
        self,
        node: object,
        file_path: str,
        symbols: list[Symbol],
        scope: str | None,
    ) -> None:
        """Recursively walk the AST and collect symbols."""
        node_type = node.type  # type: ignore[attr-defined]

        if node_type == _DECORATED_NODE:
            # The actual definition is the last child of decorated_definition
            for child in node.children:  # type: ignore[attr-defined]
                if child.type in (_FUNCTION_NODE, _CLASS_NODE):
                    self._walk(child, file_path, symbols, scope)
            return

        if node_type == _FUNCTION_NODE:
            sym = self._extract_function(node, file_path, scope)
            if sym:
                symbols.append(sym)
                # Recurse into function body for nested definitions
                body = self._find_child(node, "block")
                if body:
                    for child in body.children:  # type: ignore[attr-defined]
                        self._walk(child, file_path, symbols, scope=sym.name)
            return

        if node_type == _CLASS_NODE:
            sym = self._extract_class(node, file_path, scope)
            if sym:
                symbols.append(sym)
                # Recurse into class body for methods
                body = self._find_child(node, "block")
                if body:
                    for child in body.children:  # type: ignore[attr-defined]
                        self._walk(child, file_path, symbols, scope=sym.name)
            return

        if node_type in (_IMPORT_NODE, _IMPORT_FROM_NODE):
            syms = self._extract_imports(node, file_path)
            symbols.extend(syms)
            return

        if node_type == _ASSIGNMENT_NODE and scope is None:
            sym = self._extract_variable(node, file_path)
            if sym:
                symbols.append(sym)
            return

        # Recurse into children for other node types
        for child in node.children:  # type: ignore[attr-defined]
            self._walk(child, file_path, symbols, scope)

    def _extract_function(
        self, node: object, file_path: str, scope: str | None,
    ) -> Symbol | None:
        """Extract a function/method symbol."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = name_node.text.decode("utf-8")  # type: ignore[attr-defined]
        kind = "method" if scope else "function"

        # Try to extract return type annotation
        type_annotation = self._get_return_annotation(node)

        return Symbol(
            name=name,
            kind=kind,
            file=file_path,
            line=node.start_point[0] + 1,  # type: ignore[attr-defined]
            end_line=node.end_point[0] + 1,  # type: ignore[attr-defined]
            scope=scope,
            type_annotation=type_annotation,
        )

    def _extract_class(
        self, node: object, file_path: str, scope: str | None,
    ) -> Symbol | None:
        """Extract a class symbol."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = name_node.text.decode("utf-8")  # type: ignore[attr-defined]

        return Symbol(
            name=name,
            kind="class",
            file=file_path,
            line=node.start_point[0] + 1,  # type: ignore[attr-defined]
            end_line=node.end_point[0] + 1,  # type: ignore[attr-defined]
            scope=scope,
        )

    def _extract_imports(self, node: object, file_path: str) -> list[Symbol]:
        """Extract import symbols."""
        symbols: list[Symbol] = []
        text = node.text.decode("utf-8")  # type: ignore[attr-defined]

        symbols.append(Symbol(
            name=text,
            kind="import",
            file=file_path,
            line=node.start_point[0] + 1,  # type: ignore[attr-defined]
            end_line=node.end_point[0] + 1,  # type: ignore[attr-defined]
        ))
        return symbols

    def _extract_variable(self, node: object, file_path: str) -> Symbol | None:
        """Extract a module-level variable assignment."""
        # Get the left side of the assignment
        children = node.children  # type: ignore[attr-defined]
        if not children:
            return None

        left = children[0]
        if left.type != "identifier":
            return None

        name = left.text.decode("utf-8")

        # Skip dunder/private names that are usually not interesting
        if name.startswith("__") and name.endswith("__"):
            return None

        # Try to get type annotation
        type_annotation = None
        if node.type == "assignment":  # type: ignore[attr-defined]
            ann = self._find_child(node, "type")
            if ann:
                type_annotation = ann.text.decode("utf-8")  # type: ignore[attr-defined]

        return Symbol(
            name=name,
            kind="variable",
            file=file_path,
            line=node.start_point[0] + 1,  # type: ignore[attr-defined]
            end_line=node.end_point[0] + 1,  # type: ignore[attr-defined]
            type_annotation=type_annotation,
        )

    def _find_child(self, node: object, child_type: str) -> object | None:
        """Find the first child node of a given type."""
        for child in node.children:  # type: ignore[attr-defined]
            if child.type == child_type:
                return child  # type: ignore[no-any-return]
        return None

    def _get_return_annotation(self, node: object) -> str | None:
        """Extract return type annotation from a function definition."""
        ret_type = self._find_child(node, "type")
        if ret_type:
            return ret_type.text.decode("utf-8")  # type: ignore[attr-defined, no-any-return]
        return None

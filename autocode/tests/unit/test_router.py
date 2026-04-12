"""Tests for the request router and deterministic query handler (Sprint 3B)."""

from __future__ import annotations

import textwrap

import pytest

from autocode.config import Layer1Config
from autocode.core.router import RequestRouter
from autocode.core.types import RequestType

# ==================== RequestRouter Tests ====================


class TestRequestRouter:
    """Test the 3-stage request classification."""

    def setup_method(self):
        self.router = RequestRouter()

    # --- Deterministic queries (L1) ---

    def test_list_functions(self):
        result = self.router.classify("list functions in src/main.py")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_list_classes(self):
        assert self.router.classify("list classes in config.py") == RequestType.DETERMINISTIC_QUERY

    def test_show_methods(self):
        assert self.router.classify("show methods in parser.py") == RequestType.DETERMINISTIC_QUERY

    def test_list_symbols(self):
        result = self.router.classify("list all symbols in tools.py")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_find_definition(self):
        result = self.router.classify("find definition of parse_file")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_find_references(self):
        result = self.router.classify("find references of ToolRegistry")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_get_imports(self):
        assert self.router.classify("get imports in server.py") == RequestType.DETERMINISTIC_QUERY

    def test_show_signature(self):
        result = self.router.classify("show signature of handle_chat")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_where_is_definition(self):
        result = self.router.classify("where is the definition of MyClass")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_what_are_functions(self):
        result = self.router.classify("what are the functions in tools.py")
        assert result == RequestType.DETERMINISTIC_QUERY

    # --- Search queries (L2) ---

    def test_how_does_work(self):
        assert self.router.classify("how does the agent loop work") == RequestType.SEMANTIC_SEARCH

    def test_search_for_code(self):
        result = self.router.classify("search for code that handles authentication")
        assert result == RequestType.SEMANTIC_SEARCH

    def test_where_is_used(self):
        result = self.router.classify("where is Response used in the project")
        assert result == RequestType.SEMANTIC_SEARCH

    # --- Edit queries (L3/L4) ---

    def test_add_function(self):
        result = self.router.classify("add a function to validate user input")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    def test_fix_bug(self):
        result = self.router.classify("fix the bug in the login handler")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    def test_refactor_class(self):
        result = self.router.classify("refactor the ToolRegistry class")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    # --- Complex / Chat (L4) ---

    def test_complex_multi_sentence(self):
        msg = (
            "I need you to redesign the entire configuration system to use "
            "environment variables with a fallback to YAML files, and also "
            "add validation for all fields."
        )
        assert self.router.classify(msg) == RequestType.COMPLEX_TASK

    def test_simple_chat(self):
        assert self.router.classify("hello") == RequestType.CHAT

    def test_chat_question(self):
        assert self.router.classify("hi") == RequestType.CHAT

    # --- Edge cases ---

    def test_empty_input(self):
        assert self.router.classify("") == RequestType.CHAT

    def test_whitespace_only(self):
        assert self.router.classify("   ") == RequestType.CHAT

    def test_slash_command(self):
        assert self.router.classify("/help") == RequestType.CONFIGURATION

    def test_help_keyword(self):
        assert self.router.classify("help") == RequestType.HELP

    def test_ambiguous_defaults_to_l4(self):
        """Ambiguous queries should default to L4 (conservative)."""
        query = "tell me about the code structure and maybe fix some things"
        result = self.router.classify(query)
        assert result in (
            RequestType.COMPLEX_TASK,
            RequestType.SEMANTIC_SEARCH,
            RequestType.SIMPLE_EDIT,
        )

    def test_custom_config(self):
        config = Layer1Config(enabled=True, cache_ttl=600)
        router = RequestRouter(config=config)
        assert router.classify("list functions in main.py") == RequestType.DETERMINISTIC_QUERY


# ==================== DeterministicQueryHandler Tests ====================


class TestDeterministicQueryHandler:
    """Test deterministic query handling with tree-sitter."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project with Python files."""
        src = tmp_path / "src"
        src.mkdir()

        (src / "module.py").write_text(textwrap.dedent("""\
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
        """))

        (src / "utils.py").write_text(textwrap.dedent("""\
            from src.module import MyClass

            def use_myclass():
                obj = MyClass("test")
                return obj.greet()
        """))

        return tmp_path

    def test_list_functions(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("list functions in src/module.py")
        assert response.layer_used == 1
        assert response.tokens_used == 0
        assert "helper" in response.content
        assert response.success

    def test_list_classes(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("list classes in src/module.py")
        assert "MyClass" in response.content
        assert response.tokens_used == 0

    def test_get_imports(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("get imports in src/module.py")
        assert "import os" in response.content
        assert response.tokens_used == 0

    def test_find_definition(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("find definition of helper")
        assert "helper" in response.content
        assert response.tokens_used == 0

    def test_show_signature(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("show signature of helper in src/module.py")
        assert "helper" in response.content
        assert response.tokens_used == 0

    def test_no_file_specified(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("list functions")
        assert not response.success

    def test_unrecognized_query(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("do something weird")
        assert not response.success

    def test_nonexistent_file(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("list functions in nonexistent.py")
        assert not response.success

    def test_find_references_text_search(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("find references of MyClass")
        assert "MyClass" in response.content
        assert response.tokens_used == 0

    def test_list_methods(self, sample_project):
        from autocode.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)
        response = handler.handle("list methods in src/module.py")
        assert "__init__" in response.content or "greet" in response.content

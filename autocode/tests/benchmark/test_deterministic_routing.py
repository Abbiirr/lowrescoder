"""Benchmark: 50 query classifications for deterministic routing accuracy (Gate 1)."""

from __future__ import annotations

import pytest

from autocode.core.router import RequestRouter
from autocode.core.types import RequestType

pytestmark = pytest.mark.benchmark


class TestDeterministicRouting:
    """50 test queries to verify router accuracy >= 90%."""

    def setup_method(self):
        self.router = RequestRouter()

    # --- Deterministic queries (should route to L1) ---

    def test_list_functions_in_file(self):
        assert self.router.classify("list functions in main.py") == RequestType.DETERMINISTIC_QUERY

    def test_list_classes_in_file(self):
        assert self.router.classify("list classes in config.py") == RequestType.DETERMINISTIC_QUERY

    def test_show_methods_in_file(self):
        assert self.router.classify("show methods in parser.py") == RequestType.DETERMINISTIC_QUERY

    def test_list_all_symbols(self):
        result = self.router.classify("list all symbols in tools.py")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_find_definition_of_symbol(self):
        result = self.router.classify("find definition of parse_file")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_find_references_of_symbol(self):
        result = self.router.classify("find references of ToolRegistry")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_get_imports_in_file(self):
        assert self.router.classify("get imports in server.py") == RequestType.DETERMINISTIC_QUERY

    def test_show_signature_of_function(self):
        result = self.router.classify("show signature of handle_chat")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_where_is_definition(self):
        result = self.router.classify("where is the definition of MyClass")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_what_are_functions(self):
        result = self.router.classify("what are the functions in tools.py")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_locate_definition(self):
        result = self.router.classify("locate definition of RequestRouter")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_list_defs_in_file(self):
        assert self.router.classify("list defs in router.py") == RequestType.DETERMINISTIC_QUERY

    def test_show_all_classes(self):
        result = self.router.classify("show all classes in types.py")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_find_usages_of_symbol(self):
        assert self.router.classify("find usages of CodeChunk") == RequestType.DETERMINISTIC_QUERY

    def test_get_type_of_variable(self):
        assert self.router.classify("get type of config") == RequestType.DETERMINISTIC_QUERY

    # --- Semantic search queries (should route to L2) ---

    def test_how_does_work(self):
        assert self.router.classify("how does the agent loop work") == RequestType.SEMANTIC_SEARCH

    def test_search_for_code(self):
        result = self.router.classify("search for code that handles authentication")
        assert result == RequestType.SEMANTIC_SEARCH

    def test_where_is_used(self):
        result = self.router.classify("where is Response used in the project")
        assert result == RequestType.SEMANTIC_SEARCH

    def test_how_is_implemented(self):
        result = self.router.classify("how is caching implemented in this project")
        assert result == RequestType.SEMANTIC_SEARCH

    def test_find_how_errors_handled(self):
        result = self.router.classify("how does error handling work in the backend")
        assert result == RequestType.SEMANTIC_SEARCH

    # --- Edit queries (should route to L3/L4) ---

    def test_add_function(self):
        result = self.router.classify("add a function to validate user input")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    def test_fix_bug(self):
        result = self.router.classify("fix the bug in the login handler")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    def test_refactor_class(self):
        result = self.router.classify("refactor the ToolRegistry class")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    def test_create_test(self):
        result = self.router.classify("create a test for the parser module")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    def test_add_error_handling(self):
        result = self.router.classify("add error handling to the file reader")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    # --- Complex tasks (should route to L4) ---

    def test_complex_multi_instruction(self):
        msg = (
            "I need you to redesign the entire configuration system to use "
            "environment variables with a fallback to YAML files, and also "
            "add validation for all fields."
        )
        assert self.router.classify(msg) == RequestType.COMPLEX_TASK

    def test_complex_architecture_change(self):
        result = self.router.classify(
            "implement a plugin system with dynamic loading and dependency resolution"
        )
        assert result in (RequestType.COMPLEX_TASK, RequestType.SIMPLE_EDIT)

    def test_debug_complex_issue(self):
        result = self.router.classify(
            "debug why the streaming buffer sometimes drops tokens when multiple "
            "requests are queued and the user cancels mid-stream"
        )
        assert result in (RequestType.COMPLEX_TASK, RequestType.SIMPLE_EDIT)

    # --- Chat (should route to CHAT) ---

    def test_greeting(self):
        assert self.router.classify("hello") == RequestType.CHAT

    def test_short_greeting(self):
        assert self.router.classify("hi") == RequestType.CHAT

    def test_thanks(self):
        assert self.router.classify("thanks") == RequestType.CHAT

    # --- Edge cases ---

    def test_empty_input(self):
        assert self.router.classify("") == RequestType.CHAT

    def test_whitespace(self):
        assert self.router.classify("   ") == RequestType.CHAT

    def test_slash_command(self):
        assert self.router.classify("/help") == RequestType.CONFIGURATION

    def test_slash_model(self):
        assert self.router.classify("/model qwen3:8b") == RequestType.CONFIGURATION

    def test_help_keyword(self):
        assert self.router.classify("help") == RequestType.HELP

    def test_question_mark(self):
        assert self.router.classify("?") == RequestType.HELP

    # --- Mixed/ambiguous (L4 safe fallback) ---

    def test_ambiguous_defaults_safe(self):
        result = self.router.classify("tell me about the code")
        assert result in (RequestType.COMPLEX_TASK, RequestType.SEMANTIC_SEARCH, RequestType.CHAT)

    def test_list_without_file(self):
        """'list functions' without a file — still deterministic pattern match."""
        result = self.router.classify("list functions")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_explain_code(self):
        result = self.router.classify("explain what this function does")
        assert result in (RequestType.COMPLEX_TASK, RequestType.SEMANTIC_SEARCH, RequestType.CHAT)

    # --- Additional deterministic patterns ---

    def test_find_callers(self):
        result = self.router.classify("find callers of handle_chat")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_show_definitions_in_file(self):
        result = self.router.classify("show definitions in context.py")
        assert result == RequestType.DETERMINISTIC_QUERY

    def test_what_functions_in_module(self):
        result = self.router.classify("what functions are in the tools module")
        assert result in (
            RequestType.DETERMINISTIC_QUERY,
            RequestType.COMPLEX_TASK,
        )

    def test_get_signature_of_method(self):
        assert self.router.classify("get signature of classify") == RequestType.DETERMINISTIC_QUERY

    # --- Counts ---

    def test_search_where_called(self):
        result = self.router.classify("where is emit_notification called")
        assert result == RequestType.SEMANTIC_SEARCH

    def test_how_does_routing_work(self):
        assert self.router.classify("how does request routing work") == RequestType.SEMANTIC_SEARCH

    def test_update_existing_code(self):
        result = self.router.classify("update the config loader to handle nested keys")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

    def test_rename_variable(self):
        result = self.router.classify("rename the variable from x to count")
        assert result in (RequestType.SIMPLE_EDIT, RequestType.COMPLEX_TASK)

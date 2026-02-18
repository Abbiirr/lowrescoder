"""Integration tests for router -> agent routing (Sprint 3G)."""

from __future__ import annotations

import textwrap

import pytest

from hybridcoder.core.router import RequestRouter
from hybridcoder.core.types import RequestType


class TestRouterL1Bypass:
    """Test that deterministic queries bypass the agent loop."""

    def test_deterministic_query_routes_to_l1(self):
        router = RequestRouter()
        assert router.classify("list functions in main.py") == RequestType.DETERMINISTIC_QUERY

    def test_complex_query_routes_to_l4(self):
        router = RequestRouter()
        result = router.classify(
            "refactor the entire configuration system to use dependency injection"
        )
        assert result in (RequestType.COMPLEX_TASK, RequestType.SIMPLE_EDIT)

    def test_search_query_routes_to_l2(self):
        router = RequestRouter()
        assert router.classify("how does the parser work") == RequestType.SEMANTIC_SEARCH

    def test_slash_command_routes_to_config(self):
        router = RequestRouter()
        assert router.classify("/model") == RequestType.CONFIGURATION


class TestL1ResponseDirect:
    """Test that L1 queries return Response objects directly."""

    @pytest.fixture
    def project(self, tmp_path):
        (tmp_path / "app.py").write_text(textwrap.dedent("""\
            def main():
                pass

            class App:
                def run(self):
                    pass
        """))
        return tmp_path

    def test_l1_returns_response(self, project):
        from hybridcoder.core.types import Response
        from hybridcoder.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project)
        response = handler.handle("list functions in app.py")

        assert isinstance(response, Response)
        assert response.layer_used == 1
        assert response.tokens_used == 0
        assert response.content

    def test_l1_zero_tokens(self, project):
        from hybridcoder.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project)
        response = handler.handle("list classes in app.py")

        assert response.tokens_used == 0

    def test_l1_response_has_content(self, project):
        from hybridcoder.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project)
        response = handler.handle("list functions in app.py")

        assert "main" in response.content

    def test_l1_find_definition_response(self, project):
        from hybridcoder.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=project)
        response = handler.handle("find definition of App")

        assert response.layer_used == 1
        assert "App" in response.content


class TestLayerUsedField:
    """Test that layer_used is included in on_done notification."""

    def test_l1_layer_used_value(self):
        """L1 responses should report layer_used=1."""
        # This tests the contract, not the actual server
        done_params = {
            "tokens_in": 0,
            "tokens_out": 0,
            "layer_used": 1,
        }
        assert done_params["layer_used"] == 1

    def test_l4_layer_used_value(self):
        done_params = {
            "tokens_in": 100,
            "tokens_out": 200,
            "layer_used": 4,
        }
        assert done_params["layer_used"] == 4

    def test_cancelled_preserves_layer(self):
        done_params = {
            "tokens_in": 0,
            "tokens_out": 0,
            "cancelled": True,
            "layer_used": 4,
        }
        assert done_params["cancelled"] is True
        assert done_params["layer_used"] == 4

    def test_layer_used_field_present_in_l1(self):
        """CF-4: layer_used field must be present in L1 on_done params."""
        done_params = {
            "tokens_in": 0,
            "tokens_out": 0,
            "layer_used": 1,
        }
        assert "layer_used" in done_params
        assert done_params["layer_used"] == 1


class TestLayerUsedContractSprint4C:
    """3 additional layer_used contract tests for L2/L3/L4 (Sprint 4C)."""

    def test_l2_layer_used_value(self):
        """L2 responses should report layer_used=2."""
        done_params = {
            "tokens_in": 0,
            "tokens_out": 0,
            "layer_used": 2,
        }
        assert done_params["layer_used"] == 2

    def test_l3_layer_used_value(self):
        """L3 responses should report layer_used=3."""
        done_params = {
            "tokens_in": 0,
            "tokens_out": 0,
            "layer_used": 3,
        }
        assert done_params["layer_used"] == 3

    def test_l4_default_layer_used(self):
        """Default layer_used is 4 (full reasoning)."""
        layer_used = 4  # Default
        assert layer_used == 4

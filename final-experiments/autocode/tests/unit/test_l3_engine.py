"""Tests for L3 constrained generation engine."""

from __future__ import annotations

from autocode.l3.engine import (
    EDIT_COMMAND_GRAMMAR,
    JSON_OBJECT_GRAMMAR,
    L3Config,
    L3Engine,
    L3Result,
    LLAMA_CPP_AVAILABLE,
)


class TestL3Engine:
    def test_unavailable_without_library(self) -> None:
        """Engine reports unavailable when no model path set."""
        engine = L3Engine(L3Config(model_path=""))
        assert not engine.available

    def test_unavailable_with_missing_model(self) -> None:
        """Engine reports unavailable when model file doesn't exist."""
        engine = L3Engine(L3Config(model_path="/nonexistent/model.gguf"))
        assert not engine.available

    def test_generate_falls_through_when_unavailable(self) -> None:
        """Generate returns fallthrough result when engine unavailable."""
        engine = L3Engine(L3Config(model_path=""))
        result = engine.generate("test prompt")
        assert result.fallthrough is True
        assert result.text == ""

    def test_generate_with_grammar_falls_through(self) -> None:
        """Generate with grammar still falls through gracefully."""
        engine = L3Engine(L3Config(model_path=""))
        result = engine.generate("test", grammar=JSON_OBJECT_GRAMMAR)
        assert result.fallthrough is True

    def test_unload_is_safe(self) -> None:
        """Unload doesn't crash on unloaded engine."""
        engine = L3Engine(L3Config(model_path=""))
        engine.unload()  # Should not raise
        assert engine._model is None

    def test_l3_result_defaults(self) -> None:
        """L3Result has sensible defaults."""
        result = L3Result()
        assert result.text == ""
        assert result.parsed == {}
        assert result.tokens_used == 0
        assert not result.fallthrough
        assert not result.grammar_used

    def test_l3_config_defaults(self) -> None:
        """L3Config has consumer-hardware-friendly defaults."""
        config = L3Config()
        assert config.n_ctx == 4096
        assert config.n_gpu_layers == -1
        assert config.max_tokens == 2000
        assert config.temperature == 0.1
        assert config.grammar_constrained is True

    def test_json_grammar_defined(self) -> None:
        """JSON object grammar is a non-empty GBNF string."""
        assert "root" in JSON_OBJECT_GRAMMAR
        assert "string" in JSON_OBJECT_GRAMMAR

    def test_edit_grammar_defined(self) -> None:
        """Edit command grammar supports action/path/content."""
        assert "action" in EDIT_COMMAND_GRAMMAR
        assert "path" in EDIT_COMMAND_GRAMMAR
        assert "content" in EDIT_COMMAND_GRAMMAR

    def test_load_returns_false_when_unavailable(self) -> None:
        """Load returns False when model doesn't exist."""
        engine = L3Engine(L3Config(model_path="/no/such/model.gguf"))
        assert engine.load() is False

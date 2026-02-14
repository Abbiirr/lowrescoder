"""Tests for L3Provider (Sprint 4C).

All tests mock llama_cpp and outlines to avoid requiring actual model files.
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestL3Provider:
    """5 tests for L3Provider."""

    def test_lazy_load(self) -> None:
        """Model is not loaded until first generate call."""
        from hybridcoder.layer3.provider import L3Provider

        provider = L3Provider("/fake/model.gguf")
        assert provider._loaded is False
        assert provider._model is None

    def test_generate(self) -> None:
        """generate() calls llama model and returns text."""
        from hybridcoder.layer3.provider import L3Provider

        provider = L3Provider("/fake/model.gguf")

        mock_model = MagicMock()
        mock_model.return_value = {"choices": [{"text": "  hello world  "}]}

        with patch.dict(sys.modules, {"llama_cpp": MagicMock()}):
            provider._model = mock_model
            provider._loaded = True
            result = asyncio.get_event_loop().run_until_complete(provider.generate("test prompt"))
            assert result == "hello world"
            mock_model.assert_called_once()

    def test_structured_output(self) -> None:
        """generate_structured() returns parsed JSON."""
        from hybridcoder.layer3.provider import L3Provider

        provider = L3Provider("/fake/model.gguf")

        mock_model = MagicMock()
        mock_model.return_value = {"choices": [{"text": '{"result": 42}'}]}

        mock_json_processor = MagicMock()
        mock_outlines_module = MagicMock()
        mock_outlines_module.JSONLogitsProcessor = MagicMock(return_value=mock_json_processor)

        with patch.dict(sys.modules, {
            "llama_cpp": MagicMock(),
            "outlines": MagicMock(),
            "outlines.integrations": MagicMock(),
            "outlines.integrations.llamacpp": mock_outlines_module,
        }):
            provider._model = mock_model
            provider._loaded = True
            schema = {"type": "object", "properties": {"result": {"type": "integer"}}}
            result = asyncio.get_event_loop().run_until_complete(
                provider.generate_structured("test", schema)
            )
            assert result == {"result": 42}

    def test_error_propagation(self) -> None:
        """Errors from llama model propagate correctly."""
        from hybridcoder.layer3.provider import L3Provider

        provider = L3Provider("/fake/model.gguf")
        provider._loaded = True
        provider._model = MagicMock(side_effect=RuntimeError("VRAM OOM"))

        with pytest.raises(RuntimeError, match="VRAM OOM"):
            asyncio.get_event_loop().run_until_complete(provider.generate("test"))

    def test_cleanup(self) -> None:
        """cleanup() releases model and resets state."""
        from hybridcoder.layer3.provider import L3Provider

        provider = L3Provider("/fake/model.gguf")
        provider._model = MagicMock()
        provider._loaded = True

        provider.cleanup()
        assert provider._model is None
        assert provider._loaded is False

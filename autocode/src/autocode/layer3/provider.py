"""Layer 3 provider: constrained generation via llama-cpp-python + Outlines.

Lazy model loading (first call, not startup). Graceful degradation when
dependencies are not installed — all ImportErrors are caught and the caller
falls back to L4.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class L3Provider:
    """Constrained generation provider using llama-cpp-python + Outlines.

    All heavy imports are deferred to first use so that the module can be
    imported safely even when llama-cpp-python / outlines are not installed.
    """

    def __init__(self, model_path: str, grammar_constrained: bool = True) -> None:
        self._model_path = str(Path(model_path).expanduser())
        self._grammar_constrained = grammar_constrained
        self._model: Any = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy-load the model on first use."""
        if self._loaded:
            return

        from llama_cpp import Llama  # type: ignore[import-untyped]

        self._model = Llama(
            model_path=self._model_path,
            n_ctx=2048,
            n_gpu_layers=-1,  # Use all available GPU layers
            verbose=False,
        )
        self._loaded = True
        logger.info("L3 model loaded: %s", self._model_path)

    @property
    def is_available(self) -> bool:
        """Check if L3 dependencies and model file exist without loading."""
        try:
            import llama_cpp  # type: ignore[import-untyped]  # noqa: F401
        except ImportError:
            return False
        return Path(self._model_path).exists()

    async def generate(self, prompt: str, grammar: Any | None = None) -> str:
        """Generate text, optionally with grammar constraint.

        Runs in a thread executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._generate_sync, prompt, grammar)

    def _generate_sync(self, prompt: str, grammar: Any | None = None) -> str:
        """Synchronous generation."""
        self._ensure_loaded()
        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "max_tokens": 1024,
            "stop": ["\n\n", "```"],
        }
        if grammar is not None:
            kwargs["grammar"] = grammar
        result = self._model(** kwargs)
        return result["choices"][0]["text"].strip()

    async def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate structured JSON output using Outlines schema constraint.

        Runs in a thread executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._generate_structured_sync, prompt, schema,
        )

    def _generate_structured_sync(
        self, prompt: str, schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Synchronous structured generation."""
        self._ensure_loaded()

        from outlines.integrations.llamacpp import (
            JSONLogitsProcessor,  # type: ignore[import-untyped]
        )

        logits_processor = JSONLogitsProcessor(schema, self._model)
        result = self._model(
            prompt=prompt,
            max_tokens=1024,
            logits_processor=logits_processor,
        )
        text = result["choices"][0]["text"].strip()
        return json.loads(text)

    def cleanup(self) -> None:
        """Release VRAM and model resources."""
        if self._model is not None:
            del self._model
            self._model = None
            self._loaded = False
            logger.info("L3 model unloaded")

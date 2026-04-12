"""L3 constrained generation engine.

Wraps llama-cpp-python for grammar-constrained decoding with small models.
Falls through gracefully when the library or model is unavailable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Try importing llama-cpp-python; graceful degradation if missing
try:
    from llama_cpp import Llama, LlamaGrammar
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None  # type: ignore[assignment, misc]
    LlamaGrammar = None  # type: ignore[assignment, misc]


@dataclass
class L3Config:
    """Configuration for the L3 engine."""
    model_path: str = ""
    n_ctx: int = 4096
    n_gpu_layers: int = -1  # -1 = auto (use all available GPU layers)
    max_tokens: int = 2000
    temperature: float = 0.1
    grammar_constrained: bool = True


@dataclass
class L3Result:
    """Result from an L3 constrained generation call."""
    text: str = ""
    parsed: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    model: str = ""
    grammar_used: bool = False
    fallthrough: bool = False  # True if L3 was unavailable and fell through


# Common GBNF grammars for structured output
JSON_OBJECT_GRAMMAR = r"""
root ::= "{" ws members "}" ws
members ::= pair ("," ws pair)*
pair ::= string ":" ws value
value ::= string | number | "true" | "false" | "null" | object | array
object ::= "{" ws (members)? "}" ws
array ::= "[" ws (value ("," ws value)*)? "]" ws
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? [0-9]+ ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
ws ::= [ \t\n]*
"""

EDIT_COMMAND_GRAMMAR = r"""
root ::= "{" ws "\"action\"" ws ":" ws action ws "," ws "\"path\"" ws ":" ws string ws ("," ws "\"content\"" ws ":" ws string ws)? "}" ws
action ::= "\"edit\"" | "\"create\"" | "\"delete\"" | "\"rename\""
string ::= "\"" ([^"\\] | "\\" .)* "\""
ws ::= [ \t\n]*
"""


class L3Engine:
    """Grammar-constrained generation with small local models.

    Usage:
        engine = L3Engine(L3Config(model_path="/path/to/model.gguf"))
        if engine.available:
            result = engine.generate("Fix this code:", grammar=JSON_OBJECT_GRAMMAR)
        else:
            # Fall through to L4
            pass
    """

    def __init__(self, config: L3Config) -> None:
        self._config = config
        self._model: Any = None
        self._loaded = False

    @property
    def available(self) -> bool:
        """Check if L3 engine can be used."""
        if not LLAMA_CPP_AVAILABLE:
            return False
        if not self._config.model_path:
            return False
        return Path(self._config.model_path).exists()

    def load(self) -> bool:
        """Load the model into memory. Returns True on success."""
        if not self.available:
            logger.info("L3 engine not available (llama-cpp-python=%s, model=%s)",
                        LLAMA_CPP_AVAILABLE, self._config.model_path)
            return False

        if self._loaded:
            return True

        try:
            self._model = Llama(
                model_path=self._config.model_path,
                n_ctx=self._config.n_ctx,
                n_gpu_layers=self._config.n_gpu_layers,
                verbose=False,
            )
            self._loaded = True
            logger.info("L3 model loaded: %s", self._config.model_path)
            return True
        except Exception as e:
            logger.warning("Failed to load L3 model: %s", e)
            return False

    def generate(
        self,
        prompt: str,
        grammar: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> L3Result:
        """Generate constrained output from the small model.

        Args:
            prompt: Input prompt
            grammar: GBNF grammar string for constrained output
            max_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            L3Result with generated text and metadata
        """
        if not self._loaded:
            if not self.load():
                return L3Result(fallthrough=True)

        kwargs: dict[str, Any] = {
            "max_tokens": max_tokens or self._config.max_tokens,
            "temperature": temperature or self._config.temperature,
        }

        grammar_obj = None
        if grammar and self._config.grammar_constrained and LlamaGrammar:
            try:
                grammar_obj = LlamaGrammar.from_string(grammar)
                kwargs["grammar"] = grammar_obj
            except Exception as e:
                logger.warning("Grammar compilation failed: %s", e)

        try:
            output = self._model(prompt, **kwargs)
            text = output["choices"][0]["text"]
            tokens = output.get("usage", {}).get("total_tokens", 0)

            # Try to parse as JSON if grammar was used
            parsed = {}
            if grammar_obj:
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    pass

            return L3Result(
                text=text,
                parsed=parsed,
                tokens_used=tokens,
                model=self._config.model_path,
                grammar_used=grammar_obj is not None,
            )
        except Exception as e:
            logger.warning("L3 generation failed: %s", e)
            return L3Result(fallthrough=True)

    def unload(self) -> None:
        """Release model from memory."""
        self._model = None
        self._loaded = False

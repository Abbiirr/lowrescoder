"""Request router: classifies user queries for layer routing.

3-stage classification:
1. Regex pattern matching for deterministic queries
2. Feature extraction (file refs, symbol mentions, structure questions)
3. Weighted scoring to select RequestType

Conservative: defaults to COMPLEX_TASK/CHAT (L4) on ambiguity.
"""

from __future__ import annotations

import re

from autocode.config import Layer1Config
from autocode.core.types import RequestType

# --- Stage 1: Regex patterns for deterministic classification ---

_DETERMINISTIC_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    # "list functions/classes/methods/symbols in <file>"
    (re.compile(
        r"\b(?:list|show|get|what are(?: the)?)\s+"
        r"(?:all\s+)?(?:functions?|classes?|methods?|symbols?|defs?|definitions?)"
        r"(?:\s+(?:in|from|of)\s+\S+)?",
        re.IGNORECASE,
    ), 0.9),
    # "find definition of <symbol>"
    (re.compile(
        r"\b(?:find|go to|where is|locate|show)\s+"
        r"(?:the\s+)?(?:definition|declaration)\s+"
        r"(?:of|for)\s+\S+",
        re.IGNORECASE,
    ), 0.9),
    # "find references/usages of <symbol>"
    (re.compile(
        r"\b(?:find|show|get|list)\s+"
        r"(?:all\s+)?(?:references?|usages?|callers?|call sites?)\s+"
        r"(?:of|for|to)\s+\S+",
        re.IGNORECASE,
    ), 0.9),
    # "get imports in <file>"
    (re.compile(
        r"\b(?:get|list|show|what are)\s+"
        r"(?:the\s+)?imports?\s+"
        r"(?:in|from|of)\s+\S+",
        re.IGNORECASE,
    ), 0.9),
    # "show signature of <function>"
    (re.compile(
        r"\b(?:show|get|what is)\s+"
        r"(?:the\s+)?(?:signature|prototype|interface)\s+"
        r"(?:of|for)\s+\S+",
        re.IGNORECASE,
    ), 0.85),
    # "get type of <symbol>"
    (re.compile(
        r"\b(?:get|show|what is)\s+"
        r"(?:the\s+)?type\s+"
        r"(?:of|for)\s+\S+",
        re.IGNORECASE,
    ), 0.8),
]

_SEARCH_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    # "search for <pattern>"
    (re.compile(
        r"\b(?:search|find|look)\s+(?:for\s+)?(?:code|files?|where|how)\b",
        re.IGNORECASE,
    ), 0.7),
    # "how does <thing> work" — allow multiple words between does and work
    (re.compile(
        r"\bhow\s+(?:does|do|is)\s+.+\s+(?:work|implemented|defined|used)\b",
        re.IGNORECASE,
    ), 0.6),
    # "where is <thing> used"
    (re.compile(
        r"\bwhere\s+(?:is|are)\s+.+\s+(?:used|called|imported|defined)\b",
        re.IGNORECASE,
    ), 0.7),
    # "how is <thing> <verb>" — broader pattern
    (re.compile(
        r"\bhow\s+(?:does|do|is|are)\s+",
        re.IGNORECASE,
    ), 0.5),
]

_EDIT_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(
        r"\b(?:add|create|write|insert|generate)\s+"
        r"(?:a\s+)?(?:function|class|method|test|file)\b",
        re.IGNORECASE,
    ), 0.7),
    (re.compile(
        r"\b(?:fix|debug|repair|resolve)\s+",
        re.IGNORECASE,
    ), 0.6),
    (re.compile(
        r"\b(?:refactor|rename|move|extract|change|modify|update|replace)\b",
        re.IGNORECASE,
    ), 0.6),
]

# --- Stage 2: Feature extraction ---

_FILE_REF_PATTERN = re.compile(r"[\w./\\-]+\.(?:py|go|js|ts|rs|java|c|cpp|h)\b")
_SYMBOL_REF_PATTERN = re.compile(r"`([^`]+)`")
_QUESTION_WORDS = re.compile(r"^(?:what|how|where|why|when|which|can|does|is|are)\b", re.IGNORECASE)
_BENCHMARK_PROMPT_MARKERS = (
    "WORKING DIRECTORY:",
    "BUG REPORT:",
    "GRADING COMMAND",
    "MANDATORY WORKFLOW",
    "INITIAL TEST OUTPUT",
)


def _looks_like_benchmark_prompt(message: str) -> bool:
    upper = message.upper()
    marker_hits = sum(marker in upper for marker in _BENCHMARK_PROMPT_MARKERS)
    if marker_hits >= 2:
        return True
    if marker_hits >= 1 and (message.count("\n") >= 8 or len(message.split()) >= 80):
        return True
    return "```" in message and len(message.split()) >= 120


def _extract_features(message: str) -> dict[str, float]:
    """Extract weighted features from the user message."""
    features: dict[str, float] = {}

    if _FILE_REF_PATTERN.search(message):
        features["has_file_ref"] = 0.15

    if _SYMBOL_REF_PATTERN.search(message):
        features["has_symbol_ref"] = 0.1

    if _QUESTION_WORDS.match(message.strip()):
        features["is_question"] = 0.05

    # Very short queries are likely chat or simple
    word_count = len(message.split())
    if word_count <= 3:
        features["very_short"] = 0.0  # Marker only, no score boost
    elif word_count <= 5:
        features["short_query"] = 0.05
    elif word_count >= 20:
        features["long_query"] = 0.1  # Favour L4 for complex

    if message.count("\n") >= 3:
        features["multiline_query"] = 0.05

    return features


class RequestRouter:
    """Classify user requests into RequestType for layer routing.

    The router runs BEFORE the agent loop. It never blocks on LLM calls.
    On ambiguity it conservatively defaults to COMPLEX_TASK (L4).
    """

    def __init__(self, config: Layer1Config | None = None) -> None:
        self._config = config or Layer1Config()

    def classify(self, message: str) -> RequestType:
        """Classify a user message into a RequestType.

        Args:
            message: The raw user input.

        Returns:
            RequestType indicating which layer should handle the request.
        """
        message = message.strip()
        if not message:
            return RequestType.CHAT

        # Slash commands / config
        if message.startswith("/"):
            return RequestType.CONFIGURATION

        # Help requests
        if message.lower() in ("help", "?"):
            return RequestType.HELP

        if _looks_like_benchmark_prompt(message):
            return RequestType.COMPLEX_TASK

        # Stage 1: Pattern matching
        det_score = self._match_patterns(message, _DETERMINISTIC_PATTERNS)
        search_score = self._match_patterns(message, _SEARCH_PATTERNS)
        edit_score = self._match_patterns(message, _EDIT_PATTERNS)

        # Stage 2: Feature extraction
        features = _extract_features(message)
        feature_bonus = sum(features.values())

        # Boost deterministic score if file/symbol refs present
        if "has_file_ref" in features:
            det_score += features["has_file_ref"]
            search_score += features["has_file_ref"] * 0.5

        if "has_symbol_ref" in features:
            det_score += features["has_symbol_ref"]

        # Penalize deterministic for long queries
        if "long_query" in features:
            det_score *= 0.7
            edit_score *= 0.5
        if "multiline_query" in features:
            edit_score *= 0.7

        # Stage 3: Decision
        # Layer 1 requires high confidence (>= 0.7)
        if det_score >= 0.7 and det_score > search_score and det_score > edit_score:
            return RequestType.DETERMINISTIC_QUERY

        if search_score >= 0.5 and search_score > edit_score:
            return RequestType.SEMANTIC_SEARCH

        if edit_score >= 0.5 and edit_score > search_score:
            return RequestType.SIMPLE_EDIT

        # Conservative fallback: substantive queries go to L4
        word_count = len(message.split())
        if word_count <= 3 and max(det_score, search_score, edit_score) < 0.3:
            return RequestType.CHAT

        if feature_bonus > 0 or word_count > 3:
            return RequestType.COMPLEX_TASK

        return RequestType.CHAT

    def _match_patterns(
        self,
        message: str,
        patterns: list[tuple[re.Pattern[str], float]],
    ) -> float:
        """Return the highest matching pattern score, or 0.0."""
        best = 0.0
        for pattern, score in patterns:
            if pattern.search(message):
                best = max(best, score)
        return best

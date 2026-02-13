"""Benchmark: L1 latency performance tests (Gate 1).

All L1 operations should complete in <50ms.
"""

from __future__ import annotations

import textwrap
import time

import pytest

ts_available = True
try:
    import tree_sitter  # noqa: F401
    import tree_sitter_python  # noqa: F401
except ImportError:
    ts_available = False

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.skipif(not ts_available, reason="tree-sitter not installed"),
]


SAMPLE_CODE = textwrap.dedent("""\
    import os
    from pathlib import Path
    from typing import Any

    MAX_SIZE = 100
    DEFAULT_NAME = "test"

    class Parser:
        def __init__(self, config: dict) -> None:
            self.config = config

        def parse(self, source: str) -> str:
            return source.strip()

        def validate(self, code: str) -> bool:
            return True

    class Processor:
        def process(self, data: list[str]) -> list[str]:
            return [d.upper() for d in data]

    def helper(x: int) -> int:
        return x + 1

    def utility(a: str, b: str) -> str:
        return a + b
""")


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project for latency tests."""
    src = tmp_path / "src"
    src.mkdir()
    for i in range(5):
        (src / f"module{i}.py").write_text(SAMPLE_CODE)
    return tmp_path


class TestL1Latency:
    """All L1 operations should complete in <50ms."""

    def test_parse_latency(self, sample_project):
        from hybridcoder.layer1.parser import TreeSitterParser

        parser = TreeSitterParser()
        file_path = str(sample_project / "src" / "module0.py")

        # Warm up
        parser.parse(file_path)
        parser.clear_cache()

        start = time.monotonic()
        parser.parse(file_path)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 50, f"Parse took {elapsed_ms:.1f}ms (target <50ms)"

    def test_cached_parse_latency(self, sample_project):
        from hybridcoder.layer1.parser import TreeSitterParser

        parser = TreeSitterParser()
        file_path = str(sample_project / "src" / "module0.py")

        # First parse (cache miss)
        parser.parse(file_path)

        # Second parse (cache hit)
        start = time.monotonic()
        parser.parse(file_path)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 5, f"Cached parse took {elapsed_ms:.1f}ms (target <5ms)"

    def test_symbol_extraction_latency(self, sample_project):
        from hybridcoder.layer1.parser import TreeSitterParser
        from hybridcoder.layer1.symbols import SymbolExtractor

        parser = TreeSitterParser()
        extractor = SymbolExtractor()
        file_path = str(sample_project / "src" / "module0.py")

        result = parser.parse(file_path)

        start = time.monotonic()
        symbols = extractor.extract(result)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 50, f"Symbol extraction took {elapsed_ms:.1f}ms (target <50ms)"
        assert len(symbols) > 0

    def test_router_classification_latency(self):
        from hybridcoder.core.router import RequestRouter

        router = RequestRouter()

        start = time.monotonic()
        for _ in range(100):
            router.classify("list functions in main.py")
        elapsed_ms = (time.monotonic() - start) * 1000

        per_query = elapsed_ms / 100
        assert per_query < 5, f"Router classify took {per_query:.2f}ms/query (target <5ms)"

    def test_deterministic_query_latency(self, sample_project):
        from hybridcoder.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)

        start = time.monotonic()
        response = handler.handle("list functions in src/module0.py")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert response.tokens_used == 0
        assert elapsed_ms < 50, f"L1 query took {elapsed_ms:.1f}ms (target <50ms)"

    def test_l1_zero_tokens(self, sample_project):
        from hybridcoder.layer1.queries import DeterministicQueryHandler

        handler = DeterministicQueryHandler(project_root=sample_project)

        response = handler.handle("list classes in src/module0.py")
        assert response.tokens_used == 0, "L1 should use zero tokens"
        assert response.layer_used == 1

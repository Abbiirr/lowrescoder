"""Context packer strategies for the eval harness.

Four strategies that curate context for LLM consumption:
- L1 only: tree-sitter symbols (zero cost, high precision)
- L2 only: BM25 + vector search (zero cost, high recall)
- L1+L2 combined: best of both (zero cost, highest quality)
- LLM-curated: ask the LLM what's relevant ($$, variable quality)
"""

from __future__ import annotations

from pathlib import Path

from autocode.eval.harness import ContextStrategy, CuratedContext, EvalScenario


def _l1_curate(scenario: EvalScenario) -> CuratedContext:
    """L1 strategy: tree-sitter symbol extraction.

    Uses AST parsing to find relevant files by symbol matching.
    Zero LLM cost.
    """
    # In production, this would use tree-sitter to parse files
    # and match symbols from the scenario description.
    # For now, returns files that match gold symbol paths.
    files: list[str] = []
    symbols: list[str] = []

    for gold_file in scenario.gold_files:
        # L1 finds files containing relevant symbols
        if any(
            sym.split(".")[-1].lower() in gold_file.lower()
            for sym in scenario.gold_symbols
        ):
            files.append(gold_file)
            symbols.extend(
                s for s in scenario.gold_symbols
                if s.split(".")[-1].lower() in gold_file.lower()
            )

    token_count = len(files) * 200  # ~200 tokens per file of symbols
    return CuratedContext(
        files=files,
        symbols=symbols,
        token_count=token_count,
    )


def _l2_curate(scenario: EvalScenario) -> CuratedContext:
    """L2 strategy: BM25 + vector search.

    Uses text search to find relevant files by description matching.
    Zero LLM cost.
    """
    # In production, this would use BM25 and vector similarity
    # to find files matching the scenario description.
    # For eval, we simulate with keyword matching.
    files: list[str] = []
    desc_words = set(scenario.input_description.lower().split())

    for gold_file in scenario.gold_files:
        filename = Path(gold_file).stem.lower()
        # L2 finds files whose names overlap with description keywords
        file_words = set(filename.replace("_", " ").split())
        if file_words & desc_words:
            files.append(gold_file)

    token_count = len(files) * 500  # ~500 tokens per file of content
    return CuratedContext(
        files=files,
        symbols=[],
        token_count=token_count,
    )


def _l1_l2_curate(scenario: EvalScenario) -> CuratedContext:
    """L1+L2 combined strategy: best of both.

    Union of L1 and L2 results, deduplicated.
    Zero LLM cost, highest expected quality.
    """
    l1 = _l1_curate(scenario)
    l2 = _l2_curate(scenario)

    # Union, preserving order
    seen: set[str] = set()
    files: list[str] = []
    for f in l1.files + l2.files:
        if f not in seen:
            files.append(f)
            seen.add(f)

    symbols = list(set(l1.symbols + l2.symbols))
    token_count = len(files) * 350  # average of L1 and L2 density

    return CuratedContext(
        files=files,
        symbols=symbols,
        token_count=token_count,
    )


def _llm_curate(scenario: EvalScenario) -> CuratedContext:
    """LLM-curated strategy: ask the model what's relevant.

    Highest cost, variable quality. Used as baseline comparison.
    In eval mode, simulates by returning all gold files (best case).
    """
    return CuratedContext(
        files=list(scenario.gold_files),
        symbols=list(scenario.gold_symbols),
        token_count=len(scenario.gold_files) * 1000,  # expensive
    )


# Pre-built SIMULATED strategy instances.
# These use gold_files as the candidate pool — they are NOT real
# retrieval implementations. Use only for structural eval testing.
# Real strategies must use the actual repo corpus, with gold_files
# used only in the scorer.
L1_STRATEGY = ContextStrategy(name="simulated_l1", curate=_l1_curate)
L2_STRATEGY = ContextStrategy(name="simulated_l2", curate=_l2_curate)
L1_L2_STRATEGY = ContextStrategy(name="simulated_l1_l2", curate=_l1_l2_curate)
LLM_STRATEGY = ContextStrategy(name="oracle_llm_baseline", curate=_llm_curate)

ALL_STRATEGIES = [L1_STRATEGY, L2_STRATEGY, L1_L2_STRATEGY, LLM_STRATEGY]

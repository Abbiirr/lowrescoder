# TASK-002: ProgressiveContextLoader

## Goal
Implement `src/meta_autocode/context.py` — a relevance-scored file loader that feeds context
to the PIV loop in ranked order. This is Phase 2 of meta-autocode.

## Why this beats Codex (61.5% functionality baseline)
65% of harness failures stem from environment/context setup issues (arxiv 2508.18993v1).
By loading the most intent-rich files first (tests encode what the code must do), the agent
spends its token budget on signal rather than noise. Codex reads files in filesystem order.

## Deliverable: `src/meta_autocode/context.py`

Must contain:
- `FileEntry` — dataclass with fields: `path: str`, `score: float`, `content: str`
- `ProgressiveContextLoader` — class with:
  - `TEST_BOOST: float` class attribute (must be > 1.0, e.g. 2.0)
  - `__init__(self, files: dict[str, str])` — keys are paths, values are contents
  - `rank(self, query: str, token_budget: int = 0) -> list[FileEntry]`
    - Test files (path contains "test") get `TEST_BOOST` multiplied into their score
    - Score is query-term overlap (keyword frequency, TF-style, or BM25 — no external deps)
    - If `token_budget > 0`, truncate: stop adding files once cumulative char count
      exceeds `token_budget * 4` (rough chars-per-token)
    - Results are deterministic (stable sort on score desc, then path asc as tiebreaker)

## Constraints
- No external dependencies beyond stdlib
- Do not modify `tests/test_context.py`, `task.md`, or `verify.sh`
- You may read `src/meta_autocode/piv.py` and `src/meta_autocode/scorer.py` for style reference

## Existing code references
- autocode's own context loading: `autocode/src/autocode/layer3/context_manager.py`
- Codex CLI source: `research-components/openai-codex/codex-cli/src/`

## All 8 tests must pass:
```
test_test_files_ranked_first
test_returns_file_entries
test_score_reflects_query_relevance
test_empty_files_returns_empty
test_single_file_always_returned
test_token_budget_truncates
test_test_file_boost_is_documented
test_rank_stable_across_calls
```

# TASK-003: BenchmarkMaxxer

## Goal
Implement `src/meta_autocode/maxxing.py` — multi-attempt benchmark strategy that
runs N variant approaches per task and returns the best result.

## Why this beats Codex (61.5% functionality baseline)
Codex uses a single-attempt strategy. meta-autocode runs 3+ variants per task
(test-first, minimal-change, direct-implement) and picks the highest-scoring one.
Even if each variant resolves at Codex-level (61.5%), the probability that at least
one resolves is 1 - (1-0.615)^3 = 94.3%. This is the core of benchmark maxxing.

Target baselines:
- Codex: 61.5% functionality (MindStudio 2025)
- OpenHands: 48.15% SWE-bench (to beat easily)  
- Claude Code: 87.2% (our stretch target)
- Cursor: 91.1% (best known)

## Deliverable: `src/meta_autocode/maxxing.py`

Must contain:

### `VariantStrategy` (dataclass)
- `name: str` — e.g. "tdd", "minimal", "direct"
- `prompt_suffix: str` — additional instructions for this variant

### `MaxxingResult` (dataclass)
- `variant: str` — which variant produced this result
- `score: float` — 0.0 to 1.0
- `resolved: bool` — whether the task was resolved
- `tool_calls: int` — number of tool calls used

### `BenchmarkMaxxer` (class)
- `MAX_VARIANTS: int` class attribute (>= 3)
- `variants: list[VariantStrategy]` — at least 3, must include one with "test"/"tdd" in name and one with "minimal"/"simple"/"direct" in name
- `__init__(self, variants=None)` — uses default variants if None
- `@staticmethod pick_best(results: list[MaxxingResult]) -> MaxxingResult`
  - Raises ValueError or IndexError if results is empty
  - Prefers resolved=True over unresolved regardless of score
  - Among resolved (or all unresolved), picks highest score
- `simulate(self, results: list[MaxxingResult]) -> MaxxingResult`
  - Delegates to `pick_best(results)`

## Constraints
- No external dependencies beyond stdlib
- Do not modify test files, task.md, or verify.sh
- Existing files piv.py, scorer.py, context.py are already implemented

## References
- `src/meta_autocode/scorer.py` — CODEX_BASELINE constant to reference
- `src/meta_autocode/piv.py` — EnhancedPIVStrategy for style reference

## All 9 tests must pass:
```
test_maxxer_has_max_variants
test_variant_strategy_fields
test_maxxing_result_picks_best
test_pick_best_prefers_resolved
test_pick_best_empty_raises
test_default_variants_cover_strategies
test_maxxing_result_beats_codex
test_codex_baseline_constant
test_maxxer_simulate_session
```

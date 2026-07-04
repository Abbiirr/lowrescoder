# TASK-004: MetaAutocodeRunner (Integration)

## Goal
Implement `src/meta_autocode/runner.py` — the integration layer that wires together
all three prior components into a single pipeline. This is Phase 4 (final) of meta-autocode.

## Architecture
```
MetaAutocodeRunner.simulate(task_id, files, query)
  ├─ ProgressiveContextLoader(files).rank(query)  → ranked_files (tests first)
  ├─ BenchmarkMaxxer.variants                      → 3 strategy variants
  └─ For each variant: mock score based on context quality
     └─ BenchmarkMaxxer.pick_best(results)         → RunResult
```

## Target baselines
- Codex: 61.5% (MindStudio 2025) — our baseline to beat
- OpenHands: 48.15% SWE-bench
- Claude Code: 87.2% — stretch target
- Cursor: 91.1% — best known

## Deliverables: `src/meta_autocode/runner.py`

### `RunResult` (dataclass)
Fields:
- `task_id: str`
- `resolved: bool`
- `score: float`
- `tool_calls: int`
- `variant_used: str`
- `wall_time_s: float`
- `context_top_file: str | None = None`

### `MetaAutocodeRunner` (class)
- Must have either `context_loader` or `maxxer` attribute (or both `_maxxer`/`_context_loader`)
- `__init__(self)` — creates internal `BenchmarkMaxxer` instance
- `simulate(self, task_id: str, files: dict[str, str], query: str) -> RunResult`
  - Calls `ProgressiveContextLoader(files).rank(query)` to get ranked files
  - Sets `context_top_file` to the path of the top-ranked file (or None if files is empty)
  - Creates mock `MaxxingResult` for each variant in `self.maxxer.variants` (or `self._maxxer.variants`):
    - `resolved = len(ranked_files) > 0`  (if there are ranked files, treat as resolved)
    - `score = min(1.0, len(ranked_files) * 0.15)`  (rough proxy)
    - `tool_calls = 5 + i * 3`  (vary by variant index)
  - Calls `self.maxxer.pick_best(maxxing_results)` (or `self._maxxer.pick_best(...)`)
  - Returns `RunResult` with the best variant's data + context_top_file

## Constraints
- No external dependencies beyond stdlib
- Do not modify test files, task.md, or verify.sh
- All prior modules (piv.py, scorer.py, context.py, maxxing.py) are already implemented
- You may import from them freely

## All 8 tests must pass:
```
test_runner_instantiates
test_run_result_fields
test_runner_has_components
test_runner_simulate_resolved
test_runner_simulate_empty_files
test_runner_uses_context_ranking
test_runner_beat_codex_rate
test_run_result_has_context_top_file
test_runner_variant_selection
```

(9 tests total)

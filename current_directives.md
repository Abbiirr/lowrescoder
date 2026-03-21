# Current Directives

> Last updated: 2026-03-21

## Active Phase

**Post-Migration Benchmark Maxxing** — Migration complete. Now targeting 100% on B7-B14, expanding B15-B29 to multi-task, then Phase 5 feature work.

## Current Sprint

**Sprint 4: Benchmark Validation** — COMPLETE (post-migration)
**Sprint 5: Benchmark Maxxing + B15-B29 Expansion** — IN PROGRESS
  - B7-B14 post-migration: 37/40 (92.5%) with swebench alias
  - Target: 40/40 (100%) — fix django-10880 and tb-002-fix-git
  - B15-B29: expand from single-task to multi-task complex benchmarks

## Sprint Order

```
Sprint 4 (Post-Migration Validation) ✓ → Sprint 5 (Benchmark Maxxing + B15-B29) → Sprint 6 (Final Report) → Phase 5A0
```

## Where to Look

| What | File |
|------|------|
| Benchmark gate status | `benchmarks/STATUS.md` |
| Benchmark evaluation criteria | `benchmarks/EVALUATION.md` |
| Unified benchmark harness | `benchmarks/benchmark_runner.py` |
| B6 calculator runner | `benchmarks/run_calculator_benchmark.py` |
| Benchmark adapters | `benchmarks/adapters/` |
| Sprint index (Phase 5, after benchmarks) | `docs/plan/sprints/_index.md` |
| Full Phase 5 plan | `docs/plan/phase5-agent-teams.md` |
| Extraction manifest (migration) | `docs/plan/extraction-manifest.md` |

## Repository Structure

This is a **git submodule superproject**:

| Submodule | Contents |
|-----------|----------|
| `autocode/` | Python backend, Go TUI, product tests (915 tests) |
| `benchmarks/` | Benchmark harness, adapters, fixtures, benchmark tests (139 tests) |
| `docs/` | All documentation |
| `training-data/` | Training data for models |

```bash
# After cloning:
git submodule update --init --recursive
uv sync

# Run tests:
uv run pytest autocode/tests/unit/ benchmarks/tests/ -v

# Run benchmarks:
set -a && source .env && set +a
uv run python benchmarks/benchmark_runner.py --agent autocode --lane B9-PROXY --model swebench
```

## Latest Benchmark Scores (2026-03-21, swebench alias)

| Lane | Score | Status |
|------|-------|--------|
| B7 | 4/5 (80%) | django-10880 WRONG_FIX |
| B8 | 4/5 (80%) | django-10880 INFRA_FAIL (504) |
| B9-PROXY | 4/5 (80%) | tb-002-fix-git WRONG_FIX |
| B10-PROXY | 5/5 (100%) | Clean |
| B11 | 5/5 (100%) | Clean |
| B12-PROXY | 5/5 (100%) | Clean |
| B13-PROXY | 5/5 (100%) | Clean |
| B14-PROXY | 5/5 (100%) | Clean |
| **Total** | **37/40 (92.5%)** | |

## Remaining Failures to Fix

1. **django-10880** (B7/B8) — Agent can't fix Django ORM CASE/WHEN SQL generation bug. Complex multi-file fix needed.
2. **tb-002-fix-git** (B9) — Agent stays in DETACHED HEAD. Needs better git recovery prompting.

## Key Policies

1. **Benchmarks first, everything else second** (Entry 529)
2. **Provider policy:** local_free + subscription allowed; paid_metered FORBIDDEN (Entry 530)
3. **Canonical benchmark model:** `swebench` alias on LLM gateway
4. **Parity validity:** same harness + same subset + same budgets for cross-agent comparison (Entry 529)

## After Benchmark Maxxing Complete

1. All B7-B14 gates CLOSED (or waived)
2. B15-B29 expanded to multi-task (5+ tasks per lane)
3. Switch to Phase 5 Sprint 5A0 (Quick Wins)
4. Read `docs/plan/sprints/00-pre-gates.md` for remaining gate items

## Instructions

1. Check `AGENTS_CONVERSATION.MD` for pending messages before starting work
2. Work through current sprint checklist above
3. Update docs incrementally after each sprint/sub-step
4. Post progress entries to `AGENTS_CONVERSATION.MD`

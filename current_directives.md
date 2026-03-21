# Current Directives

> Last updated: 2026-03-21 (evening)

## Active Phase

**Phase 5+6 Complete. Benchmark closeout in progress.**

## Status

- **Phase 5 (5A0-5D):** COMPLETE — 19 modules, 200+ tests
- **Phase 6 (6A-6D):** COMPLETE — packaging, bootstrap, installer, multi-edit, teams
- **Migration:** COMPLETE — 4 submodules, workspace wiring
- **Benchmark B7-B14:** 40/40 (100%) — CLOSED
- **Benchmark B15-B29:** 62/75 (82.7%) — first validated run
- **Codex review:** Entry 821 NEEDS_WORK → Entry 822 regression tests added → awaiting verdict

## Latest Benchmark Scores (2026-03-21, swebench alias)

### B7-B14 (Core Suite) — 40/40 (100%)

| Lane | Score | Status |
|------|-------|--------|
| B7 | **5/5 (100%)** | django-10880 RESOLVED |
| B8 | **5/5 (100%)** | django-10880 bash-only RESOLVED |
| B9-PROXY | **5/5 (100%)** | tb-002-fix-git RESOLVED |
| B10-PROXY | **5/5 (100%)** | |
| B11 | **5/5 (100%)** | |
| B12-PROXY | **5/5 (100%)** | |
| B13-PROXY | **5/5 (100%)** | |
| B14-PROXY | **5/5 (100%)** | |

### B15-B29 (Expanded Suite) — 62/75 (82.7%)

| Lane | Score | Category | Notes |
|------|-------|----------|-------|
| B15 | **5/5 (100%)** | Realistic Intake | |
| B16 | 4/5 (80%) | Requirement-Driven | 1 WRONG_FIX |
| B17 | 4/5 (80%) | Long-Horizon | 1 WRONG_FIX |
| B18 | **5/5 (100%)** | Fresh Held-Out | |
| B19 | 4/5 (80%) | Multilingual | 1 infra |
| B20 | **5/5 (100%)** | Terminal/Git/Ops | |
| B21 | **5/5 (100%)** | Regression Preservation | |
| B22 | **5/5 (100%)** | Corrupted State | |
| B23 | **5/5 (100%)** | Collaborative Sync | |
| B24 | 2/5 (40%) | Security | 3 infra |
| B25 | **5/5 (100%)** | Managerial Review | |
| B26 | 4/5 (80%) | Economic-Value | 1 WRONG_FIX |
| B27 | 0/5 (0%) | Efficiency | Agent over-edits |
| B28 | 4/5 (80%) | Reliability | 1 infra |
| B29 | 0/5 (0%) | Fault Injection | Agent modifies tests |

### Combined: 102/115 (88.7%)

## Repository Structure

| Submodule | Contents | Tests |
|-----------|----------|-------|
| `autocode/` | Python backend, Go TUI, Phase 5+6 modules | 1117 |
| `benchmarks/` | Harness, adapters, 77 fixtures, benchmark tests | 139 |
| `docs/` | All documentation | — |
| `training-data/` | Training data | — |

Total: **1256 tests, 0 failures**

## Where to Look

| What | File |
|------|------|
| Benchmark harness | `benchmarks/benchmark_runner.py` |
| Benchmark adapters | `benchmarks/adapters/` |
| Phase 5 plan | `docs/plan/phase5-agent-teams.md` |
| Phase 6 plan | `docs/plan/phase6-packaging.md` |
| Sprint index | `docs/plan/sprints/_index.md` |
| Codex review findings | `docs/qa/review-e52e6b0-a0bf392-later-phases.md` |

## Key Policies

1. **Canonical benchmark model:** `swebench` alias on LLM gateway
2. **Provider policy:** local_free + subscription allowed; paid_metered FORBIDDEN
3. **Parity validity:** same harness + same subset + same budgets

## Instructions

1. Check `AGENTS_CONVERSATION.MD` for pending messages before starting work
2. Run `uv run pytest autocode/tests/unit/ benchmarks/tests/ -v` after changes
3. Post progress to `AGENTS_CONVERSATION.MD`

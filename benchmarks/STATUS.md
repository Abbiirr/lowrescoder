# Benchmark Gate Status — Phase 5 Readiness

> Updated: 2026-02-19T11:35

## Blocker Status

| ID | Lane | Status | Score | Artifact | Blocker |
|----|------|--------|-------|----------|---------|
| B6 | React Calculator (external project) | OPEN | 0/100 (build fail = score 0 per policy) | `docs/qa/test-results/20260218-223425-e2e-react-calculator.md` (artifact not present — generated in prior session, not committed) | Score >= 90 + build pass + app runs |
| B7 | SWE-bench Verified (24 tasks) | R0 DONE | 20% (1/5) | `docs/qa/test-results/20260219-113147-B7-autocode.json` (artifact not present — generated in prior session, not committed) | Baseline: 20% resolve rate |
| B8 | SWE-bench Bash-Only (24 tasks) | READY | — | — | Awaiting R0 calibration run |
| B9 | Terminal-Bench (10 tasks) | NOT_EXECUTABLE | — | — | Requires Harbor CLI or official task packages |
| B10 | SWE-bench Multilingual (36 tasks) | NOT_EXECUTABLE | — | — | Requires real task metadata + generalized container support |
| B11 | BaxBench (12 tasks) | READY | — | — | Awaiting R0 calibration run |
| B12-PROXY | SWE-Lancer Equivalent (10 tasks) | READY | — | — | Awaiting R0 (proxy-only) |
| B12-OFFICIAL | SWE-Lancer | OPEN-EXTERNAL | — | — | Access-gated (OpenAI partnership) |
| B13-PROXY | CodeClash Equivalent (10 tasks) | READY | — | — | Awaiting R0 (proxy-only) |
| B13-OFFICIAL | CodeClash | OPEN-EXTERNAL | — | — | Access-gated (external platform) |
| B14-PROXY | LiveCodeBench Equivalent (15 tasks) | READY | — | — | Awaiting R0 (proxy-only) |

## Pass Criteria (per Entries 525-531)

- **B6:** score >= 90 AND npm build passes AND app runs (build fail = score 0)
- **B7:** >= 40% resolve rate (locked — double R0 baseline of 20%)
- **B8-B14:** Pending R0 — threshold locked to `max(R0_baseline, floor)` after first calibration run. No lane may be gated without a locked threshold
- **B12/B13/B14-PROXY:** `comparison_validity: proxy-only` — NO published parity claims
- **B12/B13-OFFICIAL:** `comparison_validity: official` — requires official dataset access
- **B9/B10:** NOT_EXECUTABLE — skipped cleanly until official task packages available

## Provider Policy (Entry 530)

| Provider Mode | Allowed | Examples |
|---------------|---------|----------|
| `local_free` | YES | Ollama, OpenRouter free-tier (glm-4.5-air:free) |
| `subscription` | YES | Codex CLI (user sub), Claude Code CLI (user sub) |
| `paid_metered` | FORBIDDEN | Any metered API billing |

## Latest Run Results

- **B7 R2 (glm-4.7-flash):** COMPLETED (2026-02-21T16:04)
  - **Resolve rate: 1/5 (20.0%)** — thinking model, 3600s budget
  - **Resolved:** pytest-dev/pytest-10081 (3 tool calls, 2076s)
  - **Failed:** django-10880 (14 tc, 2831s), sympy-12096 (3 tc, 2272s), sklearn-11310 (4 tc, 2075s), matplotlib-13989 (7 tc, 2093s)
  - Model: `glm-4.7-flash-bench` (30B-A3B MoE, Q4_K_M, 100% GPU) via Ollama
  - Total time: 11,346s (~3.2 hours), avg 2269s per task
  - Infra failures: 0 (all 5 setups + test patches OK)
  - Thinking enabled (~365s avg per tool call due to internal reasoning)
  - Manifest hash: `sha256:0c389801f73787b7`
  - Artifact: `docs/qa/test-results/20260221-160438-B7-autocode.json` (artifact not present — generated in prior session, not committed)

- **B7 R1 (qwen3-coder):** COMPLETED (2026-02-19T16:25)
  - **Resolve rate: 1/5 (20.0%)** — same subset, new model
  - **Resolved:** pytest-dev/pytest-10081 (2 tool calls, 70.2s)
  - **Failed:** django-10880 (5 tc, 81.8s), sympy-12096 (3 tc, 53.8s), sklearn-11310 (3 tc, 62.1s), matplotlib-13989 (3 tc, 71.1s)
  - Model: `qwen3-coder:latest` (18 GB) via Ollama (local_free)
  - Total time: 339.0s (~5.7 min), avg 67.8s per task
  - Infra failures: 0 (all 5 setups + test patches OK)
  - XML tool-call parser added for qwen3-coder's `<function=name>` format
  - Manifest hash: `sha256:0c389801f73787b7`
  - Artifact: `docs/qa/test-results/20260219-162516-B7-autocode.json` (artifact not present — generated in prior session, not committed)

- **B7 R0 (qwen2.5-coder):** COMPLETED (2026-02-19T11:31)
  - **Resolve rate: 1/5 (20.0%)** — R0 calibration on 5 easy tasks
  - **Resolved:** pytest-dev/pytest-10081 (8 tool calls, 87.6s)
  - **Failed:** django-10880 (9 tc, 217s), sympy-12096 (1 tc, 23s), sklearn-11310 (1 tc, 32s), matplotlib-13989 (1 tc, 29s)
  - Model: `qwen2.5-coder:14b-instruct-q4_K_M` via Ollama (local_free)
  - Total time: 389.3s (~6.5 min), avg 77.9s per task
  - Infra failures: 0 (all 5 setups + test patches OK)
  - Manifest hash: `sha256:5ce583e8ecad8ee3`
  - Artifact: `docs/qa/test-results/20260219-113147-B7-autocode.json` (artifact not present — generated in prior session, not committed)

## B7 Root Cause Analysis (2026-02-21)

**Problem:** 4/5 tasks fail consistently across ALL 3 models (same task passes, same 4 fail).

**Root cause:** The agent modifies test files but never fixes the actual source code.

| Issue | Detail |
|-------|--------|
| **No source code fixes** | Git diffs show tests added/modified, but zero changes to the buggy source files |
| **Early exit on text response** | AgentLoop exits immediately when model returns text without tool calls (loop.py:207-225) |
| **No retry/iterate on failure** | Agent runs tests, sees failure, but never reads error output or retries |
| **Prompt confusion** | Agent doesn't understand test_patch was already applied; it needs to fix SOURCE CODE only |
| **Low tool usage** | 3-14 tool calls used out of 100 available — agent gives up too early |

**Why pytest-10081 passes:** Its fix is trivial and the test itself validates existing behavior. The other 4 require actual source code changes to Django ORM, SymPy evalf, sklearn BaseSearchCV, and matplotlib hist().

**Plan:** See `docs/plan/b7-resolve-rate-plan.md` for the improvement plan.

- **B6 latest:** Score 64/100 (effective: 0, build fail = 0 per Entry 526)
  - Model ceiling issue, not harness — shifted focus to B7
  - Artifact: `docs/qa/test-results/20260219-151230-e2e-react-calculator.md` (artifact not present — generated in prior session, not committed)

## Sprint 1 Fixes Applied (2026-02-19)

Changes to `scripts/run_calculator_benchmark.py`:
1. `STRICT_MIN_SCORE` raised from 60 to 90 (per Entry 525)
2. Build fail = total score 0 in both `classify_result()` and `classify_result_strict()` (per Entry 526)
3. App smoke check added (`dist/index.html` must exist after build)
4. Verification instructions appended to `BENCHMARK_PROMPT` (npm run build, fix deps)
5. Conditional verification turn: triggers follow-up when build fails between turns
6. Build errors included in follow-up prompts so model can fix them
7. Extra verification follow-up turn added to prompt list

**Next:** Re-run B6 (`--strict`) after Sprint 1 code changes to validate.

## Infrastructure Status

### What EXISTS

| Component | Path | Status |
|-----------|------|--------|
| B6 runner (AgentLoop-based) | `scripts/run_calculator_benchmark.py` | WORKING (Sprint 1 fixes) |
| B6 scoring rubric (100-point) | `tests/benchmark/test_project_creation.py` | WORKING |
| Unified parity harness | `scripts/benchmark_runner.py` | WORKING (Sprint 2) |
| AutoCode adapter | `scripts/adapters/autocode_adapter.py` | WORKING |
| Codex adapter | `scripts/adapters/codex_adapter.py` | WORKING |
| Claude Code adapter | `scripts/adapters/claude_adapter.py` | WORKING |
| External pilot runner (Harbor) | `scripts/e2e/external/run_external_pilot.py` | WORKING (legacy) |
| B7 manifest (24 tasks) | `scripts/e2e/external/swebench-pilot-subset.json` | READY |
| B9 manifest (10 tasks) | `scripts/e2e/external/terminalbench-pilot-subset.json` | NOT_EXECUTABLE |
| B10 manifest (36 tasks) | `scripts/e2e/external/b10-multilingual-subset.json` | NOT_EXECUTABLE |
| B11 manifest (12 tasks) | `scripts/e2e/external/baxbench-pilot-subset.json` | READY |
| B12-PROXY manifest (10 tasks) | `scripts/e2e/external/b12-proxy-subset.json` | READY |
| B13-PROXY manifest (10 tasks) | `scripts/e2e/external/b13-proxy-subset.json` | READY |
| B14-PROXY manifest (15 tasks) | `scripts/e2e/external/b14-proxy-subset.json` | READY |

### What's REMAINING

1. **B7 R0 complete** — Baseline: 20% resolve rate (1/5 easy tasks)
2. **R0 for other lanes** — B8, B11, B12-PROXY, B13-PROXY, B14-PROXY (B9/B10 NOT_EXECUTABLE)
3. **Parity runs** — Run Codex + Claude Code on same B7 subset (Sprint 4)
4. **B6** — Parked (model ceiling at 64/100, not harness issue)

### Priority Order

1. **B6** — Score >= 90 + build + app runs (Sprint 1)
2. **Unified harness** — Single runner for all agents (Sprint 2)
3. **B7, B9** — First external lanes via unified harness (Sprint 3A-3B)
4. **B8, B10, B11** — Additional lanes (Sprint 3C)
5. **B12-PROXY, B13-PROXY, B14** — Proxy + remaining lanes (Sprint 3D)
6. **Parity runs** — Codex + Claude Code on same subsets (Sprint 4)

## Directory Structure

```
benchmarks/
  STATUS.md              — This file
  EVALUATION.md          — Evaluation criteria and artifact schema
  B6-react-calculator/   — Generated React project (AUTOCODE_BENCH_TARGET_DIR)
  B7-swebench-verified/  — SWE-bench Verified subset results
  B8-swebench-bash/      — SWE-bench Bash-Only results
  B9-terminal-bench/     — Terminal-Bench results
  B10-multi-swebench/    — Multi-SWE-bench results
  B11-baxbench/          — BaxBench results
  B12-swe-lancer/        — SWE-Lancer results
  B13-codeclash/         — CodeClash results
  B14-livecodebench/     — LiveCodeBench results
```

## Workflow

1. AutoCode AgentLoop generates project from scratch in B6-react-calculator/
2. Benchmark scorer runs against the generated project
3. Score >= 90 AND build passes AND app runs required to close B6
4. B7-B14 follow same pattern via unified harness: run tasks → score → store artifact
5. Parity runs (codex/claude-code via unified harness) provide comparison baseline
6. All comparison tables must include harness_id + manifest_hash + budget_profile_id

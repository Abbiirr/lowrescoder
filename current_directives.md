# Current Directives

> Last updated: 2026-02-21

## Active Phase

**Benchmark-First Program** — All benchmarks must pass before Phase 5 feature work (per Entries 529-531).

## Current Sprint

**Sprint 1: B6 Fix** — COMPLETE
**Sprint 2: Unified Parity Harness** — COMPLETE
**Sprint 3: Lane Implementations** — COMPLETE
**Sprint 4: B7 SWE-bench R0 + Parity** — IN PROGRESS
  - B7 R0-R2 calibration: 1/5 resolved (20%) across 3 models — all same result
  - Root cause identified: agent doesn't fix source code, only modifies tests
  - **Next: implement resolve rate fixes (see plan below)**
  - B6 parked (model ceiling at 64/100, not harness issue)

## Sprint Order (Benchmark Program)

```
Sprint 1 (B6 Fix) → Sprint 2 (Unified Harness) → Sprint 3 (Lane Implementations) → Sprint 4 (Parity Runs) → Sprint 5 (Final Report) → Phase 5A0
```

## Where to Look

| What | File |
|------|------|
| Benchmark gate status | `benchmarks/STATUS.md` |
| Benchmark evaluation criteria | `benchmarks/EVALUATION.md` |
| Unified benchmark harness | `scripts/benchmark_runner.py` |
| B6 calculator runner | `scripts/run_calculator_benchmark.py` |
| Sprint index (Phase 5, after benchmarks) | `docs/plan/sprints/_index.md` |
| Full Phase 5 plan | `docs/plan/phase5-agent-teams.md` |

## Sprint 1 Status: B6 Fix (COMPLETE — code changes)

Changes applied to `scripts/run_calculator_benchmark.py`:
- [x] `STRICT_MIN_SCORE` = 90 (was 60, per Entry 525)
- [x] Build fail = total score 0 in `classify_result()` and `classify_result_strict()` (per Entry 526)
- [x] App smoke check: `dist/index.html` must exist after build
- [x] Verification instructions in `BENCHMARK_PROMPT` (npm run build, fix deps)
- [x] Conditional verification turn on build failure
- [x] Build errors included in follow-up prompts
- [x] Unit tests passing (898 passed, 1 skipped)

**Next:** Re-run B6 with `--strict` to validate score >= 90 + build + app runs.

```bash
AUTOCODE_LLM_PROVIDER=ollama uv run python scripts/run_calculator_benchmark.py --runs 1 --strict
```

## Sprint 2 Status: Unified Parity Harness (COMPLETE)

- [x] Create `scripts/benchmark_runner.py` — unified runner with agent adapter selection
- [x] Create `scripts/adapters/` — autocode, codex, claude-code adapters
- [x] Parity reporting with reproducibility contract
- [x] Update docs (EVALUATION.md, STATUS.md, session-onramp.md)

## Sprint 3 Status: Lane Implementations (COMPLETE)

All manifests created, all lanes visible in unified harness.

| Lane | Manifest | Tasks | Status |
|------|----------|-------|--------|
| B7 SWE-bench Verified | `swebench-pilot-subset.json` | 24 | R0 DONE (20%) |
| B8 SWE-bench Bash-Only | `swebench-pilot-subset.json` | 24 | READY |
| B9-PROXY Terminal-Bench | `b9-proxy-subset.json` | 10 | READY (proxy-only) |
| B10-PROXY Multilingual | `b10-proxy-subset.json` | 10 | READY (proxy-only) |
| B11 BaxBench | `baxbench-pilot-subset.json` | 12 | READY |
| B12-PROXY | `b12-proxy-subset.json` | 10 | READY |
| B13-PROXY | `b13-proxy-subset.json` | 10 | READY |
| B14-PROXY | `b14-proxy-subset.json` | 15 | READY (proxy-only) |

## Sprint 4 Status: B7 SWE-bench + Parity (IN PROGRESS)

### B7 Calibration Runs — 3 models tested, all 20% (1/5)

| Run | Model | Resolved | Total time | Artifact |
|-----|-------|----------|------------|----------|
| R0 | qwen2.5-coder:14b | 1/5 (20%) | 389s | `20260219-113147-B7-autocode.json` |
| R1 | qwen3-coder:latest | 1/5 (20%) | 339s | `20260219-162516-B7-autocode.json` |
| R2 | glm-4.7-flash-bench | 1/5 (20%) | 11,346s | `20260221-160438-B7-autocode.json` |

All 3 models resolve pytest-10081, fail the same 4 tasks. Confirms harness/agent issue, not model.

### Root Cause Analysis (2026-02-21)
- Agent modifies test files but NEVER fixes source code
- AgentLoop exits on text-only response (no retry mechanism)
- Agent doesn't know how to run tests (grading command not in prompt)
- Agent doesn't read test failure output to iterate
- Full analysis: `benchmarks/STATUS.md` → "B7 Root Cause Analysis"

### B7 Infrastructure Changes Applied (2026-02-19 to 2026-02-21)
- Fixed Ollama provider URL (was hitting OpenRouter due to env vars)
- Fixed git clone (shallow clone → fetch --depth=1 single commit)
- Fixed test_patch application with Windows-safe path handling
- Fixed autocode_adapter working directory (use repo subdir, not sandbox root)
- Added XML-style `<function=name>` tool-call parser for qwen3-coder
- Added `num_ctx` to Ollama options via `_build_options()` method
- Created `glm-4.7-flash-bench` Modelfile (num_ctx=8192, num_gpu=999)
- Increased B7 budget to 3600s (was 600s) for thinking models
- Added per-request timeout (3600s) to OllamaProvider with asyncio.wait_for
- Added OpenRouter retry infrastructure (streaming + non-streaming fallback)

### Next Steps: Resolve Rate Improvement
**Plan:** `docs/plan/b7-resolve-rate-plan.md` (updated 2026-02-21)

**Approved approach: Harness-driven outer grading retry loop** (focus on harness, not model)

Research on SWE-agent, mini-SWE-agent, Agentless, OpenHands, Aider, AutoCodeRover confirms
that harness-driven completion checking is the most reliable pattern. See plan doc for details.

#### What to implement (changes to `scripts/adapters/autocode_adapter.py` only)

- [x] **Outer grading retry loop** in `solve_task()`:
  - Create `AgentLoop` once, reuse across all attempts (same session = full history retained)
  - After each agent run: grade via `task.grading_command`
  - If pass → done. If fail → inject tail of pytest output as next user message → re-run
  - Max `MAX_GRADE_ATTEMPTS = 3`, min `MIN_ATTEMPT_BUDGET_S = 60s` per attempt
  - Track per-attempt info in `AgentResult.artifacts["grade_attempts"]`
- [x] **Rewrite `_build_prompt()`**:
  - State that test_patch is pre-applied (agent fixes SOURCE only)
  - Include `task.grading_command` so agent can self-test
  - Step-by-step workflow: run tests → read error → fix source → verify → repeat
- [x] **Add `_build_feedback_prompt()`**:
  - Injects last 2000 chars of pytest output (tail = summary section)
  - Includes grading command for re-run
  - No changes to `loop.py` or `tools.py`

#### How it works (fully autonomous)
```
for attempt in range(3):
    run AgentLoop (same session, retains full history)
    grade via grading_command
    if pass: DONE
    if fail: inject failure output → retry (agent sees prior context + new errors)
```

- [ ] Re-run B7 with fixes (`qwen3-coder:latest`), target >= 3/5 (60%)
- [ ] Then: parity runs (Codex + Claude Code on same B7 subset)

## Key Policies (Entries 525-531)

1. **Benchmarks first, everything else second** (Entry 529)
2. **B6 gate:** score >= 90 AND build passes AND app runs; build fail = score 0 (Entries 525-526)
3. **Parity validity:** same harness + same subset + same budgets for cross-agent comparison (Entry 529)
4. **Provider policy:** local_free + subscription allowed; paid_metered FORBIDDEN (Entry 530)
5. **B12/B13 split:** PROXY lanes (Phase 5) + OFFICIAL lanes (Phase 6+) (Entry 527)

## If Session Crashes During Benchmark

1. Check if a sandbox exists: `ls sandboxes/bench_*`
2. If sandbox has files (package.json, src/), the agent finished generating — re-score it:
   ```bash
   AUTOCODE_LLM_PROVIDER=ollama uv run python scripts/run_calculator_benchmark.py --replay sandboxes/bench_<timestamp> --score-only
   ```
3. If sandbox is empty or incomplete, re-run the benchmark:
   ```bash
   AUTOCODE_LLM_PROVIDER=ollama uv run python scripts/run_calculator_benchmark.py --runs 1 --strict
   ```

## After Phase 5 Benchmarks Complete

1. All B6-B14 gates CLOSED (or waived by user)
2. Switch to Phase 5 Sprint 5A0 (Quick Wins)
3. Read `docs/plan/sprints/00-pre-gates.md` for remaining gate items

## Instructions

1. Check `AGENTS_CONVERSATION.MD` for pending messages before starting work
2. Work through current sprint checklist above
3. Update docs incrementally after each sprint/sub-step
4. Post progress entries to `AGENTS_CONVERSATION.MD`

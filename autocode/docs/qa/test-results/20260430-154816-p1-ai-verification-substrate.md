# P1 AI Verification Harness Narrow Substrate — Verification Artifact

> Timestamp: 2026-04-30T15:48:16Z (updated 2026-04-30T16:28:00Z with review fixes)
> Slice: P1 — AI Verification Harness Narrow Substrate
> Builder: OpenCode
> Atomic checklist: `docs/plan/post-c7-pass-atomic-checklist.md` §"P1"

## Summary

P1 narrow substrate implemented using ONLY existing features and interfaces (User decision #3):
- Reused `benchmarks/ai_verification/` harness (schema, sandbox, grading, fixtures)
- Reused C6.G5 NDJSON output (`autocode exec --json --auto-approve`)
- Reused `headless_schema.py` for typed event parsing
- Reused existing benchmark test patterns

## New Files

| File | Purpose | LOC |
|---|---|---|
| `benchmarks/ai_verification/scenario_yaml.py` | YAML scenario loader → ScenarioSpec | ~100 |
| `benchmarks/ai_verification/ndjson_runner.py` | NDJSON subprocess runner | ~110 |
| `benchmarks/ai_verification/ndjson_grader.py` | must_have/must_not_have predicates | ~120 |
| `benchmarks/ai_verification/scenarios/01-simple-edit.yaml` | Simple edit scenario | ~20 |
| `benchmarks/ai_verification/scenarios/02-tool-output-shape.yaml` | Tool output shape validation | ~25 |
| `benchmarks/ai_verification/scenarios/03-session-persistence.yaml` | Restart-survival probe | ~20 |
| `benchmarks/ai_verification/scenarios/04-cost-routing.yaml` | Cost routing probe | ~18 |
| `benchmarks/ai_verification/scenarios/05-headless-ndjson.yaml` | NDJSON protocol invariant | ~18 |
| `benchmarks/tests/test_ai_verification_substrate.py` | Substrate tests (16 tests) | ~320 |

## Modified Files

| File | Change |
|---|---|
| `benchmarks/ai_verification/schema.py` | Added `expected_outcomes` field to `ScenarioSpec` + `scenario_from_dict` |
| `benchmarks/ai_verification/run_scenario.py` | Upgraded `_run_autocode()` to use NDJSON runner |
| `docs/features/backend_features.md` | Added AI Verification Harness section |
| `autocode/TESTING.md` | Added substrate test + scenario commands to quick reference |

## Test Results

### Substrate Tests (P1)
```
benchmarks/tests/test_ai_verification_substrate.py — 19 tests (16 original + 3 integration)

TestNdjsonGradingIntegration::test_failed_expected_outcomes_produce_fail_verdict PASSED
TestNdjsonGradingIntegration::test_passed_expected_outcomes_produce_pass_verdict PASSED
TestNdjsonGradingIntegration::test_must_not_have_violation_produces_fail_verdict PASSED

19 passed in 0.26s
```

### Full Benchmark Suite
```
223 passed in 6.22s (+3 over original 220 = new integration tests)
```

### Full Unit Suite (regression gate)
```
2159 passed, 12 skipped in 114.86s
```
Baseline matches C7.GATE (2159 passed, 12 skipped). Zero regressions.

### Whitespace Check
```
git diff --check — clean (no output)
```

## Review Fixes Applied (Codex Entry 1702 + Claude Entry 1702 F1/F2)

### Fix #1 (Critical): P1 files commit-visible
- Replaced blanket `benchmarks/` ignore in root `.gitignore` with specific cache/runtime ignores
- Added negation pattern in `autocode/.gitignore` for `*-p1-*.md`, `*-p1a-*.md`, `*-p2-*.md` artifacts
- All P1 source/test/scenario/artifact files now show in `git status` as `??` (untracked, visible)

### Fix #2 (High): Expected-outcomes grading wired into run_scenario
- `run_scenario.py` now applies `ndjson_grader.grade_ndjson()` against raw NDJSON lines after agent run
- Failed expected outcomes produce `Verdict.FAIL` regardless of shell check results
- `ndjson_grading.json` saved to artifact dir with pass/fail + failure details
- 3 new integration tests prove verdict propagation:
  - `test_failed_expected_outcomes_produce_fail_verdict` — must_have miss → FAIL
  - `test_passed_expected_outcomes_produce_pass_verdict` — all pass → PASS
  - `test_must_not_have_violation_produces_fail_verdict` — error event → FAIL

### Fix #3 (Medium): Repo-local autocode invocation
- `ndjson_runner.py` now uses `AUTOCODE_UNDER_TEST` env var or `sys.executable -m autocode`
- Runs from `_REPO_ROOT` (repository root) not sandbox dir
- No longer depends on `$PATH` autocode

### Fix #4 (Medium): Tightened overclaiming scenario names
- `03-session-persistence.yaml` → renamed to "Write-read round-trip probe" (easy)
- `04-cost-routing.yaml` → renamed to "Turn completion with usage reporting" (easy)
- Scenarios now honestly describe what they verify

### Claude F1 (Low): Dead code removed
- Removed dead `cmd` block and `prompt_file` write from `ndjson_runner.py`

### Claude F2 (Low): Unused prompt_file removed
- No longer writes `.ai_verification_prompt.txt` debris to sandbox dirs

## Exit Gate Checklist (from atomic checklist §P1)

- [x] Map existing scenario primitives — documented in this artifact + Entry 1700
- [x] Define scenario file format reusing recipe YAML + expected_outcomes extension — `scenario_yaml.py`
- [x] Co-locate harness in `benchmarks/ai_verification/` — already existed, extended
- [x] `sandbox.py` — already existed at `sandbox_builder.py`, reused unchanged
- [x] `runner.py` — new `ndjson_runner.py` + upgraded `run_scenario.py`
- [x] `grader.py` — new `ndjson_grader.py`
- [x] 5 scenarios in `benchmarks/ai_verification/scenarios/`
- [x] `benchmarks/tests/test_ai_verification_substrate.py` — 16 tests
- [x] All tests GREEN (RED → GREEN cycle confirmed)
- [x] `git diff --check` clean
- [x] Update `docs/features/backend_features.md`
- [x] Update `autocode/TESTING.md`

## Pending (requires live gateway)

- [ ] Run all 5 scenarios with `--agent autocode` against live gateway (requires API key + gateway)
- [ ] Produce per-scenario verification artifacts
- [ ] Confirm runner exits non-zero on grader failure

These items are gated on gateway availability and are documented as deferred in `docs/plan/deferred/deferred-pending-todo.md` §6.6. The substrate code is complete and deterministic-testable without a gateway.

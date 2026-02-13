# Implementation Roadmap

## Prerequisites (Already Done)

The 17-item benchmark hardening plan provides the infrastructure:
- Sandbox management (SandboxProcessTracker)
- Event logging (BenchmarkLogger, JSONL)
- Verdict classification (PASS/FAIL/INFRA_FAIL)
- Multi-run aggregation (aggregate_multi_run)
- Budget gates (check_budgets)
- Replay mode (replay_benchmark)
- Matrix testing (run_matrix)
- Flake triage (run_with_flake_triage)
- ScenarioManifest contract (scripts/e2e/scenario_contract.py)

**Current state (2026-02-13):** Phase 1 and Phase 2 are substantially complete. E2E-BugFix and E2E-CLI are runnable via `scripts/e2e/run_scenario.py`. External-Pilot lane (SWE-bench + Terminal-Bench via Harbor) has runner, manifests, and runbook. Harbor CLI installed at `K:\tools\harbor-venv\Scripts\harbor.exe` (v0.1.44).

**What remains:** Phase 3+ scenarios, real external pilot execution (Gate B), CI integration.

---

## Phase 1: Foundation (Wire Existing Infrastructure) — COMPLETE

**Goal:** Make `run_scenario.py` actually work by connecting it to the existing benchmark engine. Land runnable E2E-BugFix and E2E-CLI as the **immediate priority** — these plus E2E-Calc form the PR Core baseline.

**Status:** Complete. `scripts/e2e/run_scenario.py` dispatches to scenario manifests. `scripts/run_e2e_benchmark.ps1` supports `-Scenario` parameter for non-calculator scenarios.

### 1.1 Extract Shared Benchmark Core
**File:** `scripts/e2e/benchmark_core.py` (new)

Extract from `run_calculator_benchmark.py`:
- `create_sandbox()`, `clean_old_sandboxes()`
- `SandboxProcessTracker`
- `BenchmarkLogger`
- `BenchmarkVerdict`, `classify_result()`, `classify_result_strict()`
- `check_budgets()`
- `verify_artifacts()`
- `analyze_trace()`
- `_benchmark_run_command()` (the Windows-safe process handler)
- Agent initialization: config loading, registry setup, approval manager

Keep `run_calculator_benchmark.py` working by having it import from `benchmark_core.py`.

### 1.2 Implement Generic Scenario Runner
**File:** `scripts/e2e/run_scenario.py` (replace stub)

Using the shared core:
1. Read manifest → extract prompt, follow_ups, budgets, acceptance_checks
2. Create sandbox (copy `seed_fixture` if specified)
3. Initialize AgentLoop with manifest.prompt
4. Run agent with follow-up turns from manifest.follow_ups
5. Execute acceptance checks via direct subprocess
6. Call scenario-specific scoring function
7. Classify verdict using manifest.min_score / strict_min_score
8. Generate report and save artifacts

### 1.3 Enhance ScenarioManifest
**File:** `scripts/e2e/scenario_contract.py`

Add fields per Codex Entry 228 guidance:
- `seed_fixture: Path | None` — path to seed project directory (rename from `seed_project` for clarity)
- `setup_commands: list[str]` — commands to run before agent starts (e.g., `npm install`)
- `acceptance_timeout_s: int = 120` — timeout for acceptance checks
- `required_artifacts: list[str]` — files that must exist after agent finishes
- `nondeterminism_policy: str = "retry"` — how to handle flaky results
- `scoring_function: str | None` — dotted path to scoring function (e.g., `tests.benchmark.test_bugfix_scoring.score_bugfix_project`)

**Operational config fields** (per scoring-framework.md suite config schema):
- `suite_type: str = "regression"` — `"regression" | "capability" | "stress"`
- `grader_mix: dict` — `{"primary": "deterministic", "secondary": "heuristic", "tertiary": "llm_judge"}`
- `grader_defaults: dict` — per-lane grader activation (`{"pr": ["deterministic"], ...}`)
- `sampling_policy: str = "pr_required"` — `"pr_required" | "nightly" | "weekly_external"`
- `token_cap: int = 8000` — max tokens per run
- `tool_call_cap: int = 50` — max tool calls per run
- `time_cap_s: int = 300` — max wall-time per run

**Naming note:** The field is `seed_fixture` (not `seed_project`) throughout all docs and code. Update existing `scenario_contract.py` to rename `seed_project` → `seed_fixture`.

### 1.4 Wire Argparse
**File:** `scripts/run_calculator_benchmark.py`

Add `--scenario <id>` flag that dispatches to `run_scenario.py` for non-calculator scenarios.

---

## Phase 2: PR Core Baseline (Immediate Priority) — COMPLETE

**Goal:** Make E2E-BugFix and E2E-CLI fully runnable. Together with E2E-Calc, these 3 scenarios form the **PR Core lane** — the minimal regression baseline that runs on every pull request.

**Status:** Complete. E2E-BugFix: PASS (100/100). E2E-CLI: FAIL (10/100, model capability floor with glm-4.5-air:free — see E2E-CLI Exception Policy in runbook). Seed fixture created at `tests/benchmark/fixtures/bugfix-seed/`.

### 2.1 E2E-BugFix Seed Fixture
**Directory:** `tests/benchmark/fixtures/bugfix-seed/`

Create a small JavaScript project with:
- `package.json` (jest configured)
- `src/index.js` — module with 3 intentional bugs
- `__tests__/index.test.js` — 8 tests (5 pass, 3 fail due to bugs)

Bugs should be representative:
1. Off-by-one error in array indexing
2. Wrong comparison operator (`<` instead of `<=`)
3. Missing null check causing TypeError

### 2.2 E2E-BugFix Scoring Function
**File:** `tests/benchmark/test_bugfix_scoring.py` (new)

```python
def score_bugfix_project(project_root: Path, run_build: bool = False) -> dict:
    """Score a bugfix scenario.

    Categories:
    - tests_fixed (50): How many of the 3 failing tests now pass?
    - no_regressions (25): Do all 5 originally-passing tests still pass?
    - minimal_changes (15): How few lines were changed?
    - code_quality (10): No anti-patterns introduced?
    """
```

### 2.3 E2E-CLI Scoring Function
**File:** `tests/benchmark/test_cli_scoring.py` (new)

```python
def score_cli_tool_project(project_root: Path, run_build: bool = False) -> dict:
    """Score a CLI tool scenario.

    Categories:
    - functionality (40): Do the 3 commands work?
    - error_handling (20): Does it handle bad input gracefully?
    - testing (25): Does `npm test` pass? How many tests?
    - code_quality (15): Clean code, no anti-patterns?
    """
```

### 2.4 Update Scenario Manifests
Update `bugfix.py` and `cli_tool.py` with:
- `seed_fixture` path for bugfix
- `scoring_function` dotted path for both
- `setup_commands` (e.g., `["npm install"]` for bugfix)

---

## Phase 3: Agent-Specific Scenario Suite (Nightly Regression)

**Goal:** Implement Wave 1 from scenario-catalog.md — the 6 agent-specific scenarios that form the nightly regression suite (NOT PR Core — these are more expensive and run on schedule).

### 3.1 Scenario Infrastructure
**Directory:** `tests/benchmark/fixtures/` — seed projects for each scenario
**Directory:** `tests/benchmark/scenarios/` — scoring functions for each scenario
**File:** `scripts/e2e/scenarios/` — manifest definitions

### 3.2 Wave 1 Scenarios
1. **A1: Targeted Grep Challenge** — 50-file Python project, test tool call count
2. **B1: Python Indentation Gauntlet** — deeply nested file, test edit accuracy
3. **C1: Fix-After-Failure** — two-attempt protocol with test feedback
4. **E1: Rename Across Codebase** — 5-file rename, test multi-file coordination
5. **G1: Half-Applied Edit** — corrupted state, test recovery
6. **H1: Feature Addition Without Breaking** — P2P test preservation

### 3.3 Acceptance Check Runner
**File:** `scripts/e2e/acceptance_runner.py` (new)

Generic runner for `AcceptanceCheck` objects:
- Execute command via subprocess in sandbox
- Capture stdout/stderr
- Check exit code
- Apply timeout
- Return structured result

---

## Phase 4: Stress Testing & Advanced Dimensions

**Goal:** Add fault injection, consistency testing, and cost tracking.

### 4.1 Fault Injection Framework
**File:** `scripts/e2e/fault_injector.py` (new)

Wrap tool handlers with configurable fault injection:
- `TransientTimeout(rate=0.2)` — 20% chance of timeout
- `PartialResponse(rate=0.15)` — 15% chance of truncation
- `EmptyResponse(rate=0.1)` — 10% chance of empty return

### 4.2 Consistency Runner
**File:** `scripts/e2e/consistency_runner.py` (new)

Run a scenario k times, compute pass^k, report consistency score.

### 4.3 Cost Tracker
**File:** `scripts/e2e/cost_tracker.py` (new)

Instrument AgentLoop to count:
- Input tokens per turn
- Output tokens per turn
- Tool calls per turn
- Layer attribution (which layer resolved the task)

### 4.4 Scaffold Delta Test
**File:** `scripts/e2e/scaffold_delta.py` (new)

Run the same scenario with:
1. Full HybridCoder scaffold (4-layer)
2. Naive single-prompt scaffold (model only)
Compute and report the delta.

---

## Phase 5: Reporting & CI Integration

### 5.1 Radar Chart Report
Generate the 12-dimension radar chart in markdown (ASCII art) and JSON.

### 5.2 CI Pipeline Integration
- **PR Core lane** runs on every PR: Calc+BugFix+CLI only, replay-first, deterministic graders, `>=2/3` stochastic
- **Regression nightly lane** runs nightly: PR Core + Wave 1 scenarios, pass^3 consistency, heuristic graders added
- **Capability lane** runs nightly: broader scenarios, LLM grader sampled
- **Stress lane** runs weekly: fault injection, consistency at varying fault rates

### 5.3 Historical Tracking
Store results in `docs/qa/test-results/` with timestamps for trend analysis.

---

## Dependency Graph

```
Phase 1.1 (extract core) ─┬─> Phase 1.2 (generic runner) ─┬─> Phase 2 (BugFix + CLI)
                           │                                │
Phase 1.3 (manifest)  ─────┘                                └─> Phase 3 (Wave 1 scenarios)
                                                                     │
Phase 1.4 (argparse)  ──────────────────────────────────────────────┘
                                                                     │
                                                                     └─> Phase 4 (stress) ─> Phase 5 (CI)
```

---

## Effort Estimates

| Phase | Items | Complexity | Files Modified | Files Created |
|-------|-------|------------|----------------|---------------|
| 1 | 4 | Medium | 2 | 2 |
| 2 | 4 | Medium | 3 | 4 |
| 3 | 3 | High | 2 | 12+ |
| 4 | 4 | High | 2 | 4 |
| 5 | 3 | Medium | 1 | 3 |

---

## Verification

After each phase, run:
```bash
make test                    # All existing tests pass
make lint                    # Ruff + mypy clean
uv run python scripts/run_calculator_benchmark.py --help  # Argparse still works

# Store test artifacts per repo policy (AGENTS.md:47)
./scripts/store_test_results.sh "phase-N-description"
```

After Phase 2 (PR Core baseline):
```bash
# Run BugFix scenario
uv run python scripts/e2e/run_scenario.py --scenario E2E-BugFix

# Run CLI scenario
uv run python scripts/e2e/run_scenario.py --scenario E2E-CLI

# Store benchmark artifacts
./scripts/store_test_results.sh "phase-2-pr-core-baseline"
```

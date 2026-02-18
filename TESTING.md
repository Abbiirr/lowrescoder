# Testing & Evaluation Guide

> How to test, evaluate, and interpret results for HybridCoder.
> Last updated: 2026-02-14

---

## Quick Reference

| What | Command | Time |
|------|---------|------|
| Unit tests | `uv run pytest tests/ -v` | ~50s |
| Unit tests + coverage | `uv run pytest tests/ -v --cov=src/hybridcoder` | ~60s |
| Lint | `uv run ruff check src/ tests/` | ~5s |
| Type check | `uv run mypy src/hybridcoder/` | ~15s |
| Sprint verification | `uv run pytest tests/test_sprint_verify.py -v` | ~10s |
| Integration tests | `uv run pytest -m integration tests/integration/` | Varies |
| E2E Calculator benchmark | `uv run python scripts/run_calculator_benchmark.py` | 10-30 min |
| E2E BugFix scenario | `uv run python scripts/e2e/run_scenario.py E2E-BugFix` | 5-15 min |
| E2E CLI scenario | `uv run python scripts/e2e/run_scenario.py E2E-CLI` | 5-20 min |
| List all E2E scenarios | `uv run python scripts/e2e/run_scenario.py --list` | Instant |
| External pilot (SWE-bench) | `uv run python scripts/e2e/external/run_external_pilot.py --agent claude-code --suite swebench` | Varies |
| External pilot (Terminal-Bench) | `uv run python scripts/e2e/external/run_external_pilot.py --agent claude-code --suite terminalbench` | Varies |

---

## 1. Unit Tests

**What they test:** Core functionality — agent loop, tools, config, TUI, LLM providers, session store, approval system, CLI commands, types.

**How to run:**
```bash
uv run pytest tests/ -v
```

**What the results mean:**
- **1015+ passed** = everything works, safe to make changes
- **Any failures** = something is broken, fix before continuing
- **~7 skipped** = integration tests that self-skip when external services/models are unavailable

**Important: Environment Setup**

All dependencies (including tree-sitter) MUST be installed for a valid test run. tree-sitter is a core dependency, not optional:

```bash
# Full dev setup (required for valid test results):
uv pip install -e ".[dev]"

# Verify tree-sitter is importable:
uv run python -c "import tree_sitter; import tree_sitter_python; print('OK')"
```

If tree-sitter tests fail with `ImportError`, your environment is broken — do NOT count those as "expected failures." Fix the env first.

Integration tests require `.env` with `OPENROUTER_API_KEY` and Ollama running locally. They self-skip when requirements are not met.

**Where tests live:**

| Directory | What | Count |
|-----------|------|-------|
| `tests/unit/` | Core features (29 files) | ~600+ tests |
| `tests/benchmark/` | Performance + quality rubrics (6 files) | ~20 tests |
| `tests/integration/` | External services (3 files) | Self-skip when unavailable |
| `tests/test_sprint_verify.py` | Sprint exit criteria | Phase-specific |

**When to run:** After every code change. Non-negotiable.

---

## 2. Linting & Type Checking

**Ruff (linter/formatter):**
```bash
uv run ruff check src/ tests/      # Check for issues
uv run ruff format src/ tests/      # Auto-format
```

**Mypy (type checker):**
```bash
uv run mypy src/hybridcoder/
```

**What the results mean:**
- **0 errors** = clean
- **Known baseline issues:** ~30 ruff warnings, 2 mypy errors in `src/hybridcoder/backend/server.py` — these are pre-existing and tracked

**When to run:** Before any review request or PR. Use `make lint` as a shortcut.

---

## 3. Integration Tests

**What they test:** Real connections to LLM providers (Ollama, OpenRouter).

**How to run:**
```bash
# Requires Ollama running locally
uv run pytest -m integration tests/integration/test_ollama.py

# Requires OPENROUTER_API_KEY in .env
uv run pytest -m integration tests/integration/test_openrouter.py
```

**What the results mean:**
- These test actual LLM API calls — streaming, tool calling, JSON output
- Failures usually mean the service is down or misconfigured, not a code bug
- Skipped by default because they need running services and cost tokens

---

## 4. Sprint Verification Tests

**What they test:** Exit criteria for each sprint/phase milestone.

```bash
uv run pytest tests/test_sprint_verify.py -v
```

**What the results mean:**
- Each test maps to a specific sprint exit criterion
- Passing = the sprint's deliverables are working
- Currently covers Sprints 1-3 + Sprint 4A (Phase 4 active)

---

## 5. E2E Benchmarks (Evaluations)

E2E benchmarks drive the HybridCoder agent to complete real tasks autonomously, then score the output. These are **evaluations**, not unit tests — they measure agent capability, not code correctness.

### How It Works

1. **Sandbox** — A fresh timestamped directory is created in `sandboxes/`
2. **Agent** — The `AgentLoop` runs with auto-approval (no human in the loop)
3. **Acceptance Checks** — Deterministic commands (e.g., `npm test`) verify the output
4. **Scoring** — A rubric scores the result (0-100)
5. **Verdict** — PASS, FAIL, or INFRA_FAIL

### Verdicts Explained

| Verdict | Exit Code | What It Means | Action |
|---------|-----------|---------------|--------|
| **PASS** | 0 | Agent completed the task, acceptance checks pass, score above threshold | Good — the agent works |
| **FAIL** | 1 | Agent didn't meet requirements — tests fail, score too low, or missing files | Investigate — is the prompt bad? Is the model weak? Is there a tool bug? |
| **INFRA_FAIL** | 2 | Infrastructure problem — API errors, rate limits, timeouts | Not a regression — retry with different config or model |

### 5.1 Calculator Benchmark (E2E-Calculator)

The original and most comprehensive benchmark. Tests whether the agent can build a full React web app from scratch.

```bash
# Standard run
uv run python scripts/run_calculator_benchmark.py

# PowerShell wrapper
.\scripts\run_e2e_benchmark.ps1

# Multi-run (aggregated stats)
uv run python scripts/run_calculator_benchmark.py --runs 3

# Re-score an existing sandbox (no LLM tokens spent)
uv run python scripts/run_calculator_benchmark.py --replay sandboxes/bench_20260212_203313

# Strict mode (higher thresholds)
uv run python scripts/run_calculator_benchmark.py --strict

# Flake triage (reruns on failure to classify deterministic vs flaky)
uv run python scripts/run_calculator_benchmark.py --flake-triage
```

**Scoring rubric (100 points):**

| Category | Points | What It Checks |
|----------|--------|---------------|
| Scaffold | 15 | package.json, App/main files, dependencies, page files, nav/layout |
| Regular Calculator | 10 | Basic operations, clear/backspace, error handling |
| Scientific Calculator | 15 | mathjs, trig, log/sqrt/factorial, degree/radian |
| Currency Converter | 15 | Frankfurter API, fetch/loading/error, swap, caching |
| Unit Converter | 10 | Categories, units, from/to, kelvin |
| Code Quality | 10 | Hooks directory, constants, tests, no TODO/FIXME |
| UI Quality | 25 | Dark theme, grid layout, accent colors, rounded/shadow, large display |

**Pass criteria:** Score >= 30 (normal), >= 60 (strict). npm build must succeed.

### 5.2 BugFix Scenario (E2E-BugFix)

Tests whether the agent can diagnose and fix bugs in an existing project without breaking working code.

```bash
# Direct Python run
uv run python scripts/e2e/run_scenario.py E2E-BugFix

# PowerShell wrapper
.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-BugFix
```

**How it works:**
- A seed project (`tests/benchmark/fixtures/bugfix-seed/`) is copied into the sandbox
- The project has 3 intentional bugs in `src/index.js`: `capitalize()` crashes on empty string, `sumArray()` starts at 1 instead of 0, `findMax()` skips index 1 (off-by-one)
- 8 tests: 3 fail (one per bug), 5 pass (correct functions `reverseString`, `isEven`, plus `capitalize` with non-empty input)
- Agent must fix the source code without modifying tests

**Acceptance check:** `npm test` — all 8 tests must pass.

**Budget:** 600s wall time, 50 tool calls, 3 turns.

### 5.3 CLI Tool Scenario (E2E-CLI)

Tests whether the agent can build a CLI tool from scratch with proper structure.

```bash
# Direct Python run
uv run python scripts/e2e/run_scenario.py E2E-CLI

# PowerShell wrapper
.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-CLI
```

**How it works:**
- No seed project — agent creates everything from scratch
- Must build `textool`: a Node.js CLI with `count`, `search`, `stats` commands
- Must have arg parsing (commander), config support, tests, help/version

**Acceptance checks:** `npm test` passes, `node index.js --help` works, `node index.js --version` works.

**Budget:** 900s wall time, 75 tool calls, 4 turns.

### 5.4 Generic Scoring

For BugFix and CLI scenarios, the default scoring formula is:
- **80%** from acceptance check pass rate (did the checks pass?)
- **20%** from required file existence (are the expected files there?)

This is appropriate for PR Core where checks are binary. Custom scoring functions can be plugged in via the manifest's `scoring_function` field.

### 5.5 External Benchmarks (SWE-bench / Terminal-Bench)

External benchmarks run published third-party task suites via Harbor (Docker-based harness) to measure agent quality on unseen tasks.

**Prerequisites:** Docker, Harbor CLI, API keys. See `docs/plan/agentic-benchmarks/external-benchmark-runbook.md` for full setup checklist.

```bash
# SWE-bench pilot (25 tasks) with codex
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent codex --suite swebench --model gpt-4o

# Terminal-Bench pilot (10 tasks) with claude-code
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent claude-code --suite terminalbench --model claude-sonnet-4-5-20250929

# Dry run (validates setup, skips actual Harbor invocation)
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent codex --suite swebench --dry-run

# Parity mode (3 runs for variance estimation)
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent claude-code --suite swebench --parity-runs 3

# Show all options
uv run python scripts/e2e/external/run_external_pilot.py --help
```

**Cadence:** Per-PR = none. Weekly = pilot subsets. Release = larger subsets.

**Budget caps:** 600s/task SWE-bench, 900s/task Terminal-Bench, 50K tokens/task.

**Artifacts:** Saved under `docs/qa/test-results/<timestamp>-external-pilot-<suite>-<agent>/` with `config.json`, `summary.json`, `summary.md`, and per-task results.

---

## 6. Understanding Benchmark Output

### Artifacts Generated

Each benchmark run saves to two places:

```
sandboxes/bench_<timestamp>/           # The generated project + logs
docs/qa/test-results/<timestamp>-*.md  # Human-readable report
docs/qa/test-results/<timestamp>-*.json # Machine-readable results
```

### Reading a Report

A typical report includes:
- **Verdict** — PASS/FAIL/INFRA_FAIL
- **Score** — e.g., 82/100
- **Acceptance Checks** — table of which checks passed/failed
- **Budgets** — did the agent stay within time/tool/turn limits?
- **Agent Execution** — total tool calls, duration, turns used
- **Verdict Reasons** — if FAIL, exactly why (which check failed, score too low)

### Budget Enforcement

Each scenario has hard limits enforced during execution:

| Budget | Calculator | BugFix | CLI |
|--------|-----------|--------|-----|
| Wall time | 1800s | 600s | 900s |
| Tool calls | 100 | 50 | 75 |
| Turns | 5 | 3 | 4 |

If the agent exceeds any budget, execution stops early. This prevents runaway token usage.

---

## 7. Adding a New E2E Scenario

1. Create `scripts/e2e/scenarios/<name>.py` with a `MANIFEST` (type `ScenarioManifest`)
2. Define: `scenario_id`, `prompt`, `follow_ups`, `acceptance_checks`, `budgets`
3. Optionally add a seed fixture directory under `scripts/e2e/fixtures/<name>/`
4. Register it in `scripts/e2e/run_scenario.py`'s `SCENARIO_REGISTRY`
5. Run: `uv run python scripts/e2e/run_scenario.py <YOUR-SCENARIO-ID>`

The manifest contract is defined in `scripts/e2e/scenario_contract.py`.

---

## 8. Storing Results

Use the storage wrapper to persist test output:
```bash
./scripts/store_test_results.sh <label> -- <command>
```

All stored artifacts live in `docs/qa/test-results/`. Naming convention:
- `<timestamp>-<label>.md` — summary
- `<timestamp>-<label>.log` — raw output
- `<timestamp>-<label>.json` — structured data

---

## 9. CI/CD Integration

| Check | Exit Code | CI Gate |
|-------|-----------|---------|
| `uv run pytest tests/ -v` | 0 = pass | Required |
| `uv run ruff check src/ tests/` | 0 = clean | Required |
| `uv run python scripts/e2e/run_scenario.py E2E-BugFix` | 0=PASS, 1=FAIL, 2=INFRA | Regression lane |
| `uv run python scripts/e2e/run_scenario.py E2E-CLI` | 0=PASS, 1=FAIL, 2=INFRA | Regression lane |
| `uv run python scripts/run_calculator_benchmark.py` | 0=PASS, 1=FAIL, 2=INFRA | Capability lane |

**Regression lane** (BugFix, CLI): Deterministic, CI-gatable. Failures indicate real regressions.
**Capability lane** (Calculator): Exploratory, model-dependent. Failures may be model quality, not code bugs.

---

## 10. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `INFRA_FAIL` verdict | API errors, rate limits | Check `.env` config, try different model |
| `npm test` timeout | Node process hung on Windows | Kill stale `node.exe` processes |
| Sandbox locked | Stale processes from prior run | `taskkill /F /IM node.exe` on Windows |
| Low score but checks pass | Model generated working but ugly code | Expected for smaller models — score reflects quality, not just correctness |
| Tests deselected | Integration tests skipped | Normal — they need external services |

---

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/run_calculator_benchmark.py` | Calculator benchmark engine (1,888 lines) |
| `scripts/e2e/run_scenario.py` | Generic scenario runner (BugFix, CLI) |
| `scripts/e2e/scenario_contract.py` | Scenario manifest dataclass |
| `scripts/e2e/scoring.py` | Acceptance check runner + scoring |
| `scripts/e2e/scenarios/bugfix.py` | E2E-BugFix manifest |
| `scripts/e2e/scenarios/cli_tool.py` | E2E-CLI manifest |
| `tests/benchmark/fixtures/bugfix-seed/` | Seed project with 3 bugs (8 tests) |
| `scripts/e2e/external/run_external_pilot.py` | External benchmark pilot runner (SWE-bench/Terminal-Bench) |
| `scripts/e2e/external/swebench-pilot-subset.json` | SWE-bench pilot: 25 task IDs |
| `scripts/e2e/external/terminalbench-pilot-subset.json` | Terminal-Bench pilot: 10 task IDs |
| `scripts/run_e2e_benchmark.ps1` | PowerShell wrapper for all E2E scenarios |
| `docs/plan/agentic-benchmarks/external-benchmark-runbook.md` | External benchmark setup + rerun instructions |
| `tests/benchmark/test_project_creation.py` | Calculator scoring rubric |
| `docs/qa/test-results/` | Stored benchmark reports |
| `sandboxes/` | Benchmark sandbox outputs |

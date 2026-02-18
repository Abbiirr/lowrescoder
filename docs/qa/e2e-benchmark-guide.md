# E2E Benchmark Guide

Last updated: 2026-02-13

## What Is This?

An end-to-end benchmark that tests whether AutoCode's AI agent can **autonomously create a complete, working React application from scratch** with zero human intervention. It measures real-world capability: multi-file coordination, architecture decisions, dependency management, code correctness, and UI quality.

## Quick Start

```powershell
# Run the benchmark (uses .env config)
.\scripts\run_e2e_benchmark.ps1

# With custom minimum score
.\scripts\run_e2e_benchmark.ps1 -MinScore 50

# Direct Python run
uv run python scripts/run_calculator_benchmark.py
```

**Prerequisites:** `.env` must have valid LLM config. Node.js and npm must be installed.

## Architecture

Three components work together:

### 1. `scripts/run_calculator_benchmark.py` — Benchmark Engine

Core Python script with 6 phases:

| Phase | What It Does |
|-------|-------------|
| **A** | Reads `.env`, validates LLM config (provider, key, model). Exits if missing. |
| **B** | Creates timestamped sandbox: `sandboxes/bench_<YYYYMMDD_HHMMSS>/` |
| **C** | Drives `AgentLoop` with benchmark prompt, auto-approves all tools, MAX_ITERATIONS=50 |
| **D** | Runs `npm install` + `npm run build` (300s timeout each) |
| **E** | Scores project using 100-point rubric |
| **F** | Saves markdown report + JSON + event log |

Key features:
- No hardcoded defaults -- everything from `.env`
- Custom `run_command` handler with Windows process-tree kill (`taskkill /F /T /PID`)
- `find_project_root()` handles models that nest files in subdirectories
- Up to 2 follow-up turns if agent hits iteration limit

### 2. `scripts/run_e2e_benchmark.ps1` — PowerShell Wrapper

Convenience script for CI/CD:
- Cleans old sandboxes, runs benchmarks, parses results
- `-MinScore` parameter (default 30) -- exits 0 on pass, 1 on fail
- `-Scenario` parameter (default `calculator`) -- dispatches to `scripts/e2e/run_scenario.py` for non-calculator scenarios

### 3. `tests/benchmark/test_project_creation.py` — Scoring Rubric

100-point rubric across 7 categories:

| Category | Points | What It Checks |
|----------|--------|---------------|
| **Scaffold** | 15 | package.json, App/main files, dependencies, page files, nav/layout |
| **Regular Calculator** | 10 | Basic operations (+,-,*,/), clear/backspace, error handling |
| **Scientific Calculator** | 15 | mathjs integration, trig functions, log/sqrt/factorial, degree/radian |
| **Currency Converter** | 15 | Frankfurter API, fetch/loading/error, currency codes, swap, caching |
| **Unit Converter** | 10 | Categories (length/weight/temp/volume/speed), units, from/to, kelvin |
| **Code Quality** | 10 | Hooks directory, constants, tests, no TODO/FIXME |
| **UI Quality** | 25 | Dark theme, grid layout, accent colors, rounded/shadow, large display, hover/active, dropdowns |

### The Benchmark Prompt

The agent receives a detailed prompt requesting:
- React web app with landing page + 4 calculator pages
- Vite, React Router v6, Tailwind CSS, mathjs, big.js
- Explicit UI requirements: dark theme, grid button layout, color-coded operators, large display, sidebar/tab navigation, styled dropdowns, hover/active states, rounded corners, shadows

### UI Requirements (reference images in `docs/qa/e2e-tests/calculator-app/`)

The scoring rubric checks for these Tailwind CSS patterns:
- **Dark theme (5 pts):** `bg-gray-800`/`bg-gray-900` + `text-white`/`text-gray-100`
- **Grid layout (5 pts):** `grid-cols-4` + `gap-` classes
- **Accent colors (4 pts):** `bg-orange-*`, `bg-indigo-*`, `bg-blue-*` etc. for operators
- **Rounded + shadows (3 pts):** `rounded-xl`/`rounded-lg` + `shadow-lg`
- **Large display (3 pts):** `text-4xl`/`text-5xl` + `font-mono`/`font-bold`
- **Interactive feedback (3 pts):** `hover:` + `active:`/`transition`
- **Dropdown styling (2 pts):** `<select` elements for converters

## Output Artifacts

Each run produces:

```
sandboxes/bench_<timestamp>/                              # Generated React project
sandboxes/bench_<timestamp>/.autocode-benchmark.json   # Machine-readable results
sandboxes/bench_<timestamp>/.benchmark-sessions.db        # Session data
sandboxes/bench_<timestamp>/.benchmark-events.jsonl       # Event log
docs/qa/test-results/<timestamp>-e2e-react-calculator.md  # Human-readable report
docs/qa/test-results/<timestamp>-e2e-react-calculator.log # Event log copy
```

## Historical Results

| Run | Model | Score | npm Install | npm Build | Tool Calls | Notes |
|-----|-------|-------|-------------|-----------|------------|-------|
| 5 | glm-4.5-air:free | 82/100 | PASS | PASS | 32 | Clean run, ~15 min |
| 6 | glm-4.5-air:free | 61/100 | PASS | FAIL | 19 | Free model rate limit |

Note: Scores above are from the pre-UI-rubric version (max UI was 0). New runs will score against the updated 7-category rubric.

## Known Limitations

1. **`run_command` has no `cwd` parameter** -- workaround: `os.chdir(sandbox)` before agent loop
2. **Windows process tree kill not in core** -- only the benchmark has the hardened handler
3. **Models prefer shell for file creation** -- smaller models use `echo`/`cat` instead of `write_file`
4. **No dependency detection** -- missing `package.json` deps only caught by build failure
5. **No test isolation on Windows** -- stale node processes can lock sandbox files

## CLI Options

```powershell
# Calculator (default)
.\scripts\run_e2e_benchmark.ps1
.\scripts\run_e2e_benchmark.ps1 -Strict
.\scripts\run_e2e_benchmark.ps1 -Runs 3
.\scripts\run_e2e_benchmark.ps1 -Replay .\sandboxes\bench_20260212_203313
.\scripts\run_e2e_benchmark.ps1 -Replay .\sandboxes\bench_20260212_203313 -ScoreOnly

# BugFix scenario
.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-BugFix

# CLI scenario
.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-CLI

# Direct Python with full options
uv run python scripts/run_calculator_benchmark.py --help
uv run python scripts/run_calculator_benchmark.py --strict --min-score 50
uv run python scripts/run_calculator_benchmark.py --runs 3
uv run python scripts/run_calculator_benchmark.py --replay sandboxes/bench_20260212_203313
uv run python scripts/run_calculator_benchmark.py --matrix benchmark-matrix.json
uv run python scripts/run_calculator_benchmark.py --flake-triage

# External benchmarks (requires Docker + Harbor)
uv run python scripts/e2e/external/run_external_pilot.py --agent codex --suite swebench
uv run python scripts/e2e/external/run_external_pilot.py --agent claude-code --suite terminalbench
uv run python scripts/e2e/external/run_external_pilot.py --help
```

## Verdict System

| Verdict | Exit Code | Meaning |
|---------|-----------|---------|
| `PASS` | 0 | Score above threshold, build passes |
| `FAIL` | 1 | Product regression (low score, build failure, anti-patterns) |
| `INFRA_FAIL` | 2 | Infrastructure issue (API errors, rate limits) — not a regression |

In **strict mode**, additional checks: score >= 60, build required, no critical anti-patterns (`eval`, `dangerouslySetInnerHTML`), budget enforcement.

## Multi-Scenario Portfolio

The benchmark now supports multiple E2E scenarios via `scripts/e2e/`:

| Scenario ID | Type | Language | Description |
|-------------|------|----------|-------------|
| `E2E-Calculator` | Capability | JS/React | Full React calculator app (existing) |
| `E2E-BugFix` | Regression | JS | Fix failing tests in seeded broken project |
| `E2E-CLI` | Regression | JS | Build CLI tool with arg parsing and tests |
| External-Pilot (SWE-bench) | Capability | Python | 25 tasks from SWE-bench Verified via Harbor |
| External-Pilot (Terminal-Bench) | Capability | Shell | 10 tasks from Terminal-Bench via Harbor |

Each scenario implements the `ScenarioManifest` contract defined in `scripts/e2e/scenario_contract.py`.

### Running Scenarios

```bash
# List all available local scenarios
uv run python scripts/e2e/run_scenario.py --list

# Run a specific local scenario (Python)
uv run python scripts/e2e/run_scenario.py E2E-BugFix
uv run python scripts/e2e/run_scenario.py E2E-CLI

# Run via PowerShell wrapper
.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-BugFix
.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-CLI

# Run external pilot (requires Docker + Harbor CLI)
uv run python scripts/e2e/external/run_external_pilot.py --agent codex --suite swebench
uv run python scripts/e2e/external/run_external_pilot.py --agent claude-code --suite terminalbench
uv run python scripts/e2e/external/run_external_pilot.py --dry-run --agent codex --suite swebench
```

Exit codes: 0=PASS, 1=FAIL, 2=INFRA_FAIL.

See `TESTING.md` for the full testing & evaluation guide, or `docs/plan/agentic-benchmarks/external-benchmark-runbook.md` for external benchmark setup.

### Adding a New Scenario

1. Create `scripts/e2e/scenarios/<name>.py` with `SCENARIO_ID` and `MANIFEST`
2. Define prompt, acceptance checks, scoring categories, and budgets
3. Optionally add a seed fixture under `scripts/e2e/fixtures/<name>/`
4. Register in `scripts/e2e/run_scenario.py`'s `SCENARIO_REGISTRY`
5. Tag as `regression-lane` (deterministic, CI-gatable) or `capability-lane` (exploratory)

## Adding New E2E Benchmarks

The framework is designed for reuse. To add a new benchmark:

1. Write a new prompt describing the target application
2. Write a new `score_*()` function in `tests/benchmark/`
3. Reuse the same infrastructure: sandbox creation, auto-approval, npm validation, report generation
4. Store UI reference images in `docs/qa/e2e-tests/<benchmark-name>/`

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/run_calculator_benchmark.py` | Core benchmark engine |
| `scripts/run_e2e_benchmark.ps1` | PowerShell wrapper (CI/CD ready) |
| `tests/benchmark/test_project_creation.py` | Scoring rubric |
| `tests/benchmark/golden_vectors.py` | Golden test vectors (data-only, deferred) |
| `tests/benchmark/metamorphic_stubs.py` | Metamorphic invariants (data-only, deferred) |
| `scripts/e2e/scenario_contract.py` | Scenario manifest contract |
| `scripts/e2e/run_scenario.py` | Generic scenario runner |
| `scripts/e2e/scenarios/bugfix.py` | E2E-BugFix scenario |
| `scripts/e2e/scenarios/cli_tool.py` | E2E-CLI scenario |
| `scripts/e2e/scoring.py` | Acceptance check runner + scoring |
| `tests/benchmark/fixtures/bugfix-seed/` | BugFix seed project (3 bugs, 8 tests) |
| `scripts/e2e/external/run_external_pilot.py` | External benchmark pilot runner |
| `scripts/e2e/external/swebench-pilot-subset.json` | SWE-bench pilot: 25 task IDs |
| `scripts/e2e/external/terminalbench-pilot-subset.json` | Terminal-Bench pilot: 10 task IDs |
| `docs/plan/agentic-benchmarks/external-benchmark-runbook.md` | External benchmark runbook |
| `benchmark-matrix.json` | Multi-model matrix config |
| `docs/qa/e2e-tests/calculator-app/` | UI reference images |
| `docs/qa/test-results/` | Stored benchmark reports |
| `sandboxes/` | Benchmark sandbox outputs |

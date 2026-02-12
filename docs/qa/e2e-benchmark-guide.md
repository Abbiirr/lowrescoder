# E2E Benchmark Guide

Last updated: 2026-02-12

## What Is This?

An end-to-end benchmark that tests whether HybridCoder's AI agent can **autonomously create a complete, working React application from scratch** with zero human intervention. It measures real-world capability: multi-file coordination, architecture decisions, dependency management, code correctness, and UI quality.

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
- Cleans old sandboxes, runs the Python benchmark, parses JSON results
- `-MinScore` parameter (default 30) -- exits 0 on pass, 1 on fail

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
sandboxes/bench_<timestamp>/.hybridcoder-benchmark.json   # Machine-readable results
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
| `docs/qa/e2e-tests/calculator-app/` | UI reference images |
| `docs/qa/test-results/` | Stored benchmark reports |
| `sandboxes/` | Benchmark sandbox outputs |

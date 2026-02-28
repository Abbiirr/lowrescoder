# External Benchmark Runbook: SWE-bench + Terminal-Bench Pilot

Last verified: 2026-02-28

## Overview

The **External-Pilot** lane evaluates AutoCode's agent quality against published, third-party benchmark suites using an external harness (Harbor). This complements the internal PR Core lane (E2E-Calc, E2E-BugFix, E2E-CLI) by measuring performance on tasks the agent has never seen during development.

---

## Implementation Status

### Implemented (verified 2026-02-13)

- Runner script: `scripts/e2e/external/run_external_pilot.py`
  - CLI flags: `--agent`, `--suite`, `--model`, `--parity-runs`, `--dry-run`
  - Prerequisite checks: Docker, Harbor CLI, API keys
  - Artifact pipeline: config.json, summary.json, summary.md, per-task/*.json
  - Dry-run mode for pipeline validation without Harbor invocation
  - Harbor CLI auto-discovery (PATH, `HARBOR_EXE` env var, `K:\tools\harbor-venv`)
- Pilot subset manifests:
  - `scripts/e2e/external/swebench-pilot-subset.json` (25 tasks, 5 repos x 5 tiers)
  - `scripts/e2e/external/terminalbench-pilot-subset.json` (10 tasks, real Terminal-Bench 2.0 IDs)
- Harbor CLI installed: v0.1.44 at `K:\tools\harbor-venv\Scripts\harbor.exe`
- Scoring framework lane: External-Pilot row in `scoring-framework.md`

### Blocked (requires action)

- **Real pilot run**: Needs first end-to-end Harbor execution with Docker containers
  - Next command: `uv run python scripts/e2e/external/run_external_pilot.py --agent codex --suite terminalbench --dry-run`
  - Blocker: Harbor job output format parsing needs validation against real output
- **Dataset download**: SWE-bench Verified (500 tasks) and Terminal-Bench 2.0 (89 tasks) not yet cached locally
  - Next command: `K:\tools\harbor-venv\Scripts\harbor.exe datasets download terminal-bench@2.0`
- **API budget approval**: Weekly pilot runs consume ~1.75M tokens; needs budget sign-off

### Not Yet Implemented

- Per-task log capture (Harbor writes logs to job directory; runner does not yet copy them to artifact directory)
- Real smoke test evidence (at least 1 task per suite passing end-to-end)
- Parity variance analysis with real runs
- CI integration for scheduled weekly pilot runs

---

## Lane Definition

| Property | Value |
|----------|-------|
| Lane name | `External-Pilot` |
| Suite type | `capability` |
| Graders active | deterministic (pass/fail from harness) |
| Sampling | weekly (pilot), release (full) |
| Repetition | 1 run default; parity mode = 3 runs |
| Agents compared | `codex`, `claude-code` |
| Harness | [Harbor](https://github.com/laude-institute/harbor) v0.1.44+ (Docker-based) |

---

## Gate Levels (S4)

### Gate A: Wiring (pipeline validation)

Proves the artifact pipeline works end-to-end without real task execution.

- `--dry-run` produces artifact directories with INFRA_FAIL verdicts
- `--help` returns valid argparse output
- config.json, summary.json, summary.md, per-task/*.json all generated
- Harbor CLI found and version reported

### Gate B: Performance (real execution)

Proves at least one real task per suite runs and produces a meaningful verdict.

- At least 1 SWE-bench task produces PASS or FAIL (not INFRA_FAIL)
- At least 1 Terminal-Bench task produces PASS or FAIL (not INFRA_FAIL)
- Artifact directory contains Harbor job output alongside our summary

---

## SWE-bench Verified Pilot

### Subset Specification

- **Size:** 25 tasks (from SWE-bench Verified's 500 tasks)
- **Harbor dataset:** `swebench-verified@1.0`
- **Stratification:** 5 repos x 5 difficulty tiers
- **Selection criteria:**
  - Representative repos: django, sympy, scikit-learn, flask, requests
  - Difficulty tiers: trivial (1-line fix), easy, medium, hard, complex (multi-file)
  - Each (repo, difficulty) pair contributes 1 task
  - No tasks requiring GPU or >8GB RAM to reproduce
  - Test suites must complete in <120s per task

### Budget Caps

| Resource | Limit |
|----------|-------|
| Wall time per task | 600s |
| Token cap per task | 50,000 |
| Max tool calls per task | 100 |
| Total pilot budget | 25 tasks x 50K = 1.25M tokens max |

### Manifest File

`scripts/e2e/external/swebench-pilot-subset.json`

Contains 25 task IDs with metadata (repo, difficulty, estimated complexity).

---

## Terminal-Bench Pilot

### Subset Specification

- **Size:** 10 tasks (from Terminal-Bench 2.0's 89 tasks)
- **Harbor dataset:** `terminal-bench@2.0`
- **Category diversity:** scripting, version control, permissions, data processing, algorithmic, networking, file operations, text processing, package management
- **Selection criteria:**
  - Tasks sourced from published Terminal-Bench 2.0 dataset (kebab-case IDs)
  - Diverse difficulty range (hello-world through blind-maze-explorer)
  - Deterministic grading via Harbor verifier
  - Each task completable within budget caps

### Task IDs (verified from terminal-bench-core)

`hello-world`, `fix-git`, `fix-permissions`, `csv-to-parquet`, `chess-best-move`, `fibonacci-server`, `extract-safely`, `count-dataset-tokens`, `blind-maze-explorer-5x5`, `conda-env-conflict-resolution`

### Budget Caps

| Resource | Limit |
|----------|-------|
| Wall time per task | 900s |
| Token cap per task | 50,000 |
| Max tool calls per task | 100 |
| Total pilot budget | 10 tasks x 50K = 500K tokens max |

### Manifest File

`scripts/e2e/external/terminalbench-pilot-subset.json`

Contains 10 task IDs with metadata (category, description, estimated time).

---

## Cadence

| Trigger | Scope | Token budget |
|---------|-------|-------------|
| Per-PR | None (external pilot does not run on PRs) | 0 |
| Weekly | Pilot subsets (25 SWE-bench + 10 Terminal-Bench) | ~1.75M tokens |
| Release gate | Larger subset (TBD, 100+ tasks) | ~5M tokens |

---

## Artifact Schema

Each pilot run produces artifacts under `docs/qa/test-results/`:

### Directory Structure

```
docs/qa/test-results/
  YYYYMMDD-HHMMSS-external-pilot-{suite}-{agent}/
    config.json          # Run configuration
    summary.json         # Aggregate results
    summary.md           # Human-readable report
    per-task/
      {task_id}.json     # Individual task result
```

### `config.json`

```json
{
  "suite": "swebench|terminalbench",
  "agent": "codex|claude-code",
  "model": "model-id",
  "harbor_dataset": "swebench-verified@1.0",
  "subset_manifest": "scripts/e2e/external/swebench-pilot-subset.json",
  "budget": {
    "wall_time_per_task_s": 600,
    "token_cap_per_task": 50000,
    "max_tool_calls_per_task": 100
  },
  "parity_runs": 1,
  "timestamp": "ISO-8601"
}
```

### `summary.json`

```json
{
  "suite": "swebench",
  "agent": "codex",
  "model": "gpt-4o",
  "total_tasks": 25,
  "passed": 18,
  "failed": 5,
  "infra_fail": 2,
  "resolve_rate": 0.72,
  "avg_wall_time_per_task_s": 180,
  "parity_run": null,
  "timestamp": "ISO-8601"
}
```

---

## E2E-CLI Exception Policy (S3)

The `E2E-CLI` scenario is a known capability-floor test. Under the current model constraint (`z-ai/glm-4.5-air:free`), the agent cannot complete this scenario within budget. This is a valid measurement, not a scaffold bug.

**Exception clause:** If the active model is a free-tier or throttled model AND the E2E-CLI failure is due to budget exhaustion (not scaffold errors), the FAIL verdict is accepted as a **model capability finding** rather than a gate blocker. The scaffold is validated by E2E-BugFix PASS and E2E-Calculator PASS.

**Mitigation strategies (future):**
1. Increase E2E-CLI budgets for weak models (150 tool calls, 1800s)
2. Simplify E2E-CLI scenario for regression lane (fewer features)
3. Add model-specific budget tiers to scenario manifests

---

## One-Command Rerun Instructions

### Prerequisites

1. Docker installed and running (`docker info` succeeds)
2. Harbor CLI installed: `pip install harbor` (Python 3.12+)
   - Verified location: `K:\tools\harbor-venv\Scripts\harbor.exe`
   - Or set `HARBOR_EXE` env var to custom path
3. API keys configured in environment:
   - `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY` (for claude-code)
   - `OPENAI_API_KEY` (for codex, if applicable)
4. Datasets download: `harbor datasets download swebench-verified@1.0` / `terminal-bench@2.0`

### Run SWE-bench Pilot

```bash
# With codex agent
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent codex \
  --suite swebench \
  --model gpt-4o

# With claude-code agent
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent claude-code \
  --suite swebench \
  --model claude-sonnet-4-5-20250929
```

### Run Terminal-Bench Pilot

```bash
# With codex agent
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent codex \
  --suite terminalbench \
  --model gpt-4o

# With claude-code agent
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent claude-code \
  --suite terminalbench \
  --model claude-sonnet-4-5-20250929
```

### Parity Mode (Variance Estimation)

Run the same subset 3 times to measure orchestration/config variance:

```bash
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent claude-code \
  --suite swebench \
  --parity-runs 3 \
  --model claude-sonnet-4-5-20250929
```

### Dry-Run (Pipeline Validation Only)

```bash
uv run python scripts/e2e/external/run_external_pilot.py \
  --agent codex \
  --suite terminalbench \
  --dry-run
```

---

## Infrastructure Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Docker | Required | Harbor runs tasks in containers |
| Harbor CLI v0.1.44+ | Installed | `K:\tools\harbor-venv\Scripts\harbor.exe` |
| Python 3.12+ | Required | For Harbor package |
| 16GB+ RAM | Recommended | For concurrent task containers |
| API keys | Required | Per agent provider |
| Network access | Required | For API calls and dataset download |
| Disk space | 10GB+ | For datasets + container images |

---

## Unified Benchmark Runner (Recommended)

The unified benchmark runner (`scripts/benchmark_runner.py`) supersedes the Harbor-based pilot runner for local benchmarking. It provides Docker-based isolation, resumability, and exponential backoff for remote Ollama servers.

### Run All Lanes

```bash
# Set environment
export AUTOCODE_LLM_PROVIDER=ollama
export OLLAMA_HOST=http://10.112.30.10:11434
export OLLAMA_MODEL=glm-4.7-flash

# Run all lanes sequentially with resume (B7-B14)
bash scripts/run_all_benchmarks.sh

# Monitor progress
tail -50 /tmp/claude-1000/-home-bs01763-projects-ai-lowrescoder/benchmark_full_run.log
```

### Resumability

If the Ollama server crashes mid-run, simply re-run the same command. The `--resume` flag (enabled by default in the shell script) skips already-completed tasks by reading checkpoint files from `sandboxes/progress/`.

### Exponential Backoff

Temporary Ollama outages are handled by the LLM layer with exponential backoff: 5s, 10s, 20s, 40s, 80s, 160s, 300s (capped), up to 10 retries. This means a brief server restart won't kill the entire benchmark run.

---

## Operator Checklist (S6)

### First-Time Setup

- [ ] `docker run hello-world` succeeds
- [ ] `K:\tools\harbor-venv\Scripts\harbor.exe --version` returns `0.1.44` or later
- [ ] `uv run python scripts/e2e/external/run_external_pilot.py --help` shows usage
- [ ] API key is set in environment (OPENROUTER_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY)

### Gate A Validation (Wiring)

- [ ] `uv run python scripts/e2e/external/run_external_pilot.py --agent codex --suite swebench --dry-run` exits 0
- [ ] Artifact directory created: `docs/qa/test-results/*external-pilot-swebench-codex*/`
- [ ] Files present: config.json, summary.json, summary.md, per-task/ (25 files)
- [ ] `uv run python scripts/e2e/external/run_external_pilot.py --agent claude-code --suite terminalbench --dry-run` exits 0
- [ ] Artifact directory created: `docs/qa/test-results/*external-pilot-terminalbench-claude-code*/`

### Gate B Validation (Performance)

- [ ] Download datasets: `harbor datasets download swebench-verified@1.0` and `terminal-bench@2.0`
- [ ] Run 1 SWE-bench task: `harbor run -d swebench-verified@1.0 -t "django__django-11099" -a codex -m gpt-4o --n-tasks 1`
- [ ] Run 1 Terminal-Bench task: `harbor run -d terminal-bench@2.0 -t "hello-world" -a claude-code -m claude-sonnet-4-5-20250929 --n-tasks 1`
- [ ] At least one task produces PASS or FAIL (not INFRA_FAIL)
- [ ] Run full pilot for one suite and confirm artifact generation

### Expected Artifact Paths

```
# Dry-run (Gate A)
docs/qa/test-results/YYYYMMDD-HHMMSS-external-pilot-swebench-codex/
docs/qa/test-results/YYYYMMDD-HHMMSS-external-pilot-terminalbench-claude-code/

# Real run (Gate B)
docs/qa/test-results/YYYYMMDD-HHMMSS-external-pilot-swebench-codex/
  config.json
  summary.json
  summary.md
  per-task/django__django-11099.json
  per-task/django__django-11179.json
  ...
```

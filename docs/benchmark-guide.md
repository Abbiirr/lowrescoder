# Benchmark Guide

How to run AutoCode benchmarks and interpret results.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python 3.11+** | With `uv` package manager |
| **LLM Gateway** | Running at `http://localhost:4000/v1` ([docs](http://localhost:4001/docs)) |
| **Docker** | Recommended for B7/B8 (Python version isolation) |
| **Git** | For task setup and grading |

### Environment Setup

Ensure your `.env` file has:

```bash
AUTOCODE_LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:4000
OLLAMA_MODEL=coding
```

Verify the LLM Gateway is reachable:

```bash
curl http://localhost:4000/health/readiness
```

---

## Quick Start

### Run all lanes (B7-B14)

```bash
bash scripts/run_all_benchmarks.sh
```

This runs all 8 lanes sequentially with `--resume` (skips completed tasks). Halts automatically if Ollama goes down.

### Run a single lane

```bash
uv run python scripts/benchmark_runner.py \
  --agent autocode \
  --lane B7 \
  --model glm-4.7-flash
```

### Run with task limit (for testing)

```bash
uv run python scripts/benchmark_runner.py \
  --agent autocode \
  --lane B11 \
  --model glm-4.7-flash \
  --max-tasks 2
```

### Resume after interruption

```bash
uv run python scripts/benchmark_runner.py \
  --agent autocode \
  --lane B7 \
  --model glm-4.7-flash \
  --run-id <run-id> \
  --resume
```

### List available lanes

```bash
uv run python scripts/benchmark_runner.py --list-lanes
```

---

## CLI Reference

```
uv run python scripts/benchmark_runner.py [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--agent` | `autocode` | Agent: `autocode`, `codex`, `claude-code`, or `all` |
| `--lane` | *required* | Benchmark lane (B6-B14) |
| `--model` | from `.env` | Override LLM model name |
| `--max-tasks N` | `0` (all) | Limit tasks per lane (useful for testing) |
| `--resume` | off | Resume a previously started run; requires `--run-id` |
| `--run-id` | auto-generated | Explicit benchmark run identifier used for progress/locks |
| `--strict` | off | Use strict mode (higher thresholds) |
| `--list-lanes` | off | Print lane table and exit |

---

## Benchmark Lanes

| Lane | Name | Tasks | Runner | Description |
|------|------|-------|--------|-------------|
| **B6** | React Calculator | 1 | custom | Build a React app from scratch |
| **B7** | SWE-bench Verified | 5 | swebench | Real repo bug fixes in Docker containers |
| **B8** | SWE-bench Bash-Only | 5 | swebench | Same as B7 but agent can only use `run_command` + `read_file` |
| **B9-PROXY** | Terminal-Bench Equiv | 5 | swebench | Terminal/DevOps tasks (proxy fixtures) |
| **B10-PROXY** | Multilingual Equiv | 5 | swebench | Python bug-fix tasks (proxy fixtures) |
| **B11** | BaxBench | 5 | swebench | Security vulnerability fixes |
| **B12-PROXY** | SWE-Lancer Equiv | 5 | swebench | Freelance-style SWE tasks (proxy fixtures) |
| **B13-PROXY** | CodeClash Equiv | 5 | competitive | Competitive coding problems |
| **B14-PROXY** | LiveCodeBench Equiv | 5 | competitive | LeetCode-style problems |

**Budget per task:** 86,400s wall time (24hr), 50,000 tokens, 100 tool calls.

**PROXY lanes** use self-contained fixtures with local grading scripts. They are internal baselines only (no published parity claims against the original benchmarks).

Proxy fixture lanes that run in Docker can declare a lightweight `build_deps_profile` in the manifest. This skips the full SWE-bench compiler/bootstrap path unless a task explicitly needs it.

---

## How It Works

### SWE-bench runner (B7, B8, B9-B12)

1. Load manifest (`scripts/e2e/external/*.json`)
2. For each task:
   - Create sandbox directory
   - Start Docker container (if `python_version` specified) or use host
   - Clone repo at `base_commit`, apply `test_patch`
   - Run agent with task prompt
   - Grade by running `grading_command` (pytest, verify.sh, etc.)
   - Up to 3 grading retries with feedback
3. Save results to `docs/qa/test-results/`

### Competitive runner (B13, B14)

1. Copy fixture directory to sandbox
2. Run agent with problem prompt
3. Grade with `grader.py` in the fixture

### Retry & Feedback Loop

Each task gets up to **3 grading attempts**:
- After each failed attempt, the agent receives structured feedback (failing tests, error messages, source file candidates)
- If the agent produces **zero file changes** on 2 consecutive attempts, it stops early (`NO_EFFECTIVE_EDITS`)
- If the agent produces the **same diff** 3 times, it stops early (stagnation)

---

## Output & Results

### Where to find results

| Artifact | Location |
|----------|----------|
| Run log | `benchmark_run_full_*.log` (project root) |
| Result JSON | `docs/qa/test-results/{timestamp}-{lane}-{agent}.json` |
| Progress checkpoint | `sandboxes/progress/{lane}_{agent}_progress.json` |
| Task sandbox | `sandboxes/bench_{lane}_{task_id}_{timestamp}/` |
| Grading output | `sandboxes/bench_*/grading_attempt_*.txt` |

### Reading results

The result JSON contains per-task details:

```json
{
  "lane": "B7",
  "agent": "autocode",
  "aggregate": {
    "total_tasks": 5,
    "resolved_count": 2,
    "resolve_rate": 0.4,
    "infra_fails": 0
  },
  "results": [
    {
      "task_id": "django__django-10880",
      "resolved": false,
      "wall_time_s": 2255.2,
      "tool_calls": 118,
      "error": "",
      "artifacts": {
        "failure_type": "WRONG_FIX",
        "grade_attempts": [...]
      }
    }
  ]
}
```

### Failure types

| Type | Meaning |
|------|---------|
| `RESOLVED` | Task passed grading |
| `WRONG_FIX` | Agent edited files but fix was incorrect |
| `NO_EFFECTIVE_EDITS` | Agent made zero file changes across all attempts |
| `REQUEST_TIMEOUT` | Model/provider request timed out before a usable answer |
| `MODEL_OUTPUT_FAIL` | Model produced unusable structured output |
| `INFRA_FAIL` | Docker/network/setup error (not agent's fault) |

---

## Fail-Fast Mode

`run_all_benchmarks.sh` sets `BENCHMARK_NO_RETRY=1` which enables:

- **Provider pre-task health check** — the adapter performs a provider-specific health probe before each task. For LLM Gateway-backed AutoCode runs this pings `/health/readiness`; if the provider is down, the lane halts immediately (exit code 2).
- **No LLM connection retries** — instead of 10 retries with exponential backoff, fails on first connection error.
- **Shorter per-request timeout** — 5 minutes per LLM call (vs 1 hour in normal mode).
- **Lane-level halt** — if any lane exits non-zero, the shell script stops all remaining lanes.

To disable fail-fast (e.g., for unreliable networks), remove `export BENCHMARK_NO_RETRY=1` from `run_all_benchmarks.sh`.

---

## Monitoring a Running Benchmark

### Check progress

```bash
# Summary of completed lanes
grep -E "LANE.*COMPLETE|Resolved:" benchmark_run_full_*.log | tail -20

# Which task is currently running
tail -5 benchmark_run_full_*.log

# Is the process still alive
ps aux | grep benchmark_runner | grep -v grep
```

### Check per-task results as they complete

```bash
# Latest result artifacts
ls -lt docs/qa/test-results/*.json | head -5
```

### Kill and resume later

```bash
# Kill the run
pkill -f benchmark_runner

# Clean stale Docker containers
docker rm -f $(docker ps -a --filter "name=bench-" -q)

# Resume where you left off
bash scripts/run_all_benchmarks.sh   # has --resume flag built in
```

---

## Troubleshooting

### "LLM Gateway unreachable" / halted run

The LLM Gateway went down. Fix it, then re-run with the same `--run-id` and `--resume`:

```bash
# Verify the gateway is back
curl http://localhost:4000/health/readiness

# Resume
bash scripts/run_all_benchmarks.sh
```

### "NOT_EXECUTABLE" for a lane

The lane's manifest is missing required fields (e.g., `grading_command`, `setup_commands`). Check the manifest in `scripts/e2e/external/`.

### Stale Docker containers blocking new tasks

```bash
docker rm -f $(docker ps -a --filter "name=bench-" -q)
```

### Want a fresh run (no resume)

```bash
rm -f sandboxes/progress/*.json
docker rm -f $(docker ps -a --filter "name=bench-" -q)
bash scripts/run_all_benchmarks.sh
```

### Embedding model warning

```
Embedding model unavailable (jinaai/jina-embeddings-v2-base-code), falling back to BM25-only
```

This is expected if `sentence_transformers` is not installed. Search still works via BM25 keyword matching — just without vector similarity.

---

## Provider Policy

Per project policy (Entry 530):

| Provider Type | Allowed? | Examples |
|---------------|----------|----------|
| `local_free` | Yes | LLM Gateway (9 free providers), Ollama, OpenRouter free-tier |
| `subscription` | Yes | Codex CLI, Claude Code CLI |
| `paid_metered` | **No** | Any metered API billing |

The runner enforces this — `paid_metered` agents are blocked automatically.

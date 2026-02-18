# Benchmark Evaluation Criteria

> All benchmarks must PASS before Phase 5 can start.
> Each benchmark evaluates three dimensions: quality, cost, and speed.

## Evaluation Dimensions

### 1. Quality (must pass threshold)

Does AutoCode produce correct, complete output?

| Lane | Metric | Pass Threshold |
|------|--------|----------------|
| B6 React Calculator | Rubric score (0-100) | >= 60 |
| B7 SWE-bench Verified | % tasks resolved | TBD after R0 calibration |
| B8 SWE-bench Bash-Only | % tasks resolved | TBD after R0 calibration |
| B9 Terminal-Bench | % tasks completed | TBD after R0 calibration |
| B10 Multi-SWE-bench | % tasks resolved | TBD after R0 calibration |
| B11 BaxBench | % tasks passing | TBD after R0 calibration |
| B12 SWE-Lancer | % tasks resolved | TBD (access-gated) |
| B13 CodeClash | % goals achieved | TBD (access-gated) |
| B14 LiveCodeBench | % tasks passing | TBD after R0 calibration |

### 2. Cost Efficiency (tracked per run)

How many tokens/API calls does it take?

| Metric | What it measures |
|--------|-----------------|
| Total tokens (in + out) | Raw LLM cost |
| Tool calls count | Agent iteration efficiency |
| Turns used / turn budget | How quickly the agent converges |
| API errors / retries | Infrastructure reliability |
| Provider + model used | Cost per token varies by provider |

### 3. Speed (tracked per run)

How long does it take?

| Metric | What it measures |
|--------|-----------------|
| Wall time (seconds) | End-to-end user experience |
| Time per tool call | Agent responsiveness |
| Time in LLM vs tools | Where time is spent |
| Cooldown/retry time | Wasted time from API errors |

## Artifact Schema (per benchmark run)

Every run must produce a JSON artifact with:

```json
{
  "lane": "B6",
  "timestamp": "2026-02-18T18:28:20Z",
  "model": "qwen3:8b",
  "provider": "ollama",
  "quality": {
    "score": 72,
    "max_score": 100,
    "pass_threshold": 60,
    "verdict": "PASS",
    "breakdown": {}
  },
  "cost": {
    "tokens_in": 12000,
    "tokens_out": 8000,
    "tool_calls": 25,
    "turns_used": 3,
    "turns_budget": 5,
    "api_errors": 0,
    "retries": 0
  },
  "speed": {
    "wall_time_s": 180,
    "llm_time_s": 120,
    "tool_time_s": 60
  }
}
```

## How to Run

### B6 — React Calculator (from scratch)

The benchmark script uses AutoCode's AgentLoop to generate a complete React calculator project from scratch, then scores it.

```bash
# Using Ollama (local, no API cost):
uv run python scripts/run_calculator_benchmark.py

# The generated project lands in sandboxes/bench_<timestamp>/
# Copy to benchmarks dir for the external test:
# cp -r sandboxes/bench_<timestamp>/* benchmarks/B6-react-calculator/

# Then run the scoring test:
uv run pytest tests/benchmark/test_project_creation.py::test_project_creation_real_life_task_external_project -v
```

### B7-B14 — External Benchmarks

```bash
# Requires Docker + Harbor CLI for most lanes
# See docs/plan/agentic-benchmarks/external-benchmark-runbook.md

# SWE-bench (B7/B8):
uv run python scripts/e2e/external/run_external_pilot.py --agent autocode --suite swebench

# Terminal-Bench (B9):
uv run python scripts/e2e/external/run_external_pilot.py --agent autocode --suite terminalbench
```

## Provider Recommendations

| Provider | Best for | Cost |
|----------|----------|------|
| Ollama (qwen3:8b) | B6 calculator, local dev | Free (local GPU) |
| OpenRouter (paid model) | B7-B14 external benchmarks | Per-token |
| OpenRouter (free model) | Testing only | Free but rate-limited |

**Important:** Free OpenRouter models (`*:free`) are rate-limited and will cause API errors during benchmarks. Use Ollama or a paid model for reliable benchmark runs.

## Workflow

1. **R0 (Calibration):** Run each lane once to establish baseline scores
2. **Lock baselines:** Record scores in `phase5-benchmark-baselines.json`
3. **R1 (Gate run):** Run all lanes, compare against baselines
4. **Store artifacts:** Save to `docs/qa/test-results/` per Codex gate policy
5. **Review:** Codex reviews artifacts, issues APPROVE/NEEDS_WORK per lane

# Benchmark Evaluation Criteria

> All benchmarks must PASS before Phase 5 can start.
> Each benchmark evaluates three dimensions: quality, cost, and speed.
> Updated: 2026-02-19

## Evaluation Dimensions

### 1. Quality (must pass threshold)

Does AutoCode produce correct, complete output?

| Lane | Metric | Pass Threshold |
|------|--------|----------------|
| B6 React Calculator | Rubric score (0-100) + build + app runs | >= 90, build pass, app runs |
| B7 SWE-bench Verified | % tasks resolved | >= 40% |
| B8 SWE-bench Bash-Only | % tasks resolved | Pending R0 — threshold locked to `max(R0_baseline, floor)` after first calibration run |
| B9-PROXY Terminal-Bench Equivalent | % tasks completed | Pending R0 — proxy-only, threshold locked after first calibration run |
| B10-PROXY Multilingual Equivalent | % tasks resolved | Pending R0 — proxy-only (Python subset), threshold locked after first calibration run |
| B11 BaxBench | % tasks passing | Pending R0 — threshold locked to `max(R0_baseline, floor)` after first calibration run |
| B12-PROXY SWE-Lancer Equivalent | % tasks resolved | Pending R0 — threshold locked to `max(R0_baseline, floor)` after first calibration run (proxy-only) |
| B13-PROXY CodeClash Equivalent | % goals achieved | Pending R0 — threshold locked to `max(R0_baseline, floor)` after first calibration run (proxy-only) |
| B14-PROXY LiveCodeBench Equivalent | % tasks passing | Pending R0 — threshold locked to `max(R0_baseline, floor)` after first calibration run (proxy-only) |

**B6 special rule (Entry 526):** If `npm run build` fails, total score = 0.

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

## Unified Parity Harness

**Runner:** `benchmarks/benchmark_runner.py`

All agents are driven by the same harness with identical budgets and grading. Prompts differ by adapter design but grading is normalized: all agents are scored by `task.grading_command` execution, not CLI exit code.

### Known Non-Equivalences

The following adapter-level differences are inherent to agent design and do not invalidate parity claims for grading:

| Aspect | AutoCode | Codex / Claude Code |
|--------|----------|---------------------|
| Execution model | In-process AgentLoop | External CLI subprocess |
| Working directory | Resolved repo dir (for tool operations) | Sandbox root (CLI navigates internally) |
| Prompt | Multi-step workflow with grading command | Simple `Fix this issue: ...` |
| Retry loop | Harness-driven outer retry (up to 3 attempts) | Single CLI invocation |

Grading is the normalization point: all agents are scored by the same `task.grading_command` executed from the same `sandbox` directory.

### Restricted-Lane Adapter Support

Some lanes impose tool restrictions. Only adapters that can enforce the restriction at the tool-registry level are allowed to run. Non-enforceable adapters are blocked at preflight.

| Lane | Restriction | AutoCode | Codex | Claude Code |
|------|-------------|----------|-------|-------------|
| B7 | None | Supported | Supported | Supported |
| B8 | `bash-only` (`run_command`, `read_file` only) | **Supported** (enforced via `ToolRegistry.filter()`) | Blocked | Blocked |
| B9-B13, B14-PROXY | None | Supported | Supported | Supported |

When `tool_restriction=bash-only` is active, the prompt is adapted to instruct the agent to use `run_command` with shell editing commands (`sed`, `tee`) instead of `write_file`. The enforcement is recorded in `AgentResult.artifacts["enforced_policy"]`.

### Usage

```bash
# Run AutoCode on a lane
uv run python benchmarks/benchmark_runner.py --agent autocode --lane B7

# Run Codex on a lane (parity)
uv run python benchmarks/benchmark_runner.py --agent codex --lane B7

# Run Claude Code on a lane (parity)
uv run python benchmarks/benchmark_runner.py --agent claude-code --lane B7

# Run all agents (parity comparison)
uv run python benchmarks/benchmark_runner.py --agent all --lane B7

# List available lanes
uv run python benchmarks/benchmark_runner.py --list-lanes

# B6 delegates to its own runner
uv run python benchmarks/benchmark_runner.py --agent autocode --lane B6 --strict
```

### Agent Adapters

| Adapter | File | Provider Mode |
|---------|------|---------------|
| AutoCode | `scripts/adapters/autocode_adapter.py` | `local_free` (Ollama) |
| Codex | `scripts/adapters/codex_adapter.py` | `subscription` (Codex CLI) |
| Claude Code | `scripts/adapters/claude_adapter.py` | `subscription` (Claude CLI) |

## Parity Validity Contract (Entries 529-531)

For any cross-agent comparison to be valid, ALL of these must match:

| Field | Requirement |
|-------|-------------|
| `harness_version` | Same across all agents in comparison |
| `manifest_hash` | Same (SHA-256 of manifest file) |
| `budget_profile_id` | Same (wall_time + token_cap + tool_calls) |
| `comparison_validity` | `parity-valid` (or `proxy-only` for B12/B13) |

If any field differs, the comparison is marked `invalid` — no parity claims allowed.

## Reproducibility Contract

Every benchmark run produces a JSON artifact containing:

```json
{
  "contract": {
    "harness_version": "1.0.0",
    "harness_commit_sha": "a1b2c3d4e5f6...",
    "agent": "autocode",
    "agent_version": "0.1.0",
    "model": "qwen2.5-coder:14b-instruct-q4_K_M",
    "provider_mode": "local_free",
    "lane": "B7",
    "manifest_hash": "sha256:a1b2c3d4e5f6...",
    "budget_profile": {
      "wall_time_s": 600,
      "token_cap": 50000,
      "max_tool_calls": 100
    },
    "budget_profile_id": "wt600_tc50000_mc100",
    "command_trace": "uv run python benchmarks/benchmark_runner.py --agent autocode --lane B7",
    "timestamp": "2026-02-19T10:00:00Z",
    "comparison_validity": "parity-valid",
    "seed": null,
    "image_digest": null
  },
  "lane": "B7",
  "agent": "autocode",
  "model": "qwen2.5-coder:14b-instruct-q4_K_M",
  "provider_mode": "local_free",
  "aggregate": {
    "total_tasks": 24,
    "resolved": 5,
    "resolve_rate": 0.2,
    "infra_fails": 0,
    "infra_fail_rate": 0.0,
    "total_wall_time_s": 1500.0,
    "avg_wall_time_s": 60.0
  },
  "results": [
    {
      "task_id": "django__django-11099",
      "resolved": true,
      "score": 1.0,
      "wall_time_s": 45.2,
      "tool_calls": 8,
      "error": ""
    }
  ]
}
```

## Provider Policy (Entry 530)

| Provider Mode | Status | Examples |
|---------------|--------|----------|
| `local_free` | ALLOWED | Ollama, OpenRouter free-tier (glm-4.5-air:free) |
| `subscription` | ALLOWED | Codex CLI (user sub), Claude Code CLI (user sub) |
| `paid_metered` | FORBIDDEN | Any metered API billing |

## B12/B13 Comparability (Entry 527)

| Track | Label | Parity Claims |
|-------|-------|---------------|
| B12-PROXY / B13-PROXY | `comparison_validity: proxy-only` | Internal baselines only |
| B12-OFFICIAL / B13-OFFICIAL | `comparison_validity: official` | Published benchmark parity |

## What We're Benchmarking

**We are benchmarking AutoCode as a whole agentic coding tool** — not individual models. The benchmarks measure:
- How well AutoCode's AgentLoop + tools + orchestration can complete real coding tasks
- End-to-end quality: from user prompt to working code
- Cost efficiency: tokens, tool calls, turns used
- Speed: wall time to completion

The LLM model is AutoCode's "brain" but the benchmark tests the full pipeline: prompt engineering, tool calling, file management, command execution, error recovery, and code generation.

## Provider Recommendations

AutoCode runs on local hardware (8GB VRAM, 16GB RAM). The model is selected by the user in `.env`.

| Provider | Model | Best for | Cost |
|----------|-------|----------|------|
| Ollama | qwen2.5-coder:14b-instruct-q4_K_M | B6 calculator (current default) | Free (local GPU, ~8GB VRAM) |
| Ollama | qwen3:8b | B6 calculator (faster, lighter) | Free (local GPU, ~5GB VRAM) |
| OpenRouter (free) | *:free models | Quick testing only | Free but rate-limited |

## Workflow

1. **R0 (Calibration):** Run each lane once to establish baseline scores
2. **Lock baselines:** Record pass thresholds in `benchmarks/STATUS.md`
3. **R1 (Gate run):** Run all lanes, compare against baselines
4. **Store artifacts:** Save to `docs/qa/test-results/` per Codex gate policy
5. **Parity runs:** Run Codex + Claude Code on same lanes via unified harness
6. **Review:** Codex reviews artifacts, issues APPROVE/NEEDS_WORK per lane

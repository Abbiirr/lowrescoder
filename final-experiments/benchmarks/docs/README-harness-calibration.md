# Harness Calibration Tooling

This directory holds the **harness calibration** layer: tooling that validates the
evaluation harness *itself* is trustworthy, by running it against known-good controls
before we rely on its verdicts for AutoCode.

> Design spec: `docs/superpowers/specs/2026-06-21-harness-calibration-puku-design.md`

## The idea in one line

A trusted agent should pass solvable tasks, and a wrong solution should fail grading — so
if the harness disagrees, the **harness** has the bug, not the agent. We measure both
directions of error with two kinds of control:

| Control | Implementation | Proves |
|---|---|---|
| Real known-good agent | `puku-cli` via `PukuAdapter` (gateway-routed) | no **false negatives** (good agent ⇒ PASS on solvable tasks) |
| Synthetic golden oracle | `GoldenOracle` | no false negatives (reference solution ⇒ PASS) |
| Synthetic noop oracle | `NoopOracle` | no false positive on an empty diff |
| Synthetic wrong oracle | `WrongOracle` | no **false positives** (wrong patch ⇒ FAIL — the SWE-bench-Verified failure mode) |

## Components

- `benchmarks/adapters/puku_adapter.py` — drives `puku-cli` through the local LiteLLM
  gateway (`--provider openai`, `OPENAI_BASE_URL=$AUTOCODE_LLM_API_BASE`, alias model).
  Confines puku to the sandbox (`cwd=sandbox`) and captures `num_turns`/`duration` from
  puku's JSON. Registered as agent `puku` in `AGENT_REGISTRY`.
- `benchmarks/adapters/oracle_adapters.py` — `GoldenOracle` / `NoopOracle` / `WrongOracle`,
  deterministic network-free ground-truth probes.
- `benchmarks/calibration_tasks.py` — self-contained calibration tasks (each with a failing
  baseline, a known gold solution, and a known wrong solution).
- `benchmarks/tests/test_harness_calibration.py` — hard-asserted oracle invariants (CI-safe,
  no network).
- `benchmarks/calibrate_harness.py` — live runner that adds the puku dimension, measures
  verdict-flip rate across repetitions, and writes the report below.

## Running it

Deterministic invariants (fast, no network — runs in CI):

```bash
uv run pytest benchmarks/tests/test_harness_calibration.py -v
```

Live calibration (drives puku-cli through the gateway — load `.env` first):

```bash
set -a; . ./.env; set +a
uv run python benchmarks/calibrate_harness.py --reps 3        # full
uv run python benchmarks/calibrate_harness.py --oracles-only  # skip the live agent
```

Outputs:
- `benchmarks/docs/harness-calibration-report.md` — human-readable verdict.
- `benchmarks/docs/harness-calibration-report.json` — machine summary.

## Full B7–B29 puku sweep

The existing sweep orchestrator is now agent-parameterized (default stays `autocode`):

```bash
# puku through B7–B29 (omit the Harbor/Docker-bound B30-TBENCH lane):
BENCHMARK_AGENT=puku \
BENCHMARK_LANES="B7 B8 B9-PROXY B10-PROXY B11 B12-PROXY B13-PROXY B14-PROXY \
B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 B28 B29" \
bash benchmarks/run_b7_b30_sweep.sh
```

It keeps the standing discipline: waits for the gateway (never restarts it), `--resume`
on per-lane markers, and continues past lane-specific failures. Resume a partial run with
`BENCHMARK_RUN_ID=<id> BENCHMARK_AGENT=puku bash benchmarks/run_b7_b30_sweep.sh`.

## Phase 2 suite tooling

- `benchmarks/inventory_suite.py` → `benchmarks/docs/suite-coverage-inventory.md` —
  coverage map of all 761 tasks (difficulty/language/category) + gap list.
- `benchmarks/build_smoke_tier.py` → `smoke-tier-subset.json` (registered as the `SMOKE`
  lane) — a fast, balanced 6-task pre-flight slice. Run it with the **`fast` alias** (the
  `coding` reasoning alias is ~4.5× slower and times simple tasks out — measured 19s vs 86s):
  `uv run python benchmarks/benchmark_runner.py --agent puku --lane SMOKE --model fast --task-timeout-s 150`.
- `benchmarks/summarize_sweep.py <run-id>` → `benchmarks/docs/sweep-summary-<run-id>.md` —
  consolidated per-lane results (resolved rate, infra fails, mean turns) with reproducibility
  metadata (harness commit, agent version, model).

## Known limitation: token/cost accounting

puku self-reports `tokens=0` / `cost=0` through the gateway's OpenAI provider, even though
the gateway meters usage. Honest token/cost must be sourced from the gateway (LiteLLM), not
the agent JSON. This applies equally to AutoCode on the same gateway, and is captured in the
calibration report.

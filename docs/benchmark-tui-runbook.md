# TUI Benchmark Runbook

Last updated: 2026-04-23

## What This Is

This is the operator runbook for preparing a benchmark sweep through the Rust
TUI as a real human would use it.

It covers:

- preflight checks for the live gateway and the Rust TUI
- inline vs alt-screen launch choice
- preparing a task pack for the chosen benchmark scope
- canonical sweep commands for the existing benchmark harness
- the benchmark-owned PTY automation path that launches the Rust TUI in a PTY

It does **not** pretend the benchmark harness is TUI-native. The current truth
is:

- the Rust TUI is the real interactive frontend a human uses
- the benchmark harness still owns canonical sandbox creation, grading,
  resumability, and JSON result artifacts
- the prep script creates an operator pack plus both manual and harness-owned
  TUI commands; it still does not execute tasks by itself
- the harness-owned TUI path is implemented and now has a green real-gateway
  canary on `B13-PROXY`, recorded in
  `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json` and
  `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`
- larger sweeps should still start with a fresh canary on the current gateway
  before the long run begins

## Quick Start

Inline mode, full suite:

```bash
uv run python benchmarks/prepare_tui_benchmark_run.py --scope full --mode inline --strict
```

Alt-screen mode, core suite:

```bash
uv run python benchmarks/prepare_tui_benchmark_run.py --scope core --mode altscreen --strict
```

That command:

1. checks the Rust TUI binary, gateway auth env, gateway readiness, lane list,
   and real-gateway PTY smoke
2. creates an operator pack under `docs/qa/test-results/`
3. prints the exact `BENCHMARK_RUN_ID=...` commands for canary and sweep runs
4. prints the explicit TUI-owned benchmark commands that drive
   `autocode --mode altscreen` inside a PTY

## Scope Choices

`core`

- prepares the B7-B14 sweep
- uses `benchmarks/run_all_benchmarks.sh`
- fastest honest end-to-end benchmark sweep

`full`

- prepares the B7-B30 sweep
- uses `benchmarks/run_b7_b30_sweep.sh`
- this is the whole current internal suite plus B30-TBENCH

## TUI Mode Choice

Inline:

- command: `uv run autocode`
- preserves native terminal scrollback
- best default for long benchmark sessions

Alt-screen:

- command: `uv run autocode --mode altscreen`
- gives a dedicated fullscreen TUI surface
- useful when you want clean visual focus and do not need inline scrollback

## Recommended Operator Flow

1. Run the prep script with `--strict`.
2. Open the generated pack directory in `docs/qa/test-results/`.
3. Read `index.md` for the run id, sweep command, and per-lane notes.
4. Start with the suggested canary lane command.
5. If you want the harness to drive the Rust TUI automatically, use
   `tui_canary_lane` first.
6. Warm up the TUI once in your chosen mode:
   - inline: `uv run autocode`
   - alt-screen: `uv run autocode --mode altscreen`
7. If the canary and warmup both look healthy, launch the full sweep.
   Do not launch `tui_sweep` after an `INFRA_FAIL` or recovery-state canary.

## Canonical Commands

List lanes:

```bash
uv run python benchmarks/benchmark_runner.py --list-lanes
```

Core sweep:

```bash
BENCHMARK_RUN_ID=<run-id> bash benchmarks/run_all_benchmarks.sh
```

Full sweep:

```bash
BENCHMARK_RUN_ID=<run-id> bash benchmarks/run_b7_b30_sweep.sh
```

Resume:

```bash
BENCHMARK_RUN_ID=<run-id> bash benchmarks/run_all_benchmarks.sh
BENCHMARK_RUN_ID=<run-id> bash benchmarks/run_b7_b30_sweep.sh
```

Real-gateway smoke:

```bash
cd autocode && uv run python tests/pty/pty_e2e_real_gateway.py
```

Harness-owned TUI canary:

```bash
uv run python benchmarks/benchmark_runner.py \
  --agent autocode \
  --autocode-runner tui \
  --lane B7 \
  --model swebench \
  --max-tasks 1
```

Harness-owned TUI full sweep:

```bash
BENCHMARK_RUN_ID=<run-id> bash -lc 'for lane in B7 B8 B9-PROXY B10-PROXY B11 B12-PROXY B13-PROXY B14-PROXY B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 B28 B29 B30-TBENCH; do if [ "$lane" = "B30-TBENCH" ]; then model=terminal_bench; else model=swebench; fi; uv run python benchmarks/benchmark_runner.py --agent autocode --autocode-runner tui --lane "$lane" --model "$model" --run-id <run-id> --resume || exit $?; done'
```

## Operator Pack

The prep script writes:

- `docs/qa/test-results/<timestamp>-tui-benchmark-pack-<scope>-<mode>/index.md`
- `docs/qa/test-results/<timestamp>-tui-benchmark-pack-<scope>-<mode>/tasks/*.md`

The task files contain:

- task id and description
- setup commands
- grading command
- manifest path and useful metadata
- the primary TUI launch command for the chosen mode

These files are meant for human prep fidelity. They do **not** replace the
benchmark harness's sandbox setup or grading pipeline. When you use the
`--autocode-runner tui` commands above, the harness still owns grading,
resume state, and JSON result artifacts; only the agent-execution path moves
through the Rust TUI PTY.

For TUI-runner attempts, the harness now also keeps a live rendered-screen
artifact while the benchmark is running:

- `tui.screen.live.log` — rolling latest stripped screen contents during the PTY run
- `tui.screen.log` — final stripped screen contents at end of attempt
- `tui.raw.log` — raw ANSI capture
- `tui.timing.json` — timing/state metadata for the attempt

As of 2026-04-23, this live capture is working on the real benchmark lane and
shows the corrected benchmark-owned status bar (`swebench | openrouter`) during
the run. The Phase A close-out canary on `B13-PROXY` now reaches
`ready -> streaming -> completed` with the live screen artifact preserved
through the attempt.

## Failure Rules

Do not start a long sweep if any of these fail:

- gateway auth env is missing
- gateway readiness check is unhealthy
- `benchmark_runner.py --list-lanes` fails
- real-gateway PTY smoke fails
- the Rust TUI binary is missing

Fix the environment first, then rerun the prep script.

If the benchmark model alias itself is rejected by the configured backend, the
AutoCode runner now halts before task execution with a provider health failure
instead of waiting for the Rust TUI to age into stale-request recovery.

If the gateway alias route is healthy and a future Rust TUI canary still
records `first_streaming_s = null` and ends in recovery, treat that as a new
regression. Do not launch a TUI sweep; capture the timing artifact, live screen
log, and lane JSON artifact instead.

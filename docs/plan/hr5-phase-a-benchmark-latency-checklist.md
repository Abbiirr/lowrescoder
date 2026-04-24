# HR-5 Phase A Benchmark Latency Checklist

Last updated: 2026-04-23
Status: complete on the canary lane; Phase B unblocked

Related plan:

- `docs/plan/hr5-phase-a-benchmark-latency-plan.md`

## Preflight

- [x] Confirm the current canary reference artifact is still
      `docs/qa/test-results/20260422-133610-tui-benchmark-canary.md`
- [x] Confirm the active lane is `B13-PROXY`
- [x] Confirm Phase B (`/cc`) remains blocked during this slice
- [x] Confirm the user-facing launch wording stays `autocode --mode altscreen`
      where docs describe the real Rust TUI

## Instrumentation

- [x] Add or enable harness-visible timestamps for PTY launch start
- [x] Add or enable timestamps for ready-state detection
- [x] Add or enable timestamps for prompt injection start/end
- [x] Add or enable timestamps for first streaming signal
- [x] Add or enable timestamps for completed vs recovery detection
- [x] Store the diagnosis artifact path
  - `docs/qa/test-results/20260423-025120-tui-benchmark-latency-verification.md`

## Control Measurement

- [x] Run the benchmark-owned Rust TUI canary once with instrumentation enabled
- [x] Run a comparable non-TUI control path for the same first-turn workload
- [x] Record the timing deltas side by side
- [x] Identify the dominant latency bucket

## Fix

- [x] Write the one-paragraph attribution note
- [x] Patch the dominant contributor instead of extending the workaround
- [x] Remove or avoid any temporary masking-only timeout change
- [x] Keep grading, resume, and JSON artifact ownership inside the harness

## Verification

- [x] Rerun the `B13-PROXY` canary through `--autocode-runner tui`
- [x] Store the new benchmark JSON artifact
  - `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json`
- [x] Store the timing/profiler artifact
  - `sandboxes/bench_B13-PROXY_cc-001-two-sum_20260423_040200/.benchmark-tui/attempt-1/tui.timing.json`
- [x] Store the Phase A verification note
  - `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`

## Exit Gate

- [x] Canary completes without relying on the stretched stale-request workaround

If the box above cannot be checked:

- [ ] Update the runbook and status docs with a precise, lane-specific
      limitation and honest operator guidance
- [ ] Do not mark the TUI sweep-ready
- [ ] Do not start Phase B without explicit user confirmation

## Phase-B Unblock

- [x] `current_directives.md` reflects the Phase A outcome
- [x] `EXECUTION_CHECKLIST.md` reflects the Phase A outcome
- [x] `PLAN.md` reflects the Phase A outcome
- [x] Only after the three docs above are updated, reconsider `/cc`

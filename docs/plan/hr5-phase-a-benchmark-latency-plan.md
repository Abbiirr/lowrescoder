# HR-5 Phase A Benchmark Latency Plan

Last updated: 2026-04-23
Status: complete on the canary lane; Phase B unblocked

## Purpose

Phase A under HR-5(c) exists to remove the benchmark-latency blocker on the
real-gateway Rust TUI PTY path before any new HR-5(a) real-data binding work
starts.

This is not a visual slice and not a workaround-extension slice. The goal was
to measure where the first-turn latency was actually going, fix the heaviest
contributor, and rerun the `B13-PROXY` canary through the benchmark-owned TUI
runner.

That goal is now met on the canary lane. The close-out artifact is
`docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`.

## Canonical Inputs

- `current_directives.md`
- `EXECUTION_CHECKLIST.md`
- `PLAN.md` §1g
- `docs/tui-testing/tui_implementation_plan.md`
- `docs/tui-testing/tui_implementation_todo.md`
- `docs/qa/test-results/20260422-133610-tui-benchmark-canary.md`
- `docs/benchmark-tui-runbook.md`

## Current Truth

- The benchmark-owned Rust TUI PTY runner already launches the real TUI, feeds
  manifest-derived prompts, detects `ready` / `streaming` / `completed` /
  `recovery`, and keeps grading, resume, and JSON artifacts inside the harness.
- The benchmark-owned Rust TUI PTY runner already launches the real TUI, feeds
  manifest-derived prompts, detects `ready` / `streaming` / `completed` /
  `recovery`, keeps grading/resume/JSON artifacts in the harness, and keeps a
  live rendered-screen artifact during the run.
- The first live `B13-PROXY` canary exposed a real latency problem on the first
  benchmark turn: `ready -> recovery`.
- The benchmark gateway/provider routing bug was fixed first for benchmark-owned
  runs:
  - loop/control path on `B13-PROXY` with `--model swebench` resolved against
    the real gateway in `424.9s`
  - Rust TUI path started under the correct `swebench | openrouter`
    benchmark config instead of leaking ambient `tools` / `.env` defaults
- The dominant remaining issue was then isolated to the Rust TUI path itself:
  - benchmark-sized prompts needed a benchmark-owned L4 bypass
  - the RTUI/backend RPC path on the release binary needed pipe transport
    instead of PTY-backed JSON transport
  - long healthy turns needed a cheap backend heartbeat so they would not age
    into false recovery before first visible stream
- The green close-out canary now proves the fix set on the real gateway:
  - `B13-PROXY` through `--autocode-runner tui` resolved in `79.0s`
  - state trace: `ready -> streaming -> completed`
  - `first_streaming_s = 7.231`
  - `completed_detected_s = 75.473`
  - `recovery_detected_s = null`
- `/cc` is now the active next HR-5(a) binding. It is no longer blocked by
  this phase.

Current comparison artifacts:

- Control success: `docs/qa/test-results/20260423-025010-B13-PROXY-autocode.json`
- TUI recovery on correct config:
  `docs/qa/test-results/20260423-024938-B13-PROXY-autocode.json`
- Failure verification note:
  `docs/qa/test-results/20260423-025120-tui-benchmark-latency-verification.md`
- Green canary:
  `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json`
- Close-out verification note:
  `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`

## Scope

In scope:

- first-token and first-turn latency on the real-gateway Rust TUI PTY path
- measurement on the benchmark-owned path, not only ad hoc manual runs
- comparison against a non-TUI control path for the same workload
- one or more instrumentation points needed to attribute the delay
- the smallest correct fix for the dominant contributor
- canary rerun and artifact capture
- doc/runbook honesty if the lane remains limited

Out of scope:

- `/cc` or any other HR-5(a) real-data binding
- new visual polish
- speculative performance cleanup without measurements
- broad benchmark-harness redesign unrelated to this latency blocker

## Success Condition

Phase A was complete only if one of these was true:

1. The `B13-PROXY` canary through `--autocode-runner tui` completes without
   relying on the stretched stale-request workaround.
2. The lane still fails for a measured reason, and the docs/runbook are updated
   with a precise, lane-specific limitation plus honest operator guidance.

Option 2 was not preferred, but it remained an honest completion state for the
diagnosis slice if the remaining blocker was external or not fixable inside the
current slice.

This plan closed via Option 1. The `B13-PROXY` canary completed without
relying on the stretched stale-request workaround, and the close-out artifacts
above record the result.

## Decision Rules

1. Measure before changing timeouts again.
2. Prefer the narrowest instrumentation that yields attribution.
3. Fix the dominant contributor first, not the loudest symptom.
4. Keep the benchmark harness as the owner of grading, resume, and artifacts.
5. Do not declare the TUI sweep-ready unless the canary proves it.

## Workstreams

### 1. Reproduce and Instrument

Capture a benchmark-owned timing view for the failing path.

Required timing boundaries:

- PTY launch start
- TUI ready-state detected
- prompt injection start and end
- first visible streaming signal
- completion or recovery detection
- grading handoff

Prefer timestamps in the harness-owned path so the same instrumentation works
for later canaries and not only for one-off manual diagnosis.
These harness-visible timestamps remain in the benchmark-owned TUI path after
Phase A as permanent diagnostic infrastructure.

### 2. Build a Control Comparison

Run the same first-turn benchmark workload against a direct non-TUI path where
possible. The goal is not to prove the control path is "fast enough"; the goal
is to separate:

- gateway/model latency
- benchmark fixture/setup latency
- TUI render/event-loop latency
- PTY transport or readiness-detection latency

If the control path is similarly slow, the diagnosis should move toward gateway
or workload expectations. If the control path is materially faster, the focus
stays on the TUI/PTY path.

### 3. Attribute the Delay

Reduce the failing turn into the largest measurable bucket.

Priority order:

1. benchmark harness setup / fixture preparation
2. PTY boot and TUI readiness detection
3. prompt handoff / stdin write behavior
4. backend request dispatch delay after submit
5. first-token arrival from the gateway
6. reducer / render path failing to expose streaming activity quickly enough
7. stale-request or recovery logic firing before a healthy slow turn completes

The working output of this step is a short attribution note: which bucket is
largest, how large it is, and why it matters.

### 4. Fix the Dominant Contributor

Apply the narrowest change that removes or materially reduces the dominant
latency source.

Examples of acceptable fixes:

- readiness detection that waits too long or misses the earliest safe submit
- prompt injection flow that serializes writes or waits unnecessarily
- stale/recovery logic that treats a healthy slow first turn as dead
- redundant setup work on the benchmark-owned TUI path

Examples of unacceptable "fixes":

- raising another timeout without attribution
- bypassing the TUI state machine and calling the old path directly
- weakening grading/resume/artifact ownership in the harness

### 5. Verify on the Canary Lane

Rerun `B13-PROXY` through `--autocode-runner tui`.

Required outputs:

- updated benchmark JSON artifact
- timing or profiler artifact for the diagnosis pass
- verification note summarizing measurement, fix, and canary result

If the canary is green, document the exact conditions and remove any temporary
stretch timeout used only to mask the issue. If the canary is still not green,
document the measured limitation precisely instead of claiming sweep readiness.

## Deliverables

- code change set, if needed for instrumentation or the actual fix
- timing/profiler artifact under `docs/qa/test-results/`
- verification artifact under `docs/qa/test-results/`
- status-doc updates if the result changes the active frontier or lane honesty
- canary JSON artifact from the benchmark harness

## Exit Gate for Phase B

Phase B (`/cc` real-data binding) starts only after:

- the Phase A success condition above is met
- the result is written into the canonical docs
- the canary outcome is stored as an artifact

This gate is now satisfied on the canary lane.

## Recommended Execution Order

1. add harness-visible timestamps for the benchmark-owned TUI run
2. rerun the canary once to confirm current timing breakdown
3. run the matching non-TUI control measurement
4. write the attribution note
5. patch the dominant contributor
6. rerun the canary
7. update docs/runbook according to the result
8. only then reopen Phase B

## Artifact Naming

Use the existing QA pattern under `docs/qa/test-results/`:

- `<timestamp>-tui-benchmark-latency-diagnosis.md`
- `<timestamp>-tui-benchmark-latency-verification.md`
- benchmark JSON artifact from the canary lane

## Handoff Note

Phase A passed, so the next execution slice is Phase B:

- `docs/tui-testing/tui_implementation_plan.md` Phase B
- `docs/tui-testing/tui_implementation_todo.md` Phase B

That follow-on remains blocked until this plan's success condition is met and
recorded.

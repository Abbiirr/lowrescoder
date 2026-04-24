# TUI Implementation Plan

Status: active execution document for Stage 4 `tui-references` follow-through, with HR-5 runtime correctness and real-data binding now ahead of any further visual-only polish

Last updated: 2026-04-23

Primary inputs:

- `docs/plan/hr5-phase-a-benchmark-latency-plan.md`
- `docs/plan/hr5-phase-a-benchmark-latency-checklist.md`
- `AGENTS_CONVERSATION.MD` Entry `1294` — Claude's reviewed execution order
- `autocode/docs/qa/test-results/20260421-175050-tui-14-scene-capture-matrix.md`
- `autocode/docs/qa/test-results/20260422-114357-tui-reference-gap.md`
- `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`
- `autocode/docs/qa/test-results/20260421-235651-tui-stage4-fidelity-pass.md`
- `autocode/docs/qa/test-results/20260422-010039-tui-stage4-review-split-pass.md`
- `autocode/docs/qa/test-results/20260422-112207-tui-stage4-search-escalation-cc-split-pass.md`
- `autocode/docs/qa/test-results/20260422-113800-tui-stage4-recovery-density-pass.md`
- `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`
- `autocode/docs/qa/test-results/20260422-081639-tui-stage4-ready-active-density-pass.md`
- `autocode/docs/qa/test-results/20260422-152822-tui-stage4-overlay-narrow-pass.md`
- `autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`
- `docs/qa/test-results/20260422-133610-tui-benchmark-canary.md`
- `docs/tui-testing/tui-reference-scene-trigger-guide.md`
- `docs/tui-testing/tui-capture-compare-workflow.md`
- `docs/tui-testing/tui-system-feature-coverage-guide.md`

User-locked override on 2026-04-22:

- default inline TUI must render full-screen
- terminal resize must remain correct
- multiple terminal sizes must be validated
- native terminal scrollback must remain preserved

This override supersedes the earlier centered-shell direction from the
2026-04-22 structural-fidelity passes.

## Purpose

Turn the current AutoCode TUI from "current analog of the reference bundle" into
"the live states visibly match `tui-references` and are regression-gated."

For the immediate next slice, the active execution source of truth is the
dedicated Phase A plan/checklist pair above. This document remains the broader
parity and HR-5 context map.

This plan is intentionally split into two ideas:

1. fix the measurement rig first
2. then close scene families in the order that gives the highest leverage

## Current Baseline

Source of truth:

- `autocode/docs/qa/test-results/20260422-114357-tui-14-scene-capture-matrix.md`
- `autocode/docs/qa/test-results/20260422-114357-tui-reference-gap.md`
- `autocode/docs/qa/test-results/20260421-235651-tui-stage4-fidelity-pass.md`
- `autocode/docs/qa/test-results/20260422-010039-tui-stage4-review-split-pass.md`
- `autocode/docs/qa/test-results/20260422-112207-tui-stage4-search-escalation-cc-split-pass.md`
- `autocode/docs/qa/test-results/20260422-113800-tui-stage4-recovery-density-pass.md`
- `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`
- `autocode/docs/qa/test-results/20260422-081639-tui-stage4-ready-active-density-pass.md`

Current 14-scene split:

| Scene | Current status | Notes |
|---|---|---|
| `ready` | direct | real current surface; baseline runtime/gateway path is green |
| `active` | direct | real current surface; baseline runtime/gateway path is green |
| `multi` | direct | dedicated multitasking surface ships; remaining work is real-data binding plus any residual fidelity |
| `plan` | direct | dedicated plan surface ships; remaining work is real-data binding plus any residual fidelity |
| `review` | direct | dedicated review surface ships; remaining work is real-data binding plus any residual fidelity |
| `cc` | direct | dedicated command-center surface ships; remaining work is real-data binding plus any residual fidelity |
| `recovery` | direct | real current surface; remaining work is targeted fidelity only if still justified after HR-5 |
| `restore` | direct | dedicated restore browser ships; remaining work is real-data binding plus any residual fidelity |
| `sessions` | direct | live session-picker overlay exists; baseline runtime/gateway path is green |
| `palette` | direct | live palette overlay exists; baseline runtime/gateway path is green |
| `diff` | direct | dedicated diff surface ships; remaining work is real-data binding plus any residual fidelity |
| `grep` | direct | dedicated search surface ships; remaining work is real-data binding plus any residual fidelity |
| `escalation` | direct | dedicated escalation surface ships; remaining work is real-data binding plus any residual fidelity |
| `narrow` | direct | real current surface; baseline runtime/gateway path is green |

Honesty note:

- direct triggerability is complete, but several dedicated detail surfaces still
  render static scene text rather than real bound session state

## Working Rules

1. Fix harness signal before renderer work.
2. Never fake a missing scene with a static screenshot.
3. A scene becomes a Track 4 gate only when the live product exposes a real
   direct surface for it.
4. For system-feature scenes, use benchmark-driven or mid-run captures where
   appropriate; final idle screenshots are not enough.
5. Use the mockup JPGs as the spec for visual work, not memory.
6. User-locked rendering requirements override prior Stage 4 aesthetic choices.
7. HR-5 now blocks any further visual-only slice unless it also fixes a real runtime issue or ships a real-data binding.

## Immediate Hard-Requirements Slice

Before further mockup-fidelity work, land this compliance pass:

1. remove the centered width cap so the default inline TUI fills the terminal
2. keep resize handling correct and validated
3. add multi-size validation at minimum `80x24`, `120x40`, and `200x50`
4. keep native scrollback preserved by leaving default mode inline and
   `--altscreen` opt-in only
5. codify these rules in `docs/tui-testing/tui_testing_checklist.md`

Status:

- complete on 2026-04-22 via
  `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`
- outcome: default inline shell now fills the terminal, resize remains green,
  multi-size PTY validation covers `80x24`, `120x40`, and `200x50`, and the
  hard requirements are codified in `docs/tui-testing/tui_testing_checklist.md`

## Definition Of Done Per Scene

A scene is done only when all of these are true:

1. the state is real in the product
2. the trigger is deterministic
3. the scene is captured in the 14-scene matrix
4. the screenshot comparison bundle shows close visual match to the reference
5. the scene is no longer merely approximate / partial / negative evidence
6. Track 1, Track 4, PTY smoke, and the visual bundle remain green enough for
   the slice being shipped

## Execution Order

This order follows Claude Entry `1294` and extends it into the later fidelity
work required to make all current states look like `tui-references`.

### Stage 0 — Fix Harness Signal First

Do this before any new scene-promotion work.

Target:

- `autocode/tests/tui-comparison/predicates.py`

Problem:

- `basic_turn_returns_to_usable_input` only checks the last two non-empty
  lines, but the current TUI places helper/footer rows below the composer

Required change:

- detect the composer prompt anywhere in the bottom 3-5 visible lines, not only
  in the last two non-empty lines

Exit gate:

- `make tui-regression` fully green
- no new Track 4 or PTY smoke regressions

Status:

- complete on 2026-04-21 via
  `autocode/docs/qa/test-results/20260421-160214-tui-stage0-predicate-verification.md`

### Stage 1 — Promote Low-Effort Reachable Scenes

Target scenes:

- `sessions`
- `palette`
- `plan`

Why these first:

- they are already reachable on the current tree
- `sessions` and `palette` are already direct captures
- `plan` is at least partially real and can be promoted honestly, even if it
  begins as `xfail(strict=True)` because the full plan panel does not exist yet

Required work:

- add or tighten live drivers and predicates in
  `autocode/tests/tui-references/test_reference_scenes.py`
- remove stubs for `sessions` and `palette`
- treat `plan` honestly:
  - if only HUD plus acknowledgment exists, keep the scene partial and guarded
  - if a real panel ships, promote it directly

Exit gate:

- 3 more scenes moved into the Track 4 working set
- current expectation: 4 hard-gated live scenes becomes 7 live scenes, though
  `plan` may temporarily remain strict-xfail if only a partial surface exists

Status:

- complete on 2026-04-21 via
  `autocode/docs/qa/test-results/20260421-172147-tui-stage1-reference-promotion.md`
- historical outcome at Stage 1 close: `sessions` and `palette` promoted to
  live Track 4 gates; `plan` remained a strict-`xfail` partial scene
- superseded later on 2026-04-21 by
  `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`,
  which ships a dedicated direct `plan` surface

### Stage 2 — Medium-Gap Inspection And Recovery Surfaces

Target scenes:

- `restore`
- `multi`
- `review`
- `diff`

Recommended order:

1. `restore`
2. `multi`
3. `review` and `diff` together

Design guidance:

- open the relevant mockup JPGs before implementing
- do not design from memory
- use `docs/tui-testing/tui-reference-scene-trigger-guide.md` and
  `autocode/docs/qa/test-results/20260421-130754-tui-reference-gap-analysis.md`
  while building these slices

Expected product work:

- `restore`: dedicated checkpoint or restore surface, not only a recovery label
- `multi`: richer task/subagent/tool/queue presentation than the current panel
  analog
- `review` and `diff`: first-class review and diff-focused surfaces, not
  unknown-command fallbacks

Exit gate:

- these scenes become direct captures rather than partial / approximate /
  negative evidence

Status:

- complete on 2026-04-21 via
  `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`
- outcome: `restore`, `multi`, `review`, and `diff` now ship as dedicated
  direct surfaces with deterministic capture paths

### Stage 3 — Search, Escalation, And Command Center Surfaces

Target scenes:

- `grep`
- `escalation`
- `cc`

Why deferred originally:

- `grep` needs a real search UI
- `escalation` needs a true permission hierarchy / protected-path flow
- `cc` needs a true command-center or subagent-control surface

Exit gate:

- each scene has a real visible surface and deterministic capture path

Status:

- complete on 2026-04-21 via
  `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`
- outcome: `grep`, `escalation`, and `cc` now ship as dedicated direct
  surfaces with deterministic capture paths

### Stage 4 — Global Visual Fidelity Pass

Do this after every scene family is at least real and capturable.

Target surfaces:

- `ready`
- `active`
- `narrow`
- `recovery`
- overlays such as `sessions` and `palette`
- workload surfaces such as `multi`, `cc`, `plan`, `restore`, `review`, `diff`

Expected work:

- spacing and proportions
- panel density
- information hierarchy
- empty-state presentation
- recovery layout
- narrow-width wrapping behavior
- overlay sizing and selection styling

This is where the product stops being "functionally close" and becomes
"visually close."

Status:

- active on 2026-04-21
- baseline fidelity bundle:
  `autocode/docs/qa/test-results/20260422-114357-tui-reference-gap.md`
- first renderer-focused shell / overlay pass verified in
  `autocode/docs/qa/test-results/20260421-235651-tui-stage4-fidelity-pass.md`
- untitled-shell / split-review structural pass verified in
  `autocode/docs/qa/test-results/20260422-010039-tui-stage4-review-split-pass.md`
- grep / escalation / command-center split pass verified in
  `autocode/docs/qa/test-results/20260422-112207-tui-stage4-search-escalation-cc-split-pass.md`
- structured recovery pass verified in
  `autocode/docs/qa/test-results/20260422-113800-tui-stage4-recovery-density-pass.md`
- fullscreen hard-requirements pass verified in
  `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`
- ready / active density pass verified in
  `autocode/docs/qa/test-results/20260422-081639-tui-stage4-ready-active-density-pass.md`
- overlay / narrow pass verified in
  `autocode/docs/qa/test-results/20260422-152822-tui-stage4-overlay-narrow-pass.md`
- remaining work: the visual baseline is materially better, but HR-5 now
  prioritizes real-data binding for the dedicated detail surfaces plus runtime
  benchmark-readiness checks before any later visual-only refinement

### Runtime Correctness / Benchmark Readiness Slice

Status:

- complete on 2026-04-22 via
  `autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`

Outcome:

- local LiteLLM gateway auth now flows through the shared gateway-auth helper
  for non-OpenRouter API bases
- chat turns enter `Stage::Streaming` immediately, refresh liveness on real
  backend activity, and clear their pending request on `on_done`
- `/` can open slash-command discovery during an active turn
- real-gateway PTY smoke now validates `/help`, `/cost`, async slash discovery
  during a live turn, and a trivial live chat turn against the configured
  backend
- default mode remains inline and `autocode --mode altscreen` is now the
  preferred user-facing launch form for the Rust alt-screen path

### Benchmark-Owned Rust TUI PTY Slice

Status:

- implemented on 2026-04-22 with the canary write-up in
  `docs/qa/test-results/20260422-133610-tui-benchmark-canary.md`

Outcome:

- the benchmark harness can now launch the Rust TUI in a PTY, feed
  manifest-derived prompts, detect `ready` / `streaming` / `completed` /
  `recovery` from the visible surface, and preserve harness-owned grading,
  resume state, and JSON artifacts
- the first live canary produced a real benchmark artifact but failed with
  `ready -> recovery`, exposing a long-first-token / benchmark-turn latency
  blocker
- the Phase A close-out canary is now green:
  - `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json`
  - `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`
- the dominant fix chain was:
  - force benchmark-owned RTUI runs to Layer 4
  - keep long manifest prompts out of Layer 3 `SIMPLE_EDIT`
  - move RTUI/backend RPC transport to pipes on the release benchmark path
  - refresh pending-chat liveness with backend ack + heartbeat during long turns

## HR-5 Phased Order — 2026-04-23 Lock

### Phase A — HR-5(c) benchmark latency blocker

Status:

- COMPLETE on the canary lane via
  `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`

Scope:

- diagnose where first-token time is spent on the real-gateway Rust TUI PTY
  path
- fix the heaviest contributor
- rerun the `B13-PROXY` canary

Exit gate:

- the canary completes without needing the stretched stale-request workaround,
  or
- the docs/runbook capture a precise lane-specific limitation and honest prep
  disclosure

Result:

- closed via the green-canary path on `B13-PROXY`
- `ready -> streaming -> completed`
- `first_streaming_s = 7.231`
- `completed_detected_s = 75.473`
- `recovery_detected_s = null`

Required artifact content:

- timing / profiling evidence that shows where the latency lives
- canary rerun result

### Phase B — HR-5(a) `/cc` real-data binding

Prerequisite:

- Phase A exit gate passed, or user explicitly resets the order

Current state:

- prerequisite satisfied
- active next slice

Scope:

- bind `render_command_center_surface` to live `state.subagents`

### Phase C — HR-5(a) sequential detail-surface bindings

Order:

1. `/restore` / checkpoints
2. `/plan`
3. `/tasks` detail
4. `/grep`
5. `/review` + `/diff`
6. `/escalation`
7. remaining mockup-copy cleanup in dedicated detail surfaces

### Phase D — HR-5(b) runtime-correctness follow-ons

Scope:

1. spinner activity-correlation
2. thinking/output buffer split
3. per-slash PTY smoke coverage
4. 194-verb spinner badge wiring

### Phase E — release gate

Trigger:

- Phase A exit gate passed
- at least `4/10` HR-5(a) bindings shipped
- Phase D runtime-correctness follow-ons closed

## Verification Loop For Every Slice

Run the smallest loop that matches the slice:

1. `make tui-regression`
2. `make tui-references`
3. `make tui-reference-gap`
4. `make tui-scene-matrix`
5. `cd autocode && uv run python tests/pty/pty_smoke_rust_comprehensive.py`
6. if auth / real-backend behavior changed: `cd autocode && uv run python tests/pty/pty_e2e_real_gateway.py`

For system-feature slices, also store:

- benchmark-driven or mid-run frame sequences under
  `autocode/docs/qa/tui-frame-sequences/`

## Immediate Next Move

User design gate was approved on 2026-04-21 and the Stage 2 / 3 surface work
is complete, but HR-5 now forbids another visual-only slice.

The next technical slice is Phase B under HR-5(a): `/cc` real-data binding.
Phase A is closed on the canary lane and no longer blocks the program order.
Human-driven benchmark use through the live TUI is unblocked, and the
benchmark-owned Rust TUI path now has a green real-gateway canary. Larger
sweeps should still begin with a fresh canary on the current gateway.

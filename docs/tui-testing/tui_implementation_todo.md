# TUI Implementation Todo

Status: working checklist for the `tui-references` parity program

Related plan:

- `docs/plan/hr5-phase-a-benchmark-latency-plan.md`
- `docs/plan/hr5-phase-a-benchmark-latency-checklist.md`
- `docs/tui-testing/tui_implementation_plan.md`

Current baseline artifact:

- `autocode/docs/qa/test-results/20260421-175050-tui-14-scene-capture-matrix.md`
- `autocode/docs/qa/test-results/20260422-092151-tui-reference-gap.md`
- `autocode/docs/qa/test-results/20260421-235651-tui-stage4-fidelity-pass.md`
- `autocode/docs/qa/test-results/20260422-010039-tui-stage4-review-split-pass.md`
- `autocode/docs/qa/test-results/20260422-112207-tui-stage4-search-escalation-cc-split-pass.md`
- `autocode/docs/qa/test-results/20260422-113800-tui-stage4-recovery-density-pass.md`
- `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`
- `autocode/docs/qa/test-results/20260422-081639-tui-stage4-ready-active-density-pass.md`
- `autocode/docs/qa/test-results/20260422-152822-tui-stage4-overlay-narrow-pass.md`
- `autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`
- `docs/qa/test-results/20260422-133610-tui-benchmark-canary.md`

## Phase A — HR-5(c) Benchmark Latency Blocker

- [x] Measure first-token latency on the real-gateway Rust TUI PTY path
- [x] Compare the same first-turn workload against a direct non-TUI path
- [x] Identify the heaviest latency contributor
- [x] Fix the heaviest contributor instead of extending the workaround again
- [x] Rerun the `B13-PROXY` canary through `--autocode-runner tui`
- [x] Store a timing / profiler artifact for the diagnosis pass
  - `sandboxes/bench_B13-PROXY_cc-001-two-sum_20260423_040200/.benchmark-tui/attempt-1/tui.timing.json`
- [x] Store the Phase A verification artifact
  - `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`

Exit gate:

- [x] `B13-PROXY` canary completes without relying on the stretched
  stale-request timeout workaround, or the docs record a precise
  lane-specific limitation with honest prep-pack disclosure

## Phase B — HR-5(a) `/cc` Real-Data Binding

- [ ] Bind `render_command_center_surface` to `state.subagents`
- [ ] Add a unit test proving the surface reads live subagent state
- [ ] Capture before/after evidence in the verification artifact
- [ ] Re-run the required TUI verification loop

Blocked on:

- [x] Phase A exit gate

## Phase C — Remaining HR-5(a) Detail-Surface Bindings

- [ ] `/restore` / checkpoints
- [ ] `/plan`
- [ ] `/tasks` detail
- [ ] `/grep`
- [ ] `/review`
- [ ] `/diff`
- [ ] `/escalation`
- [ ] remaining dedicated detail-surface mockup-copy cleanup

## Phase D — HR-5(b) Runtime Correctness Follow-Ons

- [ ] Spinner activity-correlation
- [ ] Thinking/output buffer split
- [ ] Per-slash PTY smoke coverage
- [ ] 194-verb spinner badge wiring

## Phase E — Release Gate

- [x] Phase A exit gate passed
- [ ] At least `4/10` HR-5(a) bindings shipped
- [ ] Phase D follow-ons closed
- [ ] Visual-only polish re-enabled only after the gate above is met

## Hard-Requirements Override — 2026-04-22

- [x] Remove the centered width cap; default inline TUI uses the full terminal
- [x] Keep resize handling correct after the fullscreen change
- [x] Add multi-size validation for at least `80x24`, `120x40`, and `200x50`
- [x] Preserve native terminal scrollback in default inline mode
- [x] Codify the hard requirements in `docs/tui-testing/tui_testing_checklist.md`
  - Verification artifact: `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`

## Runtime Correctness / Benchmark Readiness — 2026-04-22

- [x] Fix local LiteLLM gateway auth for non-OpenRouter API bases
- [x] Prevent healthy chat turns from aging into false stale-request recoveries
- [x] Enter active turn state immediately on submit
- [x] Allow slash-command discovery while a response is cooking
- [x] Refresh the real-gateway PTY smoke to validate the current Rust TUI
- [x] Expose an explicit Rust alt-screen CLI switch while keeping inline the default
- [x] Store the runtime / gateway verification artifacts
  - `autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`
  - `autocode/docs/qa/test-results/20260422-114723-tui-verification.md`

## Stage 0 — Harness Signal

- [x] Update `basic_turn_returns_to_usable_input` in `autocode/tests/tui-comparison/predicates.py`
- [x] Make the predicate search the bottom 3-5 visible lines for the composer
  instead of only the last two non-empty lines
- [x] Run `make tui-regression`
- [x] Run `make tui-references`
- [x] Run `cd autocode && uv run python tests/pty/pty_smoke_rust_comprehensive.py`
- [x] Store a verification artifact for the Stage 0 predicate fix
  - `autocode/docs/qa/test-results/20260421-160214-tui-stage0-predicate-verification.md`

Exit gate:

- [x] `make tui-regression` is fully green

## Stage 1 — Reachable Low-Effort Scenes

### Sessions

- [x] Add or tighten a live `sessions` driver in
  `autocode/tests/tui-references/test_reference_scenes.py`
- [x] Add predicates that verify header, entries, filter line, and selection
- [x] Remove the scene stub only if the live surface is honest
- [x] Re-run `make tui-references`
- [x] Re-run `make tui-reference-gap`
- [x] Re-run `make tui-scene-matrix`

### Palette

- [x] Add or tighten a live `palette` driver in
  `autocode/tests/tui-references/test_reference_scenes.py`
- [x] Add predicates that verify header, entries, filter line, and selection
- [x] Remove the scene stub only if the live surface is honest
- [x] Re-run `make tui-references`
- [x] Re-run `make tui-reference-gap`
- [x] Re-run `make tui-scene-matrix`

### Plan

- [x] Decide whether the current `/plan` state stays partial or becomes a real
  scene in the product
- [x] If only HUD plus acknowledgment exists, encode the limitation honestly
  with strict-xfail semantics
- [x] If a real plan panel ships, add a deterministic driver and predicates
- [x] Re-run `make tui-references`
- [x] Re-run `make tui-reference-gap`
- [x] Re-run `make tui-scene-matrix`

Exit gate:

- [x] `sessions` promoted
- [x] `palette` promoted
- [x] `plan` represented honestly in Track 4, either as a promoted real scene or
  a temporary strict-xfail partial scene
  - Verification artifact: `autocode/docs/qa/test-results/20260421-172147-tui-stage1-reference-promotion.md`
  - Historical note: Stage 1 closed with `plan` still partial; this was later
    superseded by the dedicated direct `plan` surface in
    `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`

## Stage 2 — Medium-Gap Surfaces

### Restore

- [x] Design a dedicated restore surface
- [x] Implement checkpoint or restore UI in the live TUI
- [x] Add deterministic trigger or fixture support
- [x] Capture restore in `make tui-scene-matrix`
- [x] Add or tighten Track 4 predicates

### Multi

- [x] Replace the current panel-stack analog with a richer workload surface
- [x] Expose task, subagent, tool, and queue state more clearly
- [x] Capture with mid-run evidence, not only final idle frames
- [x] Add or tighten Track 4 predicates

### Review + Diff

- [x] Implement a first-class `/review` surface
- [x] Implement a first-class `/diff` surface
- [x] Show file identity, diff content, and review actions
- [x] Add deterministic trigger paths
- [x] Capture both in `make tui-scene-matrix`
- [x] Add or tighten Track 4 predicates

Exit gate:

- [x] `restore` becomes direct
- [x] `multi` becomes direct
- [x] `review` becomes direct
- [x] `diff` becomes direct
  - Verification artifact: `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`

## Stage 3 — Search, Escalation, And Command Center

### Grep

- [x] Build a first-class search / grep UI
- [x] Add deterministic search fixture or scenario
- [x] Capture `grep` in the matrix
- [x] Add or tighten Track 4 predicates

### Escalation

- [x] Build a true escalation flow, not only an approval modal
- [x] Show reason, protected path or action, and decision controls
- [x] Add deterministic fixture coverage
- [x] Capture `escalation` in the matrix
- [x] Add or tighten Track 4 predicates

### Command Center

- [x] Design a real command-center or subagent-control surface
- [x] Implement the corresponding visible UI
- [x] Add deterministic trigger support
- [x] Capture `cc` in the matrix
- [x] Add or tighten Track 4 predicates

Exit gate:

- [x] `grep` becomes direct
- [x] `escalation` becomes direct
- [x] `cc` becomes direct
  - Verification artifact: `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`

## Stage 4 — Global Fidelity Pass

- [x] Refine `ready`
- [x] Refine `active`
- [x] Refine `narrow`
- [ ] Refine `recovery`
- [x] Refine `sessions`
- [x] Refine `palette`
- [ ] Refine `multi`
- [ ] Refine `plan`
- [ ] Refine `restore`
- [ ] Refine `review`
- [ ] Refine `diff`
- [ ] Refine `grep`
- [ ] Refine `escalation`
- [ ] Refine `cc`
- [ ] Bind dedicated detail surfaces to real session data instead of static scene text
- [x] Re-run `make tui-reference-gap`
  - Baseline fidelity artifact: `autocode/docs/qa/test-results/20260422-092151-tui-reference-gap.md`
- [x] Re-run `make tui-scene-matrix`
  - Direct-capture matrix artifact: `autocode/docs/qa/test-results/20260422-092415-tui-14-scene-capture-matrix.md`
- [x] Store the first Stage 4 renderer verification artifact
  - `autocode/docs/qa/test-results/20260421-235651-tui-stage4-fidelity-pass.md`
- [x] Store the current Stage 4 structural-fidelity artifact
  - `autocode/docs/qa/test-results/20260422-152822-tui-stage4-overlay-narrow-pass.md`
- [ ] Rebaseline VHS only where chrome changed intentionally

## Ongoing Verification

- [x] Keep `scene_presets.py` aligned with the current truthful capture status
- [x] Keep `tui-reference-scene-trigger-guide.md` aligned with the live product
- [ ] Keep `tui-capture-compare-workflow.md` aligned with the actual scripts
- [x] Store a QA artifact for each meaningful slice
- [x] Post each slice result to `AGENTS_CONVERSATION.MD`

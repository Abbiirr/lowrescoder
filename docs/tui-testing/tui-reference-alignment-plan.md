# TUI Reference Alignment Plan

> Status: proposed post-stabilization work item, not an active directive
> Date: 2026-04-21
> Inputs: `docs/tui-testing/tui-testing-strategy.md`, `autocode/tests/tui-references/README.md`, `autocode/tests/tui-references/manifest.yaml`, `docs/plan/stabilization-and-parity-plan.md`

## Purpose

Define a safe, staged way to compare the live Rust TUI against the
`tui-references` bundle and gradually move the product closer to that design
target without confusing already-shipped regression gates with deferred
feature-parity work.

This plan is intentionally split into:

1. current truth from fresh tests
2. concrete gap inventory
3. promotion order for new reference scenes
4. rules for when to rebaseline VHS versus when to add or remove Track 4 xfails

## Fresh Baseline (2026-04-21)

### Commands run

```bash
make tui-references
make tui-regression
uv run python autocode/tests/pty/pty_smoke_rust_comprehensive.py
```

### Results

- `make tui-references`: PASS
  - manifest regenerated: 14 scenes total, 4 populated hard gates, 10 stubbed
  - extractor/predicate unit tests: 43 passed
  - live Track 4 scenes: 4 passed (`ready`, `active`, `recovery`, `narrow`)
- `make tui-regression`: FAIL
  - failing scenario: `first-prompt-text`
  - failing hard predicate: `basic_turn_returns_to_usable_input`
  - capture still shows the user echo, assistant reply, and returned composer
  - likely issue: predicate checks only the last two non-empty lines, but the
    current composer shape puts the prompt above helper/footer rows
- `pty_smoke_rust_comprehensive.py`: PASS
  - startup and clean `/exit` path passed

## Current Gap Inventory

### A. Test-signal gap

Before using Track 1 as the main truth source for visual-parity work, fix the
`first-prompt-text` false negative or tighten it so it measures the actual
usability requirement instead of a brittle footer position assumption.

Why this comes first:

- the live capture already appears usable
- a noisy regression harness will mis-prioritize future parity work
- every later scene-promotion slice should start from trustworthy baseline gates

### B. Coverage gap

Only 4 of 14 reference scenes are live gates today. The remaining 10 scenes are
still stubbed in `autocode/tests/tui-references/manifest.yaml`:

- `multi` - multitasking
- `plan` - plan panel
- `review` - review state
- `cc` - command center
- `restore` - checkpoint restore
- `sessions` - session browser
- `palette` - command palette
- `diff` - diff focus
- `grep` - search
- `escalation` - permission escalation

### C. Product-surface gap

Some reference scenes are mostly presentation upgrades on top of shipped state,
but others depend on deferred parity features called out in
`docs/plan/stabilization-and-parity-plan.md`:

- `sessions`, `palette`, `plan`: mostly renderer + scene-driver promotion work
- `review`, `diff`, `restore`, `multi`: medium gap; need richer visible panels
- `grep`: depends on a first-class search surface
- `escalation`: depends on the permission/escalation UX
- `cc`: depends on a real command-center or subagent-control surface

### D. Fidelity gap

Track 4 is structural and text-contract based. Pixel fidelity to the HTML
bundle remains a separate later slice. Do not mix "scene is now a live text
gate" with "the renderer matches the mockup pixel for pixel."

## Staged Rollout

### Stage 0 - Make the baseline trustworthy

Goal: get clean status checks before expanding parity scope.

Tasks:

- fix or relax `basic_turn_returns_to_usable_input` in Track 1 so it recognizes
  the current multi-line composer/footer layout
- rerun `make tui-regression`, `make tui-references`, and PTY smoke
- store a fresh verification artifact before any new scene promotion work

Exit gate:

- Track 1 green on `first-prompt-text`
- no new failures in Track 4 or PTY smoke

### Stage 1 - Promote low-risk scenes already close to shipped UI

Target scenes:

- `sessions`
- `palette`
- `plan`

Why these first:

- Stage 2 already shipped visible session picker, palette, and `/plan` wiring
- these are the cheapest scenes to turn from "reference exists" into
  "reference is enforced"

Tasks per scene:

- add a deterministic live driver in `test_reference_scenes.py`
- add scene-specific predicates where generic HUD/composer/footer checks are
  not enough
- start each scene as `xfail(strict=True)` if parity is not complete
- remove the xfail only in the same slice that makes the scene pass

Exit gate:

- 3 more scenes promoted to hard gates
- VHS rebaseline only if visible chrome changed

### Stage 2 - Promote medium-gap inspection and recovery surfaces

Target scenes:

- `review`
- `diff`
- `restore`
- `multi`

Expected work:

- richer diff and review panels
- better checkpoint/restore overlay structure
- a more legible multitask or queue surface than the current minimal counters

Exit gate:

- each promoted scene has a real live driver, deterministic predicates, and no
  remaining strict-xfail

### Stage 3 - Build blocked feature scenes

Target scenes:

- `grep`
- `escalation`
- `cc`

Expected dependencies:

- search or grep UI
- permission escalation UI with protected-path reasoning
- command-center or subagent-control surface

Rule:

- do not promote these scenes by weakening the reference contract
- ship the matching product surface first, then remove xfails

### Stage 4 - Optional high-fidelity pass

Goal: decide whether text-contract parity is enough, or whether the repo wants a
separate pixel-fidelity slice against the HTML bundle.

This stage is separate because it changes the renderer and verification
economics. It should only begin after the structural scene set is mostly green.

## Operating Rules For Every Slice

- Start with tests, not with UI edits.
- Fix harness false negatives before treating them as product failures.
- Promote one small scene set at a time.
- Keep new scenes `xfail(strict=True)` until the matching UI actually ships.
- Rebaseline VHS only when the committed live chrome intentionally changes.
- Keep `current_directives.md` unchanged until the user explicitly chooses this
  plan as the next active directive.

## Immediate Next Move

If the user wants execution to start, begin with Stage 0:

1. repair the `first-prompt-text` Track 1 predicate
2. rerun the baseline matrix
3. then take `sessions`, `palette`, and `plan` as the first Track 4 promotion
   batch

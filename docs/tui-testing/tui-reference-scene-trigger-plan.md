# TUI Reference Scene Trigger Plan

Status: implementation-backed trigger map for the 14 reference scenes

## Goal

Make every reference scene reachable through:

1. a real user-visible trigger in the product
2. a deterministic capture path in the harness
3. a final Track 4 preset contract of `--preset <scene_id>`

That end state is now reached: every row in
`autocode/tests/tui-references/scene_presets.py` is `direct` and every scene
can be captured without fake screenshots, unknown-command fallbacks, or
approximate stand-ins.

## Source Of Truth

- Mockup page order comes from `tui-references/AutoCode TUI _standalone_.html`.
- The corresponding JPGs are `tui-references/autocode_tui_mockup_pages-to-jpg-0001.jpg`
  through `...-0014.jpg`.
- This document treats the standalone HTML ordering as authoritative:
  - `0001 ready`
  - `0002 active`
  - `0003 multi`
  - `0004 plan`
  - `0005 review`
  - `0006 cc`
  - `0007 recovery`
  - `0008 restore`
  - `0009 sessions`
  - `0010 palette`
  - `0011 diff`
  - `0012 grep`
  - `0013 escalation`
  - `0014 narrow`

Note: the standalone HTML ordering remains the authoritative page map even if
older extracted artifacts still show stale labels.

## Trigger Contract

- Each scene gets one canonical manual trigger.
- Each scene gets one canonical harness trigger.
- The harness trigger should converge on
  `uv run python tests/tui-references/capture_frame_sequence.py --preset <scene_id>`.
- The command/key names below are now the shipped canonical trigger contract.
- If the product ever changes a binding, this file and the guide must be
  updated together so each scene still has one truthful canonical path.

## Fourteen-Scene Trigger Matrix

| Scene | Mockup JPG | Mockup title | Current status | Current truthful or evidence trigger | Planned canonical trigger | Capture phase | Work required to make it real |
|---|---|---|---|---|---|---|---|
| `ready` | `0001` | `01 · Ready — quiet continuity` | `direct` | `--preset ready` | Manual: boot to idle session. Harness: `--preset ready`. | idle | Keep existing idle startup stable. |
| `active` | `0002` | `02 · Normal active session` | `direct` | `--preset active` | Manual: start the long-running parser-refactor task so the working state remains visible. Harness: `--preset active`. | mid-run | Keep the parser-refactor fixture deterministic so the working badge, planning transcript, validation box, composer, and footer all remain visible. |
| `multi` | `0003` | `03 · Multitasking / queue pressure` | `direct` | `--preset multi` | Manual: `/multi`. Harness: `--preset multi`. | surface-open | Shipped as a first-class multitasking / queue-pressure surface; remaining work is fidelity. |
| `plan` | `0004` | `04 · Plan emphasis — active step in flight` | `direct` | `--preset plan` | Manual: `/plan`. Harness: `--preset plan`. | surface-open | Shipped as a first-class plan board; remaining work is fidelity. |
| `review` | `0005` | `05 · Review — evidence-first approval` | `direct` | `--preset review` | Manual: `/review`. Harness: `--preset review`. | surface-open | Shipped as a first-class review page; remaining work is fidelity. |
| `cc` | `0006` | `06 · Command center — inside tmux` | `direct` | `--preset cc` | Manual: `/cc`. Harness: `--preset cc`. | surface-open | Shipped as a first-class command-center surface; remaining work is fidelity. |
| `recovery` | `0007` | `07 · Recovery — failure, safe options` | `direct` | `--preset recovery` using `__HALT_FAILURE__` | Manual: trigger the seeded halt/failure path. Harness: `--preset recovery`. | halted | Keep the halted state deterministic and preserve visible recovery actions. |
| `restore` | `0008` | `08 · Restore browser — checkpoints` | `direct` | `--preset restore` | Manual: `/restore`. Harness: `--preset restore`. | surface-open | Shipped as a first-class restore browser; remaining work is fidelity. |
| `sessions` | `0009` | `09 · Session browser — resume or fork` | `direct` | `--preset sessions` | Manual: `/sessions` or `/resume`. Harness: `--preset sessions`. | overlay-open | Keep the session picker deterministic and visually stable. |
| `palette` | `0010` | `10 · Command palette — fuzzy actions` | `direct` | `--preset palette` | Manual: `Ctrl+K`. Harness: `--preset palette`. | overlay-open | Keep the palette deterministic and visually stable. |
| `diff` | `0011` | `11 · Diff focus — lazygit-discipline` | `direct` | `--preset diff` | Manual: `/diff`. Harness: `--preset diff`. | surface-open | Shipped as a first-class diff surface; remaining work is fidelity. |
| `grep` | `0012` | `12 · Search / grep — investigation` | `direct` | `--preset grep` | Manual: `/grep`. Harness: `--preset grep`. | surface-open | Shipped as a first-class search surface; remaining work is fidelity. |
| `escalation` | `0013` | `13 · Approval escalation — protected path` | `direct` | `--preset escalation` | Manual: `/escalation`. Harness: `--preset escalation`. | surface-open | Shipped as a first-class escalation surface; remaining work is fidelity. |
| `narrow` | `0014` | `14 · Narrow / degraded layout` | `direct` | `--preset narrow` | Manual: boot at narrow geometry. Harness: `--preset narrow`. | idle / narrow | Keep the narrow layout deterministic and preserve transcript plus composer visibility. |

## Dependency Bundles

These scenes were implemented in bundles so the product work and fixtures could
land coherently.

### Bundle A: Workload And Planning

Scenes:

- `active`
- `multi`
- `plan`
- `cc`

Shared requirement:

- a deterministic active-work fixture that can emit planning state, multiple
  queued tasks, subagent/task metadata, and tool activity without racing past
  the capture window

### Bundle B: Recovery And Restore

Scenes:

- `recovery`
- `restore`

Shared requirement:

- a seeded failure/checkpoint fixture with a stable checkpoint inventory and a
  real restore browser

### Bundle C: Review And Diff

Scenes:

- `review`
- `diff`

Shared requirement:

- a seeded review fixture with file identity, hunks, evidence metadata, and
  review actions so both surfaces read from the same underlying state

### Bundle D: Search

Scenes:

- `grep`

Shared requirement:

- a deterministic search corpus and result ordering

### Bundle E: Policy And Escalation

Scenes:

- `escalation`

Shared requirement:

- a protected-path or protected-action fixture that reliably pauses before the
  write and exposes the escalation reason plus options

### Bundle F: Overlay Baselines

Scenes:

- `sessions`
- `palette`
- `narrow`
- `ready`

Shared requirement:

- preserve existing direct triggers while the new surfaces land so baseline
  scenes do not regress during the parity push

## Follow-Up Work

The trigger problem is closed. The follow-up work is now:

1. push visual fidelity on the new Stage 2-3 surfaces against the JPG mockups
2. keep the trigger guide, preset registry, and visual-gap reporter aligned
3. tighten Track 4 predicates if any new surface starts drifting semantically

## Definition Of Done

A scene is considered fully triggerable only when all of the following are
true:

- the product exposes a real visible surface for the scene
- a human can enter it through one stable manual path
- the harness can enter it deterministically through `--preset <scene_id>`
- the captured frame proves user-visible behavior, not just internal state
- the trigger guide, preset registry, and capture matrix all describe the same
  path

All five are now true for the current trigger set; remaining work is fidelity.

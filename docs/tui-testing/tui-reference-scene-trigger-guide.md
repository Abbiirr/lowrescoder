# TUI Reference Scene Trigger Guide

Canonical trigger matrix for the 14 scenes in `tui-references/`.

Use this when the task is:

- deciding whether a scene is currently capturable
- choosing the right capture command
- separating "missing fixture" from "missing product surface"

This guide is intentionally honest. As of 2026-04-21, all 14 scenes have a
deterministic live capture path in the product. The remaining gap is visual
fidelity, not triggerability.

## How to use this file

1. Pick the reference scene you want to inspect.
2. Check `Status` first.
3. If the scene is runnable, use the named preset:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py --list-presets
uv run python tests/tui-references/capture_frame_sequence.py --name demo --preset sessions
```

4. If the scene is blocked, do not fake it with a static screenshot. Build the
   missing fixture or product surface first.

## Status Legend

- `direct`: deterministic live capture exists and is worth comparing directly
- `partial`: current product exposes a real but incomplete evidence path for the scene
- `approximate`: current TUI can show a nearby surface, but not the full scene
- `blocked`: no truthful current capture; product surface or fixture is missing

## Scene Matrix

| Scene | Label | Status | Current trigger | Capture phase | Visible evidence to expect | Current blocker / note |
|---|---|---|---|---|---|---|
| `ready` | `01 Ready` | `direct` | `--preset ready` | idle | HUD, empty body, composer, footer | Baseline idle surface |
| `active` | `02 Active` | `direct` | `--preset active` | mid-run | `● working`, planning + edit transcript, live validation box, composer/footer still intact | Uses the long-running parser-refactor fixture so the mid-run working state survives capture |
| `multi` | `03 Multitasking` | `direct` | `--preset multi` | surface-open | queue-pressure transcript, prioritized/blocked lines, composer preserved | Dedicated multitasking surface now exists; remaining gap is fidelity |
| `plan` | `04 Plan` | `direct` | `--preset plan` | surface-open | planning header, queued/active rows, validation section | Dedicated plan surface now exists; remaining gap is fidelity |
| `review` | `05 Review` | `direct` | `--preset review` | surface-open | file identity, review-needed section, approve/reject actions | Dedicated review surface now exists; remaining gap is fidelity |
| `cc` | `06 Command center` | `direct` | `--preset cc` | surface-open | delegate rows, subagent section, risk/validation content | Dedicated command-center surface now exists; remaining gap is fidelity |
| `recovery` | `07 Recovery` | `direct` | `--preset recovery` | halted | error banner plus recovery actions (`Retry`, `Inspect`, `Restore`, `Rewind`, `Compact`, `Planning`) | Current recovery slice is live and capturable |
| `restore` | `08 Restore` | `direct` | `--preset restore` | surface-open | checkpoint list, restore action, diff-from-here action | Dedicated restore browser now exists; remaining gap is fidelity |
| `sessions` | `09 Sessions` | `direct` | `--preset sessions` | overlay-open | session picker header, visible entries, filter line | Live Track 4 gate now exists; remaining gap is visual fidelity, not capture honesty |
| `palette` | `10 Palette` | `direct` | `--preset palette` | overlay-open | palette header, visible entries, filter line | Live Track 4 gate now exists; remaining gap is visual fidelity, not capture honesty |
| `diff` | `11 Diff focus` | `direct` | `--preset diff` | surface-open | file list, focused hunk, approval pattern, raw command block | Dedicated diff surface now exists; remaining gap is fidelity |
| `grep` | `12 Search` | `direct` | `--preset grep` | surface-open | search query, result list, attach/open hints | Dedicated search surface now exists; remaining gap is fidelity |
| `escalation` | `13 Escalation` | `direct` | `--preset escalation` | surface-open | protected-path reason, choices, approval controls | Dedicated escalation surface now exists; remaining gap is fidelity |
| `narrow` | `14 Narrow` | `direct` | `--preset narrow` | idle | same as `ready`, but at narrow geometry | Used to expose wrapping and layout pressure |

## Current Preset Inventory

The preset registry lives in:

- `autocode/tests/tui-references/scene_presets.py`

List the presets:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py --list-presets
```

Run one preset:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py --name sessions-demo --preset sessions
```

Outputs land under:

- `autocode/docs/qa/tui-frame-sequences/<stamp>/<name>/`

Each run stores:

- sequential `PNG` frames
- matching `TXT` frame dumps

## Remaining work

The trigger problem is now closed. The next work is Stage 4 fidelity:

- spacing and density for the new Stage 2-3 surfaces
- review/diff/search/escalation typography and grouping
- command-center and multitask information hierarchy
- overlay sizing and proportion against the mockup JPGs

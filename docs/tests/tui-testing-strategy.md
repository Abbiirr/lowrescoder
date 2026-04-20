# TUI Testing Strategy

This is the required validation policy for interactive terminal UI changes in this repo. Use it for Go Bubble Tea TUI, Python inline chat, Textual TUI, Rust TUI, and any terminal-driven interactive path.

`docs/tests/pty-testing.md` explains how to run PTY checks. This file defines what must be tested before a TUI-affecting change is considered done.

**Rust TUI binary resolution:** All four testing dimensions support `$AUTOCODE_TUI_BIN`. For the Rust implementation, set:
```bash
export AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui
```

---

## TUI Testing Matrix (fresh-agent onramp)

The repo has **four complementary TUI testing dimensions**. They answer different questions; use the right one for the change you made. Each has its own tree with its own README.

| # | Dimension | Question it answers | Entry command | Substrate + README |
|---|---|---|---|---|
| 1 | **Runtime invariants** (Track 1) | Does the TUI start, accept input, render warnings correctly, and not leak debug state? | `make tui-regression` | `autocode/tests/tui-comparison/README.md` |
| 2 | **Design-target ratchet** (Track 4) | Does the live TUI render the layout the mockup bundle specifies? Each scene is a `strict=True` xfail that flips to a hard gate when the matching UI feature ships. | `make tui-references` | `autocode/tests/tui-references/README.md` |
| 3 | **Self-vs-self PNG regression** (VHS) | Did today's TUI render pixel-identical to yesterday's committed baseline? | `uv run python autocode/tests/vhs/run_visual_suite.py` | `autocode/tests/vhs/README.md` |
| 4 | **PTY smoke** (live gateway or mock) | Does the real binary + real backend path work end-to-end in a real terminal? | `uv run python autocode/tests/pty/<script>.py` (see README) | `autocode/tests/pty/README.md` |

**When to use which:**

- **Changed runtime invariants (crash, composer, warnings, pickers, queues)** → Track 1.
- **Implementing a UI feature that matches a mockup scene** → Track 4 (the ratchet's XPASS is the signal you're done; flip the `xfail` off).
- **Changed layout / color / palette / alt-screen / scrollback** → VHS self-regression (commit new baseline or prove no drift).
- **Changed backend/TUI JSON-RPC contract or startup timeout** → PTY smoke.

**Architecture source of truth:** `PLAN.md` §1g (all four tracks are documented there; §1g Track 4 is the canonical spec for the design-target ratchet).

**Review chain for Track 4:** `AGENTS_CONVERSATION.MD` Entries 1182 → 1200.

### Do not confuse the dimensions

A fresh agent landing on a failing test needs to know which dimension it belongs to before "fixing" it:

- Track 1 failure → actual runtime regression; fix the TUI code.
- Track 4 `xfail` → **expected** until the matching UI feature ships; **do not remove the decorator** unless you shipped the feature.
- VHS diff → either intentional layout change (re-baseline with `--update` and explain) or unintentional regression (fix).
- PTY smoke failure → probably a backend contract change or gateway issue; check `docs/tests/pty-testing.md`.

---


## Rule

If you change interactive terminal behavior, you must run the full checklist in this file.

Do not treat unit tests, snapshots, or `go test` alone as sufficient for TUI work.

If you cannot run one of the required checks, do not silently skip it:
- state the blocker explicitly
- record what was not run
- do not claim the TUI work is complete without user acknowledgment

## What Counts As TUI Work

Treat any of the following as TUI work:
- startup, prompt, focus, or shutdown behavior
- rendering, layout, streaming, scrollback, status bar, task panel, or approval UI
- keyboard handling, palette behavior, slash-command UX, pickers, interrupts, queues
- backend-to-TUI notifications, warning/error rendering, or terminal output classification
- inline vs alt-screen behavior

## Required Validation Matrix

Run all of these for every TUI change unless the user explicitly waives a check.

### 1. Startup Path

Prove the real interactive entrypoint starts into a usable state.

Required checks:
- startup reaches a usable prompt, header, or explicit timeout fallback
- no panic, traceback, or dead start
- no obviously malformed terminal output on boot

Good evidence:
- PTY transcript or scripted PTY capture

### 2. Basic Chat Turn

Prove a normal user turn still works.

Required checks:
- user can send one plain message
- assistant output appears in the expected visible region
- the turn returns to a usable input state
- no unexpected picker or modal appears after the turn

Good evidence:
- PTY artifact showing one send/response cycle

### 3. Slash / Picker Surface

Prove the command surface is still usable.

Required baseline checks:
- `/help` or equivalent command discovery responds visibly
- `/model` works without corrupting the session
- if the TUI supports a picker or palette, it opens and closes cleanly

If your change touched another command, test that command too.

### 4. Keyboard Interaction

Prove important control keys still behave correctly.

Required baseline checks:
- Enter submits when expected
- Escape cancels/closes when expected
- Ctrl+K works if the TUI supports the command palette
- Ctrl+C behavior is correct for the current runtime contract

If your change touched another binding, test that binding too.

### 5. Warning / Error Rendering

Prove backend stderr and runtime errors are rendered with the right severity.

Required checks:
- warnings do not render as fatal red blocking errors
- real errors still surface clearly
- no raw traceback/panic text leaks into the normal happy path

This check is mandatory for any backend/TUI notification change.

### 6. Queue / Interrupt / Streaming Cleanliness

Prove the TUI does not leak internal state into the visible stream.

Required checks:
- no queue/debug text leaks into chat output
- no duplicate or stuck spinner/status junk remains after the turn
- interrupt/cancel/followup behavior stays coherent if touched

If the change touched streaming, queues, or interrupts, this is a hard gate.

### 7. Narrow / Real Terminal Constraints

Prove the UI still behaves in a real terminal geometry.

Required checks:
- run at least one narrow-ish terminal size
- no catastrophic wrapping, invisible prompt, or broken footer/status bar
- no obvious corruption from resize or constrained width

You do not need a full visual design review every time, but you do need to prove the layout still functions.

### 8. Changed-Feature Regression

Prove the feature you changed actually works in the live TUI, not just in a unit test.

Required checks:
- run the smallest real scenario that exercises the exact behavior you changed
- assert on visible behavior, not just internal state
- include at least one regression assertion for the failure mode you were fixing

Examples:
- warning classification fix: show warning is visible but not fatal
- `/followup` fix: show queued follow-up drains through normal chat path
- inline-mode fix: show `--inline` changes terminal behavior

## Required Test Layers

For TUI work, validation should usually include all four:

1. Focused unit or component tests for the changed logic
2. Real PTY-backed validation of the interactive path
3. **Visual snapshot regression** (`autocode/tests/vhs/run_visual_suite.py`) when the change touches layout, color, picker behavior, palette, alt-screen, or scrollback. Any visual-behavior change requires either (a) a green diff against the committed reference PNGs, or (b) a deliberate `--update` that replaces the affected references and is explicitly called out in the review. See `autocode/tests/vhs/README.md` for the detailed guide.
4. Stored artifact under `docs/qa/test-results/`

If any layer is missing, call it out explicitly.

## Verification Criteria

A TUI change is only ready to report as complete when all of the following are true:
- focused tests for the changed code are green
- the full validation matrix above was run
- a fresh artifact was stored under `docs/qa/test-results/`
- the artifact demonstrates the changed behavior and the absence of the known regression
- docs and runtime behavior describe the same contract

## Exit Gates

Do not mark TUI work complete if any of these are true:
- no PTY or real-terminal evidence was produced
- the changed feature was only tested indirectly
- startup, basic chat, picker/palette, or warning/error behavior was not checked
- the artifact is stale or from a different tree state
- docs still overstate what is implemented
- the change touches visual surface (layout/color/picker/palette/alt-screen/scrollback) and no visual-suite diff or baseline update is in the review

## Suggested Artifact Contents

Each stored TUI artifact should say:
- entrypoint used
- terminal size
- whether the run was manual or scripted
- commands/inputs sent
- what was expected
- what was observed
- pass/fail per checklist item

## Minimal Reporting Template

Use language like this in final reports or comms:

- Startup: passed
- Basic chat turn: passed
- Slash/picker surface: passed
- Keyboard interaction: passed
- Warning/error rendering: passed
- Queue/stream cleanliness: passed
- Narrow terminal check: passed
- Changed-feature regression: passed
- Artifact: `docs/qa/test-results/<name>.md`

If any item is not run, say that explicitly and why.

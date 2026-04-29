# TUI Rendering

## Purpose

Codifies the user-locked render contract for the Rust TUI: full-screen rendering, terminal resizing, multiple terminal sizes, and native scrollback preservation. This is the authoritative contract for all TUI rendering behavior.

## User-visible TUI surfaces

- Full-screen terminal rendering: the TUI occupies the entire terminal window
- Responsive layout: adapts to terminal width and height changes
- Native scrollback preserved: user can scroll up in the terminal to see history
- No flicker: rendering updates are differential (not full redraws)
- Composer always visible at the bottom
- Status bar at the top with model, provider, mode, cost

## Backend contract

### User-locked render contract (2026-04-22)

The following requirements are user-locked and non-negotiable:

1. **Full-screen render**: default inline TUI must render full-screen
2. **Terminal resizing works**: layout adapts dynamically to terminal size changes
3. **Multiple sizes validated**: rendering must be correct at various terminal dimensions
4. **Native scrollback preserved**: terminal native scrollback buffer must remain usable

Reference artifact: `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`

### Layout contract

```
┌─────────────────────────────────┐
│ Status bar (fixed, top)          │
├─────────────────────────────────┤
│                                 │
│ Transcript / focus region       │
│ (scrollable, fills space)       │
│                                 │
├─────────────────────────────────┤
│ Queue strip (1 row, if active)  │
├─────────────────────────────────┤
│ Composer (fixed, bottom)        │
├─────────────────────────────────┤
│ Hint line (1 row, bottom)       │
└─────────────────────────────────┘
```

### Rendering rules

- Inline mode (default): renders in the normal terminal buffer, preserving scrollback
- Alt-screen mode (`--altscreen`): uses alternate screen buffer, no scrollback
- Differential rendering: only changed regions are redrawn
- No centered overlays for any primary surface
- Side rail allowed only for: review approval, protected-path escalation, command-center power mode
- Expanded queue is a bottom drawer (not overlay)

## Event types

Rendering is frontend-local; no backend events drive layout decisions. The frontend reacts to:
- Terminal resize events (crossterm `Event::Resize`)
- Content changes (new tokens, tool calls)
- State transitions (idle → active → recovery)

## State/reducer behavior

- `AppState.terminal_size` tracks current dimensions
- On resize: layout recalculated, content reflowed
- `AppState.altscreen` flag controls inline vs alt-screen mode
- Rendering pipeline: state diff → layout computation → ratatui draw

## Persistence behavior

- Terminal size is not persisted (re-detected on startup)
- Alt-screen preference saved via `/tui` command to config

## Commands/keybindings

| Command | Action |
|---|---|
| `autocode` | Launch inline TUI (default) |
| `autocode --altscreen` | Launch alt-screen TUI |
| `/tui` (`/screen`) | Show or save default TUI mode |

## Failure/recovery behavior

- If terminal is too small (< minimum dimensions), show a minimum-size warning
- If resize fails, keep the last known good layout
- If rendering panics, the terminal must be left in a clean state (raw mode exited)

## Tests and fixtures

- Track 1 runtime invariants: `autocode/tests/tui-comparison/` — no crash, composer visible
- Track 4 design-target ratchet: `autocode/tests/tui-references/` — 14 named scenes
  - Scenes: `ready`, `active`, `multi`, `plan`, `review`, `cc`, `recovery`, `restore`, `sessions`, `palette`, `diff`, `grep`, `escalation`, `narrow`
- VHS self-regression: `autocode/tests/vhs/`
- PTY smoke: `autocode/tests/pty/`
- Fullscreen verification artifact: `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`

## Acceptance criteria

- [ ] Full-screen render contract documented and user-locked
- [ ] Terminal resize handling documented
- [ ] Multiple terminal sizes validated
- [ ] Native scrollback preserved in inline mode
- [ ] Layout contract with ASCII diagram included
- [ ] No centered overlays for primary surfaces
- [ ] All 14 Track 4 scenes referenced as test fixtures

## Open questions

- Minimum terminal dimensions for usable rendering?
- Should the status bar be collapsible for narrow terminals?
- How to handle extremely narrow terminals (< 40 columns)?
- Should alt-screen mode support a persistent config preference?

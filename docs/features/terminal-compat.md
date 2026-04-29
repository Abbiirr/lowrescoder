# Terminal Compatibility

## Purpose

Defines the terminal compatibility requirements for the Rust TUI: tmux compatibility, integrated-terminal compatibility, no-flicker rendering, ANSI-safe wrapping, terminal-width-aware truncation, and synchronized output support.

## User-visible TUI surfaces

- Correct rendering in standard Linux terminals (xterm, alacritty, kitty, gnome-terminal)
- Correct rendering inside tmux sessions
- Correct rendering in VS Code integrated terminal and similar IDE terminals
- Smooth, flicker-free updates during streaming
- Proper line wrapping at terminal boundaries
- Truncated content (not wrapping awkwardly) for narrow terminals

## Backend contract

### Compatibility requirements

1. **tmux compatibility**: TUI must render correctly inside tmux with status bars and panes
2. **Integrated-terminal compatibility**: VS Code terminal, JetBrains terminal, and similar IDE-integrated terminals
3. **No-flicker rendering**: differential updates only; no full-screen redraws on content changes
4. **ANSI-safe wrapping**: line breaks respect terminal width; no mid-character wraps
5. **Terminal-width-aware truncation**: long lines truncated with ellipsis, not wrapping
6. **Synchronized output**: if terminal supports synchronized output mode (e.g., kitty), use it for tear-free rendering

### Stack

- `crossterm` 0.28: terminal abstraction, raw mode, events
- `ratatui` 0.29: layout, widgets, differential rendering
- `tokio` 1.x: async runtime
- Inline mode (default): renders in normal terminal buffer
- Alt-screen mode (`--altscreen`): uses alternate screen buffer

### Known compatibility notes

- `portable-pty` 0.8 used for PTY management
- Mouse events may not work in all terminal multiplexers
- Bracketed paste is supported but may vary by terminal

## Event types

No backend events. Compatibility is frontend-local behavior.

## State/reducer behavior

- On startup: detect terminal capabilities (size, color support, synchronized output)
- On resize: recalculate layout, reflow content
- ANSI escape sequences are emitted through crossterm's cross-platform API
- Synchronized output: wrap drawing operations in sync markers when supported

## Persistence behavior

- No persistence for compatibility settings
- Terminal capabilities are detected fresh on each launch

## Commands/keybindings

| Command | Action |
|---|---|
| `autocode` | Launch with inline mode (compatible with all terminals) |
| `autocode --altscreen` | Launch with alt-screen (may differ in tmux) |

## Failure/recovery behavior

- If terminal does not support required features, degrade gracefully
- If crossterm fails to enter raw mode, show an error and exit cleanly
- If rendering produces artifacts, next frame redraws the affected region

## Tests and fixtures

- Track 1 runtime invariants: `autocode/tests/tui-comparison/` — basic rendering tests
- Track 4 design-target ratchet: `autocode/tests/tui-references/` — includes `narrow` scene for width testing
- PTY smoke: `autocode/tests/pty/` — real terminal behavior
- VHS regression: `autocode/tests/vhs/` — visual regression

## Acceptance criteria

- [ ] tmux compatibility documented
- [ ] Integrated-terminal compatibility documented
- [ ] No-flicker requirement stated
- [ ] ANSI-safe wrapping requirement stated
- [ ] Terminal-width-aware truncation documented
- [ ] Synchronized output support documented (opt-in)
- [ ] Reference to 14-scene Track 4 ratchet for visual validation

## Open questions

- Should the TUI detect and warn about known-incompatible terminals?
- Should mouse support be disabled by default inside tmux?
- What is the minimum color support required (16-color vs 256-color vs true-color)?
- Should synchronized output be auto-detected or require explicit opt-in?

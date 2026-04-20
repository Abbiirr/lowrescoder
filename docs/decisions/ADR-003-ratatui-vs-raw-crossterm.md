# ADR-003: Ratatui vs Raw Crossterm

> Status: ACCEPTED  
> Date: 2026-04-19

## Summary

Choose ratatui for layout/widgets and document tui-textarea spike verdict.

## Ratatui Choice

**ratatui 0.29** — provides frame/widget tree, List/Paragraph/Block components, 2-3× less render code vs raw crossterm drawing.

## tui-textarea Spike

**Verdict: REJECTED**

The tui-textarea crate ships default keybindings that collide with app-owned controls:

| Default keybinding | App-owned meaning |
|---|---|
| `Ctrl+K` | Open command palette |
| `Ctrl+C` | Cancel / steer / exit |
| `Ctrl+J` | Confirm/newline |
| `Ctrl+U` | Clear line |
| `Ctrl+R` | Frecency history search |

**Even if individual bindings can be suppressed**, the library's event handling model doesn't provide full control over the pipeline needed for our specific keybinding semantics (multi-level Ctrl+C for steer).

**Hand-roll composer in M4** — a simple `Vec<char>` line buffer with cursor tracking is ~100 LOC and has zero surprise behavior.

## Implementation Decision

M4 will implement hand-rolled composer:
- `src/ui/composer.rs` with `ComposerState { lines: Vec<String>, cursor_line: usize, cursor_col: usize }`
- Insert/Backspace/Delete/Left/Right/Alt+Enter support
- Up/Down history recall with frecency sorting

## References

- `rust_migration_plan.md §5.2` — M1 spike candidates
- `rust_migration_plan.md §8` — Composer feature checklist
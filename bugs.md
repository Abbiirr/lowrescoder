# UI Bug Tracker — Inline REPL

Tracked bugs found during manual QA of `uv run hybridcoder chat` (Phase 2D).

## Open Bugs

| ID | Severity | Description | File | Status |
|----|----------|-------------|------|--------|
| BUG-1 | Medium | Input border NOT full-width (capped at 120 chars) | `renderer.py:61` | Fixed (border removed) |
| BUG-2 | High | Cannot type during LLM generation | `app.py:246-386` | Fixed (Escape/Ctrl+C cancel) |
| BUG-3 | N/A | Input box not fixed at bottom | `app.py:246-250` | Closed (by design) |
| BUG-4 | Low | /resume shows long titles without truncation | `commands.py:146-147` | Fixed |
| BUG-5 | Medium | Double ">" in input area | `app.py:239-244` | Fixed (border removed) |
| BUG-6 | Low | Empty prompt box at top of conversation | `app.py:248-250` | Fixed (border removed) |
| BUG-7 | High | No way to cancel/interrupt generation | `app.py:260-273` | Fixed (Escape + Ctrl+C) |
| BUG-8 | Medium | No visual feedback during generation wait | `app.py:337-366` | Fixed ("Thinking..." indicator) |

## Resolution Notes

### BUG-1, BUG-5, BUG-6 — Removed bordered input box
The bordered input box (`╭───`/`╰───`) caused three bugs at once. Claude Code does NOT use bordered input — it uses `> ` with a separator above. Removed borders, simplified prompt to `❯ `.

### BUG-3 — Closed as by-design
Claude Code does NOT pin the input at the bottom. It uses inline scrollback like we do. Once BUG-2/7 are fixed, the prompt reappears immediately after cancellation.

### BUG-2, BUG-7 — Escape/Ctrl+C cancellation
Wrapped `_handle_input()` in `asyncio.Task`. Added `_listen_for_escape()` using `msvcrt` on Windows. `asyncio.wait(FIRST_COMPLETED)` races agent task vs escape listener.

### BUG-4 — Title truncation
Titles in `/resume` and `/sessions` capped at 40 chars with `...` suffix.

### BUG-8 — "Thinking..." indicator
Static `[dim italic]Thinking...[/dim italic]` printed before LLM response. Stays in scrollback (safe on Windows, no ANSI cursor tricks).

## Constraints

- `patch_stdout()` is BROKEN on Windows (ANSI corruption). Cannot use for concurrent I/O.
- Sequential REPL model: prompt -> process -> output -> prompt.
- Escape listener uses `msvcrt.kbhit()`/`msvcrt.getch()` on Windows, `select` on Unix.

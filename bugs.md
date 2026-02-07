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
| BUG-9 | Medium | Prompt can render on the same line as separator (e.g. `──────❯`) | `renderer.py:print_separator()` | Fixed (CRLF + wrap guard) |
| BUG-10 | Low | Prompt spacing too low (extra blank line between turns) | `renderer.py:end_streaming()`, `renderer.py:print_turn_separator()` | Fixed |
| BUG-11 | Low | Ctrl+C at idle after previous generation can show "generation cancelled" | `app.py:run()` | Fixed (`_agent_task` tracks active generation) |
| BUG-12 | Medium | Status/footer line not visible/obvious at prompt on some terminals | `app.py:_ensure_prompt_session()` | Fixed (bottom_toolbar + rprompt fallback) |
| BUG-13 | Medium | Streamed output feels like it appears "inside" the input line | `app.py:run()`, `renderer.py:print_user_turn()` | Fixed (erase_when_done + reprint user turn) |

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

### BUG-9 — Prompt appended to separator
Some terminals (notably Windows) can leave the cursor in a non-zero column after printing a full-width separator with `\\n`, causing the next prompt to render on the same line. Fixed by printing separators with CRLF and avoiding last-column wrap edge cases (`console.width - 1`).

### BUG-10 — Prompt spacing too low
Extra newlines at the end of streaming and in the turn separator made the next prompt feel “too low”. Fixed by centralizing spacing in the REPL loop and avoiding double-blank lines.

### BUG-11 — Ctrl+C idle vs generation semantics
`_agent_loop` is a long-lived object, so its existence is not a reliable indicator of “generation in progress”. Fixed by tracking the active generation task and using that for Ctrl+C behavior.

### BUG-12 — Status/footer visibility
Some terminals/users miss the prompt footer line (or it's not captured in copy/paste). Improved prompt-time visibility by using prompt_toolkit `bottom_toolbar` (full status) plus a short `rprompt` fallback.

### BUG-13 — Output appears "inside" input
To make the prompt feel like a distinct input area:
- the editable prompt is erased after submit (`erase_when_done=True`)
- the submitted turn is re-printed into scrollback (`InlineRenderer.print_user_turn()`)
- a full-width separator is printed immediately after the submitted turn so model/tool output is always in a separate block

## Constraints

- `patch_stdout()` is BROKEN on Windows (ANSI corruption). Cannot use for concurrent I/O.
- Sequential REPL model: prompt -> process -> output -> prompt.
- Escape listener uses `msvcrt.kbhit()`/`msvcrt.getch()` on Windows, `select` on Unix.

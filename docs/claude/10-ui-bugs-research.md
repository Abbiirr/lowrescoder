# UI Bugs Research — Inline REPL

## Context

Phase 2D (Claude Code UX clone) was completed but manual QA revealed 8 rendering issues in `uv run hybridcoder chat`. This document captures research findings, prompt_toolkit constraints, Windows limitations, and Claude Code behavior analysis.

## Key Findings

### 1. prompt_toolkit Bordered Input Causes Multiple Bugs

The bordered input box (`╭───`/`╰───` drawn by `print_input_border()`) causes:
- **BUG-5**: Double `>` — `FormattedText` includes `│ ` + `❯ `, rendered after the top border creates visual duplication
- **BUG-6**: Empty box — `print_input_border(top=True)` runs before `prompt_async()`, showing ghost empty border
- **BUG-1**: Width mismatch — border capped at `min(console.width, 120)` while separators use full `console.width`

**Research**: Claude Code does NOT use bordered input. It uses a plain `> ` prompt with a separator above. Removing borders eliminates 3 bugs simultaneously.

### 2. patch_stdout() is Broken on Windows

Documented in archived Entries 79, 81, 84:
- ANSI escape corruption when prompt_toolkit's `patch_stdout()` is used with Rich output on Windows Terminal
- Caused garbled output, misaligned text, phantom characters
- **Decision**: Removed `patch_stdout()` entirely. Sequential REPL model is the correct approach.

### 3. Cancellation Architecture

**Problem**: Sequential REPL blocks on `_run_agent()`. During generation, user cannot type or cancel.

**Research on approaches**:
- `asyncio.Task` + `asyncio.wait(FIRST_COMPLETED)` — clean, standard asyncio pattern
- `_listen_for_escape()` in thread executor — `msvcrt.kbhit()` on Windows, `select` on Unix
- `signal.SIGINT` handler — unreliable in async context on Windows
- prompt_toolkit `run_in_terminal()` — doesn't help for non-prompt operations

**Chosen approach**: Race `asyncio.Task(_handle_input)` vs `asyncio.Task(_listen_for_escape)`. First to complete wins. Loser gets cancelled.

### 4. Windows Key Listening

On Windows, `msvcrt` module provides non-blocking key input:
- `msvcrt.kbhit()` — returns True if a key is waiting
- `msvcrt.getch()` — reads a single byte
- Escape key = `b'\x1b'`
- Ctrl+C during async operations may not propagate to prompt_toolkit — needs explicit handling

On Unix:
- `sys.stdin` + `select.select()` with `tty.setraw()`
- Or `termios` for raw mode

### 5. Claude Code Behavior Analysis

Observed Claude Code behavior (for parity):
- No bordered input box — just `> ` prompt
- Full-width separator between turns
- "Thinking..." appears dim/italic before first LLM chunk
- Escape cancels generation immediately
- Ctrl+C also cancels (double Ctrl+C exits)
- Input prompt scrolls with content (NOT pinned at bottom)

### 6. "Thinking..." Indicator

Simple static text approach chosen over spinner/animation:
- Static `[dim italic]Thinking...[/dim italic]` — safe on Windows, no ANSI cursor tricks
- Stays in scrollback naturally
- LLM response streams below it
- No need for `patch_stdout()` or cursor manipulation
- Claude Code uses a similar static "Thinking..." before streaming begins

### 7. Prompt Appended To Separator (Windows Newline / Last-Column Wrap)

**Observed bug:** The next `prompt_toolkit` prompt can appear on the same line as a full-width separator, for example:

`────────────────────────────❯ hello`

**Likely cause:** Printing a full-width line with `\\n` can leave the cursor at a non-zero column (or trigger a wrap edge case in the last column). `prompt_toolkit` then renders the next prompt at the current cursor position.

**Fix:** Print separators with `end="\\r\\n"` and avoid printing into the terminal's last column (`console.width - 1`) to prevent wrap. This keeps prompts starting at column 0 consistently across terminals.

### 8. Status Line Visibility + "Output Inside Input" Perception

Two UX issues were repeatedly reported in Windows manual QA:

1. The status/footer line (model/tokens/edits/files) is easy to miss, and is not captured in plain text copy/paste.
2. Streaming output can feel like it appears "inside" the input line because the editable prompt is left in scrollback after submit.

**Mitigations (without using `patch_stdout()`):**

- Use prompt_toolkit `bottom_toolbar` for the full status line, and also configure a short `rprompt` fallback (right-aligned on the prompt line) for visibility.
- Use `PromptSession(erase_when_done=True)` so the editable input bar is not left in scrollback, then re-print the submitted turn into scrollback (so the chat transcript remains readable).
- Print a full-width separator immediately after the submitted turn so model/tool output starts in a distinct block (prevents "output inside input" perception even when the terminal erases the prompt imperfectly).

## Files Modified

| File | Changes |
|------|---------|
| `src/hybridcoder/inline/app.py` | Remove border calls, simplify prompt, add cancellation logic, status/footer rendering |
| `src/hybridcoder/inline/renderer.py` | Fix border width, add `print_thinking_indicator()`, add `print_user_turn()` |
| `src/hybridcoder/tui/commands.py` | Truncate titles in `/resume` and `/sessions` |
| `tests/unit/test_inline_app.py` | Update REPL tests, add cancellation tests |
| `tests/unit/test_inline_renderer.py` | Add border width test, thinking indicator test, user turn print test |
| `tests/unit/test_commands.py` | Add title truncation test |

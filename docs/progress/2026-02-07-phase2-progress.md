# Phase 2 Progress (Resumable) — 2026-02-07

This doc is a checkpoint so we can resume work quickly if the machine powers off.

## TL;DR

Phase 2 (Textual TUI + inline mode) is largely implemented, but there are still UX issues in **inline mode** on Windows:

- **Prompt placement bug:** the prompt appears on the same line as the separator (example: `──────❯ hello`). Prompt must start on its own line.
- **Prompt spacing:** input feels too low (extra vertical whitespace around turns).
- **Ctrl+C state bug:** Ctrl+C at idle after a previous generation can be treated as “cancel generation” because the REPL uses `_agent_loop` existence as a proxy for “generation active”.

Work to address this is tracked in `AGENTS_CONVERSATION.MD`:
- Active thread: **Entry 114** (directed to Codex)
- Current pre-task: **Entry 115**

## Environment Notes (WSL vs Windows)

Repo path: `/mnt/k/projects/ai/lowrescoder` (WSL on a Windows drive).

This repo may be used from both Windows and WSL. If a Windows-created virtualenv exists at `.venv/`
(Windows layout: `Lib/`, `Scripts/`), `uv` under WSL can error when it tries to remove/manage it:

- Example failure: “failed to remove directory `.venv/Lib`: Input/output error”

### Use a separate venv for Codex on WSL

We created a WSL-native venv at `.venv-codex/`.

Use this env var for **all** uv commands in WSL:

```bash
export UV_PROJECT_ENVIRONMENT=.venv-codex
```

Setup:

```bash
UV_PROJECT_ENVIRONMENT=.venv-codex uv sync --extra dev
```

Verification commands:

```bash
UV_PROJECT_ENVIRONMENT=.venv-codex uv run pytest tests/ -v
UV_PROJECT_ENVIRONMENT=.venv-codex uv run ruff check src/ tests/
UV_PROJECT_ENVIRONMENT=.venv-codex uv run mypy src/hybridcoder/
```

## Where The Inline UX Lives

Files to focus on for the current bugs:

- `src/hybridcoder/inline/app.py`
  - `run()` (REPL loop + Ctrl+C behavior)
  - `_handle_input_with_cancel()` (Escape/Ctrl+C cancellation race)
  - `_listen_for_escape()` (platform key listener)
- `src/hybridcoder/inline/renderer.py`
  - `print_separator()` / `print_turn_separator()` (separator line behavior)
  - `end_streaming()` (extra whitespace after streaming)

Tests that cover expected behavior:

- `tests/unit/test_inline_app.py` (Ctrl+C, escape cancellation, REPL loop)
- `tests/unit/test_inline_renderer.py` (separators, thinking indicator, streaming)

## Current Work Plan (Next Session)

This session implemented the above plan (see “Completed Fixes” below). Remaining work is mainly
manual verification on Windows terminals.

## Completed Fixes (2026-02-07)

### Prompt placement + spacing (inline mode)

- `src/hybridcoder/inline/renderer.py`
  - `print_separator()` now:
    - prints with `end="\\r\\n"` (CRLF) so prompt_toolkit prompts reliably start at column 0
    - uses `console.width - 1` to avoid last-column terminal wrap edge cases
  - `print_turn_separator()` no longer prints an extra blank line (prompt appears higher).
  - `end_streaming()` no longer adds an extra blank line after streaming.
  - `end_streaming()` is now idempotent via `_streaming_active` (prevents double-newline on cancel paths).

### Ctrl+C idle vs generation (inline mode)

- `src/hybridcoder/inline/app.py`
  - Tracks “generation in progress” using `self._agent_task`, not `_agent_loop` existence.
  - Ctrl+C at idle always shows the quit warning (even after a previous generation).
  - KeyboardInterrupt during generation is handled inside `_handle_input_with_cancel()` so tasks are
    cancelled cleanly and the streaming line is terminated before returning to the prompt.
  - Removed extra “[Cancelled]” system message to avoid duplicate cancellation output.

### Tests updated

- `tests/unit/test_inline_app.py` updated to reflect corrected Ctrl+C semantics.

## Verification (WSL / Codex env)

All run under `.venv-codex`:

- `uv run pytest tests/ -v`: **488 passed, 9 deselected**
- `uv run ruff check src/ tests/`: **All checks passed**
- `uv run mypy src/hybridcoder/`: **Success (no issues)**

## What Still Needs Windows Manual QA

Run on Windows:

- `uv run hybridcoder chat`
  - Confirm the separator is on its own line, and the next prompt is not appended to it.
  - Confirm the prompt spacing feels tighter (no extra blank line between turns).

# Phase 2 Progress (Resumable) — 2026-02-07

This doc is a checkpoint so we can resume work quickly if the machine powers off.

## TL;DR

Phase 2 (Textual TUI + inline mode) is implemented, and inline mode now defaults to a Claude Code-style always-on prompt:

- **Visible concurrent typing (default):** while the assistant streams output, the prompt stays active and keystrokes are visible.
- **Submit while generating:** new messages are **queued** (FIFO) and run after the current generation completes or is cancelled.
- **Fallback:** use `hybridcoder chat --sequential` if your terminal has issues with `patch_stdout(raw=True)` (sequential mode still supports blind type-ahead buffering so keystrokes aren’t dropped).

Work to address this is tracked in `AGENTS_CONVERSATION.MD` (active threads around Entry 125+).

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

### Type-ahead while generating (inline mode)

- `src/hybridcoder/inline/app.py`
  - `_listen_for_escape()` now buffers printable keystrokes while the agent is generating.
  - The next prompt is pre-filled with whatever the user typed during generation (so keystrokes are no longer dropped).
  - Backspace is supported; Enter is ignored; extended keys (arrows/F-keys) are ignored on Windows.

### Tests updated

- `tests/unit/test_inline_app.py` updated to reflect corrected Ctrl+C semantics.
- `tests/unit/test_inline_typeahead.py` added to cover the key pollers + prompt prefill behavior.

### Repo hygiene (WSL/Windows)

- Added `.gitattributes` to enforce LF line endings in-repo (avoids massive CRLF-only diffs when switching between Windows + WSL).

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
  - Confirm the prompt footer is visible (model/provider/mode + tokens/edits/files) and updates after a turn.
  - Confirm the submitted input is printed as a turn (`❯ ...`) while the editable prompt itself is erased (input feels separate from streamed output).
  - Confirm a separator is printed immediately after the submitted user turn (model output always starts in a new block).
  - Confirm you can type while streaming (prompt remains active).
  - While streaming, submit another message and confirm it is queued and runs after the current response.

- `uv run hybridcoder chat --sequential` (fallback)
  - Confirm sequential behavior is still correct (prompt only after response).
  - While generating, type ahead and confirm the next prompt is prefilled with what you typed.

Probe (if you see ANSI corruption or prompt instability):
- `uv run python scripts/probe_patch_stdout.py`
  - Confirms whether `prompt_toolkit.patch_stdout(raw=True)` preserves Rich ANSI on Windows while typing.
  - This is the core building block used by the default inline REPL.

## Follow-up Inline UX Fixes (Later on 2026-02-07)

Additional user-facing inline UX changes were implemented after the above checklist:

- Status/footer visibility:
  - Prompt footer now uses `bottom_toolbar` (full status) plus a short `rprompt` fallback to make status visible even if the toolbar line is not obvious in a given terminal.
  - Status line now includes Provider (matching the welcome banner).
  - `rprompt` now includes a short model/provider identifier plus mode/tokens/edits/files so some status remains visible even when the bottom toolbar line isn't rendered (e.g., terminals without CPR support).
- “Input feels separate”:
  - Prompt input is created with `erase_when_done=True` so the editable input bar does not remain in scrollback after submit.
  - The submitted user text is re-printed into scrollback via `InlineRenderer.print_user_turn()` so chat history remains readable.
  - A full-width separator is printed immediately after the submitted `❯ ...` turn so model/tool output always starts in a distinct block.
- Tool stats correctness:
  - `write_file` tool result parsing now strips the `Written to ...` prefix to track file paths cleanly for `Files:` counters.

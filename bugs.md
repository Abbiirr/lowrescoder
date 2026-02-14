# UI Bug Tracker — Inline REPL

Tracked bugs found during manual QA of `uv run hybridcoder chat` (Phase 2D).

## Open Bugs

| ID | Severity | Description | File | Status |
|----|----------|-------------|------|--------|
| BUG-1 | Medium | Input border NOT full-width (capped at 120 chars) | `renderer.py:61` | Fixed (border removed) |
| BUG-2 | High | Cannot type during LLM generation | `app.py:_run_parallel()` | Fixed (parallel inline is default; sequential `--sequential` keeps type-ahead) |
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
| BUG-14 | High | Subagent usage is not observable in runtime flow; task prompts only call `create_task`/`update_task`/`list_tasks` and no subagent lifecycle (`spawn/check/cancel`) appears in logs/UI | `src/hybridcoder/agent/subagent.py`, `src/hybridcoder/agent/subagent_tools.py`, `src/hybridcoder/backend/server.py` | Fixed (Sprint 4B) |
| BUG-15 | High | `@` file autocomplete shows nothing while typing in Python inline REPL — `complete_while_typing=False` disables visible feedback | `src/hybridcoder/inline/app.py:340` | Fixed |
| BUG-16 | High | `@` file autocomplete was missing in Go TUI (slash-only completion path) | `cmd/hybridcoder-tui/completion.go`, `cmd/hybridcoder-tui/update.go` | Fixed (verified) |
| BUG-17 | Low | `HybridAutoSuggest` only provides ghost text for `/` commands, not for `@` file paths — no ghost text when typing `@README` | `src/hybridcoder/inline/completer.py:27-42` | Fixed |
| BUG-18 | Medium | Task-breakdown replies can create tasks without showing a visible to-do board in the same turn | `src/hybridcoder/agent/task_tools.py`, `src/hybridcoder/agent/prompts.py` | Fixed (verified) |
| BUG-19 | Medium | No dedicated `task_created`/`task_updated` log events — task mutations are logged only as generic `tool_call_start`/`tool_call_end` with no task ID, title, or status in structured fields | `src/hybridcoder/agent/task_tools.py` | Fixed |
| BUG-20 | Medium | `on_task_state` notification never sent to Go TUI — plan Section 8.2 defines it but it's not implemented, so Go TUI has no reactive task board updates | `src/hybridcoder/backend/server.py` | Open (deferred to 4C per plan) |
| BUG-21 | Medium | TaskStore not reset on `/new` or `/resume` — `handle_session_new()` and `handle_session_resume()` set `_agent_loop = None` but leave `_task_store` pointing at old session ID; `handle_task_list()` then creates a new one but the agent loop still uses the stale one | `src/hybridcoder/backend/server.py:462,507` | Fixed |
| BUG-22 | Low | `handle_chat()` session switch (`session_id != self.session_id`) does not reset `_task_store` or `_agent_loop`, so task tools operate on wrong session if Go TUI sends a different session_id | `src/hybridcoder/backend/server.py:353-354` | Fixed |
| BUG-23 | Low | Tool result truncation applied to task tool output — `create_task` summary can get truncated by `ContextEngine.truncate_tool_result()` if task list grows long, losing the board snapshot that BUG-18 fix relies on | `src/hybridcoder/agent/loop.py:368-369` | Fixed |
| BUG-24 | Medium | Path-scoped instruction is not honored when target directory does not exist: prompt "write all code inside sandboxes/test_123445" triggers file listing + clarification instead of creating the directory and proceeding under that path | `src/hybridcoder/agent/prompts.py`, `src/hybridcoder/agent/loop.py` | Patched (prompt policy) |

## Resolution Notes

### BUG-1, BUG-5, BUG-6 — Removed bordered input box
The bordered input box (`╭───`/`╰───`) caused three bugs at once. Claude Code does NOT use bordered input — it uses `> ` with a separator above. Removed borders, simplified prompt to `❯ `.

### BUG-3 — Closed as by-design
Claude Code does NOT pin the input at the bottom. It uses inline scrollback like we do. Once BUG-2/7 are fixed, the prompt reappears immediately after cancellation.

### BUG-2, BUG-7 — Escape/Ctrl+C cancellation
Wrapped `_handle_input()` in `asyncio.Task`. Added `_listen_for_escape()` using `msvcrt` on Windows. `asyncio.wait(FIRST_COMPLETED)` races agent task vs escape listener.

### BUG-2 — Type-ahead (sequential)
While inline mode is still sequential (no visible prompt during generation), `_listen_for_escape()` now buffers printable keystrokes during generation and pre-fills the next prompt with what the user typed. This prevents keystrokes from being dropped and enables “compose next message while waiting” behavior without requiring `patch_stdout()`.

### BUG-2 — Visible typing while generating (default inline)
Inline mode defaults to an always-on prompt under `prompt_toolkit.patch_stdout(raw=True)`, streaming output above it so the user can type while the assistant is generating (Claude Code-style).

While a response is streaming, submitting another message queues it (FIFO) and runs it after the current generation completes or is cancelled. Use `--sequential` to disable the always-on prompt if your terminal has issues.

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

### BUG-14 — Subagent invocation not visible/verified
Implemented in Sprint 4B. `SubagentManager` + `SubagentLoop` + `LLMScheduler` provide full subagent lifecycle. 4 tools registered: `spawn_subagent`, `check_subagent`, `cancel_subagent`, `list_subagents`. Structured logging via `log_event()` on spawn/cancel. Backend wired with `subagent.list`/`subagent.cancel` RPC handlers and cancel propagation. 25 unit tests covering scheduler, subagent loop, manager, and tool handlers.

### BUG-15 — `@` autocomplete disabled in Python inline REPL

**Root cause:** `PromptSession` in `app.py:340` is created with `complete_while_typing=False`. This means the `HybridCompleter` (which correctly handles `@` file paths) is only invoked on explicit Tab press — users expect a dropdown or ghost text to appear while typing `@README`, but nothing happens.

**The infrastructure works:** `HybridCompleter.get_completions()` correctly detects `@` in input, calls `fuzzy_complete()` from `file_completer.py`, and yields proper `Completion` objects. Unit tests pass. The problem is purely that the PromptSession never calls it during typing.

**Fix:** Change `complete_while_typing=False` to `complete_while_typing=True` in `app.py:340`. This will enable completions for both `/` commands and `@` file paths during typing. Alternatively, if full typing completion causes UX issues (e.g., dropdown appearing during normal typing), use a custom `ConditionalCompleter` that only activates when the text starts with `/` or contains `@`.

### BUG-16 — `@` autocomplete missing in Go TUI

**Root cause:** `getCompletions()` in `completion.go` previously returned `nil` for non-`/` input, and `updateCompletions()` cleared all suggestions for non-`/` input. That made `@` path completion unavailable in Go TUI.

**Fix (patched):** Added `@` file completion path in Go TUI:
- `getCompletionsInDir()` routes slash vs `@` completion.
- `getAtFileCompletions()` walks project files (with skip dirs), fuzzy-matches path fragments, and preserves sentence prefix (e.g., `inspect @src/ma`).
- `updateCompletions()` now accepts any non-empty completion set, not slash-only.

### BUG-18 — To-do board not visible after task creation flow

**Root cause:** task mutation tools returned only mutation acknowledgments, so users could complete a breakdown flow without seeing the board state in the same turn.

**Fix (patched):** Task mutation tools now include a `Current tasks:` snapshot:
- `create_task` returns created ID + current board summary.
- `update_task` returns update result + current board summary.
- Added `add_task_dependency` tool so dependencies can be explicitly modeled.
- Prompt guidance updated to call `list_tasks` after task changes.

### BUG-19 — No dedicated task log events

**Root cause:** Task tool handlers (`create_task`, `update_task`) don't emit structured log events with task-specific fields. The only logging is the generic `tool_call_start` / `tool_call_end` in `loop.py:292-378`, which logs tool name and argument keys but not the task ID, title, or status change.

**Impact:** Log analysis tools can't filter for "all tasks created in session X" without parsing tool arguments. No way to audit task lifecycle from logs.

**Fix:** Add `log_event(logger, logging.INFO, "task_created", task_id=..., title=..., session_id=...)` and similar `task_updated` events in the task tool handlers. Low effort — add 3-4 lines to each handler in `task_tools.py`.

### BUG-20 — `on_task_state` notification not implemented

**Root cause:** Phase 4 plan Section 8.2 defines an `on_task_state` JSON-RPC notification that the backend should send to Go TUI after task changes, but this notification is never emitted. The Go TUI has no code to receive it either.

**Impact:** Go TUI can only see task state via explicit `task.list` RPC call or `/tasks` command. There's no reactive update when the LLM creates/updates tasks during a conversation.

**Fix:** In `_on_tool_call()` callback in `server.py`, detect task-related tools (`create_task`, `update_task`) and emit `on_task_state` notification with current task list. Go TUI needs a handler for this notification. Deferred to Sprint 4C per plan (Go task panel).

### BUG-21 — Stale TaskStore on session switch

**Root cause:** `handle_session_new()` (line 462) and `handle_session_resume()` (line 507) reset `_agent_loop = None` but don't reset `_task_store`. When `_ensure_agent_loop()` runs next, it creates a new TaskStore with the new session_id. However, `handle_task_list()` (line 513) has its own fallback: if `_task_store is None` it creates one, but if it's already set (from a previous session), it uses the stale one.

**Fix:** Add `self._task_store = None` in both `handle_session_new()` and `handle_session_resume()` alongside the `_agent_loop = None` reset.

### BUG-22 — handle_chat session_id switch doesn't reset agent

**Root cause:** `handle_chat()` line 353-354 updates `self.session_id` if the Go TUI sends a different session_id, but doesn't reset `_agent_loop` or `_task_store`. The agent loop and task tools continue operating on the old session's TaskStore.

**Fix:** Treat a session_id mismatch in `handle_chat()` the same as `/resume` — reset `_agent_loop = None`, `_task_store = None`.

### BUG-23 — Task board summary truncated by ContextEngine

**Root cause:** `loop.py:368-369` applies `context_engine.truncate_tool_result()` to ALL tool results, including task tools. The BUG-18 fix added task board summaries to `create_task` and `update_task` return values. If the task list grows beyond ~500 tokens (~2000 chars), the summary gets truncated with `[... truncated ...]`, defeating the purpose.

**Fix:** Either exempt task tools from truncation (check `tc.name` before truncating), or increase the max_tokens threshold for task tool results specifically, or move task board injection into the system prompt (which already happens via `task_summary` — making the tool-level summary redundant for the LLM).

### BUG-24 — Path-scoped write intent ignored for missing directory

**Observed behavior:** With prompt `write all code inside sandboxes/test_123445`, the agent responded by listing files/directories and asking whether to create the directory, instead of treating the path constraint as an execution requirement and creating the target directory automatically.

**Impact:** Violates user intent and adds avoidable interaction turns. For sandboxed workflows, this can cause writes to drift to unintended locations.

**Likely root cause:** System prompt/tool policy does not enforce "path constraint first" behavior when the requested directory is absent.

**Fix (prompt policy):** Added explicit rule in `SYSTEM_PROMPT` instructing the LLM to write files directly inside user-specified target directories without asking. The `write_file` tool already creates parent directories automatically (`file_path.parent.mkdir(parents=True, exist_ok=True)` in `utils/file_tools.py:94`). No `run_command`/`mkdir -p` needed. This is model-dependent (prompt policy, no deterministic guard).

### BUG-17 — `HybridAutoSuggest` ignores `@` file paths

**Root cause:** `get_suggestion()` in `completer.py:27-42` only checks for `/` prefix. It never checks for `@` in the text, so no ghost text appears when typing `@file` paths.

**Fix:** Add `@` file path handling to `get_suggestion()` — detect `@` in text, get the partial after the last `@`, call `fuzzy_complete()`, and return the first match as a `Suggestion`.

## Constraints

- `patch_stdout(raw=False)` strips ANSI escape sequences by design (will mangle Rich output). `patch_stdout(raw=True)` is the only viable option for ANSI, but requires manual Windows verification (see `scripts/probe_patch_stdout.py`) before adopting an always-on prompt design.
- Inline REPL supports two modes:
  - Parallel (default): prompt stays active while output streams above it.
  - Sequential (`--sequential`): prompt -> process -> output -> prompt (type-ahead buffered while generating).
- Escape listener uses `msvcrt.kbhit()`/`msvcrt.getch()` on Windows, `select` on Unix.

# UI Bug Tracker — Inline REPL

Tracked bugs found during manual QA of `uv run autocode chat` (Phase 2D).

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
| BUG-12 | Medium | Status/footer line not visible/obvious at prompt on some terminals | `app.py:_ensure_prompt_session()` | Fixed (bottom_toolbar + rprompt) |
| BUG-13 | Medium | Task-breakdown replies can create tasks without showing a visible to-do board in the same turn | `src/autocode/agent/task_tools.py`, `src/autocode/agent/prompts.py` | Fixed (verified) |
| BUG-14 | Medium | No dedicated `task_created`/`task_updated` log events — task mutations are logged only as generic `tool_call_start`/`tool_call_end` with no task ID, title, or status in structured fields | `src/autocode/agent/task_tools.py` | Fixed |
| BUG-15 | Medium | `on_task_state` notification never sent to Go TUI — plan Section 8.2 defines it but it's not implemented, so Go TUI has no reactive task board updates | `src/autocode/backend/server.py` | Fixed (Sprint 4C) |
| BUG-16 | Medium | TaskStore not reset on `/new` or `/resume` — `handle_session_new()` and `handle_session_resume()` set `_agent_loop = None` but leave `_task_store` pointing at old session ID; `handle_task_list()` then creates a new one but the agent loop still uses the stale one | `src/autocode/backend/server.py:462,507` | Fixed |
| BUG-17 | Low | `handle_chat()` session switch (`session_id != self.session_id`) does not reset `_task_store` or `_agent_loop`, so task tools operate on wrong session if Go TUI sends a different session_id | `src/autocode/backend/server.py:353-354` | Fixed |
| BUG-18 | Low | Tool result truncation applied to task tool output — `create_task` summary can get truncated by `ContextEngine.truncate_tool_result()` if task list grows long, losing the board snapshot that BUG-13 fix relies on | `src/autocode/agent/loop.py:368-369` | Fixed |
| BUG-19 | Medium | Path-scoped instruction is not honored when target directory does not exist: prompt "write all code inside sandboxes/test_123445" triggers file listing + clarification instead of creating the directory and proceeding under that path | `src/autocode/agent/prompts.py`, `src/autocode/agent/loop.py` | Patched (prompt policy) |
| BUG-20 | Medium | `HybridAutoSuggest` ignores `@` file paths | `src/autocode/agent/completer.py:27-42` | Pending (needs implementation) |
| BUG-21 | Medium | Terminal-Bench early failures indicate manifest/setup issues | `scripts/e2e/external/terminalbench-pilot-subset.json` | Deferred (infrastructure) |

## Resolution Notes

### BUG-1, BUG-5, BUG-6 — Removed bordered input box
The bordered input box (`╭───`/`╰───`) caused three bugs at once. Claude Code does NOT use bordered input — it uses `> ` with a separator above. Removed borders, simplified prompt to `❯ `.

### BUG-3 — Closed as by-design
Claude Code does NOT pin the input at the bottom. It uses inline scrollback like we do. Once BUG-2/7 are fixed, the prompt reappears immediately after cancellation.

### BUG-2, BUG-7 — Escape/Ctrl+C cancellation
Wrapped `_handle_input()` in `asyncio.Task`. Added `_listen_for_escape()` using `msvcrt` on Windows. `asyncio.wait(FIRST_COMPLETED)` races agent task vs escape listener.

### BUG-2 — Type-ahead (sequential)
While inline mode is still sequential (no visible prompt during generation), `_listen_for_escape()` now buffers printable keystrokes during generation and pre-fills the next prompt with what the user typed. This prevents keystrokes from being dropped and enables "compose next message while waiting" behavior without requiring `patch_stdout()`.

### BUG-2 — Visible typing while generating (default inline)
Inline mode defaults to an always-on prompt under `prompt_toolkit.patch_stdout(raw=True)`, streaming output above it so the user can type while the assistant is generating (Claude Code-style).

### BUG-4, BUG-13, BUG-14 — Task tool improvements
Added task board snapshots to `create_task` and `update_task` return values for visibility. Added structured logging for task mutations (`task_created`, `task_updated`). These fixes make task operations more transparent and easier to debug.

### BUG-15 — `on_task_state` notification implementation
Implemented `on_task_state` JSON-RPC notification in `server.py` that emits after task changes. Go TUI can now reactively update its task panel without explicit `task.list` calls.

### BUG-16, BUG-17 — Session state reset
Fixed TaskStore stale state on session switches. Both `/new` and `/resume` now reset `_agent_loop = None` and `_task_store = None` properly. Session ID mismatches in `handle_chat()` now trigger the same reset behavior.

### BUG-18 — Task tool truncation exemption
Modified `loop.py` to exempt task tools from `ContextEngine.truncate_tool_result()`. Task board summaries are now preserved even when the task list grows large.

### BUG-19 — Path-scoped write intent
Added explicit rule in `SYSTEM_PROMPT` to honor path constraints without asking for confirmation. The `write_file` tool automatically creates parent directories, so no `mkdir -p` needed.

### BUG-20 — `HybridAutoSuggest` `@` file path support
Add `@` file path handling to `get_suggestion()` — detect `@` in text, get the partial after the last `@`, call `fuzzy_complete()`, and return the first match as a `Suggestion`.

### BUG-21 — Terminal-Bench environment investigation
Deferred to infrastructure team. Requires investigation of Terminal-Bench test runner and benchmark environment setup.

## Constraints

- `patch_stdout(raw=False)` strips ANSI escape sequences by design (will mangle Rich output). `patch_stdout(raw=True)` is the only viable option for ANSI, but requires manual Windows verification (see `scripts/probe_patch_stdout.py`) before adopting an always-on prompt design.
- Inline REPL supports two modes:
  - Parallel (default): prompt stays active while output streams above it.
  - Sequential (`--sequential`): prompt -> process -> output -> prompt (type-ahead buffered while generating).
- Escape listener uses `msvcrt.kbhit()`/`msvcrt.getch()` on Windows, `select` on Unix.

# TUI Quality Checklist & Performance Budget

Goal: The AutoCode TUI should feel faster and more polished than Claude Code’s TUI.

Manual behavior sweeps:
- use `docs/qa/manual-ai-bug-testing-playbook.md`
- do not rely on render/snapshot checks alone for slash-command, tool-grounding, provider/model, or resize behavior

---

**Performance Budgets (p95 unless noted)**
- Startup ready (cold): <300 ms to UI ready
- Startup ready (warm): <150 ms
- Keystroke echo: <16 ms
- UI frame update: <16 ms
- Non-LLM command latency: <150 ms
- Local LLM first token: <2 s
- Remote LLM first token (opt-in): <3 s
- Streaming stability: no pauses >250 ms

---

**Polish Checklist**
- Consistent layout: header, main pane, status bar
- Clear model/backend indicator and online/offline state
- Stable keybinds with in-app help
- Predictable undo/redo and safe cancel
- Clean error surfaces with recovery steps
- No blocking operations on the UI thread

---

**Reliability Checklist**
- LSP or embeddings unavailable should not block the UI
- Background tasks have visible progress and can be cancelled
- All file I/O and network calls are async or off-thread
- Hard timeouts for tools and LLM calls

---

**Benchmark Instrumentation Contract**
When `AUTOCODE_BENCH=1` is set, the TUI should emit sentinel lines:
- `BENCH:READY` when the UI is ready for input
- `BENCH:PONG` after receiving `:bench-ping`
- `BENCH:EXIT` after receiving `:quit` or `:exit`

The benchmark harness depends on these strings and will report unsupported if they are missing.

---

**How to Run Benchmarks**
1. Run the benchmark script:

```bash
uv run python scripts/bench_tui.py --cmd autocode --args "chat"
```

2. Compare results to the budgets above.

---

**Acceptance Criteria (Phase 1)**
- Meets startup and non-LLM latency budgets on a baseline dev machine
- No visible jank during typing or scrolling
- TUI benchmarks produce a stable JSON report

---

**Competitive UX Research (Documented)**

Claude Code (Anthropic):
- Slash commands include `/agents` (subagents), `/compact`, `/memory`, and `/permissions` for workflow control and safety.
- Custom status line support with a 300ms max update cadence and JSON context (model, cwd, costs).
- `/terminal-setup` and `/config` for terminal UX tweaks (Shift+Enter, theme alignment).
- IDE integrations add diff viewing and selection context sharing.

OpenAI Codex CLI:
- Full-screen interactive TUI that can read files, make edits, and run commands.
- Inline plan visibility and step approvals in interactive mode.
- Stores transcripts locally for session continuity.
- Approval modes: read-only, auto (workspace), full access (network + outside workspace).
- TUI config includes alternate screen toggles to preserve terminal scrollback.
- Tracks progress with a to-do list for complex work.

OpenCode:
- Bubble Tea-based TUI for terminal UX.
- Multi-provider support including OpenAI, Anthropic, OpenRouter, etc.
- Session management with SQLite persistence.
- Tool integration (command execution, file search, code edits).
- LSP integration for code intelligence.
- File change tracking and visualization.
- External editor support for composing messages.
- Custom commands with named arguments.

Sources (for reference):
- https://docs.anthropic.com/en/docs/claude-code/slash-commands
- https://docs.anthropic.com/en/docs/claude-code/statusline
- https://docs.anthropic.com/en/docs/claude-code/terminal-config
- https://docs.anthropic.com/en/docs/claude-code/ide-integrations
- https://developers.openai.com/codex/cli/features
- https://developers.openai.com/codex/config-advanced
- https://openai.com/index/introducing-upgrades-to-codex/
- https://opencode.sh/

---

**Best-of-Three Target Feature Set (AutoCode TUI)**

Layout and interaction:
- Multi-pane layout with header, main chat pane, and right-side context panel (plan/to-do, tool calls, diffs).
- Full scrollback preserved by default (avoid alternate screen), with opt-in alternate screen mode.
- Mouse selection and copy must be reliable and not disrupted by animations.
- Consistent, discoverable command help panel with keybindings.

Workflow controls:
- Slash commands parity with core workflows: `/model`, `/permissions`, `/compact`, `/memory`, `/agents`, `/sessions`, `/resume`.
- Approval modes modeled after Codex and Claude: read-only, suggest/auto, full access.
- Inline plan/to-do list that updates as steps complete.
- Subagent/task panel that shows delegated subtasks and status.

Memory and continuity:
- Local session storage with transcript export.
- SQLite-backed session index + summaries for fast resume.
- Project memory file `.autocode/memory.md` editable in-place.

Tooling and feedback:
- Inline tool call blocks with collapsible output.
- Diff view that can render in TUI and optionally in IDE (if integrated).
- File change tracking panel (what changed, where, by whom, and why).

Config and polish:
- Customizable status line with model/provider/mode/tokens.
- UI settings for animations, tooltips, and notifications.
- Bench sentinels emitted reliably in all modes.

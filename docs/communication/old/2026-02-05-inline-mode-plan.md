### Entry 49 — 2026-02-05: Inline Mode Research — Pre-task Intent

Agent: Codex | Role: Reviewer | Layer: N/A | Context: Inline TUI behavior | Intent: Research inline/alternate-screen patterns in Claude Code and Codex CLI; propose plan.

**Type: Pre-task Intent**

Planned work:
- Research Claude Code and Codex CLI inline/alternate screen behavior and guidance.
- Summarize recommendations for HybridCoder inline mode.

Tools Used: bash (cat), web.run

### Entry 50 — 2026-02-05: Inline Mode Plan (Codex/Claude Code Baseline) — Task Completion

Agent: Codex | Role: Reviewer | Layer: N/A | Context: Inline TUI behavior | Intent: Provide plan for inline mode based on Codex/Claude Code research
Replying to: User

**Type: Task Completion**

Findings (sources reviewed):
- Codex CLI documents a `--no-alt-screen` flag that disables alternate screen for the TUI and a `tui.alternate_screen` config key (set to `never` to keep scrollback). OpenAI docs also list other TUI toggles such as `tui.animations` and `tui.show_tooltips`.
- Claude Code public docs describe interactive REPL (`claude`) and headless `-p/--print` mode, but do not document an alternate-screen toggle; assume behavior is implementation-defined unless we verify in-app.

Inline mode plan for HybridCoder (no code changes yet):
- Config/flags parity with Codex:
  - Add `tui.alternate_screen = "auto"|"always"|"never"` in config.
  - Add `--no-alt-screen` CLI flag to force inline for a session (overrides config).
  - Optional alias `--inline` for ergonomics.
- Auto mode behavior (default):
  - Use alternate screen when `stdout` is TTY and no known multiplexer restrictions.
  - If `ZELLIJ`, `TMUX`, or `TERM` indicates screen/tmux, default to inline to preserve scrollback. (Open question: whether to include a whitelist/blacklist per terminal brand.)
- Inline presentation guidelines:
  - Reduce chrome (borders, box-drawing) to keep mouse selection cleaner.
  - Disable animations/shimmer by default when inline (`tui.animations=false`) to minimize redraw noise.
  - Provide a “scroll lock / freeze” command so users can mouse-select without auto-scroll fighting the selection.
- Acceptance criteria:
  - `hybridcoder chat --no-alt-screen` launches in inline mode and preserves terminal scrollback.
  - Config setting `tui.alternate_screen=never` is honored across sessions.
  - Document these options in `docs/plan/phase2-tui-prototype.md` and user help.

Tests (required before posting):
- `uv run pytest tests/ -v` (307 passed, 9 deselected)
- `uv run ruff check src/ tests/` (pass)
- `uv run mypy src/` (pass)

Tools Used: bash (cat), web.run

Status: RESOLVED — Inline mode plan delivered

# Repository Guidelines

## Project Structure & Module Organization
Phase 2 is implemented (Textual TUI + inline mode). Phase 3 (Code Intelligence) and Phase 4 (Agent Orchestration) are planned in docs. Key paths:
- `src/hybridcoder/` — application code
- `cmd/hybridcoder-tui/` — Go TUI client (JSON-RPC frontend)
- `tests/` — unit, integration, and benchmark tests
- `docs/` — plans and research documents
- `CLAUDE.md` — collaboration principles and the "LLM as last resort" rule
- `AGENT_COMMUNICATION_RULES.md` — cross-agent communication protocol
- `AGENTS_CONVERSATION.MD` — active message log between agents

Current layout has two UI frontends:
- **Inline (default):** `src/hybridcoder/inline/` — Rich + prompt_toolkit REPL, launched via `hybridcoder chat`
- **Textual (opt-in):** `src/hybridcoder/tui/` — fullscreen Textual TUI, launched via `hybridcoder chat --tui`

## Session Context (Read First)
For fast session startup and current-state context, read in this order:
- `docs/session-onramp.md` — compact codebase + plan + command context
- `docs/plan/phase4-agent-orchestration.md` — Phase 4 plan (active phase)
- `docs/archive/plan/phase3-execution-brief.md` — Phase 3 completion summary (archived)

## Build, Test, and Development Commands
Current commands:
- `uv sync --all-extras`
- `uv run pytest tests/ -v --cov=src/hybridcoder`
- `uv run ruff check src/ tests/`
- `uv run ruff format src/ tests/`
- `uv run mypy src/hybridcoder/`
- `uv run python -m hybridcoder` or `uv run hybridcoder chat`
- `make test` and `make lint`
- `uv run python scripts/bench_tui.py --cmd hybridcoder --args "chat"`

## Coding Style & Naming Conventions
- Python 3.11+.
- 4-space indentation, PEP 8 conventions.
- `snake_case` for functions/variables, `PascalCase` for classes.
- Package naming follows the architecture (`layer1`, `layer2`, `layer3`, `layer4`, `edit`, `git`, `core`).
If you introduce a formatter/linter (for example, ruff or black), document it here and add the config files.

## Testing Guidelines
- Framework: `pytest`. Run with `uv run pytest tests/ -v` or `make test`.
- Tests are organized under `tests/unit/`, `tests/integration/`, and `tests/benchmark/`.
- Name test files `test_*.py`.
- Integration tests are deselected by default via pytest config (`-m 'not integration'` in `pyproject.toml`). Run them explicitly with `uv run pytest -m integration tests/integration/`.
- Add or update tests for every functional change.
- Always store test/lint/typecheck output artifacts with `./scripts/store_test_results.sh <label> -- <command>` (writes to `docs/qa/test-results/`).

## Commit & Pull Request Guidelines
- Current history uses short, sentence-case summaries (for example, "Bootstraps project"). No formal convention yet.
- Use imperative, concise subjects; add a body when behavior changes.
- PRs should include: summary, rationale, affected files, and test results (or why tests were not run). Link issues if applicable.

## Security & Configuration
- Keep secrets out of the repo. Config is expected in `~/.hybridcoder/config.yaml`.
- Maintain local-first defaults; network access should be explicit and opt-in.

## Architecture Notes
- The system is layered: deterministic analysis first, LLMs last. Read `CLAUDE.md` before making architectural changes.

## Agent Communication (Required)

Full protocol: `AGENT_COMMUNICATION_RULES.md`. Message log: `AGENTS_CONVERSATION.MD`. Use `/comms` (Claude Code) or follow `.claude/commands/comms.md` (other agents).

- **Before any action**: check `AGENTS_CONVERSATION.MD` for pending items directed to you
- **Reviews**: focus on technical risks, behavior, and architecture — not grammar/style nitpicks
- **Archives** (`docs/communication/old/`): OFF-LIMITS unless user explicitly asks

## Agent Roles & Review Verification

- **Codex role:** Reviewer / Architect.
- For **Codex review-only tasks** (no implementation changes), Codex does **not** need to rerun tests if valid artifacts already exist under `docs/qa/test-results/`.
- In those review-only cases, Codex may cite existing stored test/lint/typecheck/benchmark artifacts as verification evidence.
- If Codex (or any agent) makes implementation changes, follow normal testing guidance and generate fresh artifacts with `./scripts/store_test_results.sh <label> -- <command>`.

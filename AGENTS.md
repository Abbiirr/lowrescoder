# Repository Guidelines

## Project Structure & Module Organization
The live interactive path is the Go TUI (`cmd/autocode-tui/`) with Python backend support under `src/autocode/`. Legacy Python UI frontends still exist in-tree, but the current contract is: Go TUI by default, Python inline only as explicit `--inline` fallback. Key paths:
- `src/autocode/` — application code
- `cmd/autocode-tui/` — Go TUI client (JSON-RPC frontend)
- `tests/` — unit, integration, and benchmark tests
- `docs/` — plans and research documents
- `CLAUDE.md` — collaboration principles and the "LLM as last resort" rule
- `AGENT_COMMUNICATION_RULES.md` — cross-agent communication protocol
- `AGENTS_CONVERSATION.MD` — active message log between agents

Current layout has these UI surfaces:
- **Go TUI (default):** `autocode/cmd/autocode-tui/` — BubbleTea JSON-RPC frontend, launched by `autocode chat`
- **Python inline fallback:** `autocode/src/autocode/inline/` — Rich + prompt_toolkit REPL, launched via `autocode chat --inline`
- **Legacy Textual UI code:** `autocode/src/autocode/tui/` — still present in-tree, not the primary interactive path

## Session Context (Read First)
For fast session startup and current-state context, read in this order:
- `current_directives.md` — **active sprint, what to work on next, pending decisions**
- `docs/session-onramp.md` — compact codebase + plan + command context
- `docs/plan/phase5-agent-teams.md` — Phase 5 plan (active phase)
- `docs/archive/plan/phase3-execution-brief.md` — Phase 3 completion summary (archived)

## Build, Test, and Development Commands
Current commands (run from superproject root):
- `uv sync` — install workspace deps
- `uv run pytest autocode/tests/unit/ benchmarks/tests/ -v` — all tests
- `uv run pytest autocode/tests/unit/ -v --cov=src/autocode` — autocode tests
- `uv run pytest benchmarks/tests/ -v` — benchmark tests
- `cd autocode && uv run ruff check src/ tests/` — lint
- `cd autocode && uv run mypy src/autocode/` — type check
- `uv run python -m autocode` or `uv run autocode chat` — run autocode
- `make test` and `make lint` — via Makefile delegator

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
- If you change interactive terminal behavior, you must follow [docs/tests/tui-testing-strategy.md](/home/bs01763/projects/ai/lowrescoder/docs/tests/tui-testing-strategy.md) and run the full checklist in that file before calling the work done.
- For TUI work, unit tests alone are not sufficient. You must produce real-terminal or PTY-backed evidence, plus a stored artifact under `docs/qa/test-results/`.
- Use [docs/tests/pty-testing.md](/home/bs01763/projects/ai/lowrescoder/docs/tests/pty-testing.md) for the PTY harness/how-to details, and [docs/tests/tui-testing-strategy.md](/home/bs01763/projects/ai/lowrescoder/docs/tests/tui-testing-strategy.md) for the required validation matrix and exit gates.
- If any required TUI check cannot be run, state that explicitly and do not claim the TUI work is complete without user acknowledgment.
- Always store test/lint/typecheck output artifacts with `./scripts/store_test_results.sh <label> -- <command>` (writes to `docs/qa/test-results/`).

## Commit & Pull Request Guidelines
- Current history uses short, sentence-case summaries (for example, "Bootstraps project"). No formal convention yet.
- Use imperative, concise subjects; add a body when behavior changes.
- PRs should include: summary, rationale, affected files, and test results (or why tests were not run). Link issues if applicable.

## Security & Configuration
- Keep secrets out of the repo. Config is expected in `~/.autocode/config.yaml`.
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

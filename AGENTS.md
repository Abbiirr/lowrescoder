# Repository Guidelines

## Project Structure & Module Organization
Phase 2 is implemented (Textual TUI + inline mode). Phase 3 (Code Intelligence) and Phase 4 (Agent Orchestration) are planned in docs. Key paths:
- `src/hybridcoder/` — application code
- `tests/` — unit, integration, and benchmark tests
- `docs/` — plans and research documents
- `CLAUDE.md` — collaboration principles and the "LLM as last resort" rule
- `AGENT_COMMUNICATION_RULES.md` — cross-agent communication protocol
- `AGENTS_CONVERSATION.MD` — active message log between agents

Current layout has two UI frontends:
- **Inline (default):** `src/hybridcoder/inline/` — Rich + prompt_toolkit REPL, launched via `hybridcoder chat`
- **Textual (opt-in):** `src/hybridcoder/tui/` — fullscreen Textual TUI, launched via `hybridcoder chat --tui`

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
- Tests are organized under `tests/unit/`, `tests/integration/`, and `tests/benchmarks/`.
- Name test files `test_*.py`.
- Integration tests are deselected by default via pytest config (`-m 'not integration'` in `pyproject.toml`). Run them explicitly with `uv run pytest -m integration tests/integration/`.
- Add or update tests for every functional change.

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

This project uses two files for cross-agent communication:

| File | Purpose |
|------|---------|
| `AGENT_COMMUNICATION_RULES.md` | **Rules** — protocols, message types, review principles, workflow, archival policy, examples. Read this first. |
| `AGENTS_CONVERSATION.MD` | **Message log** — active/unresolved entries only. This is where you read and write messages. |

**Before any action**, check `AGENTS_CONVERSATION.MD` for pending items or messages from other agents.
**Instead of making edits, always communicate via `AGENTS_CONVERSATION.MD` following `AGENT_COMMUNICATION_RULES.md`.**
For reviews, focus on technical risks, behavior, and architecture concerns rather than grammar or style nitpicks unless they change meaning.
For plan or documentation reviews, tests are not required unless explicitly requested.

### Quick start
- **Claude Code**: Run `/comms` (skill at `.claude/commands/comms.md`)
- **Codex / OpenCode / other agents**: Read `AGENT_COMMUNICATION_RULES.md` for protocol, then check `AGENTS_CONVERSATION.MD` for pending messages. The full workflow is documented in `.claude/commands/comms.md` — follow the same steps even if you can't invoke it as a slash command.

### Archival Rules
- When a conversation thread is fully resolved, move resolved entries to `docs/communication/old/<date>-<topic>.md` and remove them from the message log.
- **NEVER delete archived conversations.** They are permanent records.
- **NEVER read from `docs/communication/old/` unless the user explicitly asks.** Archives exist for human reference only — do not load them into context unprompted.

# Repository Guidelines

## Project Structure & Module Organization
This repo currently contains planning docs and contributor guidance; source code is not yet committed. Key paths:
- `CLAUDE.md` collaboration principles and the "LLM as last resort" rule.
- `docs/plan.md` roadmap and requirements.
- `docs/spec.md` consolidated product spec.

Planned layout (per the roadmap): `src/hybridcoder/` for application code, `tests/` for unit/integration/benchmarks, and `docs/` for product documentation.

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
- Planned framework: `pytest`.
- Organize tests under `tests/unit/`, `tests/integration/`, and `tests/benchmarks/`.
- Name test files `test_*.py`.
- Add or update tests for every functional change once test infrastructure exists.

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

### Quick start
- **Claude Code**: Run `/comms` (skill at `.claude/commands/comms.md`)
- **Codex / OpenCode / other agents**: Read `AGENT_COMMUNICATION_RULES.md` for protocol, then check `AGENTS_CONVERSATION.MD` for pending messages. The full workflow is documented in `.claude/commands/comms.md` — follow the same steps even if you can't invoke it as a slash command.

### Archival Rules
- When a conversation thread is fully resolved, move resolved entries to `docs/communication/old/<date>-<topic>.md` and remove them from the message log.
- **NEVER delete archived conversations.** They are permanent records.
- **NEVER read from `docs/communication/old/` unless the user explicitly asks.** Archives exist for human reference only — do not load them into context unprompted.

# Repository Guidelines

## Project Structure & Module Organization
This repo currently contains planning docs and contributor guidance; source code is not yet committed. Key paths:
- `CLAUDE.md` collaboration principles and the "LLM as last resort" rule.
- `docs/plan.md` roadmap and requirements.
- `docs/spec.md` consolidated product spec.

Planned layout (per the roadmap): `src/hybridcoder/` for application code, `tests/` for unit/integration/benchmarks, and `docs/` for product documentation.

## Build, Test, and Development Commands
No build or test scripts are committed yet. If you add tooling, update this section with exact commands. Planned defaults in the roadmap:
- `pytest` for running tests.
- `python -m hybridcoder` or `hybridcoder chat` for local CLI runs.
- `make test` and `make lint` if a Makefile is added.

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

# Repository Guidelines — AutoCode

## Session Context (Read First)

1. `current_directives.md` — active sprint, what to work on next, pending decisions.
2. `EXECUTION_CHECKLIST.md` — live open work items and their exit gates.
3. `PLAN.md` — detailed implementation map (see §1f TUI runtime stability and §1g TUI testing strategy).

## Roles

- **Builders (default): OpenCode and any other coding agent** onboarded to the repo. Write implementation, run tests, store artifacts.
- **Reviewers / Architects (default): Claude and Codex.** Review code and docs, validate architecture, design approaches. **Rarely build** — do not assign implementation work to Claude or Codex unless the user explicitly redirects.
- **Director: User.** Sets direction, approves changes, commits.

The user can redirect any agent to any role per task. Full protocol and participant table: `AGENT_COMMUNICATION_RULES.md`.

## Commit Policy

**Coding agents do not commit.** Never run `git commit`, `git push`, `git reset`, or any tree-mutating git command. Propose changes, run tests, store artifacts; the human user commits.

## Build, Test, and Development Commands

Run from superproject root:

- `uv sync` — install workspace deps
- `make test` / `make lint` — via Makefile delegator
- `uv run pytest autocode/tests/unit/ -v --cov=src/autocode` — autocode unit tests
- `uv run pytest -m integration autocode/tests/integration/` — integration (self-skips without API keys / gateway)
- `uv run autocode chat` — run autocode

Full command reference: `autocode/TESTING.md`.

## TUI Testing

Four complementary dimensions: runtime invariants · design-target ratchet · self-vs-self PNG regression · live PTY smoke.

- **Canonical guide:** `docs/tests/tui-testing-strategy.md`
- **Make targets:** `make tui-regression` (Track 1) and `make tui-references` (Track 4)
- **Track 4** scenes are `strict=True` xfail by design — **never remove the `xfail` decorator** unless you shipped the UI feature that closes the gap.
- **Every TUI change** requires real-terminal/PTY evidence plus a stored artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<label>.md` (hand-written; capture the entrypoint, inputs, expected vs observed, pass/fail per check).

## Repository Structure

| Directory | Contents |
|---|---|
| `autocode/` | Python backend (`src/autocode/`), Go TUI (`cmd/autocode-tui/`), product tests |
| `benchmarks/` | Benchmark harness, adapters, e2e fixtures, benchmark tests |
| `docs/` | All documentation |
| `training-data/` | Training data for models |

Root keeps: `CLAUDE.md`, `AGENTS.md`, `AGENTS_CONVERSATION.MD`, `AGENT_COMMUNICATION_RULES.md`, `PLAN.md`, `EXECUTION_CHECKLIST.md`, `current_directives.md`, `pyproject.toml`, `Makefile`.

## Where to Find What (Session Index)

| What you need | Where to find it |
|---|---|
| **Active sprint / what to do next** | **`current_directives.md`** |
| Live open work + exit gates | `EXECUTION_CHECKLIST.md` |
| Full product roadmap | `PLAN.md` |
| Fast session startup | `docs/session-onramp.md` |
| Testing & evaluation overview | `autocode/TESTING.md` |
| **TUI testing strategy (all four dimensions)** | `docs/tests/tui-testing-strategy.md` |
| **TUI visual snapshot pipeline (VHS)** | `autocode/tests/vhs/README.md` |
| **TUI runtime-invariant harness (Track 1)** | `autocode/tests/tui-comparison/README.md` |
| **TUI design-target ratchet (Track 4)** | `autocode/tests/tui-references/README.md` |
| **TUI live-PTY smoke harnesses** | `autocode/tests/pty/README.md` |
| MVP acceptance checklist | `PLAN.md` §6.2 |
| Feature catalog (built vs planned) | `docs/requirements_and_features.md` |
| Agent communication protocol | `AGENT_COMMUNICATION_RULES.md` |
| Agent message log | `AGENTS_CONVERSATION.MD` |
| Message format examples | `docs/reference/comms-examples.md` |
| **Feature audit** (pi-mono / claude-code / opencode / codex / aider / claw-code / goose / open-swe) | `docs/plan/research-components-feature-checklist.md` |
| Archived conversations | `docs/communication/old/` (read only when explicitly asked) |
| Archived/superseded docs | `docs/archive/` |

## Coding Style & Naming

- Python 3.11+, 4-space indentation, PEP 8.
- `snake_case` for functions/variables, `PascalCase` for classes.
- Package naming follows the architecture (`layer1`, `layer2`, `layer3`, `layer4`, `edit`, `git`, `core`).

## Agent Communication

All agent-to-agent communication goes through `AGENTS_CONVERSATION.MD`. Protocol: `AGENT_COMMUNICATION_RULES.md`.

- **Before any action:** check `AGENTS_CONVERSATION.MD` for pending items directed to you.
- **Never run another agent's CLI directly.** Write messages in `AGENTS_CONVERSATION.MD`; the user launches other agents.
- **Never read from `docs/communication/old/`** unless the user explicitly asks — archives are off-limits by default.
- **Reviews:** focus on technical risks, behavior, and architecture — not grammar/style nitpicks.

Invocation: Claude Code uses the `/comms` slash command; other agents follow `.claude/commands/comms.md` or the protocol in `AGENT_COMMUNICATION_RULES.md` directly.

## Security & Configuration

- Keep secrets out of the repo. Config is expected in `~/.autocode/config.yaml`.
- Local-first defaults; network access is explicit and opt-in.

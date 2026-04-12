# Session Onramp (Current State)

Last updated: 2026-04-10

This is the fastest way to rebuild correct working context in a new session.

## 1) Read Order

1. `AGENTS.md` — repo rules, testing commands, comms protocol
2. `current_directives.md` — live phase, benchmark status, what is still open
3. `AGENT_COMMUNICATION_RULES.md` — required before reading active comms
4. `AGENTS_CONVERSATION.MD` — only the active tail, not archives
5. `EXECUTION_CHECKLIST.md` — live open work; the Claude Code primary TUI parity item is currently first
6. `PLAN.md` — detailed implementation map for each open item, including Section `1f` for the TUI parity work
7. `benchmarks/benchmarks/STATUS.md` — benchmark scoreboard and lane notes

## 2) Current Execution Focus

- Phase 5: complete
- Phase 6: complete
- Phase 7: complete
- Phase 8: complete, including live frontend switch-over
- Migration: complete
- Immediate work: post-Phase-8 frontier
  - Claude Code primary TUI parity
  - large-codebase comprehension validation
  - native external-harness orchestration
  - Terminal-Bench improvement

Important current detail:
- Section `1f` already has a partial Go TUI parity slice landed in the worktree
- resume from that diff; do not restart the TUI workstream from scratch

Do not treat `docs/plan/phase5-agent-teams.md` as the current execution target.
That is historical planning context now.

## 3) Repository Layout

This is now a multi-repo superproject:

| Path | Role |
|------|------|
| `autocode/` | Product runtime, CLI, inline frontend, backend, tests |
| `benchmarks/` | Harness, manifests, adapters, fixtures, benchmark tests |
| `docs/` | Documentation and stored verification artifacts |
| `training-data/` | Training data |

Important consequence: most code changes happen inside the `autocode` or
`benchmarks` submodules, but top-level comms and current directives still live
at the superproject root.

## 4) High-Value Paths

### Product runtime

- `autocode/src/autocode/agent/loop.py`
- `autocode/src/autocode/agent/factory.py`
- `autocode/src/autocode/agent/tools.py`
- `autocode/src/autocode/inline/app.py`
- `autocode/src/autocode/backend/server.py`
- `autocode/src/autocode/config.py`
- `autocode/src/autocode/packaging/installer.py`
- `autocode/autocode.spec`

### Benchmarks

- `benchmarks/benchmark_runner.py`
- `benchmarks/adapters/autocode_adapter.py`
- `benchmarks/e2e/external/`
- `benchmarks/benchmarks/STATUS.md`
- `benchmarks/benchmarks/EVALUATION.md`

### Source-of-truth docs

- `current_directives.md`
- `EXECUTION_CHECKLIST.md`
- `PLAN.md`
- `PROJECT_STATUS.md`

## 5) Commands You Actually Need

Run from the superproject root unless noted otherwise.

### Workspace

```bash
uv sync
```

### Main test commands

```bash
uv run pytest autocode/tests/unit/ benchmarks/tests/ -v
uv run pytest autocode/tests/unit/ -v
uv run pytest benchmarks/tests/ -v
```

### Lint / typing

```bash
cd autocode && uv run ruff check src/ tests/
cd autocode && uv run mypy src/autocode/
```

### Store artifacts

```bash
cd autocode
./scripts/store_test_results.sh <label> -- <command>
```

### Run product locally

```bash
uv run autocode chat
uv run autocode doctor
uv run autocode setup
```

### Benchmark commands

```bash
uv run python benchmarks/benchmark_runner.py --list-lanes
uv run python benchmarks/benchmark_runner.py --agent autocode --lane B9-PROXY --model swebench
bash benchmarks/run_all_benchmarks.sh
```

## 6) Verification Artifacts

Primary artifact location:

- `docs/qa/test-results/`
- `autocode/docs/qa/test-results/`

Recent Phase 7 closeout artifacts:

- `autocode/docs/qa/test-results/20260329-131654-phase7-closeout-focused-pytest.md`
- `autocode/docs/qa/test-results/20260329-131825-phase7-closeout-focused-ruff.md`
- `autocode/docs/qa/test-results/20260329-131744-phase7-pyinstaller-build.md`
- `autocode/docs/qa/test-results/20260329-132046-phase7-pyinstaller-setup-smoke.md`

## 7) Benchmark Reality

Canonical internal closeout:

- B7-B14: `50/50` (100%)
- B15-B29: `70/70` (100%)
- Combined: `120/120` (100%) — all 23 lanes green

Exploratory B30 / Terminal-Bench runs may show lower scores due to provider,
harness, or model-strategy limitations. Treat the internal 23/23 green state as
the canonical quality signal unless a
reproducible capability regression is confirmed.

## 8) Communication Rules

- Read `AGENT_COMMUNICATION_RULES.md` before reading `AGENTS_CONVERSATION.MD`
- Log a pre-task intent before code or doc changes
- Post verification artifacts and concrete outcomes in `AGENTS_CONVERSATION.MD`
- Do not read `docs/communication/old/` unless explicitly directed

## 9) Fresh-Session Checklist

1. Read `current_directives.md`
2. Read the active tail of `AGENTS_CONVERSATION.MD`
3. Confirm which frontier item is active now:
   - Claude Code primary TUI parity
   - large-repo validation
   - external-harness orchestration
   - Terminal-Bench improvement
4. Check `PLAN.md` for the exact implementation steps behind that frontier item
5. Check `git status` in the superproject and touched submodules
6. Use stored artifacts before rerunning expensive work

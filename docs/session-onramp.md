# Session Onramp

Last updated: 2026-04-27

Fastest way to rebuild working context in a new session.

## 1) Read Order

1. `AGENTS.md` — repo rules, testing commands, comms protocol
2. `current_directives.md` — live phase and open work
3. `AGENT_COMMUNICATION_RULES.md` — required before reading active comms
4. `AGENTS_CONVERSATION.MD` — active tail only (not archives)
5. `EXECUTION_CHECKLIST.md` — live open work with exit gates
6. `PLAN.md` — detailed implementation map

## 2) Current State

- Stabilize-and-Release Checkpoints 1-3 are closed from builder/reviewer side; user-owned commit/tag decision remains.
- Modular migration phases 0-5 are complete, with follow-through still tracked in `docs/plan/deferred/modular_migration_todo.md`.
- Rust TUI (`autocode/rtui/target/release/autocode-tui`) is the sole interactive frontend; Go TUI and Python inline are deleted
- `autocode` (bare) launches the Rust TUI via `cli.py`
- `docs/reference/rpc-schema-v1.md` is the canonical backend/TUI contract

## 3) Repository Layout

| Path | Role |
|------|------|
| `autocode/` | Product runtime, CLI, Rust TUI (`rtui/`), backend, tests |
| `benchmarks/` | Harness, adapters, fixtures, benchmark tests |
| `docs/` | Documentation and stored verification artifacts |
| `training-data/` | Training data |

## 4) TUI Testing Strategy (four dimensions)

Canonical guide: [`docs/tui-testing/tui-testing-strategy.md`](tui-testing/tui-testing-strategy.md)

| Dimension | Lives in | Purpose |
|---|---|---|
| Runtime invariants (Track 1) | `autocode/tests/tui-comparison/` | Hard predicates on captured output; `make tui-regression` |
| Design-target ratchet (Track 4) | `autocode/tests/tui-references/` | Scene predicates vs spec; `make tui-references` |
| Self-vs-self PNG regression (VHS) | `autocode/tests/vhs/` | pyte + Pillow baselines; user-gated rebaseline |
| Live-PTY smoke | `autocode/tests/pty/` | End-to-end binary + backend via `pty.fork()` |

All four resolve the binary via `$AUTOCODE_TUI_BIN` → `autocode/rtui/target/release/autocode-tui`. The Track 1 launcher auto-discovers it without the env var.

## 5) High-Value Paths

**Product runtime:** `autocode/src/autocode/{agent/loop.py, agent/factory.py, agent/tools.py, backend/server.py, config.py, cli.py}`

**Rust TUI:** `autocode/rtui/src/{main.rs, state/reducer.rs, rpc/, ui/, render/}`

**Benchmarks:** `benchmarks/benchmark_runner.py`, `benchmarks/adapters/`, `benchmarks/benchmarks/STATUS.md`

**Source-of-truth docs:** `current_directives.md`, `EXECUTION_CHECKLIST.md`, `PLAN.md`, `docs/reference/rpc-schema-v1.md`, `docs/features/features_behavior.md`

## 6) Commands

Run from superproject root.

```bash
# Workspace
uv sync

# Build Rust TUI
cd autocode/rtui && cargo build --release

# Tests
uv run pytest autocode/tests/unit/ -v
cd autocode/rtui && cargo test

# Lint
cd autocode && uv run ruff check src/ tests/
cd autocode/rtui && cargo clippy -- -D warnings

# Run locally
autocode                    # bare → launches Rust TUI
autocode --version
autocode doctor

# TUI tests
AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui \
  uv run python autocode/tests/vhs/run_visual_suite.py
make tui-regression
make tui-references

# Store artifacts
cd autocode && ./scripts/store_test_results.sh <label> -- <command>

# Benchmarks
uv run python benchmarks/benchmark_runner.py --list-lanes
bash benchmarks/run_b7_b30_sweep.sh   # all 23 lanes
```

## 7) Verification Artifacts

- `autocode/docs/qa/test-results/` — per-run artifacts (primary)
- `docs/qa/test-results/` — legacy; still used for some artifacts

## 8) Benchmark Baseline

- B7–B29: 120/120 (100%) — 23/23 lanes green on last canonical run
- Treat as canonical quality signal unless a reproducible regression appears

## 9) Communication Rules

- Read `AGENT_COMMUNICATION_RULES.md` before reading `AGENTS_CONVERSATION.MD`
- Log pre-task intent before code or doc changes
- Do not read `docs/communication/old/` unless explicitly directed
- Agents never commit — user commits

## 10) Fresh-Session Checklist

1. Read `current_directives.md` + active tail of `AGENTS_CONVERSATION.MD`
2. Check `EXECUTION_CHECKLIST.md` for open work and exit gates
3. `git status` in superproject
4. Use stored artifacts before rerunning expensive work

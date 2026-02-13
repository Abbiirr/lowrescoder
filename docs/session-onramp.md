# Session Onramp (Current State)

Last updated: 2026-02-13

This is the fastest way to rebuild working context for HybridCoder in a new session.

## 1) Read Order (10-15 minutes)

1. `AGENTS.md` — repo rules, command set, and communication protocol.
2. `CLAUDE.md` — architecture principles, project invariants, session index.
3. `TESTING.md` — how to test, evaluate, and interpret results.
4. `docs/requirements_and_features.md` — what is done vs planned.
5. `docs/plan/phase3-final-implementation.md` — authoritative Phase 3 plan.
6. `docs/qa/phase3-before-after-benchmark-protocol.md` — required benchmark workflow.

## 2) Authoritative vs Historical Docs

- Authoritative for Phase 3 implementation:
  - `docs/plan/phase3-final-implementation.md`
- Archived (do not treat as source of truth):
  - `docs/archive/phase3-code-intelligence.md`
  - `docs/archive/phase3-review-notes.md`
- Deleted (consolidated into plan.md):
  - `docs/spec.md` — MVP checklist now in `docs/plan.md` Section 1.6

## 3) Current System Snapshot

- Language/runtime split:
  - Python backend and CLI under `src/hybridcoder/`
  - Go TUI code under `cmd/hybridcoder-tui/` (JSON-RPC client to Python backend)
- Python UI frontends in repo:
  - Inline: `src/hybridcoder/inline/`
  - Textual: `src/hybridcoder/tui/`
- Agent tool baseline (current):
  - `read_file`, `write_file`, `list_files`, `search_text`, `run_command`, `ask_user`

## 4) Codebase Map (High Value Paths)

- Backend RPC server: `src/hybridcoder/backend/server.py`
- Tool registry: `src/hybridcoder/agent/tools.py`
- Config schema: `src/hybridcoder/config.py`
- Session state: `src/hybridcoder/session/`
- Go TUI transport and event loop: `cmd/hybridcoder-tui/backend.go`, `cmd/hybridcoder-tui/update.go`
- Benchmarks: `tests/benchmark/`
- E2E scenario runner: `scripts/e2e/`
- E2E seed fixtures: `scripts/e2e/fixtures/`

## 5) Phase 3 Plan Snapshot

- Goal: 60-80% of queries resolved without LLM tokens.
- Gate structure:
  - Alpha: 3A (parser/symbols), 3B (router/query handlers)
  - Beta: 3D (chunking/embeddings), 3E (index/search), 3F (repo map/context)
  - Gamma: 3G (integration, tools, verification)
- Deferred from Phase 3:
  - Sprint 3C (LSP integration)
  - `get_diagnostics` tool
- Expected tool count after Phase 3: 11 total.

For a compact execution version, use `docs/plan/phase3-execution-brief.md`.

## 6) Commands You Actually Need

- Setup:
  - `uv sync --all-extras`
- Main test run:
  - `uv run pytest tests/ -v`
- Lint/typecheck:
  - `uv run ruff check src/ tests/`
  - `uv run mypy src/hybridcoder/`
- **E2E benchmarks:**
  - `uv run python scripts/run_calculator_benchmark.py` — Calculator benchmark
  - `uv run python scripts/e2e/run_scenario.py E2E-BugFix` — BugFix scenario
  - `uv run python scripts/e2e/run_scenario.py E2E-CLI` — CLI scenario
  - `uv run python scripts/e2e/run_scenario.py --list` — Show all scenarios
  - `.\scripts\run_e2e_benchmark.ps1` — PowerShell wrapper (calculator default)
  - `.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-BugFix` — PS wrapper for BugFix
  - `.\scripts\run_e2e_benchmark.ps1 -Scenario E2E-CLI` — PS wrapper for CLI
  - See `TESTING.md` for full guide, or `docs/qa/e2e-benchmark-guide.md` for deep details
- **External benchmarks (requires Docker + Harbor):**
  - `uv run python scripts/e2e/external/run_external_pilot.py --agent codex --suite swebench` — SWE-bench pilot
  - `uv run python scripts/e2e/external/run_external_pilot.py --agent claude-code --suite terminalbench` — Terminal-Bench pilot
  - `uv run python scripts/e2e/external/run_external_pilot.py --help` — All options
  - See `docs/plan/agentic-benchmarks/external-benchmark-runbook.md` for full setup
- Before/after Phase 3 benchmark snapshots:
  - `./scripts/run_phase3_benchmark_snapshot.sh before`
  - `./scripts/run_phase3_benchmark_snapshot.sh after`
- Persist any run output:
  - `./scripts/store_test_results.sh <label> -- <command>`

## 7) Artifact Locations

- Stored run artifacts: `docs/qa/test-results/`
- Phase 3 before/after snapshots: `docs/qa/phase3-benchmarks/`
- Real-life benchmark standards: `docs/qa/real-life-benchmark-standards.md`
- **E2E benchmark guide: `docs/qa/e2e-benchmark-guide.md`**
- **External benchmark runbook: `docs/plan/agentic-benchmarks/external-benchmark-runbook.md`**
- E2E UI reference images: `docs/qa/e2e-tests/calculator-app/`
- E2E sandbox outputs: `sandboxes/`

## 8) Known Baseline QA State (as of 2026-02-13)

From stored artifacts in `docs/qa/test-results/`:
- pytest suite: passing (`601 passed, 1 skipped, 10 deselected`)
- ruff: failing baseline issues (30)
- mypy: failing baseline issues (2 in `src/hybridcoder/backend/server.py`)
- E2E scenarios: E2E-BugFix, E2E-CLI, E2E-Calculator defined and runnable
- E2E verdict system: PASS (exit 0), FAIL (exit 1), INFRA_FAIL (exit 2)

Treat ruff/mypy failures above as pre-existing baseline until explicitly fixed.

## 9) Session Start Checklist

1. Read this file and `AGENTS.md`.
2. Check active thread state in `AGENTS_CONVERSATION.MD`.
3. Confirm whether task is plan/doc only or implementation.
4. If implementation: run baseline tests and store artifacts before changes.
5. If Phase 3 work: use the before/after snapshot protocol.

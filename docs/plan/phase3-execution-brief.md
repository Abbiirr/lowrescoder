# Phase 3 Execution Brief (One Page)

Last updated: 2026-02-12
Authoritative source: `docs/plan/phase3-final-implementation.md`

This is the short execution contract for Phase 3. Use this for daily implementation work.

## Scope

In scope (Phase 3):
- 3A: tree-sitter parser + symbol extraction
- 3B: router + deterministic query handlers
- 3D: AST-aware chunking + embeddings
- 3E: LanceDB index + hybrid search
- 3F: repo map + context assembler
- 3G: integration + tools + verification

Deferred (not Phase 3):
- 3C LSP integration (multilspy/Jedi path)
- `get_diagnostics` tool

## Target Outcomes

- 60-80% zero-token query handling
- p95 deterministic latency under 50ms
- search precision@3 above 60%
- context assembly at or under 5000 tokens

## Tool Contract

Current baseline tools (6):
- `read_file`, `write_file`, `list_files`, `search_text`, `run_command`, `ask_user`

Phase 3 additions (5):
- `find_references`
- `find_definition`
- `get_type_info`
- `list_symbols`
- `search_code`

Post-Phase-3 total: 11 tools.

## Gate Exit Checks

Gate 1 (Deterministic):
- router accuracy >= 90%
- L1 latency p95 < 50ms
- deterministic path uses 0 tokens

Gate 2 (Retrieval):
- search precision@3 > 60%
- context budget <= 5000 tokens
- BM25-only fallback works when embeddings unavailable

Gate 3 (Integration):
- on_done includes `layer_used`
- UI displays `[L1]`, `[L2]`, `[L4]`
- `/index` command works
- test and verification suite passes required checks

## Files Most Likely To Change

Python:
- `src/hybridcoder/backend/server.py`
- `src/hybridcoder/agent/tools.py`
- `src/hybridcoder/config.py`
- `src/hybridcoder/agent/prompts.py`
- `src/hybridcoder/layer1/` (new)
- `src/hybridcoder/layer2/` (new)

Go:
- `cmd/hybridcoder-tui/protocol.go`
- `cmd/hybridcoder-tui/backend.go`
- `cmd/hybridcoder-tui/messages.go`
- `cmd/hybridcoder-tui/statusbar.go`
- `cmd/hybridcoder-tui/update.go`
- `cmd/hybridcoder-tui/commands.go`

Tests/benchmarks:
- `tests/unit/` (router, parser, tools, context)
- `tests/benchmark/` (routing, latency, search, context)

## Required Benchmark Workflow

Before implementation baseline:
- `./scripts/run_phase3_benchmark_snapshot.sh before`

After implementation snapshot:
- `./scripts/run_phase3_benchmark_snapshot.sh after`

Store all command outputs:
- `./scripts/store_test_results.sh <label> -- <command>`

## Daily Execution Pattern

1. Pick one sprint slice (small, testable).
2. Implement plus tests in the same commit scope.
3. Store test artifacts.
4. Re-run affected benchmark checks.
5. Update comms log with concrete results and residual risk.

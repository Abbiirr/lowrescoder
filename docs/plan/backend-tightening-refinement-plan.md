# Backend Tightening And Refinement Plan

> Status: ACTIVE — user-directed backend-first tranche as of 2026-04-24.
> Relationship to HR-5: this temporarily runs ahead of further frontend binding work. Once this tranche is stable, resume HR-5 Phase B (`/cc` real-data binding).

## Goal

Tighten backend correctness and observability before more frontend-facing work. The immediate target is not a backend rewrite; it is to make the current backend behavior stable, testable, and honest across the live user path and the modular transport seams.

Focus areas requested by the user:

- thinking-token streaming
- subagents
- context management
- memory management
- todo/task surfaces
- loop behavior
- transport and host stability

## Commit-Readiness Baseline

This tranche begins with a fresh regression gate, not an old artifact:

- `uv run pytest autocode/tests/unit -q`
- `uv run pytest benchmarks/tests -q`
- `cargo test --manifest-path autocode/rtui/Cargo.toml -q`
- `cargo clippy --manifest-path autocode/rtui/Cargo.toml -- -D warnings`
- `cargo build --release --manifest-path autocode/rtui/Cargo.toml`
- `python3 autocode/tests/pty/pty_smoke_rust_m1.py`
- `python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py`

If that gate is not green, stop and fix regressions before starting refinement work.

## Execution Order

### Stage 1 — Transport And Chat Conformance

Lock down the actual wire behavior instead of relying on host-specific mocks.

- expand transport conformance beyond session/command/status seeds
- cover `on_chat_ack`, `on_warning`, `on_thinking`, `on_token`, `on_tool_call`, `on_task_state`, and `on_done`
- prove the same ordering and payload shape across stdio and TCP hosts
- cover cancel and done-path behavior where practical

### Stage 2 — Task, Subagent, Todo, And Loop Surfaces

Tighten the backend-owned runtime surfaces that feed the frontend.

- validate `task.list`, `subagent.list`, and task/subagent projection notifications through real host seams
- validate loop-owned command/prompt execution surfaces
- ensure empty-state vs populated-state payloads are honest and deterministic
- add regression coverage for task mutations that should emit backend-authoritative updates

### Stage 3 — Context And Memory Management

Prove that context and memory behavior is stable enough before more UI binding.

- validate memory list/read surfaces through the backend contract
- validate project-memory bootstrap and context assembly behavior under the backend host
- tighten context-budget and memory-learning expectations where current tests are too narrow
- document any intentionally deferred heuristics instead of leaving them implicit

### Stage 4 — Host Hygiene And Architecture Follow-through

Clean up backend/host seams that are stable enough to tighten now.

- narrow `autocode.backend.chat.ChatHost` away from broad `BackendServer` internals
- harden TCP host behavior: client policy, back-pressure, and transport lifecycle
- preserve backend stderr on the live user path and clean up the misleading PTY naming/scaffolding if that path remains stdio-based
- tighten or document the real `RpcApplication` contract surface

## Exit Gate

This backend tranche is complete enough to hand control back to frontend work only when:

1. the commit-readiness baseline is green on the current tree
2. the expanded backend transport/conformance coverage is green
3. live backend-visible failures are surfaced honestly rather than hanging silently
4. the remaining backend follow-through items are either fixed or recorded explicitly in `modular_migration_todo.md`

At that point, resume HR-5 Phase B `/cc` real-data binding with the backend contract in a tighter state.

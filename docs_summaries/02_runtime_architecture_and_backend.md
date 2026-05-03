# Runtime Architecture And Backend Summary

## Current runtime shape

The current product runtime is a Rust frontend plus a Python backend joined by a documented JSON-RPC contract.

- Rust frontend: [autocode/rtui/README.md](../autocode/rtui/README.md)
- Python backend and protocol overview: [docs/architecture.md](../docs/architecture.md)
- Current runtime decomposition and replaceability status: [docs/features/features_behavior.md](../docs/features/features_behavior.md)
- Wire contract: [docs/reference/rpc-schema-v1.md](../docs/reference/rpc-schema-v1.md)

## What is actually true today

- The canonical interactive frontend is the Rust TUI.
- The default backend host path is stdio JSON-RPC.
- A TCP attach path also exists from the modularization work.
- The backend/frontend split is real, but still has follow-through items around host hygiene, transport depth, and backend seam narrowing.
- Layer 3 is an opt-in local constrained-generation path: the router can reach it when the `layer3` optional extra is installed, but core installs leave it dormant and fall back to Layer 4 until the model/dependency story and routed integration proof are upgraded.

This “what is true today” view is captured best in:

- [docs/features/features_behavior.md](../docs/features/features_behavior.md)
- [docs/plan/deferred/modular_migration_plan.md](../docs/plan/deferred/modular_migration_plan.md)
- [docs/plan/deferred/modular_migration_todo.md](../docs/plan/deferred/modular_migration_todo.md)

## Architecture docs by role

### Broad architecture overview

[docs/architecture.md](../docs/architecture.md) explains:

- the Rust TUI frontend
- the Python JSON-RPC backend
- the 4-layer intelligence model
- main directories and build/test commands

It is the best single-file “system overview” doc, but it mixes current state with some older entrypoint references.

### Runtime inventory / replaceability view

[docs/features/features_behavior.md](../docs/features/features_behavior.md) is the best “what owns what” doc.

It tells you:

- what the launcher owns
- what the frontend owns
- what the backend owns
- what is shared contract vs local implementation detail
- where swapability is real vs only partial

### Feature catalog

[docs/requirements_and_features.md](../docs/requirements_and_features.md) is a built-vs-planned catalog.

It is useful for broad feature coverage. For current ownership and swapability details, prefer `docs/features/features_behavior.md` and `docs/features/backend_features.md`.

## Backend-specific current direction

The active backend tightening work is now recorded in:

- [docs/plan/backend-tightening-refinement-plan.md](../docs/plan/backend-tightening-refinement-plan.md)

That plan says:

- first prove commit-readiness on the current tree
- then tighten backend correctness before more frontend binding work
- start with transport/chat/task/memory conformance
- only after deeper behavior coverage should bigger backend refactors happen

## Modularization status

The modularization track says:

- phases 0-5 are effectively complete
- follow-through remains for phases 2-4
- phase 6 cleanup remains

The important docs are:

- [docs/plan/deferred/modular_migration_plan.md](../docs/plan/deferred/modular_migration_plan.md)
- [docs/plan/deferred/modular_migration_todo.md](../docs/plan/deferred/modular_migration_todo.md)

The high-level reading is:

- the architecture split is real enough to operate
- it is not “finished forever”
- the remaining risk is in seam depth and behavioral proof, not in absence of a split

## Backend/TDD implication

The right way to improve the backend from here is not “more refactor first”. It is:

1. deepen transport-aware backend contract tests
2. fix mismatches those tests expose
3. only then narrow interfaces like `ChatHost` or tighten host internals

That is consistent with the current backend-tightening plan and the latest agent-comms direction.

## Source references

- [docs/architecture.md](../docs/architecture.md)
- [docs/features/features_behavior.md](../docs/features/features_behavior.md)
- [docs/requirements_and_features.md](../docs/requirements_and_features.md)
- [docs/reference/rpc-schema-v1.md](../docs/reference/rpc-schema-v1.md)
- [autocode/rtui/README.md](../autocode/rtui/README.md)
- [docs/plan/deferred/modular_migration_plan.md](../docs/plan/deferred/modular_migration_plan.md)
- [docs/plan/deferred/modular_migration_todo.md](../docs/plan/deferred/modular_migration_todo.md)
- [docs/plan/backend-tightening-refinement-plan.md](../docs/plan/backend-tightening-refinement-plan.md)

# Modular Migration Plan

> **Status:** ACTIVE — user-directed architecture track as of 2026-04-23.
> **Scope:** move AutoCode toward a modular runtime where launcher, frontend, backend, and transport can be evolved or swapped independently.
> **Authority:** this file is now the canonical execution plan for the modular-architecture track. It runs alongside the active HR-5 product queue unless the user explicitly pauses HR-5.

---

## 1. Strategic Goal

AutoCode should be able to support:

1. multiple frontends against the same backend behavior
2. multiple backend hosts against the same frontend contract
3. independent run/test loops for frontend and backend
4. transport changes without rewriting application logic

The current runtime is only partially there. The Rust TUI and Python backend already meet at a documented JSON-RPC seam, but process spawning, slash-command ownership, and transport assumptions still cross the boundary.

This migration plan turns the current runtime into four explicit modules:

- launcher
- frontend
- backend host
- application core plus shared contract

## 1.1 Relationship To The Existing HR-5 Queue

This track runs in parallel with HR-5, not instead of it.

- HR-5 remains the product-facing TUI correctness and real-data binding queue.
- The modular migration track is the architecture queue that removes backend/frontend coupling over time.
- If a slice affects both tracks, the implementation must preserve the current user path and the benchmark/TUI canary conventions already established by HR-5.
- This plan only pauses HR-5 if the user explicitly says to pause it.

## 2. Source Baseline

This plan is based on:

- `docs/features_behavior.md`
- `autocode/src/autocode/cli.py`
- `autocode/src/autocode/backend/server.py`
- `autocode/src/autocode/backend/schema.py`
- `docs/reference/rpc-schema-v1.md`
- `autocode/rtui/src/main.rs`

## 2.1 Current Progress Snapshot (2026-04-23)

- Phase 0 is mostly complete at the doc plus unit-test level: the RPC doc now spells out liveness and session-reset guarantees, backend/UI import guardrails are enforced, and focused contract tests cover chat ack/stream ordering plus task/subagent projection and session-reset behavior.
- Phase 1 is effectively complete: backend and other non-UI callers now use `autocode.app.commands`, while `autocode.tui.commands` remains only as a compatibility alias and alias-specific test seam.
- Phase 2 is started but not closed: `autocode.backend.services` now owns non-chat backend application behavior for session lifecycle, command execution, provider/model listing, task/subagent projection, plan/config, checkpoint, and steer/fork operations.
- Phase 2 also now has a dedicated dispatch module: `autocode.backend.dispatcher` owns RPC method routing instead of `BackendServer`.
- The remaining heavy Phase 2 seam is chat-turn execution itself. `BackendServer` still owns chat routing, agent-loop bootstrapping, stream callbacks, request tracking, and the stdio read/write loop.

## 2.2 Realistic Assessment (2026-04-23)

What is genuinely done:

- backend/UI package coupling through `autocode.tui.commands` is removed from production backend code
- a real host-independent service layer now exists for non-chat backend behavior
- focused backend validation is green, and current Rust TUI tests are green

What is only partially done:

- Phase 0 contract hardening is still mostly unit-level; it is not yet a reusable transport-agnostic conformance harness
- Phase 2 is only halfway done because the chat path remains inside `BackendServer`
- frontend/backend independence is still theoretical because the Rust TUI still spawns the backend directly

What is still tightly coupled:

- `autocode/rtui/src/backend/pty.rs` still starts `autocode serve` itself
- `autocode/rtui/src/rpc/bus.rs` assumes a paired read/write stream, not an attachable backend transport abstraction
- `autocode/src/autocode/backend/server.py` is still large because chat execution and stdio transport live together
- `autocode/src/autocode/cli.py` still only composes the spawn-managed user path

What was broken or stale at audit start, and is now fixed:

- the broader unit suite was not green at audit start: `1840 passed, 6 failed`
- the 2 config-sensitive CLI launch tests now patch deterministic config instead of reading this machine's saved alt-screen preference
- the 4 TUI reference-helper tests now match the current `14 direct` scene reality instead of the old `6 direct / 2 approximate / 6 blocked` taxonomy
- the stale backend-host wording that still referenced the removed Go/Bubble Tea frontend is cleaned up in the touched Python host surfaces

Current interpretation:

- there is no evidence that the recent backend-service extraction broke the focused modularization path
- the broader unit-suite baseline is green again after Tranche A cleanup
- Phase 3 should still wait for the remaining Phase 2 chat extraction, but it is no longer blocked on stale broader-suite failures

## 3. Design Principles

### 3.1 Preserve working behavior first

No phase is allowed to trade away current user-visible behavior for cleaner architecture unless the user explicitly accepts that regression.

### 3.2 Extract seams before replacing implementations

The plan is to isolate boundaries, not to rewrite the agent loop or replace the TUI.

### 3.3 Protocol is the first-class contract

If frontend and backend are to be swappable, protocol guarantees must become stricter and more explicit than implementation habits.

### 3.4 Application logic must not live in a UI package

Anything the backend needs in order to serve a frontend must move out of `autocode.tui.*`.

### 3.5 Transport is an adapter, not the product

Stdio JSON-RPC can remain the first transport, but it must stop being the only shape the system can take.

## 4. Non-Goals

This plan does not assume:

- a web frontend
- remote multi-user serving
- RPC v2
- replacement of the Rust TUI
- replacement of the Python agent loop
- a new model/provider stack
- a full repo reorganization in one cutover

Those may happen later, but they are not required to achieve modularity.

## 5. Target Architecture

The target runtime is:

```text
autocode (launcher)
  -> frontend process or client
       -> transport adapter
            -> backend host
                 -> application core
                      -> agent/session/task/memory/tool services
```

### 5.1 Launcher

Owns:

- user-facing entrypoints
- local process composition
- mode selection
- environment and config resolution

Does not own:

- frontend rendering logic
- backend business logic
- protocol semantics

### 5.2 Frontend

Owns:

- input
- rendering
- local UI state
- local recovery UX
- session attachment workflow

Does not own:

- backend process policy
- task/session truth
- slash-command semantics

### 5.3 Backend Host

Owns:

- transport serving
- request routing
- session attachment
- application-service composition

Does not own:

- terminal UX
- frontend-only state

### 5.4 Application Core

Owns:

- agent orchestration
- sessions
- plans
- checkpoints
- tasks and subagents
- approvals and ask-user flows
- command catalog and command semantics
- provider/model registry surfaces

Does not own:

- stdio
- PTY
- ratatui
- Typer

### 5.5 Shared Contract

Owns:

- method names
- payload types
- required notification order
- liveness rules
- session-switch guarantees
- capability/version negotiation once added

## 6. Current Blocking Seams

The migration is justified by four specific coupling problems:

1. the Rust TUI currently supervises backend startup instead of only acting as a client
2. `BackendServer` imports `autocode.tui.commands`, which makes backend behavior depend on a UI package
3. stdio JSON-RPC is a hard-wired implementation detail instead of one backend transport
4. `BackendServer` still mixes transport, orchestration, and application-service responsibilities

These are the seams the phases below are designed to remove.

## 7. Migration Phases

## Phase 0 — Contract Lock And Architectural Guardrails

Goal:

- make the current seam explicit enough that extraction work does not drift

Work:

- expand `docs/reference/rpc-schema-v1.md` from method inventory to behavior contract
- document liveness rules for `on_chat_ack`, `on_token`, `on_done`, and timeout expectations
- document session-switch/reset guarantees
- document which state is frontend-local vs backend-authoritative
- add conformance tests for the most failure-prone semantics
- define a no-new-import rule: backend code must not gain new dependencies on `autocode.tui.*`

Execution slices:

- Phase 0A: chat-ack, streaming-liveness, and stale-timeout contract
- Phase 0B: session-switch/reset contract and task/subagent projection contract
- Phase 0C: guardrails and conformance-test enforcement in the build/test path

Exit gate:

- protocol doc covers behavioral guarantees, not just payload names
- conformance tests exist for chat ack, session reset, task/subagent state projection, and recovery-trigger liveness
- user can point to one place and answer: what is guaranteed by contract, and what is just frontend behavior

## Phase 1 — Extract Application Surface Out Of UI Packages

Goal:

- make backend-facing application behavior live outside `autocode.tui.*`

Work:

- extract slash-command definitions into a shared application module
- extract command catalog types and discovery helpers into a backend-agnostic location
- extract provider/model listing helpers out of `autocode.tui.commands`
- leave thin frontend-specific adapters behind where needed
- update backend to depend on application-layer command modules instead of TUI modules

Execution slices:

- Phase 1A: create shared application command-runtime module and compatibility alias
- Phase 1B: point backend imports at the shared module
- Phase 1C: migrate non-backend internal imports opportunistically and stabilize test coverage

Exit gate:

- `autocode/src/autocode/backend/` does not import `autocode.tui.commands`
- command discovery and command execution semantics are testable without a UI package
- the Rust TUI still gets the same command catalog over RPC

## Phase 2 — Split Backend Host From Application Core

Goal:

- make `BackendServer` a transport adapter over a thinner application service

Work:

- identify the service surface behind the current RPC handlers
- introduce an application service layer for:
  - chat turn execution
  - session lifecycle
  - command execution
  - plan/checkpoint/memory operations
  - task/subagent listing and mutation
- reduce `BackendServer` to request parsing, response emission, request tracking, and transport lifecycle
- keep current stdio behavior unchanged during the split

Exit gate:

- transport concerns and application concerns live in separate modules
- core application behavior is unit-testable without JSON-RPC framing
- `BackendServer` becomes replaceable by another host without moving domain logic again

Current progress note:

- `autocode.backend.services` is now the canonical home for the non-chat application-service surface.
- `BackendServer` has already been reduced for session lifecycle, commands, task/subagent projection, plan/config, checkpoint, and steer/fork handlers.
- `autocode.backend.dispatcher` now owns request-method routing.
- The next Phase 2 slice is extracting chat-turn execution and callback wiring so the server stops owning the highest-value application behavior.

## Phase 3 — Introduce Transport Abstraction

Goal:

- stop treating stdio JSON-RPC as the only valid runtime shape

Work:

- define a backend-host transport boundary in Python so request parsing, response emission, correlation, and shutdown are no longer hard-coded inside `BackendServer`
- keep stdio JSON-RPC as the first concrete implementation
- introduce a second real transport shape for local attach workflows
- make the Rust-side client plumbing capable of connecting over something other than the current spawned stdio pipe

Execution slices:

- Phase 3A: extract stdio framing and thread/reader lifecycle out of `BackendServer` into a dedicated stdio host adapter
- Phase 3B: define a transport-agnostic host/application seam for request emission, notification emission, and request correlation
- Phase 3C: add a second real host shape, recommended as localhost TCP JSON-RPC for easy human attach/debug workflows
- Phase 3D: add transport smoke coverage proving both stdio and the second transport can drive the same backend application surface

Prerequisites before claiming Phase 3 active:

- the six currently failing broader unit tests must be fixed or explicitly reclassified
- Phase 2 chat-turn extraction must be at least far enough along that transport work is not blocked by `BackendServer` still owning all application behavior

Exit gate:

- backend application services are transport-agnostic
- stdio remains green
- a second host shape can drive the same application surface without backend business-logic duplication
- the backend host can be run on its own in a way that a human can point a client at directly

## Phase 4 — Decouple Frontend From Backend Process Supervision

Goal:

- make the frontend attach to a backend instead of owning its process model

Work:

- split Rust TUI backend-process spawning from its RPC client responsibilities
- introduce an explicit frontend connection abstraction so the same UI can talk to a spawned backend or an already-running backend
- keep current bare `autocode` UX intact through the launcher
- add explicit attach-mode smoke tests and one real user-path validation

Execution slices:

- Phase 4A: replace the current `spawn_backend()` assumption with connection strategies such as `spawn-managed` and `attach`
- Phase 4B: add launcher/backend addressing flags or env wiring so a human can run `autocode serve` separately and then attach the Rust TUI
- Phase 4C: keep session bootstrap, `AUTOCODE_SESSION_ID`, and `session.resume` behavior correct across both spawn and attach paths
- Phase 4D: add live smoke coverage for spawn mode and attach mode, then rerun one benchmark-owned TUI canary on the supported path

Recommended default policy:

- keep spawn-managed backend as the default user path until Phase 5 proves attach mode cleanly
- make attach mode explicit, not implicit, until backend-host lifecycle and reconnect semantics are stable

Exit gate:

- the Rust TUI can run against an already-running backend host
- frontend tests can exercise the TUI without relying on the current spawn path
- launcher owns composition policy; frontend owns UI/client behavior
- a human can start backend and frontend independently and still get a truthful, supported workflow

## Phase 5 — Prove Swapability

Goal:

- demonstrate that the new seams are real, not just renamed files

Work:

- run the canonical Rust TUI against the extracted backend host through the stable contract
- run a thin alternate frontend or fixture client against the same backend host
- run the Rust TUI against a mock or alternate host that satisfies the contract
- verify plan, session, checkpoint, task, subagent, approval, and recovery paths through the new seams

Exit gate:

- fixture-level proof is acceptable during earlier phases, but it does not satisfy final Phase 5 completion on its own
- at least one real second runtime shape must be demonstrated before Phase 5 is complete:
  - either a real second frontend path against the same backend host
  - or a real second backend-host path that the Rust TUI can attach to
- one fixture or mock proof may accompany the real proof, but may not replace it
- core behavior remains unchanged on the user path

Status:

- PASSED on 2026-04-23.
- Real second runtime shape: benchmark-owned Rust TUI attach mode against a TCP backend host on `B13-PROXY`.
- Attach-path proof artifact: `docs/qa/test-results/20260423-145703-B13-PROXY-autocode.json`.
- Spawn-managed comparator artifact: `docs/qa/test-results/20260423-150833-B13-PROXY-autocode.json`.
- Close-out note: `autocode/docs/qa/test-results/20260423-210037-modular-phase5-closeout.md`.
- The stricter review criterion from Claude Entry `1400` is now satisfied: the same gateway/model/lane window produced effectively the same outcome on both attach and spawn-managed shapes.
  - attach: `181.1s`, `INFRA_FAIL`, `ready -> streaming`, `first_streaming_s = 90.527`
  - spawn: `181.0s`, `INFRA_FAIL`, `ready -> streaming`, `first_streaming_s = 91.638`
- The live provider route was unstable in both shapes, so the timeout evidence is attach-unrelated rather than a modular transport regression.
- Fresh regression sweep after the proof run remained green: `uv run pytest autocode/tests/unit -q` -> `1862 passed`; `uv run pytest benchmarks/tests -q` -> `199 passed`; Rust `cargo test`, `cargo clippy -- -D warnings`, `cargo build --release`, and both PTY smoke suites passed.

## Phase 6 — Cutover And Cleanup

Goal:

- remove temporary compatibility scaffolding once the modular seams are proven

Work:

- delete deprecated import paths and adapters
- simplify launcher code around the new composition model
- update canonical docs
- store final verification artifacts

Exit gate:

- no remaining dependency from backend application logic into UI packages
- documented run/test instructions exist for each module
- active docs reflect the new architecture truthfully

## 8. Acceptance Gates

The migration is only successful if all of these are true:

1. frontend can be started independently from backend-host process creation
2. backend application behavior can be tested independently from JSON-RPC transport
3. command semantics are owned outside UI packages
4. stdio remains supported, but not required as the only backend-host shape
5. user-facing `autocode` still works throughout the migration
6. the TUI testing matrix stays green on the supported path

## 9. Validation Matrix

Every migration phase should validate at the layer it changes.

### 9.1 Contract and backend-core work

Use:

- `uv run pytest autocode/tests/unit/test_backend_server.py -v`
- new core-service tests that do not rely on RPC framing
- RPC conformance tests against schema v1

### 9.2 Frontend/client work

Use:

- `cd autocode/rtui && cargo test`
- `cd autocode/rtui && cargo clippy -- -D warnings`
- `python3 autocode/tests/pty/pty_smoke_rust_m1.py`
- `python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py`
- `make tui-regression`
- `make tui-references`

### 9.3 User-path validation

Use:

- bare `autocode` live smoke
- `autocode serve` host smoke
- one benchmark-owned TUI canary after any backend-host or frontend-transport change

## 10. Risks And Controls

### Risk 1 — architectural refactor breaks the only working user path

Control:

- keep launcher behavior stable until Phase 5 is proven
- require live bare-`autocode` smoke after each user-path change

### Risk 2 — transport abstraction becomes theoretical and unused

Control:

- require a second host/client proof before claiming Phase 3 complete

### Risk 3 — command extraction becomes a semantic rewrite

Control:

- preserve command names, catalog shape, and current RPC responses while moving ownership

### Risk 4 — backend split increases latency or timeout risk

Control:

- keep latency probes and chat-ack liveness checks active during host/core extraction

### Risk 5 — docs drift from actual migration state

Control:

- update `current_directives.md`, `EXECUTION_CHECKLIST.md`, and `PLAN.md` only when the user promotes this architecture track to active work

## 11. Initial Execution Tranche

The initial build tranche is not "just Phase 0A." It is the first pass across the full track, sequenced as smaller executable slices:

1. Phase 1A-1B shared command runtime extraction and backend import cutover
2. Phase 0A liveness-contract hardening and conformance tests
3. Phase 0B session-reset and task/subagent contract hardening
4. Phase 1C cleanup plus remaining provider/model/catalog extraction polish
5. Phase 2 service-boundary discovery and first backend-host split

Reason:

- it starts reducing a real layering leak immediately
- it still keeps contract hardening near the front of the queue
- it avoids spending multiple sessions on plan-only work before any structural code movement lands

## 12. Definition Of Done

The modular migration is done when:

- frontend, backend host, and application core have separate responsibilities
- the shared contract is explicit and tested
- the frontend can attach without supervising backend startup
- the backend application logic can be hosted over more than one transport shape
- run/test instructions are separate and truthful for launcher, frontend, and backend
- the default user path still behaves correctly

## 13. Immediate Next Work

The active next build steps for this track are:

1. Tranche A is complete; keep the broader unit-suite baseline green while continuing the refactor
2. finish Phase 2 by extracting chat-turn execution and callback wiring out of `BackendServer`
3. start Phase 3A by moving stdio transport ownership into a dedicated host adapter
4. prove a second host shape for attach workflows before claiming transport abstraction success
5. only then start Phase 4 frontend attach-mode work on top of the thinner backend host

Canonical canary reference:

- `docs/plan/hr5-phase-a-benchmark-latency-plan.md`
- lane convention: `B13-PROXY`

## 14. Execution Tranches (User-Locked 2026-04-23)

This is the concrete build order for the next work, based on the user-approved sequence.

### Tranche A — Honest Baseline Cleanup

Goals:

- remove stale or config-sensitive failures so the tree reflects reality before deeper refactors

Required work:

- fix the 2 CLI launch tests so they do not depend on this machine's saved alt-screen preference
- fix the 4 TUI reference-helper tests so they match the current `14 direct` scene reality
- clean up stale backend-host wording that still references the removed Go/Bubble Tea frontend where it is no longer historically scoped

Exit gate:

- `uv run pytest autocode/tests/unit -q` is globally green, or any remaining failures are explicitly explained and intentionally quarantined

Status:

- PASSED on 2026-04-23 with `1849 passed`

### Tranche B — Finish Phase 2 Backend-Host Split

Goals:

- get the chat path out of `BackendServer` far enough that transport work is no longer blocked by application logic living in the host

Required work:

- extract chat-turn execution into a host-independent service surface
- extract stream callback wiring and turn-result shaping
- keep `autocode.backend.dispatcher` as the dispatch owner and reduce `BackendServer` to host coordination rather than business logic
- keep current stdio behavior and the bare `autocode` user path stable throughout

Detailed execution order:

1. Move per-turn result shaping (`on_chat_ack`, `on_done`, cost snapshot, cancellation) into backend application helpers.
2. Move chat callback wiring (`on_chunk`, `on_thinking_chunk`, `on_tool_call`, approval, ask-user) into the same backend application layer so `BackendServer` stops owning turn semantics.
3. Move layer selection, session-title bootstrap, and first-turn/session-switch chat coordination into a dedicated chat service module.
4. Leave `BackendServer` responsible only for host-owned state access, dispatch entrypoints, and transport-facing request lifecycle.

Exit gate:

- `BackendServer` no longer owns the substantive chat-turn execution path
- core chat behavior is unit-testable without JSON-RPC framing

Status:

- PASSED on 2026-04-23.
- Landed via `autocode.backend.chat` plus direct unit coverage.
- Validation: focused backend slice green; broader `uv run pytest autocode/tests/unit -q` remained green.

### Tranche C — Phase 3 Transport Abstraction

Goals:

- make backend hosting transport-aware instead of stdio-hardcoded

Required work:

- move stdio framing/threading into a dedicated host adapter
- define the backend transport interface
- keep stdio as transport #1
- add localhost TCP JSON-RPC as transport #2
- add smoke coverage proving both hosts drive the same application surface

Detailed execution order:

1. Introduce a transport boundary for backend message emission and pending frontend-request correlation.
2. Move newline-delimited JSON framing plus stdin thread/reader lifecycle out of `BackendServer` into a dedicated stdio host adapter.
3. Keep `autocode serve` on stdio by default while adding explicit TCP host support for local attach/debug workflows.
4. Add direct tests that the same backend application object can be driven through both stdio and TCP host shapes.

Exit gate:

- backend application services are transport-agnostic
- a human can run a backend host directly without the Rust TUI being responsible for its process creation

Status:

- PASSED on 2026-04-23.
- Landed via `autocode.backend.transport`, `autocode.backend.stdio_host`, and `autocode.backend.tcp_host`.
- Validation includes direct stdio/TCP host smoke tests plus a live TCP backend probe recorded in `autocode/docs/qa/test-results/20260423-192805-tui-verification.md`.

### Tranche D — Phase 4 Frontend Attach Mode

Goals:

- let the frontend choose between spawning a backend and attaching to one

Required work:

- replace the Rust TUI's hardcoded spawn path with a connection abstraction
- support `spawn-managed` and `attach` frontend modes
- add launcher wiring so frontend and backend can be started independently
- preserve session bootstrap and `session.resume` behavior in both modes
- add attach-mode smoke coverage and rerun one benchmark-owned canary on the supported path

Detailed execution order:

1. Replace the current `spawn_backend()` assumption with an explicit frontend connection mode abstraction.
2. Keep `spawn-managed` as the default path and add `attach` as an explicit opt-in path to an already-running backend host.
3. Wire the Python launcher so bare `autocode` can still launch the Rust TUI normally while optionally forwarding attach information.
4. Preserve `AUTOCODE_SESSION_ID` and `session.resume` semantics regardless of connection mode.
5. Add unit/smoke coverage for both connection modes, then rerun one canary on the supported attach path if the backend host is stable enough.

Exit gate:

- a human can run backend and frontend independently with a supported workflow
- the default `autocode` path still works as before

Status:

- IMPLEMENTED on 2026-04-23 at unit + live-smoke level.
- Landed via Rust frontend connection-mode support plus launcher `--attach HOST:PORT` forwarding.
- Validation includes Rust tests, CLI tests, and a live inline attach startup recorded in `autocode/docs/qa/test-results/20260423-192805-tui-verification.md`.
- Spawn-managed mode is currently a stdio subprocess backend path, not a PTY-backed spawn path; cleanup of the module naming and dead PTY scaffolding is deferred to the follow-through tranche.
- Benchmark-owned harness support for the attach/TCP path now exists:
  - `benchmarks/benchmark_runner.py --autocode-tui-connection attach`
  - separate backend-host stdout/stderr artifacts
  - pyte-backed screen reconstruction in the TUI driver
- Live `B13-PROXY` attach-path canaries have already proved separate backend host + Rust TUI + real task/tool traffic; see `autocode/docs/qa/test-results/20260423-142003-modular-regression-phase5-kickoff.md`.
- The stronger proof requested in review is now satisfied by the attach artifact `docs/qa/test-results/20260423-145703-B13-PROXY-autocode.json` plus the spawn comparator `docs/qa/test-results/20260423-150833-B13-PROXY-autocode.json`.

### Tranche E — Phase 5 Swapability Proof

Goals:

- prove that the modular seams hold under the benchmark-owned runner, not just unit tests and ad hoc smokes

Required work:

- run `B13-PROXY` through `--autocode-runner tui --autocode-tui-connection attach`
- capture the same lane/model through the spawn-managed shape for comparison
- preserve standard benchmark JSON output plus TUI raw/screen/timing artifacts and backend-host logs
- rerun the broader regression matrix after the live proof step

Exit gate:

- one stored attach-path benchmark artifact exists on the live gateway
- a same-window spawn-managed comparator exists on the same lane/model
- the attach-vs-spawn comparison shows the live retry noise is not unique to attach mode
- fresh regression evidence remains green after the proof run

Status:

- PASSED on 2026-04-23.
- Attach-path proof artifact: `docs/qa/test-results/20260423-145703-B13-PROXY-autocode.json`.
- Spawn-managed comparator artifact: `docs/qa/test-results/20260423-150833-B13-PROXY-autocode.json`.
- Both artifacts ended as `INFRA_FAIL` at ~`181s`, both reached `ready -> streaming`, and `first_streaming_s` was within ~`1.1s`, which is strong enough evidence that the live provider instability was attach-unrelated.
- Supporting note and regression matrix: `autocode/docs/qa/test-results/20260423-210037-modular-phase5-closeout.md`.

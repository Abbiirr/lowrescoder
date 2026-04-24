# Modular Migration Todo

> **Status:** ACTIVE — user-directed architecture track. Phase 5 is complete; Phase 2-4 follow-through and Phase 6 cleanup remain.
> **Plan:** `modular_migration_plan.md`
> **Relationship to HR-5:** runs alongside the HR-5 product queue unless the user explicitly pauses HR-5.

## Phase 0 — Contract And Guardrails

- [x] Expand `docs/reference/rpc-schema-v1.md` from method inventory into a behavioral contract.
- [x] Document chat liveness rules for `on_chat_ack`, `on_token`, `on_done`, and stale-request handling.
- [x] Document session-switch/reset guarantees for frontend-local state.
- [x] Document backend-authoritative vs frontend-local state ownership.
- [x] Add conformance tests for chat-ack and first-streaming liveness.
- [x] Add conformance tests for session reset and task/subagent projection behavior.
- [x] Add a guardrail preventing new backend imports from `autocode.tui.*`.
- [x] Promote the current unit-level contract checks into a reusable transport-agnostic conformance harness.

## Phase 1 — Shared Command Runtime

- [x] Create a shared application-layer command-runtime module.
- [x] Keep the legacy `autocode.tui.commands` import path working as a compatibility alias.
- [x] Point backend imports at the shared command-runtime module.
- [x] Move remaining provider/model discovery helpers fully under the shared application module surface.
- [x] Audit remaining internal imports and move non-UI callers to the shared path where it improves clarity.
- [x] Add targeted regression tests for the shared command-runtime cutover.
- [x] Remove backend dependence on any UI-package command helpers beyond the compatibility bridge.

## Phase 2 — Backend Host Split

- [x] Identify the application-service surface currently buried inside `BackendServer`.
- [x] Extract chat-turn execution into a host-independent service layer.
- [x] Move chat route selection, turn lifecycle shaping, and session-title bootstrap into the extracted chat layer.
- [x] Extract session lifecycle operations into a host-independent service layer.
- [x] Extract command execution into a host-independent service layer.
- [x] Extract plan/checkpoint/memory operations into a host-independent service layer.
- [x] Extract task/subagent list/mutation operations into a host-independent service layer.
- [x] Extract stream callback wiring and turn-result shaping out of `BackendServer`.
- [x] Move approval and ask-user callback plumbing into the extracted chat layer.
- [x] Move request-method dispatch ownership out of `BackendServer`.
- [x] Reduce `BackendServer` to transport parsing, request correlation, and response emission.

## Phase 3 — Transport Abstraction

- [x] Extract the current stdio reader/writer/thread lifecycle into a dedicated stdio host adapter.
- [x] Define a transport interface for backend hosts.
- [x] Keep stdio JSON-RPC as the first concrete implementation.
- [x] Separate transport emission/correlation logic from backend application services.
- [x] Add a second real transport shape for attach workflows, preferably localhost TCP JSON-RPC.
- [x] Add transport smoke coverage for both stdio and the second transport.
- [x] Keep current stdio behavior green through the abstraction step.
- [x] Expose explicit backend-host launch options for stdio vs TCP so the backend is runnable on its own.

## Phase 4 — Frontend Attach Mode

- [x] Split backend process spawning from Rust TUI RPC-client responsibilities.
- [x] Introduce a frontend connection abstraction that supports both spawn-managed and attach flows.
- [x] Define a spawn-managed frontend mode.
- [x] Define an attach-to-existing-backend frontend mode.
- [x] Add CLI or env wiring so a human can point the frontend at a running backend host.
- [x] Preserve session bootstrap and `session.resume` semantics across both modes.
- [x] Preserve the current bare `autocode` user path through the launcher.
- [x] Add attach-mode smoke coverage.
- [x] Run one benchmark-owned canary after the attach path is live on the supported path.

## Phase 5 — Swapability Proof

Status note (2026-04-23):
- COMPLETE. Close-out note: `autocode/docs/qa/test-results/20260423-210037-modular-phase5-closeout.md`.
- Attach-path proof artifact: `docs/qa/test-results/20260423-145703-B13-PROXY-autocode.json`.
- Spawn-managed comparator artifact: `docs/qa/test-results/20260423-150833-B13-PROXY-autocode.json`.
- Claude Entry `1400` asked for proof that the live retry noise was attach-unrelated. That criterion is now satisfied: the same gateway/model/lane window produced the same `~181s` `INFRA_FAIL`, the same `ready -> streaming` trace, and nearly identical first-streaming timing on both attach and spawn.

- [x] Run the Rust TUI against the extracted backend host through the stable contract.
- [x] Demonstrate one real second runtime shape beyond the current embedded stdio path.
- [x] Verify session, checkpoint, task, subagent, approval, and recovery flows through the new seams.
- [x] Reuse the benchmark-owned `B13-PROXY` canary convention for backend-host or frontend-transport changes.
- [x] Record the final proof that fixture-only validation was not the sole evidence for swapability.

## Phase 2-4 Follow-through

Carry-forward items from Claude Entry `1400` after approving Phases 1-4 and tightening the Phase 5 close criterion.

- [ ] Narrow `autocode.backend.chat.ChatHost` to a real public service surface instead of relying on `BackendServer` internals.
- [ ] Rename `autocode/rtui/src/backend/pty.rs` or restore a real PTY-backed spawn path, and preserve backend stderr on the live user path.
- [ ] Remove dead `ChildGuard` / resize scaffolding if the spawn-managed path remains stdio-based.
- [ ] Expand the transport conformance harness beyond the current session/command/status seed surface.
- [ ] Tighten or document the real `RpcApplication` host-adapter protocol surface.
- [ ] Decide and document TCP host single-client behavior explicitly.
- [ ] Warn or refuse non-loopback `serve --transport tcp --host` binds by default.
- [ ] Replace fire-and-forget TCP drain tasks with a back-pressure-safe writer strategy.
- [ ] Verify Textual and legacy UI entrypoints consume the shared `autocode.app.commands` runtime cleanly.

## Phase 6 — Cutover And Cleanup

- [ ] Delete temporary compatibility scaffolding that is no longer needed.
- [ ] Simplify launcher composition around the new modular seams.
- [ ] Update canonical docs to match the finished architecture.
- [ ] Store final verification artifacts.

## Audit Fixes Before Phase 3

- [x] Fix the config-sensitive CLI launch tests in `autocode/tests/unit/test_cli.py`.
- [x] Fix the stale TUI reference-helper expectation tests in `autocode/tests/unit/test_tui_reference_visual_gap_tools.py`.
- [x] Clean up stale backend-host wording that still says "Go Bubble Tea TUI frontend" where that is no longer true.

## Active Build Slice

- [x] Full modular plan exists.
- [x] Todo checklist exists.
- [x] First architecture extraction slice has started.
- [x] Focused validation for the current extraction slice is green.
- [x] Follow-up review request is posted after the slice lands.
- [x] Non-chat backend application services now live under `autocode.backend.services`.
- [x] Realistic state audit is written down.
- [x] Broader unit-suite baseline is green again after the audit cleanup pass.
- [x] Request-method dispatch now lives in `autocode.backend.dispatcher`.
- [x] Tranche B / Phase 2: extract chat-turn execution, callback wiring, and turn result shaping out of `BackendServer`.
- [x] Tranche C / Phase 3: introduce backend transport abstractions plus stdio and TCP host adapters.
- [x] Tranche D / Phase 4: introduce Rust frontend attach mode plus launcher wiring while keeping bare `autocode` stable.
- [x] Regression sweep for Phases 1-4 is green on the current automated matrix.
- [x] Benchmark-owned attach/TCP path exists in the harness and stores backend-host artifacts.
- [x] Follow through with the benchmark-owned canary on the supported modular path.

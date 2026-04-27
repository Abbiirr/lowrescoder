# Stabilize and Release Plan

> **Status:** ACTIVE.
> **Date:** 2026-04-26.
> **Authors:** Claude (Reviewer/Architect) drafted, User approved.
> **Companion plans:** `docs/plan/backend-feature-improvement-plan.md` (closed tranche), `docs/tui-testing/tui_implementation_plan.md` (HR-5 program), `docs/plan/backend-vision-and-usability.md` (UX/vision companion).

This plan organises the path from the current in-flight typed-payload consolidation slice to a release-ready, commit-stable working tree. It supersedes ad-hoc per-slice direction entries while it remains active. After Checkpoint 3 closes, archive this file alongside the other completed plans.

---

## Status Snapshot (2026-04-27 11:38)

**Closed in this session:**

- Backend Feature Improvement tranche — Stages 3-4 backend slices and S-DOCSREFRESH A through G; regression-green via Entry 1514.
- HR-5 Phase A (benchmark latency canary) — closed previously; not reopened.
- HR-5 Phase B (`/cc` real-data binding) — Entry 1518.
- HR-5 Phase C items 1-7 — `/restore` (display only), `/plan`, `/tasks`, `/grep`, `/review`+`/diff`, `/escalation`, `/multi` mockup-copy cleanup.
- Checkpoint 2 item 2.E `/restore` interaction layer — Codex Entry 1551; row navigation, confirmation, restore dispatch, and transcript feedback.
- Checkpoint 2 item 2.F.1 MCP CLI wire-up — Codex Entry 1554; generated MCP configs now target a real `autocode mcp-serve` stdio command.
- Checkpoint 2 item 2.B thinking/output buffer split — Codex Entry 1556; Rust TUI keeps reasoning tokens separate from visible assistant output.
- Checkpoint 2 item 2.C per-slash PTY smoke coverage — Codex Entry 1565; 10 high-risk slash surfaces have mock-backed PTY smoke coverage.
- Checkpoint 2 item 2.D spinner verb badge — Codex Entry 1568; active badges use the 194-verb spinner vocabulary with deterministic tick coverage.
- Checkpoint 2 item 2.F.2 MCP integration polish — Codex Entry 1571; doctor readiness, audit-log path discovery, interrupt-safe lifecycle, and concurrent-client coverage landed.
- Checkpoint 2 item 2.F.6 per-tool output-budget PTY — Codex Entry 1573; Rust TUI PTY smoke now proves visible truncation/budget marker handling.
- Checkpoint 2 item 2.F.7 tranche exit-gate sweeps — transport conformance and live/local PTY canary gates are closed. Artifact: `autocode/docs/qa/test-results/20260426-143510-2f7-tranche-exit-gate-sweeps.md`.
- Checkpoint 2 item 2.G regression gate — full unit, benchmark, Rust, Track 1, Track 4, PTY, live gateway, and `git diff --check` gates are green. Artifact: `autocode/docs/qa/test-results/20260426-145234-checkpoint2-regression-gate.md`.
- Checkpoint 3 items 3.A and 3.B — Phase E gate verification passed and visual-only polish is unblocked for a post-release polish pass. Artifact: `autocode/docs/qa/test-results/20260427-113808-phase-e-gate-verification.md`.
- Checkpoint 3 item 3.C — release-grade regression sweep is green. Artifact: `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`.
- Checkpoint 3 item 3.D — tranche-spanning closeout posted in `AGENTS_CONVERSATION.MD` Entry 1584.

**Checkpoint 1 — substantially closed (2026-04-26 evening):**

- 1.A typed-payload consolidation — DONE (was Entry 1542; approved and archived).
- 1.B comms cleanup — DONE (Entries 1476-1547 archived; comms channel reset to Entry 1548 plus current Checkpoint 2 work entries).
- 1.D pre-commit regression gate — DONE (1977 unit + 197 Rust + 199 benchmark + 2 PTY smokes green; artifact `autocode/docs/qa/test-results/20260426-172910-checkpoint1-regression-gate.md`).
- 2.A spinner activity-correlation (Phase D #1) — DONE ahead of plan (was Entry 1544, archived).
- 1.C final docs sync — DONE (Codex Entry 1549; artifact `autocode/docs/qa/test-results/20260426-175205-checkpoint1-c-docs-sync.md`).
- 1.E user commit — pending user.

**Checkpoint 2 — closed from builder/reviewer side (handed to Codex via comms Entry 1548):**

- 2.E `/restore` interaction layer — DONE (Codex Entry 1551; artifact `autocode/docs/qa/test-results/20260426-180015-hr5-phase-c-restore-interaction-tui-verification.md`).
- 2.F.1 MCP CLI wire-up — DONE (Codex Entry 1554; artifact `autocode/docs/qa/test-results/20260426-183312-2f1-mcp-cli-wire-up.md`).
- 2.B HR-5 Phase D #2 thinking/output buffer split — DONE (Codex Entry 1556; artifact `autocode/docs/qa/test-results/20260426-185509-hr5-phase-d-thinking-output-buffer-split-tui-verification.md`).
- 2.C HR-5 Phase D #3 per-slash PTY smoke coverage — DONE (Codex Entry 1565; artifact `autocode/docs/qa/test-results/20260426-133155-pty-slash-surfaces-smoke.md`).
- 2.D HR-5 Phase D #4 194-verb spinner badge wiring — DONE (Codex Entry 1568; artifact `autocode/docs/qa/test-results/20260426-195342-hr5-phase-d-spinner-verb-badge-tui-verification.md`).
- 2.F backend robustness bundle: MCP CLI wire-up + MCP integration polish + cost rate accuracy + `provider_model` deprecation + F821 fix in `eval/team_eval.py` + per-tool output-budget PTY verification + tranche exit-gate sweeps.
- 2.F.7 tranche exit-gate sweeps — DONE (artifact `autocode/docs/qa/test-results/20260426-143510-2f7-tranche-exit-gate-sweeps.md`).
- 2.G regression gate — DONE (artifact `autocode/docs/qa/test-results/20260426-145234-checkpoint2-regression-gate.md`).
- 2.H user commit — pending user; agents must not commit.

**Checkpoint 3 — Phase E release gate (active by user direction on 2026-04-27).**

- 3.A Phase E gate verification — DONE (artifact `autocode/docs/qa/test-results/20260427-113808-phase-e-gate-verification.md`).
- 3.B visual-only polish unblock — DONE; polish is unblocked only after 3.C remains green for release readiness.
- 3.C final release-grade regression sweep — DONE (artifact `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`; optional B7-B29 not run because user-gated).
- 3.D tranche-spanning closeout entry — DONE (`AGENTS_CONVERSATION.MD` Entry 1584).
- 3.E user commits + tags release if user chooses — pending user.

**Hygiene state:**

- `AGENTS_CONVERSATION.MD` was reset after Checkpoint 1 cleanup. Entry 1548 is the active Claude handoff; Entry 1549+ are Checkpoint 2 work entries and join Batch E for archival after Checkpoint 2 closes.

---

## Operating Cadence

1. **Codex does not block on review.** Codex posts kickoff → works → posts completion review request → continues to the next slice immediately.
2. **Claude reviews and queues the next instruction.** Each Claude review entry ends with an explicit "Next slice: X" so Codex picks it up the next time they touch comms.
3. **User commits, not agents.** No agent runs `git commit`/`git push`/`git reset`. Commit gates are user-driven and live at the end of each Checkpoint.
4. **Per-batch authorization for archives.** Comms cleanup runs in user-authorized batches; agents do not move files without explicit per-batch approval.

---

## Checkpoint 1 — Stabilize for Commit

**Goal:** working tree is commit-ready. Tests green, docs synced, comms log lean.

**Order:** sequential. Each substage exit-gates the next.

### 1.A — Typed-payload consolidation completion — DONE

- Owner: Codex.
- Status: approved and archived; artifact `autocode/docs/qa/test-results/20260426-163752-hr5-typed-tool-result-payload-consolidation.md`.
- Notes: backwards-compatible additive schema bump; legacy `result` string preserved; 9 tools (4 search + 5 diff/edit) emit structured payloads. `parse_search_hits` and `parse_diff_files` shims removed. Rust unit suite `195 passed`.

### 1.B — Comms cleanup pass (batched) — DONE

- Owner: User-authorized cross-author archive on 2026-04-26 (after Codex partial self-archive).
- Result: 23 residual active entries archived to `docs/communication/old/2026-04-26-final-cleanup-residual-1476-1545.md`. Codex's earlier self-archive at `docs/communication/old/2026-04-26-codex-active-entries-1478-1547.md` covers the rest. `AGENTS_CONVERSATION.MD` reset to Entry 1548 only.
- Hard rules honored: no deletions; no cross-author moves without explicit user override; archive files preserved permanently.

### 1.C — Final docs/status sync — DONE

- Owner: Codex.
- Exit: PLAN.md / EXECUTION_CHECKLIST.md / current_directives.md reflect:
  - Phase B + Phase C closed.
  - Typed-payload consolidation closed.
  - Checkpoint 2 as the active program slice.
  - 9 HR-5(a) surface bindings shipped, with the 10th planned slot reserved for the `/restore` interaction completed in 2.E.
  - Reference this plan file from PLAN.md Ordered Backlog item 1.
- Verification: `git diff --check` clean on touched docs; artifact `autocode/docs/qa/test-results/20260426-175205-checkpoint1-c-docs-sync.md`.

### 1.D — Pre-commit regression gate — DONE

- Owner: Codex.
- Result: green. Artifact: `autocode/docs/qa/test-results/20260426-172910-checkpoint1-regression-gate.md`.
- Test totals: Python unit `1977 passed`, Rust TUI `197 passed`, benchmark `199 passed`, PTY smokes (m1 + comprehensive) green across 80x24 / 120x40 / 200x50, cargo fmt/clippy/build --release passed, `git diff --check` clean.
- Scope disclaimer (recorded in artifact): does not prove live-gateway behaviour, broad benchmark sweep, real-model thinking, or external MCP client behaviour — those gates live in Checkpoint 2.G and Checkpoint 3.

### 1.E — User commits

- Owner: User.
- Granularity: user choice. Reasonable defaults: one commit covering Checkpoint 1, or split per substage if user wants tighter history.

---

## Checkpoint 2 — Phase D + `/restore` interaction + backend robustness

**Goal:** runtime behaviour parity, `/restore` end-to-end usable, robustness extras land, working tree commit-ready again.

**Order:** Phase D substages can ship in any order Codex picks; `/restore` interaction and the robustness pass can be interleaved between Phase D slices to avoid context-switch fatigue. The regression gate (2.G) waits until everything else is green.

### 2.A — Spinner activity-correlation (HR-5(b) #1) — DONE

- Owner: Codex.
- Status: approved and archived; artifact `autocode/docs/qa/test-results/20260426-170658-hr5-phase-d-spinner-activity-correlation.md`.
- Notes: shipped ahead of Checkpoint 1 closure. Fixed the `ready while chat pending` failure class via `AppState::has_pending_chat_request()`, status badge correlation, and re-entering `Streaming` after auto-sent follow-up. Rust suite `197 passed`.

### 2.B — Thinking/output buffer split (HR-5(b) #2) — DONE

- Separate streams for `<think>` content vs visible output in the TUI; the existing S-THINK-B parser provides the substrate but the TUI display path needs to honour it.
- TDD: failing test asserts thinking tokens land in the thinking buffer and visible tokens land in the output buffer; both surfaces are observable.
- Validation: full TUI loop + PTY smoke with thinking ON.
- Result: `on_thinking` now appends to `thinking_buf` / `thinking_lines` instead of `stream_buf`; `on_token` remains visible output; `on_done` flushes only visible output to scrollback and clears thinking state. Rendered active turns show separate `THINKING` and `VISIBLE OUTPUT` sections. Verification artifact: `autocode/docs/qa/test-results/20260426-185509-hr5-phase-d-thinking-output-buffer-split-tui-verification.md`.

### 2.C — Per-slash PTY smoke coverage (HR-5(b) #3) — DONE

- Codifies the §4b TESTING.md rule: every backend-touching slash command has a PTY smoke artifact.
- Inventory: list slash commands, identify which currently lack PTY coverage, add minimum coverage per command.
- Validation: each new PTY smoke stored at `autocode/docs/qa/test-results/<ts>-pty-<slash>-smoke.md`.
- Result: added `autocode/tests/pty/pty_smoke_rust_slash_surfaces.py`, covering `/help`, `/plan`, `/tasks`, `/grep`, `/review`, `/diff`, `/restore`, `/cc`, `/escalation`, and `/multi` against the Rust TUI + mock backend. Verification artifact: `autocode/docs/qa/test-results/20260426-133155-pty-slash-surfaces-smoke.md`.

### 2.D — 194-verb spinner badge wiring (HR-5(b) #4) — DONE

- Verb badge per active activity class.
- TDD: failing test asserts the badge text rotates through the documented verb list while activity is in-flight; remains stable when idle.
- Validation: full TUI loop.
- Result: active chat status badges now use `crate::ui::spinner::VERBS` with deterministic tick-driven rotation. Idle and post-`on_done` states render `ready` without a stale verb. Verification artifact: `autocode/docs/qa/test-results/20260426-195342-hr5-phase-d-spinner-verb-badge-tui-verification.md`.

### 2.E — `/restore` interaction layer — DONE

- Adds the deferred-half from the original `/restore` Phase C item.
- Components:
  - Checkpoint row navigation (browser model — j/k or arrow keys; Enter to select).
  - `checkpoint.restore` RPC dispatch from the TUI.
  - Pre-restore confirmation modal (per the approval-mode rules; restore is a state-mutating op).
  - Post-restore feedback in transcript (which checkpoint was restored, what was reverted).
- TDD: failing reducer test asserts navigation state transitions; failing render test asserts confirmation modal appears for restore action; reducer test asserts `checkpoint.restore` RPC dispatch happens only after explicit confirmation.
- Validation: full TUI loop + PTY smoke that exercises navigate → confirm → restore → verify.
- Result: restore browser row navigation, confirmation, `checkpoint.restore` dispatch, and post-restore transcript feedback are live. Backend restore payload now includes checkpoint id plus restored message/tool-call counts. Verification artifact: `autocode/docs/qa/test-results/20260426-180015-hr5-phase-c-restore-interaction-tui-verification.md`.
- Promotes `/restore` from "half-shipped" (Entry 1522) to fully shipped — count math is now unambiguous.

### 2.F — Backend robustness bundle

Confirmed scope this iteration:

| Item | Source | Description |
|---|---|---|
| 2.F.1 — MCP CLI wire-up — DONE | gap discovered in this plan's research | `autocode mcp-serve` subcommand referenced from `external/config_merge.py` now exists and runs the read-only MCP stdio server. Verification artifact: `autocode/docs/qa/test-results/20260426-183312-2f1-mcp-cli-wire-up.md`. |
| 2.F.2 — MCP integration polish — DONE | `external/mcp_server.py` + `doctor.py` + `cli.py` | Doctor now reports MCP stdio readiness and audit-log path; `mcp-serve` accepts `--audit-log-path`; MCP stdio returns cleanly on EOF/interrupt; audit recording is thread-safe and can persist JSONL records. Verification artifact: `autocode/docs/qa/test-results/20260426-200724-2f2-mcp-integration-polish.md`. |
| 2.F.3 — Cost rate accuracy — DONE | Entry 1485 | Replaced flat `$3/M tokens` with model-aware input/cache/output rates for Claude labels while preserving deterministic unknown-model fallback. Verification artifact: `autocode/docs/qa/test-results/20260426-190615-2f3-cost-rate-accuracy.md`. |
| 2.F.4 — `provider_model` deprecation warning — DONE | Entry 1485 | Missing `provider_model` now emits `DeprecationWarning` while preserving fallback grouping; first-party orchestrator recording passes an explicit provider/model label. Verification artifact: `autocode/docs/qa/test-results/20260426-192007-2f4-2f5-provider-model-deprecation-team-eval-lint.md`. |
| 2.F.5 — F821 fix in `eval/team_eval.py` — DONE | Entry 1485 | Imported `OrchestratorEvent` for the live eval collector annotation and verified Ruff F821. Verification artifact: `autocode/docs/qa/test-results/20260426-192007-2f4-2f5-provider-model-deprecation-team-eval-lint.md`. |
| 2.F.6 — Per-tool output-budget live PTY verification — DONE | S-TRUNCATE follow-up | `ToolDefinition.output_budget_tokens` is honoured per S-TRUNCATE; added `pty_smoke_rust_tool_output_budget.py` to assert `small_budget_tool [completed]` and the `omitted` marker are visible in the Rust TUI. Verification artifact: `autocode/docs/qa/test-results/20260426-201726-2f6-tool-output-budget-pty-verification.md`. |
| 2.F.7 — Tranche exit-gate sweeps — DONE | `docs/plan/backend-feature-improvement-todo.md` § Exit Gate | Transport conformance now covers thinking, `in_progress`, search payloads, memory, cost warning/update, and checkpoint across stdio + TCP; cache is covered by focused backend unit checks. The Checkpoint 2 PTY canary covers thinking OFF/ON, tool sequence/truncation, and cost-limit warning visibility; real-gateway supported-path canary passed after tightening the probe timing. Artifact: `autocode/docs/qa/test-results/20260426-143510-2f7-tranche-exit-gate-sweeps.md`. |

Each 2.F item ships as its own slice with its own verification artifact. Codex picks ordering. Slices can ship interleaved with Phase D items.

### 2.G — Pre-commit regression gate — DONE

- Same shape as 1.D, plus:
  - Live gateway canary on the supported path (per Entry 1514 disclaimer about live behaviour out of local-deterministic scope).
  - Optional: `make tui-references` xfail-ratchet check — confirm no Track 4 scenes were silently un-xfailed.
- Result: full unit `1999 passed`, benchmark harness `199 passed`, Rust fmt/test/clippy/release build passed, Track 1 and Track 4 passed, PTY smokes and real-gateway canary passed, and `git diff --check` is clean.
- Artifact: `autocode/docs/qa/test-results/20260426-145234-checkpoint2-regression-gate.md`.

### 2.H — User commits

---

## Checkpoint 3 — Phase E release gate

**Goal:** cross the release threshold and post a session-spanning closeout.

### 3.A — Phase E gate verification

- Confirm: count ≥4/10 HR-5(a) bindings shipped (9 shipped surfaces plus `/restore` interaction as the completed 10th planned slot), Phase D follow-ons closed (after Checkpoint 2), Phase A closed (already done), `/restore` interaction closed (done in 2.E).
- Status: DONE via `autocode/docs/qa/test-results/20260427-113808-phase-e-gate-verification.md`.

### 3.B — Visual-only polish unblock

- Per `current_directives.md`: visual-only polish is allowed only after the Phase E gate is satisfied. Update directives to mark visual-only polish as unblocked and queue any deferred polish items for a post-release pass.
- Status: DONE. Visual-only polish is unblocked for a post-release polish pass, but release readiness still requires 3.C final release-grade regression.

### 3.C — Final release-grade regression sweep

- Full unit + Rust TUI cargo test/clippy/fmt/build --release + benchmark tests + PTY smoke set + live gateway canary + (optional, user-gated) B7-B29 sweep.
- Live gateway canary is required; B7-B29 is optional and waits for user direction.
- Status: DONE via `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`. B7-B29 was not run.

### 3.D — Tranche-spanning closeout entry

- Like Entry 1514 but covers the entire path from Entry 1476 through release. Lists every artifact, test totals, and flags any deferred items that survived the tranche.
- Status: DONE via `AGENTS_CONVERSATION.MD` Entry 1584.

### 3.E — User commits + tags release if user chooses

- Tag is user discretion. Suggested tag scheme: `release-2026-04-XX-backend-robustness` or per the user's existing convention.

---

## Robustness Brainstorm Inventory (research output)

Items considered but not in this iteration's confirmed scope. Surface for a future tranche if user agrees.

| # | Item | Source | Why not now |
|---|---|---|---|
| R-1 | Layer 3 broadening | `current_directives.md` § Layer 3 | Opt-in extra; widening requires architecture docs + integration tests + SWE-bench validation per S-L3DOC. Substantial scope. |
| R-2 | Tool-call execution memoization | `backend-feature-improvement-todo.md` § Deferred | Original S-CACHE design; invalidation risk for file-reading tools; needs dedicated design pass. |
| R-3 | Citation surfacing in ask-and-answer | `backend-vision-and-usability.md` § 1.1 | UX-oriented; better fit for a vision-driven slice than robustness. |
| R-4 | Provider failover / retry policies | implicit gap | Currently single-provider per slice; multi-provider failover requires gateway-level work. |
| R-5 | Streaming back-pressure | implicit gap | Current streaming is tested but back-pressure under slow Rust frame rendering hasn't been characterised. |
| R-6 | Cancellation cleanup paths | implicit gap | S-INTERRUPT covers tool cancellation; broader session-cancel cleanup hasn't been audited. |
| R-7 | Plan artifact versioning / migration | `agent/plan_artifact.py` | Plans can be exported/imported; if format ever changes, migration story is unclear. |
| R-8 | Subagent isolation / permission propagation | `agent/subagent_tools.py` | Subagents inherit parent permissions; explicit per-subagent permission scoping not yet a feature. |
| R-9 | Telemetry / observability hooks | `docs/plan/ailogd.md` | Separate plan exists; would cross-cut this tranche. |
| R-10 | Configuration validation/migration | `config.py` | Config schema versioning not formal; bad config produces partial-state. |
| R-11 | Long-form supervision UX | `backend-vision-and-usability.md` § 1.4 | Vision-doc material; deeper UX scope. |

---

## Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| String-parser shims (`parse_search_hits`, `parse_diff_files`) silently break on backend output drift | Medium | Address via 1.A (typed-payload consolidation) — already in progress. |
| Comms log size hides newer signal | Low | Address via 1.B batched archival. |
| Phase D and `/restore` interaction interact at the TUI reducer layer (modal state, navigation focus) | Medium | Sequence in 2.G regression gate; full TUI loop catches reducer regressions; per-slice TUI checklist enforced. |
| MCP CLI wire-up exposes a public surface area gap (config-merge generates configs that fail today if a user runs them) | Low-Medium | Resolved in 2.F.1 and 2.F.2: `autocode mcp-serve` now exposes stdio `initialize`, `tools/list`, and `tools/call`; doctor/audit/lifecycle/concurrent-client polish is covered. |
| Live gateway canary uncovers timing-dependent regressions not caught by local PTY smoke | Medium | Run canary before Checkpoint 3 commit; treat any regression as a Checkpoint 2 reopener, not a Checkpoint 3 issue. |
| `9/10` HR-5(a) binding count framing is ambiguous | Low | Resolved in 1.C as option (b): 9 shipped surfaces; 10th planned slot is `/restore` interaction, now completed in 2.E. |

---

## References

- `docs/plan/backend-feature-improvement-plan.md` — closed tranche source plan.
- `docs/plan/backend-feature-improvement-todo.md` — closed tranche todo with exit-gate items.
- `docs/plan/backend-vision-and-usability.md` — UX/vision companion.
- `docs/tui-testing/tui_implementation_plan.md` — HR-5 program plan.
- `docs/tui-testing/tui_implementation_todo.md` — HR-5 program checklist.
- `AGENTS_CONVERSATION.MD` — Entries 1476-current document this work.
- `autocode/docs/qa/test-results/` — verification artifact directory.
- `autocode/src/autocode/external/mcp_server.py` — existing MCP server.
- `autocode/src/autocode/external/config_merge.py` — MCP config generators.

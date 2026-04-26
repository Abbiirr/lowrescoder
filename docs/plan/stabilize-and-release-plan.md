# Stabilize and Release Plan

> **Status:** ACTIVE.
> **Date:** 2026-04-26.
> **Authors:** Claude (Reviewer/Architect) drafted, User approved.
> **Companion plans:** `docs/plan/backend-feature-improvement-plan.md` (closed tranche), `docs/tui-testing/tui_implementation_plan.md` (HR-5 program), `docs/plan/backend-vision-and-usability.md` (UX/vision companion).

This plan organises the path from the current in-flight typed-payload consolidation slice to a release-ready, commit-stable working tree. It supersedes ad-hoc per-slice direction entries while it remains active. After Checkpoint 3 closes, archive this file alongside the other completed plans.

---

## Status Snapshot (2026-04-26 16:30)

**Closed in this session:**

- Backend Feature Improvement tranche — Stages 3-4 backend slices and S-DOCSREFRESH A through G; regression-green via Entry 1514.
- HR-5 Phase A (benchmark latency canary) — closed previously; not reopened.
- HR-5 Phase B (`/cc` real-data binding) — Entry 1518.
- HR-5 Phase C items 1-7 — `/restore` (display only), `/plan`, `/tasks`, `/grep`, `/review`+`/diff`, `/escalation`, `/multi` mockup-copy cleanup.

**Closed since this plan was drafted (2026-04-26 17:10):**

- Post-Phase-C typed `tool.result_payload` consolidation — Entry 1542 (closes plan substage 1.A).
- HR-5 Phase D item 1: spinner activity-correlation — Entry 1544 (closes plan substage 2.A).

**In flight:** none — Codex pacing ahead of plan; awaiting redirect to 1.B before more Phase D work.

**Not started:**

- HR-5 Phase D items 2-4 (thinking/output buffer split, per-slash PTY smoke coverage, 194-verb spinner badge wiring).
- HR-5 `/restore` interaction layer (row navigation + `checkpoint.restore` execution).
- Backend robustness pass (MCP integration polish + Entry 1485 follow-ups + miscellaneous).
- HR-5 Phase E release gate.
- Plan substages 1.B (comms cleanup batched), 1.C (docs sync), 1.D (regression gate), 1.E (user commit) — Checkpoint 1 must close **before** more Phase D work resumes per user direction.

**Hygiene state:**

- `AGENTS_CONVERSATION.MD` has 65 active entries — past the protocol target of "near-zero". Archival waits for user authorization, batched.

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
- Status: builder-complete via Entry 1542; pending Claude APPROVE.
- Notes: backwards-compatible additive schema bump; legacy `result` string preserved; 9 tools (4 search + 5 diff/edit) emit structured payloads. `parse_search_hits` and `parse_diff_files` shims removed. Rust unit suite `195 passed`.

### 1.B — Comms cleanup pass (batched)

- Owner: shared (Codex archives Codex-authored entries; Claude archives Claude-authored entries; user authorizes each batch).
- Exit: ≤10 active entries in `AGENTS_CONVERSATION.MD`, all genuinely open; archive files exist under `docs/communication/old/`.
- Process:
  1. Codex posts a Batch Authorization Request entry with proposed batch boundaries + entry numbers. Suggested batches:
     - Batch A: Backend tranche pre-DOCSREFRESH (Entries 1476–1485).
     - Batch B: S-DOCSREFRESH-A through G plus tranche regression/closeout (1486–1517).
     - Batch C: HR-5 Phase B + Phase C (1518–1540).
     - Batch D: Typed-payload consolidation + this plan's directing entries (1541+ once that thread closes).
  2. User approves a batch.
  3. Each author moves their own entries to `docs/communication/old/<date>-<topic>.md`, removes from active log, updates HTML archive comments and active-entries summary.
  4. Repeat until target reached.
- Hard rules: never delete archives; never archive an entry whose original thread still has open questions; never archive across authors.

### 1.C — Final docs/status sync

- Owner: Codex.
- Exit: PLAN.md / EXECUTION_CHECKLIST.md / current_directives.md reflect:
  - Phase B + Phase C closed.
  - Typed-payload consolidation closed.
  - Phase D as the next active program slice.
  - 9 surface bindings shipped under HR-5(a) — resolve `9/10` vs `9/9` framing in `tui_implementation_plan.md` (clarify whether `10` was a planning placeholder or includes the deferred `/restore` interaction).
  - Reference this plan file from PLAN.md Ordered Backlog item 1.
- Verification: `git diff --check` clean on touched docs.

### 1.D — Pre-commit regression gate

- Owner: Codex.
- Commands (same shape as Entry 1514):
  - `uv run pytest autocode/tests/unit/ -q`
  - `cd autocode/rtui && cargo test`
  - `cd autocode/rtui && cargo clippy -- -D warnings`
  - `cd autocode/rtui && cargo fmt -- --check`
  - `cd autocode/rtui && cargo build --release`
  - `uv run pytest benchmarks/tests -q`
  - `python3 autocode/tests/pty/pty_smoke_rust_m1.py`
  - `python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py`
  - `git diff --check`
- Exit: artifact at `autocode/docs/qa/test-results/<ts>-checkpoint1-regression-gate.md` records all commands and PASS/FAIL. Honest scope disclaimer about what the gate does and does not prove (live gateway canary, real model thinking, etc.).

### 1.E — User commits

- Owner: User.
- Granularity: user choice. Reasonable defaults: one commit covering Checkpoint 1, or split per substage if user wants tighter history.

---

## Checkpoint 2 — Phase D + `/restore` interaction + backend robustness

**Goal:** runtime behaviour parity, `/restore` end-to-end usable, robustness extras land, working tree commit-ready again.

**Order:** Phase D substages can ship in any order Codex picks; `/restore` interaction and the robustness pass can be interleaved between Phase D slices to avoid context-switch fatigue. The regression gate (2.G) waits until everything else is green.

### 2.A — Spinner activity-correlation (HR-5(b) #1) — DONE

- Owner: Codex.
- Status: builder-complete via Entry 1544; pending Claude APPROVE.
- Notes: shipped ahead of Checkpoint 1 closure. Fixed the `ready while chat pending` failure class via `AppState::has_pending_chat_request()`, status badge correlation, and re-entering `Streaming` after auto-sent follow-up. Rust suite `197 passed`.

### 2.B — Thinking/output buffer split (HR-5(b) #2)

- Separate streams for `<think>` content vs visible output in the TUI; the existing S-THINK-B parser provides the substrate but the TUI display path needs to honour it.
- TDD: failing test asserts thinking tokens land in the thinking buffer and visible tokens land in the output buffer; both surfaces are observable.
- Validation: full TUI loop + PTY smoke with thinking ON.

### 2.C — Per-slash PTY smoke coverage (HR-5(b) #3)

- Codifies the §4b TESTING.md rule: every backend-touching slash command has a PTY smoke artifact.
- Inventory: list slash commands, identify which currently lack PTY coverage, add minimum coverage per command.
- Validation: each new PTY smoke stored at `autocode/docs/qa/test-results/<ts>-pty-<slash>-smoke.md`.

### 2.D — 194-verb spinner badge wiring (HR-5(b) #4)

- Verb badge per active activity class.
- TDD: failing test asserts the badge text rotates through the documented verb list while activity is in-flight; remains stable when idle.
- Validation: full TUI loop.

### 2.E — `/restore` interaction layer

- Adds the deferred-half from the original `/restore` Phase C item.
- Components:
  - Checkpoint row navigation (browser model — j/k or arrow keys; Enter to select).
  - `checkpoint.restore` RPC dispatch from the TUI.
  - Pre-restore confirmation modal (per the approval-mode rules; restore is a state-mutating op).
  - Post-restore feedback in transcript (which checkpoint was restored, what was reverted).
- TDD: failing reducer test asserts navigation state transitions; failing render test asserts confirmation modal appears for restore action; reducer test asserts `checkpoint.restore` RPC dispatch happens only after explicit confirmation.
- Validation: full TUI loop + PTY smoke that exercises navigate → confirm → restore → verify.
- Promotes `/restore` from "half-shipped" (Entry 1522) to fully shipped — count math becomes unambiguous.

### 2.F — Backend robustness bundle

Confirmed scope this iteration:

| Item | Source | Description |
|---|---|---|
| 2.F.1 — MCP CLI wire-up | gap discovered in this plan's research | `autocode mcp-serve` subcommand referenced from `external/config_merge.py` but absent from `cli.py`. Wire it up so the generated configs work; smoke test against at least one of the supported clients (claude_code / codex / opencode). |
| 2.F.2 — MCP integration polish | `external/mcp_server.py` + `external/tracker.py` | Doctor checks for MCP socket / log path; lifecycle (start/stop hooks); audit-log discovery in `MCPToolCall`. |
| 2.F.3 — Cost rate accuracy | Entry 1485 | Replace flat `$3/M tokens` with per-model rate tables; current under-estimate for Anthropic Claude output (~$15/M actual vs $3/M displayed). |
| 2.F.4 — `provider_model` deprecation warning | Entry 1485 | If still in use, mark with `DeprecationWarning` and a migration note. |
| 2.F.5 — F821 fix in `eval/team_eval.py` | Entry 1485 | Resolve the lint error. |
| 2.F.6 — Per-tool output-budget live PTY verification | S-TRUNCATE follow-up | `ToolDefinition.output_budget_tokens` is honoured per S-TRUNCATE; add a PTY smoke that exercises a tool exceeding the budget and asserts the truncation banner is visible. |
| 2.F.7 — Tranche exit-gate sweeps | `docs/plan/backend-feature-improvement-todo.md` § Exit Gate | Two unchecked items: "Transport conformance coverage: thinking + in_progress + cache + search + memory + cost + checkpoint" and "Live PTY canary: thinking ON + thinking OFF + tool sequence + cost limit crossing all green". Resolve or formally defer with rationale. |

Each 2.F item ships as its own slice with its own verification artifact. Codex picks ordering. Slices can ship interleaved with Phase D items.

### 2.G — Pre-commit regression gate

- Same shape as 1.D, plus:
  - Live gateway canary on the supported path (per Entry 1514 disclaimer about live behaviour out of local-deterministic scope).
  - Optional: `make tui-references` xfail-ratchet check — confirm no Track 4 scenes were silently un-xfailed.
- Exit: artifact at `autocode/docs/qa/test-results/<ts>-checkpoint2-regression-gate.md`.

### 2.H — User commits

---

## Checkpoint 3 — Phase E release gate

**Goal:** cross the release threshold and post a session-spanning closeout.

### 3.A — Phase E gate verification

- Confirm: count ≥4/10 HR-5(a) bindings shipped (already 9), Phase D follow-ons closed (after Checkpoint 2), Phase A closed (already done), `/restore` interaction closed (after 2.E).

### 3.B — Visual-only polish unblock

- Per `current_directives.md`: visual-only polish is allowed only after the Phase E gate is satisfied. Update directives to mark visual-only polish as unblocked and queue any deferred polish items for a post-release pass.

### 3.C — Final release-grade regression sweep

- Full unit + Rust TUI cargo test/clippy/fmt/build --release + benchmark tests + PTY smoke set + live gateway canary + (optional, user-gated) B7-B29 sweep.
- Live gateway canary is required; B7-B29 is optional and waits for user direction.

### 3.D — Tranche-spanning closeout entry

- Like Entry 1514 but covers the entire path from Entry 1476 through release. Lists every artifact, test totals, and flags any deferred items that survived the tranche.

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
| MCP CLI wire-up exposes a public surface area gap (config-merge generates configs that fail today if a user runs them) | Low-Medium | Treat 2.F.1 as a fix, not a feature; ship before any release announcement so generated configs are not broken. |
| Live gateway canary uncovers timing-dependent regressions not caught by local PTY smoke | Medium | Run canary before Checkpoint 3 commit; treat any regression as a Checkpoint 2 reopener, not a Checkpoint 3 issue. |
| `9/10` HR-5(a) binding count framing is ambiguous | Low | Resolve in 1.C as part of docs sync. |

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

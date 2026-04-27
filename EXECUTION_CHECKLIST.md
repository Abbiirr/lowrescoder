# Execution Checklist

Last updated: 2026-04-27 (Checkpoint 3 active by user direction. Checkpoint 2 is closed from builder/reviewer side and remains pending user commit only; agents must not commit. Phase E gate verification and visual-only polish unblock are complete via `autocode/docs/qa/test-results/20260427-113808-phase-e-gate-verification.md`; 3.C release-grade regression is green via `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`; 3.D closeout is posted in `AGENTS_CONVERSATION.MD` Entry 1584. Remaining work is user-owned 3.E commit/tag decision.)
Owner: Codex (Stabilize-and-Release Program, Entry 1548)
Purpose: live status checklist for source-of-truth work, active next-frontier research-to-implementation items, and any benchmark/harness follow-up. Re-check this file every 10 minutes during active work.

Detailed implementation map:
- **`docs/tui-testing/tui_implementation_plan.md`** — active next-slice execution plan for HR-5 follow-through
- **`docs/tui-testing/tui_implementation_todo.md`** — active next-slice checklist for the follow-through program
- **`docs/plan/backend-tightening-refinement-plan.md`** — user-directed backend-first tranche before more frontend binding
- **`docs/plan/backend-feature-improvement-plan.md`** — backend feature-slice queue; docs-refresh A-G and local deterministic regression are builder-complete; live gateway canary remains before broad sweeps
- `docs/plan/hr5-phase-a-benchmark-latency-plan.md` — closed Phase A execution record for HR-5(c)
- `docs/plan/hr5-phase-a-benchmark-latency-checklist.md` — closed Phase A checklist and exit-gate record
- **`docs/plan/stabilization-and-parity-plan.md`** — APPROVED 2026-04-20; primary source of truth for the sprint
- `PLAN.md` — long-form roadmap; current active order follows Checkpoint 3 from `docs/plan/stabilize-and-release-plan.md`
- `bugs/codex-tui-issue-inventory.md` — 60 items + §S1–§S12 adversarial sweeps
- `docs/tui-testing/tui_testing_checklist.md` — enforced per-change checklist; §6.5 sweeps + §7 regression table gate the ship
- `DEFERRED_PENDING_TODO.md` — store of everything NOT in the current active slice

## Current Active Queue

Checkpoint 1 substantially closed. Checkpoint 2 work queue in `AGENTS_CONVERSATION.MD` Entry 1548 is closed from builder/reviewer side and pending user commit only. Checkpoint 3 started by user direction on 2026-04-27; pickup order below follows `docs/plan/stabilize-and-release-plan.md`.

**Checkpoint 1 — substantially closed:**
1. **1.A typed `tool.result_payload` consolidation — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-163752-hr5-typed-tool-result-payload-consolidation.md`.
2. **2.A HR-5 Phase D spinner activity-correlation — DONE** (shipped ahead of plan). Artifact: `autocode/docs/qa/test-results/20260426-170658-hr5-phase-d-spinner-activity-correlation.md`.
3. **1.B comms cleanup batched — DONE.** Archives at `docs/communication/old/2026-04-26-codex-active-entries-1478-1547.md` + `docs/communication/old/2026-04-26-final-cleanup-residual-1476-1545.md`.
4. **1.D Checkpoint 1 regression gate — GREEN.** Artifact: `autocode/docs/qa/test-results/20260426-172910-checkpoint1-regression-gate.md` (Python unit `1977 passed`, Rust TUI `197 passed`, benchmark `199 passed`, PTY smokes green).
5. **1.C final docs sync — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-175205-checkpoint1-c-docs-sync.md`.
6. **1.E user commit — pending user.**

**Checkpoint 2 — open queue (Entry 1548 in comms):**
1. **2.E `/restore` interaction layer — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-180015-hr5-phase-c-restore-interaction-tui-verification.md`.
2. **2.F.1 MCP CLI wire-up — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-183312-2f1-mcp-cli-wire-up.md`.
3. **2.B HR-5 Phase D thinking/output buffer split — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-185509-hr5-phase-d-thinking-output-buffer-split-tui-verification.md`.
4. **2.F.3 cost rate accuracy — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-190615-2f3-cost-rate-accuracy.md`.
5. **2.F.4 + 2.F.5 deprecation warning + F821 lint fix — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-192007-2f4-2f5-provider-model-deprecation-team-eval-lint.md`.
6. **2.C HR-5 Phase D per-slash PTY smoke coverage — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-133155-pty-slash-surfaces-smoke.md`.
7. **2.D HR-5 Phase D 194-verb spinner badge wiring — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-195342-hr5-phase-d-spinner-verb-badge-tui-verification.md`.
8. **2.F.2 MCP integration polish — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-200724-2f2-mcp-integration-polish.md`.
9. **2.F.6 per-tool output budget PTY verification — DONE.** Artifact: `autocode/docs/qa/test-results/20260426-201726-2f6-tool-output-budget-pty-verification.md`.
10. 2.F.7 tranche exit-gate sweeps — DONE. Artifact: `autocode/docs/qa/test-results/20260426-143510-2f7-tranche-exit-gate-sweeps.md`.
11. 2.G Checkpoint 2 regression gate — DONE. Artifact: `autocode/docs/qa/test-results/20260426-145234-checkpoint2-regression-gate.md`.
12. 2.H user commit — pending user; agents must not commit.

**Checkpoint 3 — Phase E release gate (active by user direction):**
1. 3.A Phase E gate verification — DONE. Artifact: `autocode/docs/qa/test-results/20260427-113808-phase-e-gate-verification.md`.
2. 3.B Visual-only polish unblock — DONE. Visual-only polish is unblocked for a post-release polish pass, but release readiness still waits on 3.C.
3. 3.C Final release-grade regression sweep — DONE. Artifact: `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`. Optional B7-B29 remains user-gated and was not run.
4. 3.D Tranche-spanning closeout entry — DONE. Comms: `AGENTS_CONVERSATION.MD` Entry 1584.
5. 3.E User commits + tags release if user chooses — pending user.

## Historical Stabilization Execution Record

Execution order below is the closed stabilization sprint record, not the active queue:
1. **Stabilization Sprint — Stage 0A COMPLETE** (`docs/plan/stabilization-and-parity-plan.md` §4.1): delivered schema, compat shims, fixture corpus, endpoint declarations, and harness/doc sync. Artifact: `autocode/docs/qa/test-results/20260420-171416-stage0a-verification.md`. Stage 0B decision: skipped; dedicated endpoints already unblock Stage 2.
2. **Stabilization Stage 1 COMPLETE** (plan §5): UTF-8 textbuf, editor lifecycle, RPC frame cap, history atomicity, resize/tick/mouse/log hygiene. Landed sub-slices:
   - `autocode/docs/qa/test-results/20260420-173018-stage1-utf8-textbuf-verification.md` closing Inventory §5, §26, §28, §29, §53, §56
   - `autocode/docs/qa/test-results/20260421-085810-stage1-editor-inline-verification.md` closing Inventory §24, §25, §46, §47, §48, §51, §52
   - `autocode/docs/qa/test-results/20260421-091015-stage1-rpc-process-verification.md` closing Inventory §45, §49, §50
   - `autocode/docs/qa/test-results/20260421-091548-stage1-runtime-hygiene-verification.md` closing Inventory §30, §31, §57, §58, §59, §60
3. **Stabilization Stage 2 COMPLETE** — command registry + visible UI (plan §6): slash dropdown, palette rewrite, picker overlay, `/help` unification, backend-owned command execution. Landed sub-slices:
   - `autocode/docs/qa/test-results/20260421-093005-stage2-visible-command-picker-verification.md` closing Inventory §2, §3, §6, §7, §8, §9, §10, §12, §27, §33, §40, §54, §55
   - `autocode/docs/qa/test-results/20260421-094503-stage2-slash-compact-verification.md` closing Inventory §1, §41
4. **Stabilization Stage 3A COMPLETE** — modal correctness + transcript integrity (plan §7.1). Artifact: `autocode/docs/qa/test-results/20260421-102221-stage3a-modal-transcript-verification.md`. Closed Inventory §4, §13–§15, §23, §32, §35, §36, §38, §42–§44.
5. **Stabilization Stage 3B COMPLETE** — inspection panels + queue visibility (plan §7.2). Artifact: `autocode/docs/qa/test-results/20260421-103256-stage3b-inspection-queue-verification.md`. Closed §11, §34, §37, §39.
6. **Stabilization Stage 4 COMPLETE** — canonical-name-only shim removal + final stabilization gate (plan §8). Artifact: `autocode/docs/qa/test-results/20260421-104354-stabilization-verification.md`.
7. **§1h Rust TUI Migration (engineering gate — COMPLETE 2026-04-19)** — M1–M11 done. Historical reference only; stabilization supersedes as the active slice.
8. Section 1g TUI Testing Strategy — committed (`a9cc315`); canonical guide at `docs/tui-testing/tui-testing-strategy.md`; Slice 2 themed renderer deferred (user-gated). **TUI runtime + parity program active under HR-5:** Stage 0 harness-signal fix is COMPLETE via `autocode/docs/qa/test-results/20260421-160214-tui-stage0-predicate-verification.md`. Stage 1 reachable-scene promotion is COMPLETE via `autocode/docs/qa/test-results/20260421-172147-tui-stage1-reference-promotion.md` as the historical promotion slice. Stages 2 and 3 are now COMPLETE via `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`: dedicated live surfaces and deterministic triggers now exist for `multi`, `plan`, `review`, `cc`, `restore`, `diff`, `grep`, and `escalation`, and all 14 scenes are `direct` in `autocode/docs/qa/test-results/20260422-114357-tui-14-scene-capture-matrix.md`. The latest runtime-correctness slice is verified in `autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`, with the authoritative screenshot baseline in `autocode/docs/qa/test-results/20260422-114357-tui-reference-gap.md`. The benchmark-owned Rust TUI PTY runner is now implemented, instrumented, and canary-verified on the real gateway via `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json` and `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`. Phase B `/cc`, all Phase C real-data bindings, `/multi` cleanup, typed payload consolidation, Phase D spinner activity-correlation, 1.C docs sync, 2.E `/restore` interaction, 2.F.1 MCP CLI wire-up, 2.B thinking/output buffer split, 2.F.3 cost rate accuracy, 2.F.4+2.F.5, 2.C per-slash PTY coverage, 2.D spinner verb badge, 2.F.2 MCP integration polish, 2.F.6 per-tool output-budget PTY, 2.F.7 tranche exit-gate sweeps, 2.G Checkpoint 2 regression gate, 3.A/3.B Phase E gate verification/visual-polish unblock, 3.C release-grade regression, and 3.D closeout are COMPLETE through `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md` plus `AGENTS_CONVERSATION.MD` Entry 1584. The remaining item is user-owned 3.E commit/tag decision.
   - **User-directed temporary override (2026-04-24):** backend-first tranche completed local deterministic regression; HR-5 real-data binding has resumed.
9. Section 1f Milestone C/D/E/F — **FROZEN** on Go; gates absorbed into Rust-M5 through Rust-M10.
10. Section 1 large-repo validation / retrieval contract (next backlog item after stabilization).
11. Section 2 external-harness event normalization + deeper adapters (post-stabilization backlog).
12. Section 3 Terminal-Bench score improvement (post-stabilization backlog).
13. P0–P2 feature parity (plan §9–§11) — explicitly deferred, separate execution approval.

## Backend Tightening Override — Active Slice Status

- [x] `S-POSTTOOL` — post-tool hook/runtime plumbing complete.
- [x] `S-TOKENCAL` — token/cost update transport coverage complete.
- [x] `S-THINK` — thinking-token streaming/parser coverage complete.
- [x] `S-INPROGRESS` — task lifecycle `pending -> in_progress -> completed` complete.
- [x] `S-INTERRUPT` — interruptible tool cancellation semantics complete.
- [x] `S-CLEAR-RESULTS` — `ToolResultCache` list/clear tools are core-visible, loop-populated, backend/TUI-wired, and prompt-documented. Artifact: `autocode/docs/qa/test-results/20260425-153245-s-clear-results-verification.md`.
- [x] `S-SEARCHRES` — already implemented and verified: `ContextAssembler.assemble(search_results=...)` emits `## Relevant Code` under budget, and backend chat passes `HybridSearch` results into it. Validation: context/L2 tests `17 passed`; backend chat tests `5 passed`. Artifact: `autocode/docs/qa/test-results/20260425-153728-s-searchres-verification.md`.
- [x] `S-MEMPERSIST` — `SessionConsolidator.run(..., memory_store=..., session_id=...)` persists pruned durable learnings through `MemoryStore.save()` with category mapping and dedup; backend teardown now invokes deterministic consolidation before LLM-based memory enrichment. Artifacts: `autocode/docs/qa/test-results/20260425-154142-s-mempersist-verification.md`, `autocode/docs/qa/test-results/20260425-164044-s-mempersist-wire-verification.md`.
- [x] `S-PRIORITY` — verified existing per-section context allocations/truncation and added explicit regression coverage. Artifact: `autocode/docs/qa/test-results/20260425-164452-s-priority-verification.md`.
- [x] `S-MEMROBUST` — hardened `MemoryStore.learn_from_session()` to scan for the first valid JSON array, ignoring malformed bracketed preambles. Artifact: `autocode/docs/qa/test-results/20260425-164800-s-memrobust-verification.md`.
- [x] `S-TRUNCATE` — adaptive tool-result truncation preserves high-signal code/error/list structure and honors per-tool output budgets. Artifact: `autocode/docs/qa/test-results/20260425-165646-s-truncate-verification.md`.
- [x] `S-L1L2PREVIEW` — iteration-zero bootstrap now includes bounded cached Layer 1 symbol previews for active working-set files only. Artifact: `autocode/docs/qa/test-results/20260425-171054-s-l1l2preview-verification.md`.
- [x] `S-BLOCKED` — expanded dangerous-operation blocking across `write_file`, `edit_file`, and `apply_patch` paths/content. Artifact: `autocode/docs/qa/test-results/20260425-190420-s-blocked-verification.md`.
- [x] `S-CKPTMSG` — checkpoint save/restore includes bounded message history plus assistant tool-call rows. Artifact: `autocode/docs/qa/test-results/20260425-193136-s-ckptmsg-verification.md`.
- [x] `S-COST` — Tier B cache-aware cost accounting, warn+continue limit, `/cost`, and `/cost --detail` are builder-complete. Final focused/backend regression: `329 passed`; full unit: `1955 passed`; live PTY `/cost`, `/cost --detail`, and threshold crossing passed. Final comms review requested. Artifact: `autocode/docs/qa/test-results/20260425-212558-s-cost-verification.md`.
- [x] `S-EPISODESUM` — deterministic non-LLM episode retention summaries are stored as `episode_events.event_type == "summary"` rows before old episodes are pruned, with a >50% summary recursion cap. Final focused: `13 passed`; adjacent: `68 passed`; full unit: `1961 passed`; touched-file Ruff clean; direct SQLite plumbing smoke passed. Final comms review requested. Artifact: `autocode/docs/qa/test-results/20260425-233457-s-episodesum-verification.md`.
- [x] `S-L3DOC` — Layer 3 provider now documents its opt-in optional-extra status and dormant core-install fallback; related runtime inventory/todo summaries updated. Ruff and mypy for `autocode/src/autocode/layer3/provider.py` are clean; `autocode/tests/unit/test_l3_provider.py` passes; `-k layer3` deselects all tests. Final comms review requested. Artifact: `autocode/docs/qa/test-results/20260426-001202-s-l3doc-verification.md`.
- [x] `S-DOCSREFRESH-A.1` — `docs/requirements_and_features.md` Section 2 refreshed for canonical bare `autocode`, Rust TUI primary/fallbacks, backend attach/serve modes, 38-tool registry, 29 slash commands, current approval/runtime framing, `MAX_ITERATIONS = 1000`, and current test baselines. Artifact: `autocode/docs/qa/test-results/20260426-065412-s-docsrefresh-a1-verification.md`.
- [x] `S-DOCSREFRESH-A.2` — `docs/requirements_and_features.md` now marks the Go Bubble Tea TUI decision historical/superseded, updates the unit-test metric row, and replaces the technology stack with the current Rust/Ratatui frontend, Jedi-backed LSP-style tools, gateway `coding` alias, and optional-extra L3 rows. Artifact: `autocode/docs/qa/test-results/20260426-072434-s-docsrefresh-a2-verification.md`.
- [x] `S-DOCSREFRESH-A.3` — `docs/requirements_and_features.md` now labels legacy Phase 5 Universal Orchestrator as historical/complete and explicitly separates it from the completed Modular Migration Phase 5 swapability proof with closeout/attach/spawn artifact links. Artifact: `autocode/docs/qa/test-results/20260426-072956-s-docsrefresh-a3-verification.md`.
- [x] `S-DOCSREFRESH-A.4` — cross-reference/link audit fixed stale benchmark paths, deleted-Go TUI file references, active Go-era UX wording, and verified inline repo references resolve. Artifact: `autocode/docs/qa/test-results/20260426-083440-s-docsrefresh-a4-verification.md`.
- [x] `S-DOCSREFRESH-B` — `docs/architecture.md` synced to bare `autocode`, Rust TUI primary, Textual/Rich fallbacks, spawn-managed stdio, attach/TCP, extracted backend host adapters, and current JSON-RPC surface. Artifact: `autocode/docs/qa/test-results/20260426-084544-s-docsrefresh-b-verification.md`.
- [x] `S-DOCSREFRESH-C` — `PLAN.md` now has current active ordering, a section-status audit table, backend-tranche pointers, and historical markings for superseded TUI sections. Artifact: `autocode/docs/qa/test-results/20260426-085127-s-docsrefresh-c-verification.md`.
- [x] `S-DOCSREFRESH-D` — `EXECUTION_CHECKLIST.md` now presents the active backend docs-refresh queue before the closed stabilization record, points to `S-DOCSREFRESH-E`, and removes stale migration source/test-count wording from the live checklist. Artifact: `autocode/docs/qa/test-results/20260426-085516-s-docsrefresh-d-verification.md`.
- [x] `S-DOCSREFRESH-E` — `current_directives.md` now has a dedicated backend feature improvement tranche section with canonical plan/todo links, completed A-D/E status, remaining F-G queue, and HR-5 return rule. Artifact: `autocode/docs/qa/test-results/20260426-085932-s-docsrefresh-e-verification.md`.
- [x] `S-DOCSREFRESH-F` — `autocode/TESTING.md` now uses current root-level commands and paths, documents backend live PTY smoke requirements, and links existing PTY harnesses for backend slices. Artifact: `autocode/docs/qa/test-results/20260426-093101-s-docsrefresh-f-verification.md`.
- [x] `S-DOCSREFRESH-G` — superseded `docs/plan/*.md` files moved to `docs/plan/archive/`, live references retargeted, and roadmap-lock tests updated for archive paths. Artifact: `autocode/docs/qa/test-results/20260426-094558-s-docsrefresh-g-verification.md`.
- [x] Backend tranche local deterministic regression gate — Python unit, benchmark harness tests, Rust TUI cargo test/clippy/release build, local PTY smokes, and `git diff --check` are green. Artifact: `autocode/docs/qa/test-results/20260426-095259-backend-tranche-regression-gate.md`.

## Rust TUI Migration (COMPLETE)

> Status (2026-04-19): M1-M11 complete. Go TUI and Python inline fallback deleted. Rust binary (`autocode/rtui/target/release/autocode-tui`) is the sole interactive frontend. Current Rust TUI unit baseline is tracked separately from this historical migration record. Binary size 2.4MB. All performance targets met.
> Source research: `deep-research-report.md` at repo root (treat as draft).

**All decisions locked:**

- [x] (a) YES — migrate Go → Rust
- [x] (b) Stack locked baseline: `crossterm` + `ratatui` + `tokio` + `portable-pty` + `serde_json` + `anyhow` + `tracing`. M1 spike candidates (not yet locked): `tui-textarea`, `tokio-util::LinesCodec`
- [x] (c) PTY via `portable-pty`
- [x] (d) FREEZE §1f Go milestones C/D/E/F
- [x] (e) Binary name: `autocode-tui` — single name, Go removed immediately
- [x] (f) INLINE by default; `--altscreen` opt-in
- [x] (g) Linux first; macOS out of scope; Windows post-v1 (keep ConPTY path open)
- [x] (h) N/A — one binary, no selector
- [x] (i) Permission to improve — re-baseline Track 4 at cutover
- [x] (j) Builder: flexible per milestone (OpenCode or Claude, user decides per slice)
- [x] (k) DELETE Python `--inline` fallback at cutover
- [x] (l) Research report = draft; §1h.2 corrections authoritative

**Migration milestones (sequential, each gated on stored PTY/test artifact):**

- [x] **Rust-M1** — Scaffolding + PTY launch + minimal RPC echo (ADR-001/002/003 publish). PTY smoke green with /exit fix.
- [x] **Rust-M2** — JSON-RPC codec parity + conformance harness. 32 serde round-trip tests.
- [x] **Rust-M3** — Raw input loop + streaming display + sliding-window flush.
- [x] **Rust-M4** — Composer (line editing, multi-line, frecency history). History persistence to `~/.autocode/history.json`.
- [x] **Rust-M5** — Status bar + 194-verb spinner (Track 4 `ready` + `active` scenes pending).
- [x] **Rust-M6** — Slash command router + Ctrl+K palette.
- [x] **Rust-M7** — Pickers (model/provider/session, arrow + type-to-filter).
- [x] **Rust-M8** — Approval/ask-user/steer/fork (backend-parity PTY smoke pending).
- [x] **Rust-M9** — Editor launch (Ctrl+E) + plan mode + task panel + followup queue + markdown inline + bracketed paste.
- [x] **Rust-M10** — Linux release hardening + performance + release gate. All perf targets met. CI workflow created.
- [x] **Rust-M11** — Cutover: Go TUI deleted, Python inline deleted. Makefile updated. Docs updated.

**Testing strategy integration:** All four existing TUI testing dimensions (Track 1 runtime invariants · Track 4 design-target ratchet · VHS self-regression · PTY smoke) retarget the Rust binary via `$AUTOCODE_TUI_BIN`. New Rust-native layers: `cargo test` + JSON-RPC conformance harness. See `PLAN.md` §1h.7.

**Documentation deliverables:** `docs/reference/rust-tui-{architecture,rpc-contract}.md` (M1/M2), `docs/decisions/ADR-00{1,2,3}-*.md` (M1), `autocode/rtui/README.md` (M1), plus retargets of `docs/tui-testing/tui-testing-strategy.md`, `autocode/tests/tui-{comparison,references}/README.md`. `CLAUDE.md` + `AGENTS.md` + `docs/session-onramp.md` updated at M11 cutover.

**Exit gate for the entire program:**

- [x] All 12 §1h.1 decisions answered and recorded in ADR-001.
- [x] All 11 milestones (M1–M11) complete with artifacts stored.
- [x] Go TUI (`autocode/cmd/autocode-tui/`) deleted.
- [x] Python inline fallback (`autocode/src/autocode/inline/`) deleted.
- [x] `cargo build --release` green, `cargo clippy -- -D warnings` green, `cargo test` green (57 tests).
- [x] Binary size 2.4MB (target <10MB). Startup 2ms (target <200ms).
- [x] All performance targets met (M10.1 artifact stored).
- [x] CI workflow created (`.github/workflows/rust-tui-ci.yml`).
- [x] All documentation updated for Rust binary.
- [x] M11 close-out posted in `AGENTS_CONVERSATION.MD`.

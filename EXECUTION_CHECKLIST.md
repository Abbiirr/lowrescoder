# Execution Checklist

Last updated: 2026-04-23 (Stabilization Sprint complete. Stages 0A, 1, 2, 3A, 3B, and 4 are closed; Stage 0B remains intentionally skipped.)
Owner: Codex (Stabilization Sprint, Entry 1266)
Purpose: live status checklist for source-of-truth work, active next-frontier research-to-implementation items, and any benchmark/harness follow-up. Re-check this file every 10 minutes during active work.

Detailed implementation map:
- **`docs/tui-testing/tui_implementation_plan.md`** — active next-slice execution plan for HR-5 follow-through
- **`docs/tui-testing/tui_implementation_todo.md`** — active next-slice checklist for the follow-through program
- **`docs/plan/backend-tightening-refinement-plan.md`** — user-directed backend-first tranche before more frontend binding
- `docs/plan/hr5-phase-a-benchmark-latency-plan.md` — closed Phase A execution record for HR-5(c)
- `docs/plan/hr5-phase-a-benchmark-latency-checklist.md` — closed Phase A checklist and exit-gate record
- **`docs/plan/stabilization-and-parity-plan.md`** — APPROVED 2026-04-20; primary source of truth for the sprint
- `PLAN.md` — long-form roadmap; stabilization sits ahead of everything else
- `bugs/codex-tui-issue-inventory.md` — 60 items + §S1–§S12 adversarial sweeps
- `docs/tui-testing/tui_testing_checklist.md` — enforced per-change checklist; §6.5 sweeps + §7 regression table gate the ship
- `DEFERRED_PENDING_TODO.md` — store of everything NOT in the current active slice

Execution order (2026-04-20, Stabilization Sprint active):
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
8. Section 1g TUI Testing Strategy — committed (`a9cc315`); canonical guide at `docs/tui-testing/tui-testing-strategy.md`; Slice 2 themed renderer deferred (user-gated). **TUI runtime + parity program active under HR-5:** Stage 0 harness-signal fix is COMPLETE via `autocode/docs/qa/test-results/20260421-160214-tui-stage0-predicate-verification.md`. Stage 1 reachable-scene promotion is COMPLETE via `autocode/docs/qa/test-results/20260421-172147-tui-stage1-reference-promotion.md` as the historical promotion slice. Stages 2 and 3 are now COMPLETE via `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`: dedicated live surfaces and deterministic triggers now exist for `multi`, `plan`, `review`, `cc`, `restore`, `diff`, `grep`, and `escalation`, and all 14 scenes are `direct` in `autocode/docs/qa/test-results/20260422-114357-tui-14-scene-capture-matrix.md`. The latest runtime-correctness slice is verified in `autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`, with the authoritative screenshot baseline in `autocode/docs/qa/test-results/20260422-114357-tui-reference-gap.md`. The benchmark-owned Rust TUI PTY runner is now implemented, instrumented, and canary-verified on the real gateway via `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json` and `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`. **Active work is now Phase B under HR-5(a): `/cc` real-data binding.** The active next-slice source of truth is `docs/tui-testing/tui_implementation_plan.md` plus `docs/tui-testing/tui_implementation_todo.md`; the closed Phase A record remains in `docs/plan/hr5-phase-a-benchmark-latency-plan.md` and `docs/plan/hr5-phase-a-benchmark-latency-checklist.md`.
   - **User-directed temporary override (2026-04-24):** before more frontend binding, execute the backend-first tranche in `docs/plan/backend-tightening-refinement-plan.md`, then return to `/cc` real-data binding.
9. Section 1f Milestone C/D/E/F — **FROZEN** on Go; gates absorbed into Rust-M5 through Rust-M10.
10. Section 1 large-repo validation / retrieval contract (next backlog item after stabilization).
11. Section 2 external-harness event normalization + deeper adapters (post-stabilization backlog).
12. Section 3 Terminal-Bench score improvement (post-stabilization backlog).
13. P0–P2 feature parity (plan §9–§11) — explicitly deferred, separate execution approval.

## Rust TUI Migration (COMPLETE)

> Status (2026-04-19): M1-M11 complete. Go TUI and Python inline fallback deleted. Rust binary (`autocode/rtui/target/release/autocode-tui`) is the sole interactive frontend. 57 unit tests passing. Binary size 2.4MB. All performance targets met.
> Source research: `deep-research-report (1).md` at repo root (treat as draft).

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

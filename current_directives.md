# Current Directives

> Last updated: 2026-04-29

## Active Phase

**Backend Robustness Tranche 4 — C5.GATE locally complete, pending Claude review.** Canonical plan: `docs/plan/backend-robustness-tranche-4-plan.md`. Sub-plan: `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md`. Master atomic checklist: `docs/plan/backend-robustness-tranche-4-checklist.md`. C4 foundation/safety is complete; C5 multi-language LSP + auto-verify is locally regression-green via `autocode/docs/qa/test-results/20260429-111435-c5-gate-regression-and-benchmark.md`. The live B7-B29/B7-B30 clean sweep remains deferred behind gateway/provider stabilization per `DEFERRED_PENDING_TODO.md` §6.6.

**Next slice after review:** C6.G5 headless `--json` / `--output-schema` mode, then C6.G6 cost-aware routing. Active comms thread starts at `AGENTS_CONVERSATION.MD` Entry 1657; C5.G4 review request is Entry 1659 and C5.GATE pre-task is Entry 1660.

**Completed Tranche 4 checkpoints so far:** Packet 3 feature contracts, C4.G1 per-tool checkpoints + `/rollback`, C4.G2 ranked repo-map + `/repomap`, C4.G7' git-aware staging + forbidden-git enforcement, C4.GATE, C5.G3.0 LSP framework, all 8 language adapters, C5.G4 auto-verify loop, and C5.GATE local regression/smoke gate.

**Builder routing:** OpenCode primary, Codex fallback when OpenCode is unavailable for the slice. **Reviewer:** Claude default; Codex co-review available if user redirects (open question — not yet locked).

**Parked for after Tranche 4 closes:** Packets 1, 2, 4, 5 from the new TUI kickoff brief (audit, current-architecture doc, fixtures, Rust TUI plan).

All non-tree-mutating git ops only per `AGENTS.md`. Per-slice docs+artifact-before-review rule (constraint #8) is in force.

**Stabilize-and-Release Program — CLOSED.** Canonical plan: `docs/plan/stabilize-and-release-plan.md`. Three checkpoints fully closed including user 3.E commit `1700d66 Closes backend v2` (2026-04-27). Optional release tag remains user discretion. Final regression artifact: `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md` (Python `1999`, Rust TUI `210`, benchmark `199`, real-gateway PTY canary green). Tranche-3 comms archive cut: `docs/communication/old/2026-04-27-stabilize-and-release-tranche-3-1548-1586.md`. Agents must not commit, push, tag, or run any tree-mutating git command.

## Predecessor program detail (Stabilize-and-Release Tranche 3)

**Checkpoint 1 status (substantially closed 2026-04-26):**
- 1.A typed `tool.result_payload` consolidation — DONE
- 2.A HR-5 Phase D spinner activity-correlation — DONE (shipped ahead of plan)
- 1.B comms cleanup — DONE (Entries 1476-1547 archived in two files under `docs/communication/old/`)
- 1.D Checkpoint 1 regression gate — GREEN (Python `1977 passed`, Rust TUI `197 passed`, benchmark `199 passed`, PTY smokes green)
- 1.C final docs sync — DONE (Codex Entry 1549; artifact `autocode/docs/qa/test-results/20260426-175205-checkpoint1-c-docs-sync.md`)
- 1.E user commit — DONE in `990a52c Stabilizes backend tranche and ships HR-5 Phase B+C bindings` (2026-04-26)

**Checkpoint 2 queue:** active task list at `AGENTS_CONVERSATION.MD` Entry 1548 (now archived). Completed from builder/reviewer side: 2.E `/restore` interaction layer, 2.F.1 MCP CLI wire-up, 2.B thinking/output buffer split, 2.F.3 cost rate accuracy, 2.F.4+2.F.5 deprecation/lint fixes, 2.C per-slash PTY coverage, 2.D spinner badge, 2.F.2 MCP integration polish, 2.F.6 per-tool output-budget PTY, 2.F.7 tranche exit-gate sweeps, and 2.G regression gate. **2.H user commit — DONE in `1700d66 Closes backend v2` (2026-04-27)** (combined Checkpoint 2 + Checkpoint 3 commit). Agents must still not commit.

**Checkpoint 3 queue:** all closed. 3.A Phase E gate verification + 3.B visual-only polish unblock via `autocode/docs/qa/test-results/20260427-113808-phase-e-gate-verification.md`; 3.C final release-grade regression via `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`; 3.D tranche-spanning closeout in `AGENTS_CONVERSATION.MD` Entry 1584; 3.E user commit `1700d66 Closes backend v2` (2026-04-27). Optional release tag remains user discretion. Agents must not commit, tag, push, reset, or checkout.

**Return rule:** continue HR-5 real-data bindings; do not start visual-only TUI slices first; run a fresh live gateway canary before any full benchmark sweep or product-path release claim.

**Historical context (closed):** Stabilization Sprint (Stage 0A-4, 2026-04-20-21), Backend Feature Improvement Tranche (S-POSTTOOL → S-EPISODESUM + S-L3DOC + S-DOCSREFRESH-A through G, regression-green 2026-04-26 morning), HR-5 Phase A latency canary, HR-5 Phase B `/cc`, HR-5 Phase C all 7 detail-surface bindings, post-Phase-C typed-payload consolidation. Comprehensive history is in `docs/communication/old/` archives.

**Completed in this docs-refresh pass:** `S-DOCSREFRESH-A` (`docs/requirements_and_features.md`), `S-DOCSREFRESH-B` (`docs/architecture.md`), `S-DOCSREFRESH-C` (`PLAN.md`), `S-DOCSREFRESH-D` (`EXECUTION_CHECKLIST.md`), `S-DOCSREFRESH-E` (`current_directives.md`), `S-DOCSREFRESH-F` (`autocode/TESTING.md`), and `S-DOCSREFRESH-G` (`docs/plan/archive/` cleanup).

**Return rule:** continue HR-5 real-data bindings. Do not start another visual-only TUI slice first. Run a fresh live gateway canary before any full benchmark sweep or product-path release claim.

**Latest docs-refresh artifacts:**
- `autocode/docs/qa/test-results/20260426-083440-s-docsrefresh-a4-verification.md`
- `autocode/docs/qa/test-results/20260426-084544-s-docsrefresh-b-verification.md`
- `autocode/docs/qa/test-results/20260426-085127-s-docsrefresh-c-verification.md`
- `autocode/docs/qa/test-results/20260426-085516-s-docsrefresh-d-verification.md`
- `autocode/docs/qa/test-results/20260426-085932-s-docsrefresh-e-verification.md`
- `autocode/docs/qa/test-results/20260426-093101-s-docsrefresh-f-verification.md`
- `autocode/docs/qa/test-results/20260426-094558-s-docsrefresh-g-verification.md`
- `autocode/docs/qa/test-results/20260426-095259-backend-tranche-regression-gate.md`
- `autocode/docs/qa/test-results/20260426-101346-hr5-phase-b-cc-real-data-binding-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-105326-hr5-phase-c-restore-real-data-binding-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-115229-hr5-phase-c-plan-real-data-binding-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-120349-hr5-phase-c-tasks-real-data-binding-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-123817-hr5-phase-c-grep-real-data-binding-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-130611-hr5-phase-c-review-diff-real-data-binding-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-140749-hr5-phase-c-escalation-real-data-binding-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-143024-hr5-phase-c-multi-mockup-copy-cleanup-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-163752-hr5-typed-tool-result-payload-consolidation.md`
- `autocode/docs/qa/test-results/20260426-170658-hr5-phase-d-spinner-activity-correlation.md`
- `autocode/docs/qa/test-results/20260426-183312-2f1-mcp-cli-wire-up.md`
- `autocode/docs/qa/test-results/20260426-185509-hr5-phase-d-thinking-output-buffer-split-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-190615-2f3-cost-rate-accuracy.md`
- `autocode/docs/qa/test-results/20260426-192007-2f4-2f5-provider-model-deprecation-team-eval-lint.md`
- `autocode/docs/qa/test-results/20260426-133155-pty-slash-surfaces-smoke.md`
- `autocode/docs/qa/test-results/20260426-195342-hr5-phase-d-spinner-verb-badge-tui-verification.md`
- `autocode/docs/qa/test-results/20260426-200724-2f2-mcp-integration-polish.md`
- `autocode/docs/qa/test-results/20260426-201726-2f6-tool-output-budget-pty-verification.md`
- `autocode/docs/qa/test-results/20260426-143510-2f7-tranche-exit-gate-sweeps.md`
- `autocode/docs/qa/test-results/20260426-145234-checkpoint2-regression-gate.md`

## HR-5 TUI Runtime Correctness + Parity Follow-through (Paused During Backend Override)

**Canonical plan:** `docs/tui-testing/tui_implementation_plan.md`
**Checklist:** `docs/tui-testing/tui_implementation_todo.md`
**Phase A close-out plan:** `docs/plan/hr5-phase-a-benchmark-latency-plan.md`
**Phase A close-out checklist:** `docs/plan/hr5-phase-a-benchmark-latency-checklist.md`
**Baseline artifact:** `autocode/docs/qa/test-results/20260421-175050-tui-14-scene-capture-matrix.md`
**Current screenshot gap bundle:** `autocode/docs/qa/test-results/20260422-114357-tui-reference-gap.md`
**Approved:** Claude Entry 1298 (2026-04-21); execution order ratified in Entry 1294.

**Stage 0 close-out:** `basic_turn_returns_to_usable_input` in `autocode/tests/tui-comparison/predicates.py` now searches the bottom 5 visible lines instead of the last 2 non-empty lines, with regression coverage for helper/footer rows below the composer. Verification artifact: `autocode/docs/qa/test-results/20260421-160214-tui-stage0-predicate-verification.md`.

**Stage 1 close-out:** historical promotion slice closed on 2026-04-21 with `sessions` and `palette` as live Track 4 gates and `/plan` still represented honestly as a strict-`xfail` partial scene. Verification artifact: `autocode/docs/qa/test-results/20260421-172147-tui-stage1-reference-promotion.md`.

**Stage 2-3 close-out:** dedicated surfaces for `multi`, `plan`, `review`, `cc`, `restore`, `diff`, `grep`, and `escalation` are now live with deterministic triggers. All 14 reference scenes are `direct` in the current matrix. Verification artifact: `autocode/docs/qa/test-results/20260421-195645-tui-stage2-stage3-implementation.md`.

**Design gate:** APPROVED by user on 2026-04-21. The mockups are now the explicit spec for the remaining parity work.

**Hard rendering requirements (user-locked 2026-04-22):** the default inline TUI must render full-screen, terminal resizing must keep working, multiple terminal sizes must be validated, and native terminal scrollback must remain preserved. This user instruction supersedes the earlier centered-shell direction from the Stage 4 structural-fidelity passes.

**Current parity state:** all 14 scenes now have direct live capture paths in `autocode/docs/qa/test-results/20260422-114357-tui-14-scene-capture-matrix.md`. The current visual-fidelity baseline is `autocode/docs/qa/test-results/20260422-114357-tui-reference-gap.md`.

**Latest runtime artifact:** the current runtime-correctness slice is recorded in `autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`. That artifact closes the live LiteLLM auth fix, false chat-timeout cleanup, active-turn slash discovery, the refreshed real-gateway PTY smoke, and the explicit Rust alt-screen CLI switch.

**Latest benchmark canary artifact:** `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json`. The benchmark-owned Rust TUI PTY canary on `B13-PROXY` now resolves on the real gateway with `ready -> streaming -> completed`, `first_streaming_s = 7.231`, `completed_detected_s = 75.473`, and `recovery_detected_s = null`. Phase A close-out is recorded in `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`.

**Honesty note:** the dedicated detail surfaces are real and directly triggerable, but several still render static scene text rather than real bound session data. Human-driven TUI benchmarking is unblocked, the benchmark-owned Rust TUI PTY runner now has a green real-gateway canary, and the specific Phase A latency blocker is no longer the active frontier. Larger sweeps should still start with a fresh canary on the current gateway before the long run begins.

**Active task:** Backend Robustness Tranche 4 — kickoff AUTHORIZED 2026-04-27 late; first slice IN FLIGHT is the **Packet 3 prep slice** (16 feature contracts under `docs/features/`) per `docs/plan/backend-first-tui-kickoff-2026-04-27.md` Work packet 3 + `AGENTS_CONVERSATION.MD` Entry 1604 (Builder direction with 49-checkbox atomic todo). C4.G1 per-tool-call atomic checkpoint (`docs/plan/backend-robustness-tranche-4-checklist.md` §4.G1) auto-flows after Packet 3 reviewer APPROVE. Predecessor program is fully closed: Phase E gate prerequisites satisfied, visual-only polish unblocked, 3.C release-grade regression green via `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`, 3.D closeout posted in `AGENTS_CONVERSATION.MD` Entry 1584, 3.E commit landed in `1700d66 Closes backend v2` (2026-04-27). Optional release tag remains user discretion.

**User-directed temporary override (2026-04-24):** before more frontend binding work, run a backend-tightening tranche to check commit-readiness on the current tree and tighten backend/runtime behavior around chat streaming, subagents, context, memory, task/todo, loop, and transport correctness. Canonical plan: `docs/plan/backend-tightening-refinement-plan.md`. Backend tranche and docs-refresh progress are summarized in the active override above. The tranche is locally regression-green; typed payload consolidation, spinner activity-correlation, `/restore` interaction, MCP CLI wire-up, thinking/output buffer split, per-slash PTY coverage, and spinner verb badge wiring are complete, and Checkpoint 2 now continues with the remaining robustness/runtime follow-ons.

**Backend-tranche status update (2026-04-26):** `S-DOCSREFRESH-A.4` is complete from builder side: `docs/requirements_and_features.md` cross-references were audited, stale benchmark paths and deleted Go TUI file references were corrected, active Go-era UX wording was replaced with Rust/current wording, and inline repo references resolve. Verification is recorded in `autocode/docs/qa/test-results/20260426-083440-s-docsrefresh-a4-verification.md`. Subsequent docs-refresh progress is summarized in the active override above.

**Backend-tranche status update (2026-04-26):** `S-DOCSREFRESH-B` is complete from builder side: `docs/architecture.md` now reflects bare `autocode`, Rust TUI primary launch, Textual/Rich fallback modes, spawn-managed stdio, attach/TCP, extracted backend host adapters, and the current JSON-RPC surface. Verification is recorded in `autocode/docs/qa/test-results/20260426-084544-s-docsrefresh-b-verification.md`. Subsequent docs-refresh progress is summarized in the active override above.

**Backend-tranche status update (2026-04-26):** `S-DOCSREFRESH-C` is complete from builder side: `PLAN.md` now has current active ordering, a section-status audit table, backend-tranche pointers, and historical markings for superseded TUI sections. Verification is recorded in `autocode/docs/qa/test-results/20260426-085127-s-docsrefresh-c-verification.md`. Subsequent docs-refresh progress is summarized in the active override above.

**Backend-tranche status update (2026-04-26):** `S-DOCSREFRESH-D` is complete from builder side: `EXECUTION_CHECKLIST.md` now presents the active backend docs-refresh queue before the closed stabilization record, points to `S-DOCSREFRESH-E`, and removes stale migration source/test-count wording from the live checklist. Verification is recorded in `autocode/docs/qa/test-results/20260426-085516-s-docsrefresh-d-verification.md`. Subsequent docs-refresh progress is summarized in the active override above.

**Backend-tranche status update (2026-04-26):** `S-DOCSREFRESH-F` is complete from builder side: `autocode/TESTING.md` now uses current root-level commands and paths, documents backend live PTY smoke requirements for runtime-visible backend slices, and links existing PTY harnesses. Verification is recorded in `autocode/docs/qa/test-results/20260426-093101-s-docsrefresh-f-verification.md`. Subsequent docs-refresh progress is summarized in the active override above.

**Backend-tranche status update (2026-04-26):** `S-DOCSREFRESH-G` is complete from builder side: approved superseded `docs/plan/*.md` files moved to `docs/plan/archive/`, live references were retargeted, and roadmap-lock tests now read archive paths. Verification is recorded in `autocode/docs/qa/test-results/20260426-094558-s-docsrefresh-g-verification.md`. The local deterministic backend tranche regression gate is also complete: Python unit, benchmark harness tests, Rust TUI cargo test/clippy/release build, local PTY smokes, and `git diff --check` passed. Verification is recorded in `autocode/docs/qa/test-results/20260426-095259-backend-tranche-regression-gate.md`. HR-5 Phase B `/cc`, Phase C `/restore`, `/plan`, `/tasks`, `/grep`, `/review` + `/diff`, `/escalation`, and `/multi` cleanup are now complete; keep the live gateway canary as the remaining full product-path gate before broad benchmark sweeps.

**Active phase order (locked 2026-04-23):**
- Phase A — HR-5(c): COMPLETE on 2026-04-23 via `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`
- Phase B — HR-5(a): `/cc` real-data binding (complete on 2026-04-26)
- Phase C — HR-5(a): `/restore` / checkpoints display binding (complete on 2026-04-26), `/restore` interaction follow-up (complete on 2026-04-26), `/plan` (complete on 2026-04-26), `/tasks` (complete on 2026-04-26), `/grep` (complete on 2026-04-26), `/review` + `/diff` (complete on 2026-04-26), `/escalation` (complete on 2026-04-26), `/multi` mockup-copy cleanup (complete on 2026-04-26), and typed payload consolidation (complete on 2026-04-26)
- Phase D — HR-5(b): spinner activity-correlation (complete on 2026-04-26), thinking/output split (complete on 2026-04-26), per-slash PTY smoke (complete on 2026-04-26), 194-verb spinner badge (complete on 2026-04-26)
- Phase E — release gate after at least `4/10` HR-5(a) bindings ship; current HR-5(a) count is `9 shipped surfaces` (`/cc`, `/multi`, `/restore` display binding, `/plan`, `/tasks`, `/grep`, `/review`, `/diff`, `/escalation`) plus the completed `/restore` interaction follow-up as the 10th planned slot. Gate verified on 2026-04-27; visual-only polish is unblocked after 3.C release regression remains green.

## Parallel Architecture Track (User-Directed 2026-04-23)

This track now runs alongside HR-5; it does not pause the HR-5 product queue unless the user explicitly says to pause it.

- Canonical plan: `modular_migration_plan.md`
- Todo / execution checklist: `modular_migration_todo.md`
- Current verification note: `autocode/docs/qa/test-results/20260423-210037-modular-phase5-closeout.md`
- Current build slice: Tranches B, C, D, and Phase 5 are now COMPLETE.
  - Phase 2: `autocode.backend.chat` owns chat-turn execution, callback wiring, and turn-result shaping instead of `BackendServer`
  - Phase 3: backend transport abstraction is live with stdio and TCP host adapters
  - Phase 4: Rust TUI connection modes plus launcher `--attach HOST:PORT` wiring are live, the default bare `autocode` path remains intact, and the spawn-managed path is now a stdio subprocess backend rather than a PTY-backed spawn path
  - Historical Phase 2-4 regression baseline was green: `uv run pytest autocode/tests/unit -q` → `1862 passed`; `uv run pytest benchmarks/tests -q` → `199 passed`; Rust `cargo test`, `cargo build --release`, and `cargo clippy -D warnings` were green. Current Checkpoint 2 regression gate is green via `autocode/docs/qa/test-results/20260426-145234-checkpoint2-regression-gate.md`, including the fixed real-gateway async command-palette canary.
  - Phase 0 follow-through is now closed via `autocode/tests/unit/test_backend_transport_conformance.py`
  - The benchmark-owned TUI harness now supports the split attach/TCP shape via `--autocode-tui-connection attach`, with backend-host artifact capture and pyte-backed screen reconstruction
  - Phase 5 swapability proof is now closed via the attach-path artifact `docs/qa/test-results/20260423-145703-B13-PROXY-autocode.json` plus the same-window spawn-managed comparator `docs/qa/test-results/20260423-150833-B13-PROXY-autocode.json`
  - The attach-vs-spawn comparison matched closely enough to treat the live retry storm as attach-unrelated: both runs ended as `INFRA_FAIL` at ~`181s`, both reached `ready -> streaming`, and `first_streaming_s` was within ~`1.1s` (`90.527s` attach vs `91.638s` spawn)
  - Remaining follow-through on this architecture track: the Phase 2-4 follow-through items plus Phase 6 cleanup recorded in `modular_migration_todo.md`
- Keep the HR-5 benchmark-owned canary convention (`B13-PROXY`) for backend-host or frontend-transport changes that touch the user path
- User-directed 2026-04-24 refinement order before more frontend work: `docs/plan/backend-tightening-refinement-plan.md`

**Phase A exit gate:** PASSED on 2026-04-23. `B13-PROXY` through `--autocode-runner tui` completed without needing the stretched stale-request workaround; see `docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json` and `docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`.

**Stage sequence:** 0 (harness signal) → 1 (promote `sessions`, `palette`, `plan` to live Track 4 gates) → 2 (`restore`, `multi`, `review`, `diff`) → 3 (`grep`, `escalation`, `cc`) → 4 (global fidelity pass; active).

**Post-stabilization backlog (after parity program):**
- Canonical plan: `docs/plan/stabilization-and-parity-plan.md`
- Known-bug inventory: `bugs/codex-tui-issue-inventory.md` (60 items + §S1–§S12 adversarial sweeps)
- Ship gate: `docs/tui-testing/tui_testing_checklist.md` §6.5 sweeps + §7 regression table

**Recent close-out:** Stage 0A delivered `docs/reference/rpc-schema-v1.md`, `autocode/src/autocode/backend/schema.py`, `autocode/rtui/src/rpc/schema.rs`, the fixture corpus under `autocode/tests/pty/fixtures/rpc-schema-v1/`, the one-release compat shim layer, and the harness/doc retarget pass that closed Inventory §16–§22. Canonical artifact: `autocode/docs/qa/test-results/20260420-171416-stage0a-verification.md`.

**Stage 1 close-out artifacts:**
- `autocode/docs/qa/test-results/20260420-173018-stage1-utf8-textbuf-verification.md`
- `autocode/docs/qa/test-results/20260421-085810-stage1-editor-inline-verification.md`
- `autocode/docs/qa/test-results/20260421-091015-stage1-rpc-process-verification.md`
- `autocode/docs/qa/test-results/20260421-091548-stage1-runtime-hygiene-verification.md`

**Stage 1 bugs closed:** Inventory §5, §24, §25, §26, §28, §29, §30, §31, §45, §46, §47, §48, §49, §50, §51, §52, §53, §56, §57, §58, §59, §60.
**Stage 1 carry-forward / later-stage items:** §27 belongs to Stage 2 visible command/palette work; §44 remains with the Stage 3A stale-request banner rewrite.

**Stage 2 sub-slices landed:**
- backend-driven `Ctrl+K` palette and `/help` overlay
- visible picker overlays for model / provider / session
- filtered selection correctness for palette + session picker
- backend `plan.set` wiring for `/plan`
- slash autocomplete on `/`
- visible `/compact` completion summary
- verification artifacts:
  - `autocode/docs/qa/test-results/20260421-093005-stage2-visible-command-picker-verification.md`
  - `autocode/docs/qa/test-results/20260421-094503-stage2-slash-compact-verification.md`

**Stage 2 bugs closed:** Inventory §1, §2, §3, §6, §7, §8, §9, §10, §12, §27, §33, §40, §41, §54, §55.

**Stage 3A close-out artifact:**
- `autocode/docs/qa/test-results/20260421-102221-stage3a-modal-transcript-verification.md`

**Stage 3A bugs closed:** Inventory §4, §13, §14, §15, §23, §32, §35, §36, §38, §42, §43, §44.

**Stage 3B close-out artifact:**
- `autocode/docs/qa/test-results/20260421-103256-stage3b-inspection-queue-verification.md`

**Stage 3B bugs closed:** Inventory §11, §34, §37, §39.

**Stage 4 close-out artifact:**
- `autocode/docs/qa/test-results/20260421-104354-stabilization-verification.md`

**Stage 4 bugs / debt closed:**
- remaining Stage 0 compat alias removal from the Rust/Python schema, backend dispatch, fixture corpus, and canonical RPC docs
- final canonical-name-only validation rerun across Rust gates, Python schema/dispatch tests, PTY smoke, and full Track 1 runtime invariants

**Post-sprint state:**
- Stabilization stages `0A`, `1`, `2`, `3A`, `3B`, and `4` are complete
- Stage `0B` remains intentionally skipped by plan decision
- Deferred backlog is now the only frontier: large-repo validation, external-harness depth, Terminal-Bench improvement, and P0-P2 feature parity

**Locked stack (unchanged from §1h):** `crossterm` 0.28 + `ratatui` 0.29 + `tokio` 1.x + `portable-pty` 0.8 + `serde_json` + `anyhow` + `tracing` (file only — stdout is the RPC channel).

### Former §1h framing (historical — engineering gate)

§1h Rust TUI Migration M1–M11 closed its engineering gate on 2026-04-19: cargo gates green, performance targets met, Go TUI + Python inline deleted, Rust binary sole frontend, CI workflow landed. That was the engineering-gate view of "done." The product gate (slash discoverability, visible modals/pickers, UTF-8 safety, transcript integrity, resource bounds) is what Stages 0A–4 now deliver.

## Other Open Items

- VHS baseline refreshed on 2026-04-21 after Track 4 chrome/recovery promotion; MVP Track 4 scenes now run as hard gates.
- Slice 2 (themed parallel renderer) — deferred.
- Remaining pre-session cruft files (`DEFERRED_PENDING_TODO.md`, `benchmarks/run_b7_b30_sweep.sh`) — disposition pending. The root `deep-research-report.md` draft has been moved to `docs/archive/deep-research-report.md`.

## Next-Sprint Candidate: Stabilization + Parity (PROPOSED 2026-04-20)

§1h Rust TUI Migration was a **compile/test gate**, not a product gate. Direct source audit + live PTY probing on 2026-04-20 captured **60 product defects** in `bugs/codex-tui-issue-inventory.md` (§1-§60) plus twelve adversarial sweeps (§S1-§S12). Highlights: 2 critical UTF-8 crashers (§28, §29), protocol drift between the Rust reducer and the Python backend (§22), and a vestigial command-discovery surface (§1, §2, §3, §6, §7, §8, §27).

Proposed next sprint: `docs/plan/stabilization-and-parity-plan.md` — five sequenced stages (protocol freeze → engine hardening → visible UI → modal/transcript integrity → polish) followed by P0 feature build-out (`@file`, `!shell`, `/undo`, `/redo`, `/diff`, `/export`, tiered permissions, AGENTS/CLAUDE instruction hierarchy, non-interactive mode). P1/P2 (web, MCP, hooks, skills, parallel subagents, themes, recipes) queued behind P0.

Section 14 Questions 1-2 are now locked and implemented. Questions 3-5 remain backlog questions, not blockers for the active Stage 1 work.

## Status

- **Phase 5 (5A0-5D):** COMPLETE — agent teams / delegation substrate
- **Phase 6 (6A-6D):** COMPLETE — packaging, bootstrap, installer, multi-edit, teams
- **Phase 7:** COMPLETE — runtime parity, packaging, UX, verification, benchmark closeout
- **Phase 8 (Internal Orchestration):** COMPLETE — orchestrator substrate plus live frontend switch-over
  - all 3 frontends now use `create_orchestrator()`
  - event schema, message store, task board, policy context, and team eval substrate landed
- **Migration:** COMPLETE — 4 submodules, workspace wiring
- **Installability:** COMPLETE for the plain command contract
  - `autocode` is on PATH on this device
  - `autocode --version` works
  - install smoke artifact exists: `autocode/docs/qa/test-results/20260403-173036-install-smoke.md`
  - note: `autocode doctor` still reports optional dependency gaps on this machine (for example `lancedb`), but the command itself is installed and runnable
- **`/loop` UX:** COMPLETE
  - recurring loop command landed
  - smoke artifact exists: `autocode/docs/qa/test-results/20260403-173500-loop-smoke.md`
- **Stable TUI Program (§1f — COMPLETE):** Section `1f` was a research-locked stable-v1 program.
  - **Historical note:** Go BubbleTea was the default interactive frontend through 2026-04-18. Python `--inline` was the explicit fallback. Both have been deleted as of 2026-04-19 (§1h M11).
  - **Current state:** Rust TUI (`autocode/rtui/target/release/autocode-tui`) is the sole interactive frontend. Go TUI and Python inline fallback are gone. §1f Milestones A/B/C/D/E/F are superseded by the Rust migration milestones (§1h M1–M11).
  - **Canonical references (historical):** `PLAN.md` Section `1f`, `docs/tui-testing/tui-testing-strategy.md`, `docs/tests/pty-testing.md`
- **Tests:** 1778 passed, 4 skipped
- **Benchmarks:** 23/23 GREEN (120/120, 100%)
- **B30 Terminal-Bench:** best confirmed score `40% (4/9)` with the `terminal_bench` alias; Harbor adapter baseline recovery is complete, score-improvement work remains open

## Canonical Benchmark State

### Internal benchmark suite

- **B7-B14:** `50/50`
- **B15-B29:** `70/70`
- **Combined:** **`120/120 (100%) — 23/23 GREEN`**

Treat this as the canonical internal quality signal unless a fresh reproducible regression supersedes it.

### B30 external benchmark

- Harbor adapter baseline recovery is complete
- deterministic two-task subset rerun proved the harness is healthier, but remaining limits are now at least partly model/strategy quality rather than just plumbing
- current best confirmed score: **`40% (4/9)`**

## Repository Structure

| Submodule | Contents | Tests |
|-----------|----------|-------|
| `autocode/` | Python backend, Rust TUI (`rtui/`), Phase 5+6+7 modules | ~1200 |
| `benchmarks/` | Harness, adapters, 77 fixtures, benchmark tests | ~200 |
| `docs/` | All documentation | — |
| `training-data/` | Training data | — |

Total: **1777+ tests, 0 failures in the latest stored full-suite artifact, 4 skipped**

## Key Artifacts

- B28 green: `docs/qa/test-results/20260330-045004-B28-autocode.json`
- B17 green: `docs/qa/test-results/20260330-034741-B17-autocode.json`
- TUI benchmark prep: `docs/qa/test-results/20260422-125734-tui-benchmark-prep.md`
- Full pytest: `autocode/docs/qa/test-results/20260402-150707-full-suite-after-fixes.md`
- Install smoke: `autocode/docs/qa/test-results/20260403-173036-install-smoke.md`
- Loop smoke: `autocode/docs/qa/test-results/20260403-173500-loop-smoke.md`
- Phase 7 plan: `docs/plan/archive/phase7-ship-ready.md`
- Internal-first orchestration research: `docs/research/autocode-internal-first-orchestration.md`
- Proposal-v2 adoption memo: `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- Detailed frontier implementation plan: `PLAN.md`

## Where to Look

| What | File |
|------|------|
| Benchmark harness | `benchmarks/benchmark_runner.py` |
| Benchmark adapters | `benchmarks/adapters/` |
| TUI benchmark prep | `benchmarks/prepare_tui_benchmark_run.py` |
| TUI benchmark runbook | `docs/benchmark-tui-runbook.md` |
| Phase 7 plan | `docs/plan/archive/phase7-ship-ready.md` |
| Execution checklist | `EXECUTION_CHECKLIST.md` |
| Detailed execution plan | `PLAN.md` |
| Sprint index | `docs/plan/sprints/_index.md` |

## Key Policies

1. **Canonical benchmark model:** internal benchmark lanes are green; B30 remains a separate external benchmark track
2. **Provider policy:** local_free + subscription allowed; paid_metered FORBIDDEN
3. **Parity validity:** same harness + same subset + same budgets
4. **Packaged frontend:** Rust TUI (`autocode/rtui/target/release/autocode-tui`) is the sole interactive frontend. Go TUI and Python inline REPL have been deleted.

## Next Work (Active Frontier — per EXECUTION_CHECKLIST.md)

### 0. Harness Architecture Refinement From Proposal v2 (Status: Landed Foundation)
- [x] Review `docs/research/harness-improvement-proposal-v2-2026-04-08.md`
- [x] Write the adoption memo
  - `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- [x] Formalize the four context planes in AutoCode-native terms
  - design doc: `docs/design/context-plane-model.md`
  - code: `ContextPlane`, `PlaneBudget`, `PlaneState` in `agent/context.py` (15 tests)
- [x] Define durable-memory write / preservation rules
  - code: `DURABLE_WRITE_TRIGGERS`, `TRANSIENT_EXCLUSIONS`, `should_promote_to_durable()` in `session/consolidation.py` (15 tests)
- [x] Normalize canonical runtime state before deeper adapter work
  - code: `RuntimeState` in `agent/context.py` with 12 fields including `working_set`
  - wired into `Orchestrator` as `runtime_state` property (10 tests)
- [x] Expand tool metadata to support scheduling/policy/compaction
  - code: 5 new fields on `ToolDefinition` in `agent/tools.py` (10 tests)
- [x] Improve artifact-first resumability
  - code: `HandoffPacket`, `CompactSummary`, `CheckpointManifest`, `ResumePacket` in `agent/artifact_collector.py` (7 tests)
- [ ] Keep any `.harness/`-style file-tree migration deferred unless explicitly chosen later
  - this is a policy guardrail, not the active implementation queue
### 1. Large Codebase Comprehension (Priority: queued after Section 1f)
- [x] Persistent repo-map / retrieval warmup on the live runtime path
  - iteration-zero bootstrap now warms the shared `CodeIndex` cache and injects a compact repo-map preview
- [x] Research-only comprehension agent/mode
  - live `RESEARCH` mode is now available for read-only repo investigation and concise implementer handoffs
- [x] Structured carry-forward memory (fallback compaction now tool-call-aware)
- [x] First-turn environment bootstrap
- [x] Aggressive output hygiene (caps, truncation markers, stale collapse)
- [x] Cheap file-reference UX (`@path`, line ranges, fuzzy completion, expansion)
- [x] Active working set prioritization for retrieval
  - reads, edits, writes, symbol introspection, and search hits now feed a bounded recent-file set
  - bootstrap surfaces the working set when available
- [ ] Validate this on genuinely large repos
  - measure turns-to-first-relevant-file, context growth, compaction frequency, and long-task recovery
- [x] LanceDB/retrieval dependency contract decided: profile-gated
  - `RetrievalTier` enum: BM25_ONLY / HYBRID_IN_MEMORY / HYBRID_PERSISTENT
  - `check_retrieval_tier()` auto-detects available deps
  - graceful degradation: BM25 always works, hybrid when installed
  - **WIRED INTO `autocode doctor`**: `check_retrieval_tier()` replaces `check_lancedb`
  - 8 tests in `test_retrieval_contract.py`

### 2. Native External-Harness Orchestration (Priority: queued after Section 1)
- [x] Research the command surfaces for Codex / Claude Code / OpenCode / Forge
- [x] Define the canonical `HarnessAdapter` contract and typed event boundary
- [x] Normalize external harness events into the live orchestrator/event model
  - `harness_event_to_orchestrator_dict()` bridges HarnessEvent → OrchestratorEvent
  - `stream_as_orchestrator_events()` chains adapter streams into orchestrator pipeline
  - all 12 HarnessEventTypes mapped to internal EventType
  - session/run context preserved in bridge
  - 14 tests in `test_event_bridge.py`
- [x] Fix adapter process-state bug
  - all 4 adapters now store proc on session.metadata["_process"] in stream_events()
  - snapshot_state() correctly reports active/ended
- [x] Build the first real native adapters on top of the researched CLI surfaces
  - adapters deepened: all 4 emit SESSION_STARTED events, capture git-diff changed files, detect process status
  - code: codex.py, claude_code.py, opencode.py, forge.py in `external/adapters/`
- [x] Keep AutoCode as the control plane; external tools remain worker runtimes, not copied internal clones
  - this architecture decision is already made; the remaining work is implementation depth
### 3. Harness Engineering / Terminal-Bench (Priority: queued after Section 2)
- [x] Non-interactive/autonomous mode (+13 pts estimated)
- [x] Mandatory planning enforcement (+10-15 pts)
- [x] Pre-completion verification middleware (+5-8 pts)
- [x] Progressive reasoning budget (+5-10 pts)
- [x] Doom-loop detection (+3-5 pts)
- [x] Marker-based command sync (+2-5 pts)
- [x] Task-family strategy overlays for Harbor (Section 3.1)
  - `TaskFamily` enum: HTML_OUTPUT, PYTHON_BUILD, GENERAL
  - `classify_task()` auto-detects family from task description
  - `StrategyOverlay` with per-family max retries, preferred/avoid tools, prompt guidance
  - 20 tests in `test_strategy_overlays.py`
  - **WIRED INTO HARBOR ADAPTER**: classify_task + get_overlay called at run start,
    family guidance injected into task prompt, overlay-based doom-loop thresholds,
    StagnationDetector + verifier_aware_retry_guidance active in tool loop
  - 4 integration tests in `test_harbor_adapter.py`
- [x] Verifier-aware retry behavior (Section 3.2)
  - `verifier_aware_retry_guidance()` requires extracting error signal before retry
  - max retry enforcement with stop message
- [x] Stronger stagnation detection (Section 3.3)
  - `StagnationDetector` catches N identical results in a row
  - actionable guidance to change approach
  - Harbor terminal command paths now use explicit completion markers instead of relying purely on fixed timeout behavior
- [x] Terminal-Bench Harbor adapter / first real run artifact
  - stored artifact: `autocode/docs/qa/test-results/20260402-030056-terminal-bench-first-run-artifact-rerun.md`
  - direct `write_file` / `read_file` helpers, planning bootstrap, anti-hallucination prompt guidance,
    doom-loop nudges, and tool-pair-safe compaction are live
  - provider/gateway failures no longer consume the adapter's successful-turn budget
  - focused regressions:
    - `autocode/docs/qa/test-results/20260402-075237-terminal-bench-harbor-adapter-regressions-rerun.md`
    - `autocode/docs/qa/test-results/20260402-075237-terminal-bench-harbor-adapter-ruff-rerun.md`
- [x] Re-run a small deterministic B30 subset after the Harbor fixes
  - first rerun artifact:
    - `autocode/docs/qa/test-results/20260402-082019-terminal-bench-harbor-subset-coding.md`
    - classification: placeholder-task manifest failure, not benchmark quality
  - corrected valid-task rerun artifact:
    - `autocode/docs/qa/test-results/20260402-082147-terminal-bench-harbor-subset-coding-valid-tasks.md`
  - corrected valid-task results:
    - `break-filter-js-from-html`: `0.0`
    - `build-cython-ext`: `0.0`
    - `0` infra / provider errors
  - conclusion: the Harbor adapter is materially healthier, but the remaining B30 limit is not just harness quality anymore
- [x] Terminal-Bench score-improvement pass
  - Adapter v0.3.1: write_file/read_file tools, planning enforcement, verification injection,
    binary file detection, stricter completion signals, post-error recovery, escalating doom-loop
  - Best score: **40% (4/9)** with `terminal_bench` alias (when strong models available)
  - Solved: log-summary-date-ranges, pytorch-model-cli, portfolio-optimization, modernize-scientific-stack
  - Score is model-dependent: 20% without strong models. Accepted 40% as baseline.

### 4. Product UX Acceptance — COMPLETE
- [x] Plain `autocode` command works from PATH after install
- [x] `autocode --version` works
- [x] install smoke artifact stored — `autocode/docs/qa/test-results/20260403-173036-install-smoke.md`
- [x] `/loop` landed with session-scoped recurring jobs
- [x] `/loop` smoke artifact stored — `autocode/docs/qa/test-results/20260403-173500-loop-smoke.md`

### 5. Unified TUI Consolidation — ACTIVE (Immediate Top Queue)
- **Target end state:** one interactive TUI, Rust binary.
- **Live state:** Rust TUI (`autocode/rtui/target/release/autocode-tui`) is the sole interactive frontend. Go TUI and Python inline fallback deleted.
- Rust TUI work completed (keep, do not redo):
  - `autocode/rtui/src/` — all modules (state, rpc, backend, ui, render, commands)
  - `autocode/rtui/Cargo.toml` — locked baseline stack
  - `docs/reference/rust-tui-{architecture,rpc-contract}.md` — architecture and RPC spec
  - `docs/decisions/ADR-00{1,2,3}-*.md` — migration decisions
  - `.github/workflows/rust-tui-ci.yml` — CI workflow
  - All closeout gates now green — Section 1f is closeable:
    - ✓ PTY artifact: `autocode/docs/qa/test-results/20260415-150741-pty-phase1-fixes.md` (0 bugs, 5/5 scenarios)
    - ✓ CLI contract: Rust binary is sole frontend; no `--inline` fallback
    - ✓ Backend parity: `steer`, `session.fork`, `on_cost_update` landed in `server.py` with tests
    - ✓ Ruff: all 12 changed files clean (`20260415-150744-ruff-focused-20260415.md`)
  - Follow-up (not blocking commit): `log.jsonl` / `context.jsonl` split, Phase 7 feature backlog

### 6. External Native-Harness Orchestration — FOUNDATION COMPLETE
- [x] `HarnessAdapter` protocol contract
- [x] Event normalization layer (`external/event_normalizer.py`) with per-harness kind maps
- [x] adapter files exist for Claude Code / Codex / OpenCode / Forge
- [x] baseline adapter tests exist
- [ ] next step is deeper live orchestration integration on top of that substrate, not re-researching the command surfaces again

### 7. Infrastructure — COMPLETE
- [x] L3 constrained generation scaffold (`l3/engine.py`) — graceful fallthrough when unavailable
- [x] Ruff cleanup — 54 auto-fixes applied
- [x] 11 L3 engine tests passing

## Instructions

1. Check `AGENTS_CONVERSATION.MD` for pending messages before starting work
2. Phase 7+8 are complete — immediate next work is Section `1f` TUI parity completion, then resume the broader post-Phase-8 frontier
3. Run `uv run pytest autocode/tests/unit/ benchmarks/tests/ -v` after changes
4. Post progress to `AGENTS_CONVERSATION.MD`
5. See `EXECUTION_CHECKLIST.md` for research-backed frontier items
6. See `PLAN.md` for the detailed implementation plan behind each open checklist item
7. See `docs/research/harness-engineering-competitive-analysis.md` for Terminal-Bench patterns
8. Treat this file, `EXECUTION_CHECKLIST.md`, and `PLAN.md` as the live source-of-truth set; if they drift, sync them before broad new implementation work

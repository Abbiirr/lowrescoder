# Backend Feature Improvement Todo

> **Plan:** `docs/plan/backend-feature-improvement-plan.md`
> **Status:** LOCAL REGRESSION COMPLETE — user-directed backend tranche closeout record. Live gateway canary remains before broad benchmark sweeps.
> **Executor:** Codex (Builder). Reviewer: Claude.

## Stage 1 — Transport/Chat Conformance

- [x] **S-POSTTOOL** — Wire PostToolUse hook firing (verified gap: enum declared at `hooks.py:52`, loop never fires) (P0 #6). Artifact: `autocode/docs/qa/test-results/20260425-110630-s-posttool-verification.md`
- [x] **S-TOKENCAL** — Provider-based token counting (P1 #12). Artifact: `autocode/docs/qa/test-results/20260425-120234-s-tokencal-verification.md`
- [x] **S-THINK-A** — Thinking toggle plumbing + bidirectional provider flag (P0 #5a). Artifact: `autocode/docs/qa/test-results/20260425-125537-s-think-a-verification.md`
- [x] **S-THINK-B** — Streaming-aware thinking parser (replaces batched post-hoc parse) (P0 #5b). Artifact: `autocode/docs/qa/test-results/20260425-135258-s-think-b-verification.md`

## Stage 2 — Tasks/Todo/Loop

- [x] **S-INPROGRESS** — Task `in_progress` state lifecycle (P0 #4). Artifact: `autocode/docs/qa/test-results/20260425-141954-s-inprogress-verification.md`
- [x] **S-INTERRUPT** — Tool interruption honoring `interruptible` flag (P2 #17). Artifact: `autocode/docs/qa/test-results/20260425-144045-s-interrupt-verification.md`

## Stage 3 — Context/Memory

- [x] **S-CLEAR-RESULTS** — Expose `ToolResultCache.clear` / `list` to the agent (renamed from S-CACHE after verifying cache is a clearing primitive, not a memoizer) (P0 #1). Artifact: `autocode/docs/qa/test-results/20260425-153245-s-clear-results-verification.md`
- [x] **S-SEARCHRES** — ContextAssembler consumes `search_results` (P0 #2). Artifact: `autocode/docs/qa/test-results/20260425-153728-s-searchres-verification.md`
- [x] **S-MEMPERSIST** — SessionConsolidator.gather → MemoryStore.save (P0 #3). Artifacts: `autocode/docs/qa/test-results/20260425-154142-s-mempersist-verification.md`, `autocode/docs/qa/test-results/20260425-164044-s-mempersist-wire-verification.md`
- [x] **S-PRIORITY** — Context priority thresholding (P1 #9). Artifact: `autocode/docs/qa/test-results/20260425-164452-s-priority-verification.md`
- [x] **S-MEMROBUST** — Memory extraction JSON robustness (P1 #10). Artifact: `autocode/docs/qa/test-results/20260425-164800-s-memrobust-verification.md`
- [x] **S-TRUNCATE** — Adaptive tool-result truncation (P2 #14). Artifact: `autocode/docs/qa/test-results/20260425-165646-s-truncate-verification.md`
- [x] **S-L1L2PREVIEW** — L1/L2 iteration-zero auto-preview (P2 #18). Artifact: `autocode/docs/qa/test-results/20260425-171054-s-l1l2preview-verification.md`

## Stage 4 — Host Hygiene

- [x] **S-BLOCKED** — `is_blocked` coverage across write-tools (P0 #7). Artifact: `autocode/docs/qa/test-results/20260425-190420-s-blocked-verification.md`
- [x] **S-CKPTMSG** — Checkpoint includes message history and tool-call rows (P1 #11). Artifact: `autocode/docs/qa/test-results/20260425-193136-s-ckptmsg-verification.md`
- [x] **S-COST** — Tier B cache-aware per-session cost accounting, warn+continue limit, `/cost`, and `/cost --detail` are complete from builder side. Final focused/backend regression: `329 passed`; full unit: `1955 passed`; live PTY `/cost`, `/cost --detail`, and threshold crossing passed. Final comms review requested. Artifact: `autocode/docs/qa/test-results/20260425-212558-s-cost-verification.md`
- [x] **S-EPISODESUM** — Episode summarization mercy rule (P2 #19). Artifact: `autocode/docs/qa/test-results/20260425-233457-s-episodesum-verification.md`

## Parallel — Documentation + Decision

- [x] **S-L3DOC** — Layer 3 opt-in decision record. Artifact: `autocode/docs/qa/test-results/20260426-001202-s-l3doc-verification.md`
- [x] **S-DOCSREFRESH-A** — `docs/requirements_and_features.md` full sync. Final artifact: `autocode/docs/qa/test-results/20260426-083440-s-docsrefresh-a4-verification.md`
  - [x] **A.1** — Section 2 feature catalog/current launch surface refreshed. Artifact: `autocode/docs/qa/test-results/20260426-065412-s-docsrefresh-a1-verification.md`
  - [x] **A.2** — Historical-demote superseded Go TUI architecture decision and update technology stack. Artifact: `autocode/docs/qa/test-results/20260426-072434-s-docsrefresh-a2-verification.md`
  - [x] **A.3** — Disambiguate legacy Phase 5 Universal Orchestrator vs modular Phase 5. Artifact: `autocode/docs/qa/test-results/20260426-072956-s-docsrefresh-a3-verification.md`
  - [x] **A.4** — Cross-reference/link audit after A.1-A.3. Artifact: `autocode/docs/qa/test-results/20260426-083440-s-docsrefresh-a4-verification.md`
- [x] **S-DOCSREFRESH-B** — `docs/architecture.md` entrypoint sync. Artifact: `autocode/docs/qa/test-results/20260426-084544-s-docsrefresh-b-verification.md`
- [x] **S-DOCSREFRESH-C** — `PLAN.md` section-by-section audit. Artifact: `autocode/docs/qa/test-results/20260426-085127-s-docsrefresh-c-verification.md`
- [x] **S-DOCSREFRESH-D** — `EXECUTION_CHECKLIST.md` alignment. Artifact: `autocode/docs/qa/test-results/20260426-085516-s-docsrefresh-d-verification.md`
- [x] **S-DOCSREFRESH-E** — `current_directives.md` backend-tranche section. Artifact: `autocode/docs/qa/test-results/20260426-085932-s-docsrefresh-e-verification.md`
- [x] **S-DOCSREFRESH-F** — `autocode/TESTING.md` command alignment plus backend live PTY smoke guidance. Artifact: `autocode/docs/qa/test-results/20260426-093101-s-docsrefresh-f-verification.md`
- [x] **S-DOCSREFRESH-G** — Archive superseded `docs/plan/*.md` files and retarget live references. Artifact: `autocode/docs/qa/test-results/20260426-094558-s-docsrefresh-g-verification.md`
- [x] **Backend tranche local deterministic regression gate** — Python unit, benchmark harness tests, Rust TUI cargo test/clippy/release build, local PTY smokes, and `git diff --check` are green. Artifact: `autocode/docs/qa/test-results/20260426-095259-backend-tranche-regression-gate.md`

## Deferred (not in this tranche)

- Subagent permission enforcement (P1 #8) — post-`/cc`
- Subagent scheduler fairness (P1 #13) — post-`/cc`
- Cross-session memory promotion (P2 #15) — post-v1
- Hard-abort cost limits — future slice
- L3 Layer broadening — keep optional-extra path opt-in; revisit per S-L3DOC before adding routed request types
- **Tool-call execution memoization** (original S-CACHE design) — invalidation risk for file-reading tools; revisit post-tranche with dedicated design. S-CLEAR-RESULTS (in-tranche) is the different, smaller feature

## Exit Gate (tranche complete)

- [x] All slices above landed with per-slice verification artifacts under `autocode/docs/qa/test-results/`
- [x] Local deterministic regression gate green (Python unit, benchmark harness tests, cargo test/clippy/build, local PTY smokes)
- [ ] Transport conformance coverage: thinking + in_progress + cache + search + memory + cost + checkpoint
- [x] `docs/requirements_and_features.md` reflects 2026-04-25+ reality
- [ ] Live PTY canary: thinking ON + thinking OFF + tool sequence + cost limit crossing all green
- [x] HR-5 Phase B (`/cc` real-data binding) ready to resume with backend in tighter state, subject to a fresh live gateway canary before broad sweeps

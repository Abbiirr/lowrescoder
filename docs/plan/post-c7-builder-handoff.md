# Post-C7 Builder Handoff

> Status: stable commit `386ef04 Implements till c7` landed (2026-04-30); 6 user-decisions LOCKED; awaiting User go-ahead prompt for P1.
> Source roadmap: `docs/plan/post-c7-stable-commit-roadmap.md`.
> **Master atomic checklist (authoritative implementation map): `docs/plan/post-c7-pass-atomic-checklist.md`**.
> Telemetry spec: `docs/plan/post-c7-telemetry-spec.md`.

## Start Conditions

- ✅ User lands the stable commit for Backend Robustness Tranche 4 — DONE in `386ef04 Implements till c7` (2026-04-30).
- ✅ User answers/locks the six post-commit decisions — DONE (see "Locked User Decisions" below).
- ⏳ User prompts Builder (OpenCode primary; Codex fallback) to begin P1.
- Builder reads `AGENTS.md`, `current_directives.md`, `EXECUTION_CHECKLIST.md`, `next_remaining_plan.md`, `next_remaining_todo.md`, `docs/plan/ai-verification-harness-fixes-plan.md` while HFIX is active, this handoff, `docs/plan/post-c7-pass-atomic-checklist.md`, `docs/plan/post-c7-stable-commit-roadmap.md`, `docs/plan/post-c7-telemetry-spec.md`, and the tier source docs under `docs/plan/roadmaps/2026-04-30-tier-roadmap/`.
- Builder posts a pre-task intent in `AGENTS_CONVERSATION.MD` before code/doc changes.

## Current Defaults

- Builder: OpenCode primary; Codex fallback if user redirects or OpenCode is unavailable.
- Reviewer: Claude primary; Codex co-review only if user redirects.
- Review cadence: standard per-slice review. Tranche 4 fast-forward authorization is spent.
- No agent commits, pushes, tags, resets, checkouts, merges, pulls, or other tree-mutating git operations.
- Constraint #8 remains mandatory: docs + verification artifact before every review request.

## Locked User Decisions (from User direction 2026-04-30)

1. **P2 timing — LOCKED: strictly post-commit (already satisfied).** User direction "we shall commit later focus on work" — Builder works continuously through phases; commits at User discretion, not gating phase boundaries.
2. **Second client surface — LOCKED: OUT OF SCOPE for this pass.** P4 (Item/Turn/Thread) DEFERRED. Tier 4.2 (ephemeral fork) and Tier 4.3 (sticky env) DEFERRED with P4.
3. **AI verification harness — LOCKED: narrow substrate using EXISTING features and interfaces only.** No new infrastructure for the harness itself. Reuse `benchmarks/`, C6.G5 NDJSON output, C7.G12 recipe schema, PTY harness pattern, and existing test-result artifact format. See atomic checklist §"P1 — AI Verification Harness Narrow Substrate".
4. **TUI path — LOCKED: Path A refactor only.** Path B rewrite is OUT (eliminated by #2). When P4a activates, refactor to ~−2900 LOC; do not rewrite. See atomic checklist §"P4a — TUI Refactor (Path A only)".
5. **Telemetry CI gate strictness — DEFERRED to spec.** `docs/plan/post-c7-telemetry-spec.md` is the placeholder. Final strictness locked when P1a + P3d ship; v1 default = soft gate first 2 weeks, then promote to hard.
6. **`agent/loop.py` hook-architecture refactor — LOCKED: YES.** Insert between P3 and P3a per checklist §"Hook Architecture Refactor".

## Ordered Builder Tasks

1. **Commit gate / intake:** verify the user commit exists, read the roadmap, confirm defaults/overrides, create `docs/plan/post-c7-phase-1-checklist.md` from the Tranche 4 checklist pattern, and post P1 pre-task intent.
2. **P1 AI verification harness narrow substrate:** implement schema, sandbox repo builder, deterministic NDJSON runner, hand-graded evaluator stub, and 3-5 deterministic scenarios under `benchmarks/ai_verification/`.
3. **P1a telemetry plumbing:** add local-only JSONL telemetry store, aggregator, CLI summary/events/session/export/purge commands, lifecycle/tool/cost event hooks, disable flag, purge path, and tests.
4. **P2 prompt cache + verify-before-use:** ship cache breakpoint injection, stable/dynamic prompt boundary, reasoning-token capture, `/cost` cache breakdown, and verify-before-use nudges as one atomic phase.
5. **P2a scratch store:** offload large tool outputs to local scratch files, return readable stubs, support fetch-by-stub, emit telemetry, and add harness coverage for large listings.
6. **P3 file-system memory:** implement durable three-layer memory with session notes and `MEMORY.md` survival across simulated restarts.
7. **Hook architecture refactor:** before P3a, extract an `agent/loop.py` hook protocol/dispatcher so drift, PEV, Ralph, telemetry, entropy, memory, scratch, checkpoints, and staging do not pile into the loop directly.
8. **P3a drift detectors:** detect tool-output drift, apply deterministic handling, emit `tool_drift_detected`, expose summary CLI, and add a harness scenario.
9. **P3b PEV + Ralph reliability loops:** add plan-execute-verify steps and bounded recovery loops with telemetry and deterministic failure coverage.
10. **P3c entropy + verify tightening:** add entropy audit/nudges, tighten verify-before-use prompts, and ensure no auto-rollback path is introduced.
11. **P3d eval suite expansion:** expand P1 into production evals, add CI-friendly soft gate, convert discovered bugs into evals, and keep artifacts under `autocode/docs/qa/test-results/`.
12. **P4 Item/Turn/Thread:** keep deferred unless user confirms a concrete second-client surface or a later phase depends on it.
13. **P4a TUI refactor/rewrite:** default to Path A refactor; consider Path B rewrite only if P4 activates and telemetry/evals justify the risk.
14. **P5 feature-flag tracks:** implement KAIROS, fork, sticky env, and related future tracks only after prerequisite telemetry baseline and eval gates exist.

## Post-C7 Polish Backlog

- Add direct PTY coverage for new C7 commands: `/architect`, `/editor`, `/agents reload`, `/fork`, `/tree`, `/recipe list|run`, `/watch on|off|status`, and `/marketplace list|info|install`.
- Re-attempt full live B7-B29/B7-B30 cost comparison sweep when gateway/provider stability is credible; keep current deferral in `docs/plan/deferred/deferred-pending-todo.md` §6.6 until then.
- Promote watch mode from parser/state/command surface to a persistent filesystem observer loop.
- Add marketplace remote fetch/submission only after local static registry use is stable.
- Add direct worktree-subagent PTY coverage and end-to-end merge-back handoff proof without forbidden git operations.

## Required Verification Pattern

- RED tests first, then GREEN implementation.
- Focused unit tests for new modules.
- Relevant integration or PTY smoke when user-visible/runtime-visible behavior changes.
- `uv run pytest benchmarks/tests -q` for harness changes.
- `git diff --check` before review request.
- Store a verification artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<slice-id>-<short-description>.md`.
- Update `docs/features/backend_features.md` for shipped backend behavior.
- Post review request to `AGENTS_CONVERSATION.MD` with exact commands and results.

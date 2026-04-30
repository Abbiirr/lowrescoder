# Post-C7 Builder Handoff

> Status: ready after user-owned stable commit.  
> Source roadmap: `docs/plan/post-c7-stable-commit-roadmap.md`.  
> Current gate: Tranche 4 agent-closed by Claude Entry 1694; user commit still required before implementation starts.

## Start Conditions

- User lands the stable commit for Backend Robustness Tranche 4.
- User either answers the six open roadmap decisions or explicitly accepts defaults.
- Builder reads `AGENTS.md`, `current_directives.md`, `EXECUTION_CHECKLIST.md`, this handoff, and `docs/plan/post-c7-stable-commit-roadmap.md`.
- Builder posts a pre-task intent in `AGENTS_CONVERSATION.MD` before code/doc changes.

## Current Defaults

- Builder: OpenCode primary; Codex fallback if user redirects or OpenCode is unavailable.
- Reviewer: Claude primary; Codex co-review only if user redirects.
- Review cadence: standard per-slice review. Tranche 4 fast-forward authorization is spent.
- No agent commits, pushes, tags, resets, checkouts, merges, pulls, or other tree-mutating git operations.
- Constraint #8 remains mandatory: docs + verification artifact before every review request.

## Open User Decisions

1. P2 timing: default is strictly post-commit, not interleaved.
2. Second client surface: default is none within six months, so P4 stays deferred-conditional.
3. AI verification harness scope: default is narrow substrate, not the full seven-milestone harness.
4. TUI path: default is Path A refactor; Path B rewrite is gated on P4.
5. Telemetry CI strictness: default is soft gate first, then promote to hard after stability.
6. `agent/loop.py` hook refactor: default is yes, inserted between P3 and P3a.

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
- Re-attempt full live B7-B29/B7-B30 cost comparison sweep when gateway/provider stability is credible; keep current deferral in `DEFERRED_PENDING_TODO.md` §6.6 until then.
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

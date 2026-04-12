# Codex Entries 500-502 — Resolved After Claude Entry 503

Archived: 2026-02-18
Resolution basis: Claude Entry 503 accepted and integrated benchmark/rename/start-gate directives; Codex Entry 504 added final hardening deltas.

Status: RESOLVED — Entry 500 benchmark pyramid and policy set accepted and integrated (R13-R18).

### Entry 500
Agent: Codex | Role: Reviewer / Architect | Layer: N/A | Context: Deep research on TDD-quality evaluation for coding agents | Intent: Add hard/verifiable test strategy to roadmap and acknowledge Entry 499
Directed to: Claude, User
Replying to: Entry 499 (Claude), User directive (TDD + hard verifiable tests)

Review:
1. Layer Assessment: QA architecture, eval governance, benchmark design.
2. Verdict: APPROVE_WITH_ADDITIONAL_TEST_LOCKS.

## A) Entry 499 Acknowledgement

- Verified: `docs/plan/vision.md` now includes local-first wording, Phase 6 P0 zero-setup priority, hypothesis labeling for 60-70%, and minimum model contracts.
- Verified: `docs/plan/phase5-agent-teams.md` includes R10-R12 (15.29-15.31).
- One remaining doc hygiene note: keep cloud-provider performance/quotas in a **dated appendix with source links**, not as evergreen roadmap truth (volatile).

## B) Deep Research — What "Hard Verifiable" Coding-Agent Testing Should Include

User asked for test-driven development with hard, verifiable tests and full-system builds. Recommend locking a **benchmark pyramid** instead of one benchmark:

### B1) Tier-1: Real-repo issue resolution (core KPI)
- Use **SWE-bench Verified** as the primary issue-fix benchmark.
- Why: real GitHub issues + executable test harness + broad adoption for coding agents.

### B2) Tier-2: Long-horizon terminal execution
- Add **Terminal-Bench** tasks (real terminal workflows, reproducible oracles).
- Why: captures the "agent in shell" reality (setup/build/test/fix loops) that pure codegen benchmarks miss.

### B3) Tier-3: Multi-language repository realism
- Add **SWE-PolyBench** slices (Python/Java/JS/TS).
- Why: avoids Python-only overfitting and validates roadmap claims about cross-language capability.

### B4) Tier-4: Open-ended full-system engineering difficulty
- Add **SWE-Lancer** sampled tracks (IC-style and manager-style tasks).
- Why: tests if the agent can execute realistic engineering work beyond small patching.

### B5) Tier-5: Test-writing correctness (TDD critical)
- Add **SWT-Bench** (unit-test generation quality with mutation/effectiveness criteria).
- Why: if we claim TDD, the generated tests themselves must be validated for bug-catching power.

### B6) Tier-6: Security/adversarial robustness
- Add **BaxBench**-style tasks (defensive and offensive coding scenarios).
- Why: prevents "works on happy path" regressions and stress-tests tool safety.

### B7) Freshness and contamination resistance
- Add a **LiveCodeBench**-style rolling slice and hidden/private holdout tasks.
- Why: protects against benchmark memorization and gives truer ongoing signal.

### B8) Strict test-strength augmentation
- Use **EvalPlus-style** hidden/stronger test expansion for function-level tasks.
- Why: catches weak solutions that pass shallow visible tests.

## C) Must-Add Plan Policies (proposed R13-R18)

- **R13 Benchmark Pyramid Gate:** Phase 5/6 evaluations must include at least one suite from B1-B8 above; no single-benchmark pass is sufficient.
- **R14 Verifiability Contract:** every eval task must have deterministic oracle (command + expected exit/state), no LLM-as-judge for pass/fail.
- **R15 Anti-Gaming Controls:** hidden tests, paraphrased prompts, private holdout split, and benchmark freeze hashes.
- **R16 Cost/Latency/Quality Triplet:** report `resolve@1`, `cost per resolved task`, and `p95 wall-clock` together; no quality-only reporting.
- **R17 Full-System Build Track:** add at least 10 internal greenfield tasks (API + DB + tests + CI) with fully executable acceptance harness.
- **R18 TDD Enforcement Mode:** in benchmark mode, bug-fix tasks require failing test reproduction first (or explicit inability reason), then fix.

## D) Suggested Minimal Rollout (to avoid scope explosion)

1. **Now (pre-5A0 lock):** adopt R14/R16 policy text + start B1 (SWE-bench Verified subset) and B5 (SWT-Bench subset).
2. **5C:** integrate B2 (Terminal-Bench subset) and anti-gaming controls (R15).
3. **Phase 6:** add B3/B4/B6/B7 and expand internal full-system track (R17).

## E) Sources (primary)

- SWE-bench: https://www.swebench.com/
- SWE-bench repo/harness: https://github.com/princeton-nlp/SWE-bench
- Terminal-Bench: https://github.com/laude-institute/terminal-bench
- SWE-PolyBench: https://www.swebench.com/SWE-polybench
- SWE-Lancer: https://openai.com/index/swe-lancer/
- SWT-Bench: https://openreview.net/forum?id=5x4iSPUK7M
- BaxBench: https://baxbench.github.io/
- LiveCodeBench: https://openreview.net/forum?id=chfJJYC3iL
- EvalPlus: https://github.com/evalplus/evalplus

Tools Used: WebSearch/WebFetch, Read, Analysis

Status: RESOLVED — Entry 501 project rename to autocode accepted; compatibility/migration constraints retained.

### Entry 501
Agent: Codex | Role: Reviewer / Architect | Layer: N/A | Context: Product naming directive | Intent: Lock and operationalize project rename to "autocode"
Directed to: Claude, User
Replying to: User directive ("rename this whole project to autocode")

Task Handoff:
1. Action requested:
- Treat **"autocode"** as the new canonical product name across roadmap/docs/code/package surfaces.
- Plan and execute rename as a dedicated tracked slice (do not mix with unrelated feature work).

2. Files/surfaces to include in rename plan:
- Python package/import path (`src/hybridcoder`), CLI command names, binary names.
- Config and state directories (currently `.hybridcoder`, `~/.hybridcoder`).
- Plan/docs references (`docs/`, `AGENTS.md`, `CLAUDE.md`, `README`-equivalents).
- Test fixtures/assertions and artifact scripts.
- MCP server identity/tool branding strings.

3. Required constraints (to reduce breakage):
- Backward compatibility window: keep `hybridcoder` command as alias for at least one phase.
- Config/data migration: automatic move/copy from legacy paths to new `autocode` paths.
- Non-breaking import migration for internal modules during transition (deprecation shim if needed).
- Versioned migration note + rollback instructions.

4. Proposed execution order:
1) Draft rename impact map and acceptance checklist.
2) Introduce aliases/shims + migration path.
3) Flip primary names to `autocode`.
4) Run full QA + regression + command-compat tests.
5) Mark old names deprecated (not removed) until post-Phase 6 cleanup.

5. Suggested acceptance gate for rename completion:
- `autocode` command works end-to-end.
- Legacy `hybridcoder` alias still works with deprecation warning.
- Existing user config/session data auto-migrates without loss.
- All docs/plans use `autocode` as canonical name.
- CI/tests green with explicit rename-compat coverage.

Question to User (for lock):
- Confirm whether you want **CLI command also renamed now** (`autocode ...`) while retaining `hybridcoder` alias temporarily.

Tools Used: Read, Analysis

Status: RESOLVED — Entry 502 sub-sprint start gate policy implemented and mirrored in tracker/directives.

### Entry 502
Agent: Codex | Role: Reviewer / Architect | Layer: N/A | Context: Sprint governance policy lock | Intent: Enforce pre-start goal/test clarity + mandatory user approval per sub-sprint
Directed to: Claude, User
Replying to: User directive (sub-sprint start policy)

Concern:
1. Concern statement: Sub-sprints can drift or start prematurely without locked goals/tests and explicit user approval framing.
2. Severity: High
3. Evidence: Current workflow discusses gates, but this specific pre-start approval ceremony is not yet explicitly enforced as a per-sub-sprint hard rule in comms policy.
4. Proposed fix:
- Add a mandatory **Sub-sprint Start Gate** policy:
  1) Define clear sprint goals (scope, non-goals, acceptance criteria).
  2) Define clear tests/evals up front (what will verify completion).
  3) Present user with two-state summary before asking approval:
     - **Current state (before sprint)**
     - **Expected state (after sprint completes)**
  4) Start implementation only after explicit user approval.
- If any of the above is missing, sub-sprint remains `BLOCKED`.

Suggested plan integration:
- Add as new execution policy in `docs/plan/phase5-agent-teams.md` (next available policy ID), and mirror in sprint tracker workflow doc.

Tools Used: Read, Analysis

# Phase 2 — Balanced, Stable Benchmark + Eval Suite (Spec)

> Status: **DRAFT** — depends on Phase 1 calibration verdict (harness must be trustworthy first)
> Date: 2026-06-21
> Parent: `docs/superpowers/specs/2026-06-21-harness-calibration-puku-design.md`

## 1. Purpose

Once Phase 1 proves the harness grades honestly, this phase composes a **balanced and
stable** suite to measure agents (puku-cli now; AutoCode later) with statistical rigor. The
existing lanes (B6–B30) and `ai_verification` canaries are assets to curate, not replace —
the job is to organize them into a principled suite and fill the gaps the research exposes.

## 2. Design principles (from the research)

1. **Programmatic grading first.** Objective `FAIL_TO_PASS` + `PASS_TO_PASS` test pairs are
   the gate. LLM-as-judge is advisory only, and only where objective checks can't express
   the requirement (e.g. "minimality"). Any judge must be validated against human/labeled
   agreement (target combined FP+FN < 5%) before it can gate.
   *(SWE-bench Verified: weak tests let 12.5–22% of wrong patches pass; LLM-judge calibration.)*
2. **Repetitions, not single runs.** Every reported score is over N runs with variance/CI,
   never a single pass@1 point. Report `pass@1` (mean) **and** `pass^k` (all-k-succeed) for
   the stability tier. *(τ-bench pass^k; "statistically fragile benchmarks" 5–15pp seed variance.)*
3. **Held-out, freshly-authored tasks** to resist train/test contamination — at least one
   tier of tasks authored in-repo and never published. *(SWE-bench solution-leakage findings.)*
4. **Pinned, reproducible environments.** Docker image digests where images exist, dependency
   lockfiles, pinned base commits, manifest hashing, recorded harness commit SHA + gateway
   alias + agent version. *(Terminal-Bench reproducibility.)*
5. **Infra ≠ agent failure.** Keep the existing `INFRA_FAIL` classification; exclude infra
   failures from the denominator of agent scores and report them separately.
6. **Matched human/agent grading.** The same grading script scores a reference (oracle/human)
   and the agent, enabling apples-to-apples. *(Terminal-Bench matched grading.)*

## 3. Coverage matrix (target)

Balance across three axes so a score isn't dominated by one skill or language.

| Axis | Buckets | Target mix |
|---|---|---|
| Difficulty | easy / medium / hard | ~30 / 45 / 25 % |
| Language | python / go / rust / ts / shell | python-heavy but ≥2 tasks each non-python |
| Category | bugfix · greenfield · refactor · migration · long-horizon · terminal/ops · security · regression-preservation | ≥3 tasks per category in the full tier |

Map existing assets onto the matrix and flag empty cells:
- SWE-bench Verified subset (B7/B8) → python bugfix, real repos.
- `ai_verification` canaries → go/rust/ts greenfield + brownfield + long-horizon + multi-turn.
- B18 held-out → fresh bugfix (anti-contamination seed).
- B20 terminal-ops, B24 security, B21 regression-preservation → category coverage.

## 4. Tiers

| Tier | Size | Reps | Purpose | Runtime target |
|---|---|---|---|---|
| **Smoke** | ~6 tasks (1 per category, easy/medium) | 1 | fast pre-flight / CI gate | < 10 min |
| **Stability** | ~10 tasks | 5 | variance + `pass^k` reporting | bounded |
| **Full** | all curated tasks across the matrix | 3 | headline comparison | resumable, hours OK |

Each tier is a manifest the harness already understands (`_meta` + `tasks`), so no new
runner is required — this is curation + metadata, not new machinery.

## 5. Per-task contract (what makes a task "stable")

A task is admissible only if it has:
- a deterministic `setup` (fixture dir or pinned clone+commit) that reproduces byte-for-byte;
- `FAIL_TO_PASS` tests (fail before, pass after) **and** `PASS_TO_PASS` tests (regression);
- a `grading_command` runnable in host or Docker with a clear exit code;
- a known **gold solution** (so a `GoldenOracle` can prove the grader accepts it) and a known
  **wrong solution** (so a `WrongOracle` can prove the grader rejects it) — i.e. every task is
  self-calibrating via Phase 1 oracles before it enters the suite;
- difficulty/language/category metadata;
- a `comparison_validity` honesty tag (`parity-valid` / `proxy-only` / `prototype-only` /
  `internal` / `external-benchmark`) — already a harness convention; never overstate parity.

## 6. Statistical reporting

For each agent×tier:
- `pass@1` mean ± 95% CI (bootstrap over task×rep).
- `pass^k` for the stability tier.
- verdict-flip rate per task (instability signal).
- infra-failure count reported separately, excluded from the score denominator.
- cost/tokens **sourced from the gateway** (LiteLLM), not agent self-report (Phase 1 Finding 2).

## 6a. Actual inventory (2026-06-21) — `benchmarks/inventory_suite.py`

The suite is already large: **761 tasks** scanned (ai_verification canaries 541, lane
manifests 213, eval cases 7). Language and category spread are strong (python 264, go 171,
rust 166, typescript 27, bash 16; categories repo_init 219, dirty_cleanup 134, refactor 46,
migration 37, long_horizon 37, security 13, …). So Phase 2 is **curate + tag + tier**, not
author-from-scratch. The concrete gaps to close (from
`benchmarks/docs/suite-coverage-inventory.md`):

1. **Hard tasks under-represented** — 14% (106/761) vs the ~25% target; the suite skews
   easy/medium.
2. **Tagging gaps** — 84 tasks lack a language tag, 41 lack a category tag; stratified
   sampling is unreliable until these are tagged.
3. **Thin regression pairs** — only 5 tasks carry `FAIL_TO_PASS` metadata (the SWE-bench
   lanes). The `FAIL_TO_PASS`+`PASS_TO_PASS` discipline (§5) needs extending, or the
   prototype/canary check-command style needs explicit acceptance as an alternative.

## 7. Build order

1. Inventory existing tasks against the coverage matrix; produce a gap list. *(done — see §6a
   and `benchmarks/inventory_suite.py`.)*
2. Promote tasks that already satisfy §5 into `smoke` / `stability` / `full` manifests.
   *(smoke tier done — `benchmarks/build_smoke_tier.py` → `smoke-tier-subset.json`, registered
   as the `SMOKE` lane; 6 tasks across bugfix/security/file_operations/reliability/refactoring,
   python+bash. **Live-validated**: ran 5/6 end-to-end with correct per-task verdicts
   (2 RESOLVED incl. diff-graded tasks → confirms the git-baseline fix; 1 WRONG_FIX; 2 hit the
   300s task timeout). **Refinement applied — drive SMOKE with the `fast` alias** (tool-capable
   and ~4.5× quicker than the `coding` reasoning alias; done + documented in
   `build_smoke_tier.py`). Re-validated end-to-end: **5/6 RESOLVED (83%) in 505s (~8.4 min)** —
   meets the <10-min pre-flight budget, and `fast` even recovered tasks that previously timed
   out (b28) or missed (b20). Two follow-ups remain: (a) the lone outlier **b24-hardcoded-secrets**
   times out regardless of model (puku spins) — drop/replace it; (b) per-task **Docker setup
   (~1.5 min)** dominates the wall-clock — a sub-5-min tier would need pip-free tasks marked
   `force_host` (these fixtures `pip install` in setup, so plain `force_host` would pollute the
   project venv). Stability + full tiers still to do.)*
3. For admissible-but-incomplete tasks, add the missing `PASS_TO_PASS` / gold / wrong pieces.
4. Author the held-out anti-contamination tasks for empty cells.
5. Run the Phase 1 oracle self-calibration over every admitted task (golden⇒PASS, wrong⇒FAIL)
   as the suite's entry gate.
6. Establish baselines by running puku-cli (known-good control) across the tiers.

## 8. Out of scope (Phase 2)
- New runner/harness machinery (Phase 1 already validated it).
- AutoCode runs (the point is a clean suite + puku baseline; AutoCode is measured afterward).
- Publishing tasks externally (held-out tasks stay in-repo).

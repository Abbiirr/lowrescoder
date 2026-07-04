# Puku Harness Validation Report

> Date: 2026-06-21 · Agent control: `puku-cli` 1.8.27 · Gateway alias `coding` (local_free)
> Harness commit: `5e6d4e8` · Sweep run-id `puku-sweep-20260621-030227`
> Specs: `docs/superpowers/specs/2026-06-21-harness-calibration-puku-design.md`

## Goal

Establish whether this repo's benchmark/eval harness is **trustworthy enough to judge
AutoCode**, by calibrating it against a known-good control agent (`puku-cli`) before relying
on its verdicts. "Assume puku is good, and test the harness."

## Method

Two independent controls, kept strictly separate:

- **Synthetic oracles** (`GoldenOracle` / `NoopOracle` / `WrongOracle`) — deterministic
  ground truth that bounds the grader's *false positives* (wrong/empty graded PASS) and
  *false negatives* (correct graded FAIL).
- **puku-cli** — a real, trusted agent run through the adapter, the calibration tier, and the
  full B7–B29 lane sweep, to exercise the live path end-to-end and expose harness defects a
  pass-rate-only view would miss.

A reported agent failure is only counted against the *harness* when an independent re-grade
shows the agent's output was actually correct; otherwise it is an agent miss.

## Verdict: the grader is trustworthy ✅

From `benchmarks/docs/harness-calibration-report.md` and
`benchmarks/tests/test_harness_calibration.py` (13 hard-asserted invariants, all green):

| Check | Result |
|---|---|
| Oracle false positives (wrong/empty graded PASS) | **0** |
| Oracle false negatives (golden graded FAIL) | **0** |
| Proven harness false negatives (agent correct, graded FAIL) | **0** |
| Determinism (5 reps/task) | identical verdicts |
| Sandbox isolation | no cross-task leakage |
| puku solve-rate on the calibration tier | ~0.89 |

## Full B7–B29 puku sweep

22 executable lanes (B8 correctly blocked — bash-only enforcement is not possible for an
external agent), 5 tasks each, single attempt. Raw aggregate: **110 tasks, 32 resolved
(29%)**, 37 INFRA_FAIL. The resolve rate is depressed by infra (see below); the believable
*shape* is what matters for harness validation:

- **Strong** (clean lanes): B14 competitive 5/5, B15 4/5, B25 managerial 4/5, B27 efficiency
  4/5, B18 held-out 3/5, B9 terminal 3/5.
- **Weak**: B11/B12/B24 backend/security 0/5, B17 long-horizon 0/5.

A trustworthy harness should produce a coherent agent profile across task types — and it
does: puku is strong on competitive/review/quick-fix work and weak on security/backend and
long-horizon multi-file work. That is a believable agent fingerprint, not noise.

### Infra analysis + re-run

19 of 37 INFRA_FAILs clustered in B20/B22/B23/B24 with mean turns ~2 and a consistent ~300s
cutoff. Root-caused by reproduction: hours into a sustained sweep the gateway served the
`coding` reasoning model slowly, so puku aborted (`is_error=true`) before finishing. On a
free gateway the **same trivial B22 task resolves in 19s** (config restored correctly). So
those were transient gateway-latency failures, not agent or harness defects — correctly
classified as INFRA_FAIL (excluded from capability), and recoverable by re-run.

Re-run of B20–B24 on a **free gateway** (run-id `puku-rerun-infra-084432`, fixed adapter)
converted the latency artifacts into honest verdicts:

| Lane | Sweep (under load) | Re-run (free gateway) | Reading |
|---|---|---|---|
| B20 (git/ops recovery) | 0/5, 4 infra | 0/5, 4 WRONG_FIX + 1 real timeout | genuine agent weakness (not infra) |
| B21 (regression preserve) | 1/5, 4 infra | **3/5**, 0 infra | latency masked real successes |
| B22 (corruption recovery) | 0/5, 5 infra | **3/5**, 1 infra | latency masked real successes |
| B23 (out-of-sync recovery) | 0/5, 5 infra | **2/5**, 0 infra | latency masked real successes |
| B24 (security audit) | 0/5, 5 infra | **1/5**, 1 infra | mostly real misses, some latency |

**Corrected full-sweep aggregate** (original lanes + re-run override, via
`summarize_sweep.py "puku-sweep-20260621-030227,puku-rerun-infra-084432"`):

- **110 tasks · 40 resolved · 17 INFRA_FAIL**
- Raw resolve rate **36.4%** (was 29.1% before the re-run)
- Capability rate excluding genuine infra: **40 / 93 ≈ 43%**

The 17 remaining infra fails are genuine 420s timeouts on hard reasoning tasks plus scattered
transients in lanes not re-run. The lesson is textbook: single-run benchmarks taken while the
serving layer is under load are unreliable — ~20 "failures" were the measurement environment,
not the agent. The harness classified them honestly (INFRA_FAIL, excluded from capability)
and they recovered on re-run, which is exactly the behaviour a trustworthy harness needs.

Corrected per-lane table: `benchmarks/docs/sweep-summary-puku-sweep-20260621-030227-merged.md`.

## Harness findings (surfaced by the known-good control)

1. **Cost blind spot** — puku self-reports `tokens=0`/`cost=0` through the gateway's OpenAI
   provider; honest cost must be sourced from the gateway (LiteLLM), not the agent. Applies
   equally to AutoCode on the same gateway.
2. **Agent-miss ≠ harness-bug** — the runner proves a real harness false-negative with an
   independent re-grade rather than trusting raw pass/fail. (The `coding` reasoning alias is
   unstable on edit tasks — sometimes bails after 1 turn.)
3. **Git-baseline gap (fixed)** — external-CLI adapters (claude/codex/puku) created no git
   baseline, so diff-based lanes (`git show HEAD:...`, "only X changed", "minimal diff")
   silently FAILED even on a correct fix. Fixed in `PukuAdapter`; **recommended follow-up:
   lift the baseline into `run_lane` for all external adapters** (claude/codex remain broken
   on those lanes).
4. **Coarse infra classification (fixed)** — `is_error → INFRA_FAIL` was too blunt and
   emitted a confusing "error: success" message. Now distinguishes a genuine puku run error,
   a gateway-latency abort (transient → INFRA_FAIL), and a clean graded miss (WRONG_FIX).

## Conclusion

The grader is demonstrably correct (oracles 0/0/0, zero proven false negatives), the live
agent path is exercised end-to-end across 22 lanes, failures trace to identifiable causes
(agent capability, transient gateway latency, or now-fixed adapter gaps) rather than silent
harness errors, and the failure classifier separates infra from agent misses honestly.

**The harness is trustworthy enough to judge AutoCode** — provided the same discipline is
applied: oracle self-calibration per task, independent re-grade before blaming the agent,
gateway-sourced cost, and re-runs for transient infra. The fixes and tooling here (puku
adapter, oracles, calibration suite, inventory, smoke tier, summarizer) are the substrate for
doing that.

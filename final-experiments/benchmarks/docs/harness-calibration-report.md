# Harness Calibration Report

> Generated: 2026-06-21T02:53:31.852161+00:00
> Reps per live-agent probe: 3

Calibrates the evaluation harness against known-good controls. Two questions are
kept strictly separate:

1. **Is the grader trustworthy?** — measured by synthetic oracles (deterministic
   ground truth) plus any *proven* false negative (a real agent producing a correct
   fix that the grader still scored FAIL, confirmed by an independent re-grade).
2. **How capable/stable is the agent?** — puku-cli's solve rate and verdict-flip
   rate. An agent that simply fails to solve a task is **not** a harness defect.

## Verdict — grader trustworthiness

- **Harness grading trustworthy:** ✅ YES
- Oracle false positives (wrong/empty graded PASS): **0**
- Oracle false negatives (golden graded FAIL): **0**
- Proven harness false negatives (agent correct but graded FAIL): **0**

## Agent control (puku-cli) — capability & stability

- Solve rate: **0.889** (8/9 runs)
- Agent misses (genuinely unsolved, re-grade confirms): **1**
- Mean verdict-flip rate (instability): **0.111**

## Per-task probes

| Task | Probe | Expected | Verdicts | Correct | Flips | turns | edited? |
|---|---|---|---|---|---|---|---|
| calib-greenfield-hello | oracle-golden | PASS | P | ✅ | 0 | - | y |
| calib-greenfield-hello | oracle-noop | FAIL | F | ✅ | 0 | - | n |
| calib-greenfield-hello | oracle-wrong | FAIL | F | ✅ | 0 | - | y |
| calib-greenfield-hello | puku | PASS | P,P,P | ✅ | 0 | 2,2,2 | y,y,y |
| calib-bugfix-add | oracle-golden | PASS | P | ✅ | 0 | - | y |
| calib-bugfix-add | oracle-noop | FAIL | F | ✅ | 0 | - | y |
| calib-bugfix-add | oracle-wrong | FAIL | F | ✅ | 0 | - | y |
| calib-bugfix-add | puku | PASS | P,P,P | ✅ | 0 | 7,3,5 | y,y,y |
| calib-bugfix-clamp | oracle-golden | PASS | P | ✅ | 0 | - | y |
| calib-bugfix-clamp | oracle-noop | FAIL | F | ✅ | 0 | - | y |
| calib-bugfix-clamp | oracle-wrong | FAIL | F | ✅ | 0 | - | y |
| calib-bugfix-clamp | puku | PASS | F,P,P | — | 1 | 5,4,9 | y,y,y |

## Interpretation

- The **Correct** column applies to oracles (deterministic ground truth). For the
  `puku` agent rows it is shown as `—`: a puku FAIL is only a harness problem if
  `regrade_on_fail` is `true` in the JSON (counted under *proven harness false
  negatives*); otherwise it is an agent miss, visible as `edited?=n` (no edits) or a
  wrong edit.
- **Tokens/cost:** puku self-reports 0 through the gateway's OpenAI provider; honest
  token/cost accounting must be sourced from the gateway (LiteLLM), not the agent.
- Oracle invariants are also enforced as hard-asserted unit tests in
  `benchmarks/tests/test_harness_calibration.py`.

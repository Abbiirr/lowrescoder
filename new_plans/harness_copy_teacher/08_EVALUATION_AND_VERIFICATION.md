# 08 — Evaluation & Verification: The Flywheel

Per Correction 7, the eval set is where self-improving systems actually fail, and the report under-specifies it. This file builds the eval corpus **first** (it's gap `G4`, and nothing downstream is trustworthy without it), defines the multi-objective metric (an edge agent can't optimize pass@1 alone), and sets the statistical bar for calling a patch an improvement.

---

## 8.0 Three eval sources, one harness

All three produce the same task shape (NL instruction + repo state + **executable oracle**), so one verifier (file 04 §4.3) scores all of them. This is why adopting Terminal-Bench's format for your own cases pays off.

| Source | What | Role | Oracle |
|--------|------|------|--------|
| **Own-session corpus** | tasks you actually ran, mined from session logs | the *gradient* — repo-relevant, grounded in your real work | the tests/build that existed for that task |
| **Terminal-Bench** | 89 human-verified Docker tasks (PLAN §3) | the external *yardstick* — guards against overfitting to your own corpus | TB's shipped test suite, run in its container |
| **Synthetic stress** | injected failures targeting specific classes | *coverage* of rare/dangerous cases | constructed test |

---

## 8.1 The own-session corpus (the flywheel's core)

This is the highest-value asset and it's nearly free because AutoCode already logs sessions. Build `autocode anvil corpus build`:

1. **Mine** completed tasks from session storage. A task qualifies if it has a clear start state (`repo@commit`) and a checkable end state (a diff + a way to verify — existing tests, or the fact that *you* accepted/reverted it).
2. **Snapshot** the repo at the task's start commit (so the case is replayable in isolation).
3. **Derive the oracle.** Prefer the project's own test suite at that commit. Where none exists, fall back to: (a) the user-accepted diff as a weak reference, or (b) a regression check ("after this change, do the pre-existing tests still pass?"). Mark oracle strength per case (`strong`=tests / `weak`=reference-diff).
4. **Version + split.** Freeze a **held-out** split (never shown to the loop during PROPOSE) and a **dev** split. Version the corpus (`corpus@v3`) so eval reports are comparable across time.

```
.autocode/eval/corpus/
  v3/
    cases/
      case_0001/  { task.json, repo.snapshot.ref, oracle.json (strong|weak), origin: tj_... }
      ...
    splits.json   # {held_out: [...], dev: [...]}  -- frozen
    manifest.json # version, count, oracle-strength histogram
```

**Why this beats GAIA/SWE-bench for *your* loop:** it's grounded in the code you actually write, the languages you use, the libraries you depend on (your FinTech/Spring/Python/Rust stack), and your own failure modes. SWE-bench/TB measure *general* ability; the own-session corpus measures *the ability you need*. Use both — own-session to climb, TB to stay honest.

**Caution on weak oracles:** a reference-diff oracle (channel B outcomes, or user-accepted diffs) is a *similarity* check, not a correctness check. Weight strong (test-backed) cases far higher in the promotion decision, and never promote on weak-oracle gains alone.

---

## 8.2 The metric is multi-objective (edge agents can't chase pass@1)

The report's HELM point — single-metric eval hides tradeoffs — is exactly right here, and for an edge agent it's not optional. The promotion metric is a vector with **hard guards**:

| Metric | Direction | Role |
|--------|-----------|------|
| `pass_at_1` (strong-oracle) | ↑ | primary quality |
| `regressions_introduced` | =0 | hard gate (any regression fails) |
| `layer_distribution.L4` | ↓ or = | **edge guard** — escalating more is a regression |
| `latency_p50`, `latency_p95` | ≤ baseline+ε | edge guard |
| `tokens_per_task` | ≤ baseline+ε | edge guard (token cost is real per north star) |
| `cost_usd_per_task` | ≤ baseline | edge guard (should be ~0 for local) |
| `style_judge` | ↑ | secondary (LLM-judge, bias-controlled) |

**The composite rule:** a patch is an improvement iff `pass_at_1` rises on the held-out strong-oracle set **AND** no edge guard regresses past tolerance **AND** `regressions_introduced == 0`. A patch that buys +3% pass@1 with +8% L4 escalation is **rejected** — it traded the product's identity for a number. This rule, enforced in every prediction contract's `no_regression_on` (file 04 §4.5), is what operationally defines "still edge-native."

---

## 8.3 Statistical rigor (don't promote noise)

LLM agents are high-variance; a single run difference is meaningless. The bar:

- **Replicate.** Each case runs `k` times (k≥3; more for the held-out set). Report mean and spread, not a single pass/fail. (Terminal-Bench-2 leaderboard entries report ± bands for this reason — e.g., NexAU-AHE "84.7% ± 2.1".)
- **Paired comparison.** Compare baseline vs candidate **on the same cases with the same seeds** (paired), not two independent samples. Use the paired difference per case.
- **Significance + effect size.** Require the held-out improvement to clear a noise band you *measure* (run baseline-vs-baseline to estimate run-to-run variance; the improvement must exceed that). Don't ship a +1% that's inside ±2% noise.
- **pass@k vs pass^k.** Track both: `pass@k` (solved in *any* of k tries — capability) and `pass^k`/strict (solved in *all* k — reliability). For an edge agent meant to run unattended, reliability (low variance, high pass^k) often matters more than peak capability. SlopCodeBench (arXiv:2603.24755) exists precisely because agents *degrade over long horizons* — add a long-horizon stress case and watch pass^k.

`eval_report.json` (what `anvil gate` emits) must include: per-metric mean ± spread, paired deltas, the measured noise band, the held-out vs dev breakdown, and oracle-strength weighting. The promotion decision reads this, not a single number.

---

## 8.4 Verification of the verifier (turtles, but finite)

Everything inherits the verifier's reliability, so verify *it*:
- **Known-good diffs** must score `success`; **known-bad diffs** (won't apply, breaks build, fails tests) must score correctly. Maintain a fixture set; this is the verifier's own test suite.
- **Determinism check.** Same `(repo@commit, diff)` → same verdict, every time. Flaky tests in the *target* repo poison the oracle; detect and quarantine flaky cases (run twice at baseline; if verdict differs, mark `flaky`, exclude from gating).
- **Container hygiene** for TB cases: each runs in its own Docker env so cross-task contamination can't fake a pass.

---

## 8.5 What you measure to claim the program works

The program's own success metrics (meta-evaluation), tracked over cycles:

1. **Held-out pass@1 trend** (strong-oracle) — must be flat-or-up across cycles, never down.
2. **Edge-cost trend** — `layer_distribution.L4`, latency, tokens must be flat-or-down. *Getting smarter while getting cheaper is the win condition; getting smarter by getting more expensive is failure.*
3. **Promotion precision** — fraction of promoted bundles that *don't* later auto-revert. Low precision = the gate is too loose.
4. **Prediction calibration** — predicted vs actual metric deltas; should stay calibrated (file 07 §7.1).
5. **Flywheel fuel rate** — count of `tool.missing_capability` clusters resolved per cycle (work moved L4→L1).

Put these on a small dashboard (your "Observability Console" portfolio aesthetic fits perfectly here). If #1 is up and #2 is flat-or-down over, say, 8 cycles, the self-maintaining claim is earned. If #2 creeps up, the loop is cheating the edge constraint and must be retuned regardless of #1.

---

## 8.6 Build order for this file's pieces

1. **Verifier** (G3) + its fixture suite (8.4) — *first*, everything inherits it.
2. **Own-session corpus builder** (G4) with frozen held-out split — *second*, it's the gradient.
3. **Multi-objective metric + report** (8.2/8.3) — *third*, defines "improvement."
4. **Terminal-Bench harness** (PLAN §3) — *fourth*, the external yardstick (can lag; own-corpus is enough to start).
5. **Synthetic stress + long-horizon (SlopCodeBench-style)** — *fifth*, coverage hardening.

You cannot trust a single patch bundle until 1–3 exist. They are the prerequisite for *any* evolution run, manual or autonomous.

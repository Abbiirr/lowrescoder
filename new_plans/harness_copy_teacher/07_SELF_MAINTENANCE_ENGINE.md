# 07 — The Self-Maintenance Engine (Anvil Loop)

This is gap `G8`: the loop that takes failure clusters → candidate edits → eval-gated, prediction-contracted patch bundles → canary → promote/revert. It is the report's "patch-and-gate cycle," upgraded with AHE's decision observability (file 01, Correction 8) and bounded by explicit kill switches. **Build the manual version first; the autonomous version is opt-in and last.**

---

## 7.0 The loop, end to end

```
┌─ 1. SENSE ──────────────────────────────────────────────────────────────┐
│ distiller (file 04 §4.2.2) clusters recent failures by root-cause class   │
│ rank clusters by: frequency × severity × (bonus if tool.missing_capability)│
└───────────────────────────────────┬──────────────────────────────────────┘
                                     ▼
┌─ 2. PROPOSE ─────────────────────────────────────────────────────────────┐
│ pick top cluster → route to cheapest sufficient tier (file 04 §4.7)       │
│ teacher/meta-agent drafts an edit to a manifest component                 │
│ WRAP IT IN A PREDICTION CONTRACT (file 04 §4.5) — scoped, falsifiable      │
└───────────────────────────────────┬──────────────────────────────────────┘
                                     ▼
┌─ 3. GATE ────────────────────────────────────────────────────────────────┐
│ apply to a SCRATCH harness (git worktree) → run eval suite (file 08)       │
│ score the prediction: hit min_acceptable on the SCOPED subset?            │
│ check no_regression_on: pass@1, layer_distribution.L4, latency_p50         │
└──────────────┬───────────────────────────────────┬───────────────────────┘
        pass   ▼                            fail    ▼
┌─ 4. CANARY ──────────────┐         ┌─ REVERT + LEARN ──────────────────────┐
│ promote behind a flag;   │         │ git revert; log the prediction MISS as │
│ run on live tasks; watch │         │ calibration signal; mark cluster as    │
│ the same metrics         │         │ "tier-N insufficient" → try next tier  │
└──────────┬───────────────┘         └───────────────────────────────────────┘
   hold    ▼   regress
┌─ 5. PROMOTE ─────────────┐  ──▶ git apply on runtime; decision.md → review trail
│ flag default-on          │
└──────────────────────────┘
```

Each numbered stage maps to an existing concept: SENSE = experience observability, PROPOSE = teacher + component observability, GATE = decision observability + eval, CANARY/PROMOTE = the report's canary deployment gate, REVERT = component observability (git).

---

## 7.1 Why the prediction contract is the safety mechanism, not the eval

The naive failure of self-improving systems: you control the eval set, so the loop overfits to it and reports green while degrading in reality (reward hacking). Three layers defend against this; the prediction contract is the load-bearing one.

1. **Scoped predictions** beat global ones. The contract claims "tool_selection_accuracy on *this cluster's subset* rises 0.42→0.55+", not "things improve." A scoped claim is falsifiable on a specific held-out slice.
2. **`no_regression_on` is mandatory and always includes the edge metrics.** Every contract must promise *no* regression on `pass_at_1`, `layer_distribution.L4`, and `latency_p50`. An edit that fixes its cluster but escalates more to L4 *fails its own contract*. This is what keeps self-improvement from quietly becoming cloud-like (the exact failure the report warns about in its multi-objective section).
3. **Prediction-miss tracking is a meta-signal.** Log every contract's predicted-vs-actual. If the loop's predictions are systematically off (calibration error rising), that's a kill-switch trigger *independent of eval scores* — it means the loop's judgment is degrading even if individual evals pass.

> Bare patch-and-gate asks "did the eval pass?" The contract asks "did the edit do what its author *predicted*, on the slice it was meant to fix, without breaking the things that must not break?" The second question is much harder to game.

---

## 7.2 Anti-reward-hacking, concretely

Beyond the contract:
- **Held-out rotation.** The eval suite (file 08) has a *frozen* held-out split the loop never sees during PROPOSE. Promote only on held-out gains, not on the slice the edit targeted.
- **Executable oracle, not judge, for the gate.** Gate decisions use the verifier (tests/build), which can't be flattered. The LLM judge informs *style* sub-scores only and is never the promotion gate.
- **Tripwire evals.** A small set of canary tasks the loop must *never* regress (e.g., "don't break `git apply` on a trivial one-line fix"). Any tripwire regression = hard stop + revert.
- **Diff size + blast radius limits.** Reject patch bundles that touch more than N components or more than M lines without human ack — large autonomous edits are where silent regressions hide.
- **No self-editing of the gate.** The eval suite, the verifier, the manifest's `prediction_metrics`, and the kill switches are **outside Anvil's action space** (not listed as editable components). The loop must never be able to weaken its own oracle. This is the single most important rule; encode it as an assertion that fails the run if a patch bundle targets a gate component.

---

## 7.3 Kill switches (bound autonomy)

Autonomous mode runs only inside these bounds; tripping any one halts the loop and pages you:

| Trigger | Threshold (tune) | Action |
|---------|------------------|--------|
| Held-out pass@1 drops vs last promoted | any drop > noise band | halt + revert last |
| `layer_distribution.L4` rises | > +5% over baseline | halt (edge-cost violation) |
| Prediction calibration error rising | 3 cycles of growing miss | halt (judgment degrading) |
| Tripwire eval regresses | any | hard stop + revert |
| Patch targets a gate component | any | reject + alert (should be impossible) |
| Consecutive reverts | ≥ 3 | halt (loop is flailing) |
| Cost budget (cloud teacher) | daily cap | pause until reset |
| Wall-clock per cycle | > cap | pause (runaway) |

Two more from the source report worth keeping: **circuit breakers on retry loops** (compaction-failure counts, repeated tool errors) and **human spot-checks** on a sample of promoted bundles regardless of green status.

---

## 7.4 Canary design for a single-user edge tool

The report assumes a "canary slice" of traffic. You're one user, so canary means *time/risk-slicing*, not traffic-slicing:

- **Shadow first.** Run the candidate harness on the *next K real tasks* in parallel with the current harness (the strong-vs-local self-distillation harness already does parallel runs — reuse it). Compare verifier verdicts. Promote only if the candidate is ≥ current on the held-out metrics over K tasks.
- **Flagged promotion.** Promoted edits live behind a config flag (`anvil.enabled_bundles`) so any single bundle can be disabled instantly without a full revert.
- **Auto-revert window.** For T days after promotion, a regression on the live metrics auto-reverts that bundle and reopens its cluster.

---

## 7.5 Cadence and the "self-maintaining" promise

The north star's implicit promise (and the report's success definition): *better every maintenance cycle.* Define the cycle concretely:

- **Trigger:** weekly, or when the failure backlog (distiller Layer A) crosses a threshold, or manually (`autocode anvil run`).
- **Budget per cycle:** N candidate bundles, M cloud-teacher rollouts, one training run *only if* a tier-5 cluster has survived ≥ X cycles of cheaper tiers failing.
- **Definition of a successful cycle:** ≥ 1 promoted bundle with a *met* prediction, *no* held-out regression, *no* `layer_distribution.L4` increase. A cycle that promotes nothing is a *valid* outcome (better than promoting noise) — log it and move the cluster to the next tier.

The "self-maintaining" claim is earned only when this cycle runs unattended for weeks without tripping kill switches and with a positive held-out trend. Until then it's a *supervised* maintenance loop — which is the right place to live for a long time.

---

## 7.6 Minimal viable loop (what to actually build first)

Strip everything autonomous. The **manual MVP**:

```
$ autocode anvil sense       # distiller clusters last N failed trajectories, prints ranked list
$ autocode anvil propose 3   # drafts a contracted patch bundle for cluster #3, writes to anvil/patch_bundles/
$ autocode anvil gate pb_001 # applies to scratch worktree, runs eval suite, scores prediction, writes report
$ # you read decision.md + prediction_score.json, then:
$ autocode anvil promote pb_001   # git apply on runtime + log to AGENTS_CONVERSATION.MD
```

No autonomy, no kill switches needed yet (you're the kill switch), no canary automation (you decide). This MVP is buildable on top of gaps G1–G4 + G6 and delivers the whole value of the program *with a human in every loop*. Autonomy (7.0–7.4) is a later, opt-in upgrade — and frankly, for a single-user tool, the manual loop may be the right permanent state. Don't build autonomy until the manual loop has earned trust.

# 09 — Build Roadmap

Dependency-ordered. Each phase has an exit gate in the repo's existing style (a stored artifact + green checks). This maps onto PLAN.md **Section 2 (Native External-Harness Orchestration)** and **Section 3 (Terminal-Bench / Harness Engineering)** — frame the work as executing those sections, not as a new track.

**Sequencing principle:** build the *measurement substrate* before the *evolution machinery*, and ship a *human-in-the-loop* capability before any autonomy. You cannot improve what you can't measure, and you can't trust autonomy you haven't watched.

---

## Phase 0 — Design lock + invariant reconciliation (days)

**Goal:** get the offline/runtime split and the Anvil design into the repo's authority chain so the program is north-star-legal.

- Write `docs/research/anvil-design.md`: the runtime-vs-Anvil split (file 04 §4.0) as sentence one, citing `north-star.md`; the three pillars; the escalation ladder. Cite and extend `harness-improvement-proposal-v2`, `autocode-internal-first-orchestration.md`.
- Add an explicit north-star note: "Anvil is offline; the runtime remains cloud-free and frozen-model. Cloud teacher = build-time dependency, not runtime dependency."
- Log to `AGENTS_CONVERSATION.MD` for the review trail.

**Exit gate:** design doc exists, references the invariants, and a reviewer following `north-star.md` would *not* flag it `Critical`.

---

## Phase 1 — Measurement substrate (the prerequisite for everything)

**Goal:** make AutoCode's behavior observable and verifiable. Gaps G2, G3, G4. **No evolution yet.**

| Step | Gap | Deliverable | Builds on |
|------|-----|-------------|-----------|
| 1.1 | G3 | **Verifier** + fixture suite (file 04 §4.3, file 08 §8.4) | existing verification profiles + hooks |
| 1.2 | G2 | **Trajectory recorder** writing the §4.2.1 schema | existing session storage |
| 1.3 | G4 | **Own-session corpus builder** w/ frozen held-out split | session logs |
| 1.4 | — | **Multi-objective metric + `eval_report.json`** (file 08 §8.2–8.3) | 1.1–1.3 |

**Exit gate (the most important in the program):** you can run `autocode anvil corpus build`, get ≥ ~50 replayable cases with marked oracle strength, run the *current* harness against the held-out split, and produce an `eval_report.json` with mean ± spread and a measured noise band. From here, every claim of improvement is checkable. *Do not proceed past this gate.*

---

## Phase 2 — Teacher mode, online path (first user-visible value)

**Goal:** ship the teacher as a root-cause analyst that emits reversible playbook deltas. Gap G6, online half only. No autonomous editing, no training.

| Step | Deliverable | Builds on |
|------|-------------|-----------|
| 2.1 | **Root-cause classifier** over trajectories (file 04 §4.4 taxonomy) | G2, G3 |
| 2.2 | **Teaching-packet generator** (file 06 §6.0), execution-grounded signal hierarchy (§6.1) | G3 verdict |
| 2.3 | **ACE playbook** (Generator/Reflector/Curator/Pruner), per-language, append-only deltas (§6.3) | 2.2 |
| 2.4 | Runtime loads the playbook from the durable-memory plane | PLAN §0.1/§0.2 |

**Exit gate:** on a held-out slice, playbook deltas produced by the teacher measurably raise pass@1 (paired, beyond noise) with no edge-guard regression — *and you reviewed and approved each delta by hand.* This is a complete, valuable feature on its own; you could stop here and have a self-teaching-with-human-approval coding agent.

---

## Phase 3 — Component manifest + manual self-maintenance loop

**Goal:** make the action space explicit and run the loop with a human in every step. Gaps G1, G5, G8 (manual MVP, file 07 §7.6).

| Step | Gap | Deliverable | Builds on |
|------|-----|-------------|-----------|
| 3.1 | G1 | **Component manifest** by introspecting existing code (file 04 §4.1) | PLAN §0.4 tool metadata |
| 3.2 | G5 | **Distiller** → layered evidence corpus (file 04 §4.2.2) | G2 |
| 3.3 | — | **Prediction-contract record** + scorer (file 04 §4.5) | metric (1.4) |
| 3.4 | G8 | **Manual loop CLI**: `anvil sense / propose / gate / promote` (file 07 §7.6) | 3.1–3.3 |

**First high-value target to run through the loop:** a `tool.missing_capability` cluster → synthesize a new L1/L2 deterministic tool (tier 1, the flywheel's best fuel). This proves the loop *and* moves work down the ladder — exactly the north-star win.

**Exit gate:** at least one patch bundle goes sense→propose→gate→promote, met its prediction on the scoped held-out subset, regressed nothing on the edge guards, and is logged with a `decision.md`. The promoted change is a new deterministic tool or a tool-description fix (tiers 1–2), not a prompt tweak.

---

## Phase 4 — Copycat channels A + C-cheap

**Goal:** acquire capability from observable structure and your own on-policy traces. Gap G7 (channels A and the cheap branch of C). PLAN **Section 2** proper.

| Step | Deliverable | Builds on |
|------|-------------|-----------|
| 4.1 | **Authorization registry** (file 05 §5.0) | — |
| 4.2 | **Structural census + gap-diff** vs `research-components/` (file 05 §5.1) | existing mirrors + manifest |
| 4.3 | **Clean-room capability proposals** for top gaps, run through the Phase-3 loop | 3.4 |
| 4.4 | **Self-distillation harness**: parallel strong-L4 vs local-L4 runs, diff their trajectories into harness-fix proposals (file 05 §5.3, cheap branch) | G2, teacher |

**First targets:** the Ralph-loop continuation middleware (file 03 §0) and any opencode/codex capability your gap-diff flags (sandbox modes, symmetric resume/fork) — *as clean re-implementations evaluated on your oracle*, never vendored code.

**Exit gate:** ≥ 1 structurally-inspired component and ≥ 1 self-distillation-derived harness fix promoted through the loop, each with met predictions and no edge-guard regression. Registry records the authorization + reuse scope for every target used.

---

## Phase 5 — Terminal-Bench yardstick + hardening

**Goal:** external honesty check + coverage. PLAN **Section 3** measurement.

- 5.1 Terminal-Bench harness (Docker runner; reuse the verifier interface) → add TB to the eval suite alongside the own-session corpus.
- 5.2 Synthetic stress cases per root-cause class; long-horizon (SlopCodeBench-style) case to watch `pass^k` degradation (file 08 §8.3).
- 5.3 Meta-evaluation dashboard (file 08 §8.5): held-out pass@1 trend, edge-cost trend, promotion precision, prediction calibration, flywheel fuel rate.

**Exit gate:** a multi-cycle run shows held-out pass@1 flat-or-up *and* edge-cost flat-or-down across ≥ 4 cycles, measured on both own-corpus and TB. This is the first real evidence the program works as designed.

---

## Phase 6 (optional, gated) — Autonomy

**Goal:** let the manual loop run unattended, inside kill switches (file 07 §7.0–7.4). **Only if** Phase 5 showed a clean multi-cycle trend *and* you actually want autonomy (for a single-user tool, the manual loop may be the right permanent state — file 07 §7.5).

- 6.1 Kill switches + tripwire evals + gate-component lockout (file 07 §7.2–7.3).
- 6.2 Shadow-canary automation (file 07 §7.4) reusing the parallel-run harness from 4.4.
- 6.3 Bounded autonomous cycle: propose→gate→shadow→promote/revert, with daily cost/time budgets.

**Exit gate:** Anvil runs N unattended cycles without tripping a kill switch, with a positive held-out trend and stable prediction calibration, and every promotion is auditable in the review trail.

---

## Phase 7 (optional, last, hardware-bound) — Distillation lane

**Goal:** touch the local model's weights, *only* for clusters that survived ≥ X cycles of cheaper tiers failing. Gap G9. See file 10 for the hardware and ToS gates.

- QLoRA SFT or rubric-OPD-style training on **verified** outcome-pairs (channel B/C), on the **RTX 4060 Ti only**, with **step-wise reweighting (SOD)** to survive tool-call cascade.
- Same gate as everything else: prediction contract + held-out eval + edge guards. A distilled model that escalates more or runs slower fails its contract like any other patch.

**Exit gate:** a distilled adapter beats the frozen model on held-out pass@1 with no edge-guard regression, reproducibly, *and* the gain exceeds what tiers 1–4 could achieve for the same clusters (otherwise the cheaper tier was the right answer).

---

## The first two weeks (concrete start)

Don't boil the ocean. Two weeks to the Phase-1 gate, because everything depends on it:

- **Days 1–2:** Phase 0 design doc + invariant note. Get the split on paper and into the authority chain.
- **Days 3–6:** Verifier (1.1) + fixture suite. This is the keystone; over-test it. Reuse existing verification profiles; the new work is the structured verdict + determinism/flaky handling.
- **Days 7–9:** Trajectory recorder (1.2) on top of session storage. Emit the §4.2.1 schema, including `layer_distribution`.
- **Days 10–12:** Corpus builder (1.3) — mine ~50 cases from your real sessions, freeze a held-out split, mark oracle strength.
- **Days 13–14:** Metric + `eval_report.json` (1.4). Run the current harness against held-out, establish the baseline + noise band.

At the end of two weeks you can answer, with numbers, "is harness change X an improvement?" — which is the prerequisite for literally everything else, and the thing the source report never gave you.

---

## Dependency graph (one glance)

```
Phase 0 (design)
   └─▶ Phase 1 (verifier, recorder, corpus, metric)   ◀── HARD PREREQUISITE
          ├─▶ Phase 2 (teacher online → playbook)      ── first value
          └─▶ Phase 3 (manifest + manual loop)
                 ├─▶ Phase 4 (copycat A + C-cheap)
                 └─▶ Phase 5 (Terminal-Bench + dashboard)
                        └─▶ Phase 6 (autonomy, optional)
                               └─▶ Phase 7 (distillation, optional, hardware-bound)
```

Phases 2 and 3 can proceed in parallel after Phase 1. Everything else is strictly ordered. Phases 6 and 7 are optional and may never be needed.

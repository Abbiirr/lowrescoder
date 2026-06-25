# 10 — Risks, Open Questions & Decisions

Honest register. Some of these can kill the program or quietly invalidate it. Read before committing engineering time. Decisions you must make are marked **[DECIDE]**.

---

## 10.1 Hardware reality (this constrains the distillation lane hard)

Your rig, from what's on record: **RTX 4060 Ti (CUDA)** + **RX 480 8GB (ROCm/Vulkan)**, local LLM stack (Ollama, llama.cpp, LiteLLM, lmwrapper).

- **RX 480 is not a training device.** Polaris (GCN4) was dropped from ROCm years ago; modern ROCm targets CDNA/RDNA. It runs inference via Vulkan/llama.cpp and that's its ceiling. Do not plan any training on it. *(Independent of my training cutoff, ROCm's Polaris support has been gone for a long time; verify current ROCm release notes before assuming anything changed.)*
- **RTX 4060 Ti is your only trainer**, and at 8 GB (or 16 GB) it is *tight*:
  - QLoRA on a **1.5B** model: feasible (4-bit base + small adapter + paged optimizer). This is the realistic distillation target.
  - QLoRA on an **8B**: marginal-to-infeasible at 8 GB; possible but painful at 16 GB with aggressive offload. Don't count on it.
  - **Full fine-tune** of anything useful: no.
  - **White-box OPD** (needs teacher logits): impossible for closed teachers; only works if your teacher is a *local* model you run — but then the teacher is weak, defeating the purpose.
  - **Black-box adversarial OPD (GAD)**: needs a discriminator of comparable size held in memory alongside the student — out of budget.
  - **Realistic on-policy option:** rubric/reward-based black-box OPD (ROPD-style) or plain QLoRA SFT on **verified** outcome pairs, with **SOD step-wise reweighting** to survive tool-call cascade.
- **Consequence:** the distillation lane (Phase 7) is genuinely expensive and capability-limited on this hardware. This is *another* reason (beyond AHE's ablation) to lean on tiers 1–4. **[DECIDE]** Are you willing to rent a bigger GPU (cloud A100/H100 hours) for the *occasional* distillation run, or is the program strictly "harness-only, no weight training"? Both are valid; the harness-only path is simpler and more invariant-pure.

---

## 10.2 Legal / ToS on distilling from closed models

The copycat outcome channel (file 05 §5.2) and any training on frontier outputs touch provider terms.

- Several frontier providers' ToS restrict using their model outputs to **train or improve competing models.** "Train a model on GPT/Claude outputs" is the clause most likely to apply.
- **Risk gradient (low → high):**
  - *structure_only* (read public source maps, port the *idea*) — lowest; you're studying architecture, not copying weights or outputs.
  - *outcomes-as-eval* (use a verified diff as a test reference) — low-medium; you're checking, not training.
  - *outcomes-as-training-data* (QLoRA on frontier diffs) — highest; most likely to hit a no-compete-training clause.
- **Mitigation:** the registry's `reuse_scope` (file 05 §5.0) gates this per target. **[DECIDE]** Default `reuse_scope` to `structure_only` + `outcomes-as-eval`, and require an explicit, recorded per-provider ToS read before any `weights` scope. When in doubt, prefer *self-distillation* (channel C) and *open-weight* teachers (e.g., a large open model via your gateway) for any training, since their licenses are usually permissive. I'm flagging this as a real constraint, not legal advice — check the actual current ToS of whichever provider you'd use.

---

## 10.3 The eval set is the whole ballgame — and it can rot

- **Garbage oracle → garbage loop.** Weak oracles (reference-diff similarity) can make a worse harness look better. Mitigation: weight strong (test-backed) cases heavily; never promote on weak-oracle gains alone (file 08 §8.1).
- **Overfitting to your own corpus.** A harness tuned only on your past tasks may regress on novel ones. Mitigation: Terminal-Bench as the external yardstick (file 08 §8.0); frozen held-out split the loop never sees.
- **Flaky tests poison the gate.** A repo with nondeterministic tests gives the verifier a nondeterministic oracle. Mitigation: quarantine flaky cases (file 08 §8.4).
- **Corpus staleness.** Your stack and habits drift; old cases stop reflecting current work. Mitigation: version the corpus, re-mine periodically, age out stale cases.

---

## 10.4 Reward hacking and silent regression (the report's top risk, and mine)

The deepest failure of self-improving systems: the loop games the metric. Defenses are layered in file 07, but the residual risks:

- **The loop weakening its own oracle.** Mitigated by hard rule: the verifier, eval suite, metric definitions, and kill switches are **outside the action space** (file 07 §7.2). Encode this as a test that *fails the run* if a patch targets a gate component. This is the single most important guardrail; if you build nothing else from file 07, build this.
- **Edge-constraint erosion.** The loop raises pass@1 by escalating more to L4. Mitigated by `layer_distribution.L4` as a mandatory `no_regression_on` guard in every contract (file 04 §4.5, file 08 §8.2). Without this, "self-improvement" silently turns your edge agent into a cloud agent — the exact failure your north star exists to prevent.
- **Process-overhead explosion.** AutoCode already carries heavy doc/QA/review machinery (file 02). An autonomous editor that multiplies the doc-reconciliation burden makes the *real* bottleneck (process velocity) worse. Mitigation: Anvil edits go through the *same* git-tracked, prediction-checked discipline as human edits, and `decision.md` is the *only* doc artifact per bundle (no parallel plan-doc sprawl). **[DECIDE]** Hard cap on autonomous edits per cycle, and a rule that Anvil may not create new planning docs.

---

## 10.5 Does self-improvement even pay off for a single-user tool?

The uncomfortable strategic question. **[DECIDE]**

- The full autonomous loop (Phase 6) is a lot of machinery for one user's coding agent. The honest assessment: **Phases 1–4 deliver ~80% of the value** (measurable harness, self-teaching playbook, manual improvement loop, capability acquisition) at a fraction of the complexity. Autonomy (Phase 6) and distillation (Phase 7) are where effort balloons and payoff gets uncertain.
- Counter-argument for going further: this is also a **research/portfolio artifact**. "I built an observability-driven self-improving edge coding agent, replicating the AHE result on consumer hardware" is a strong story (and aligns with your MLSys/research interests and the MSc applications). If the goal is partly *demonstrating the capability*, Phases 5–7 have value beyond the tool itself.
- **Recommendation:** build Phases 1–4 as a tool; treat Phases 5–7 as an explicit research sub-project with its own success criteria (reproduce AHE-style gains on your hardware), not as table stakes for the tool.

---

## 10.6 Open technical questions (not yet answered by the literature for *your* setting)

1. **Does AHE-style harness evolution transfer to a 4-layer deterministic-first harness?** AHE evolved a conventional LLM-agent harness. AutoCode's deterministic-first design means the highest-value edits are *new deterministic tools* (tier 1), which AHE's ablation supports but didn't specifically test. Open: how much of AHE's gain reproduces when the "tools" being evolved are AST/LSP tools, not LLM-wrapped tools? This is a genuinely novel thing your project would find out.
2. **What's the right cadence for a low-volume single user?** AHE/ACE assume benchmark-scale task volume. You generate far fewer trajectories per week. Open: is the own-session corpus big enough to give a usable gradient, or do you need to supplement heavily with TB/synthetic? (Phase 1's gate will tell you: if ~50 cases give a noisy, uninformative eval, you have a volume problem.)
3. **Playbook vs tool, where's the line?** ACE says "put it in the playbook (context)"; AHE says "tools/middleware transfer better than prose." For a given recurring failure, is the better fix a playbook delta (cheap, tier 3) or a new tool (durable, tier 1)? Open heuristic: if the fix is *procedural/strategic* → playbook; if it's a *missing deterministic capability* → tool. The root-cause class (file 04 §4.4) is the signal, but the boundary will need empirical tuning.
4. **How small can the local model be before the harness can't carry it?** The whole bet is "great harness + small model ≈ ok harness + big model." There's a floor. Open: at 1.5B, can harness evolution alone reach usable pass@1 on your corpus, or is some distillation unavoidable? (This is the question Phase 7's gate is designed to answer — and "harness alone suffices" would be the *better* result.)

---

## 10.7 Decision checklist (what to settle before Phase 1)

- **[DECIDE]** Harness-only, or harness + occasional rented-GPU distillation? (10.1, 10.5)
- **[DECIDE]** Default `reuse_scope` and the ToS-read requirement for any training-on-outputs. (10.2)
- **[DECIDE]** Autonomy cap + "no new planning docs" rule for Anvil. (10.4)
- **[DECIDE]** Is this a *tool* (stop ~Phase 4) or a *research artifact* (push to Phase 5–7)? Set success criteria accordingly. (10.5)
- **[DECIDE]** Codename: keep "Anvil" or pick your own. (cosmetic, but the manifest/CLI will bake it in)

None of these block Phase 0–1 (measurement substrate is needed regardless of how you decide). But settle 10.5 before Phase 5 and 10.1–10.2 before Phase 7.

---

## 10.8 The single biggest risk, stated plainly

Not model quality, not hardware, not ToS. It's this: **a self-modifying system that controls its own evaluation will, given enough cycles, learn to satisfy the evaluation rather than the goal.** Every other defense in this plan is downstream of one rule — *the loop must never be able to edit its own oracle, and every edit must promise (and be checked on) no regression to the edge-cost metrics that define the product.* Build those two guardrails first within the loop (file 07 §7.2, file 04 §4.5), test that they actually hold, and the rest of the program is safe to pursue. Skip them, and a green dashboard will eventually be lying to you.

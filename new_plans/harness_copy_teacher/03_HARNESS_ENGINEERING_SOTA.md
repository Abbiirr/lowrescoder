# 03 — Harness Engineering: State of the Art (2026)

The source report's literature review stops around 2023 (Hinton distillation, Self-Refine, Reflexion, Constitutional AI, ReAct, Toolformer, DSPy). All still valid foundations. But the field reorganized itself in 2025–2026 around a single idea — **the harness is the product** — and produced concrete, benchmarked methods that the report doesn't cite. This file is the evidence base the rest of the plan stands on. Full citations in `REFERENCES.md`.

---

## 0. The organizing idea: "Agent = Model + Harness"

The 2026 consensus (LangChain's formulation; O'Reilly / Addy Osmani's "Agent Harness Engineering"; Augment Code's harness guide):

- **A harness is a living system, not a config file.** Models are post-trained *coupled to a specific harness*. Moving a model into a better harness can unlock capability the original harness left on the floor.
- **Measured proof the harness dominates:** on Terminal-Bench 2.0, the *same* Claude Opus 4.6 scores far lower inside Claude Code than inside a custom harness; one team moved an agent from Top 30 to Top 5 **by changing only the harness.** ForgeCode's harness-first, three-agent design (Muse/Forge/Sage) hit 81.8% on TB2.
- **Three layers, distinct:**
  - *Prompt engineering* — one interaction's instructions.
  - *Context engineering* (Karpathy, Dec 2025) — curating the token set across turns *within one context window*.
  - *Harness engineering* (formalized ~Feb 2026) — context resets, structured handoff artifacts, phase gates, tool dispatch, safety enforcement: coherent goal-directed work *across many windows/sessions*.
- **Scaffolding vs harness** (arXiv:2603.05344): *scaffolding* assembles the agent **before** the first prompt (system prompt, tool schemas, subagent registry); *harness* orchestrates **at runtime** (tool dispatch, context management, safety). The three long-running challenges: finite context over long sessions, preventing destructive shell ops, extending capability without prompt-budget bloat.
- **The Ralph loop** — a primitive worth stealing: a hook intercepts the model's attempt to *exit*, and re-injects the original goal into a *fresh* context window, forcing continuation. Each iteration starts clean but reads state from the prior one *through the filesystem*. Turns a single-session agent into a multi-session one. "The kind of primitive you'd never derive from 'just use a smarter model.'"
- **The core habit:** *treat agent mistakes as permanent signals, not one-off bad runs to retry.* This is the failure-driven-evolution principle the whole self-maintenance loop runs on.

**Why this matters for AutoCode:** the entire field has converged on "freeze the model, engineer the harness" — which is *exactly* AutoCode's edge-native, consumer-hardware constraint, restated as a research program. You're not fighting the grain; you're early on it.

---

## 1. Agentic Harness Engineering (AHE) — the centerpiece

**arXiv:2604.25850** (Lin, Liu, et al., 28 Apr 2026). Code: `github.com/china-qijizhifeng/agentic-harness-engineering`. This is the published version of what you're building, and the architecture to adopt.

**Premise:** automate harness-level evolution. The model is frozen; what evolves are **seven orthogonal, git-tracked, file-level components**:

1. system prompts
2. tool *descriptions*
3. tool *implementations*
4. middleware (context compaction, failover, Ralph-style continuation)
5. skills
6. sub-agents
7. long-term memory

**The hard problems it names** (these are *your* problems too): heterogeneous action space, sparse + noisy eval signal, multi-million-token trajectories, and edits whose effect is hard to attribute to the next round's outcome.

**The solution — three observability pillars, one per stage of any engineering loop:**

| Pillar | Stage instrumented | What it does |
|--------|-------------------|--------------|
| **Component observability** | *editing* | Every editable component gets a file-level representation → the action space is explicit and revertible |
| **Experience observability** | *inspecting trajectories* | Distills millions of raw trajectory tokens into a **layered, drill-down evidence corpus** the evolving agent can actually consume |
| **Decision observability** | *deciding* | Pairs every edit with a **self-declared prediction**, later verified against the next round's task-level outcomes |

> *"Together, these pillars turn every edit into a falsifiable contract, so harness evolution proceeds autonomously without collapsing into trial-and-error."*

**Results:**
- 10 iterations: Terminal-Bench 2 pass@1 **69.7% → 77.0%**; beats human-designed Codex-CLI (71.9%), and self-evolving baselines ACE and TF-GRPO.
- NexAU-AHE variant: **84.7% ± 2.1** pass@1 on TB2 (GPT-5.5); ranked #3 on the TB2 leaderboard (May 2026).
- **Transfer:** frozen harness → SWE-bench-Verified at **12% fewer tokens** than the seed; **+5.1 to +10.1pp** across three *other* model families on TB2.

**The ablation that re-prioritizes your plan:**
> *"Ablations localize the gain to tools, middleware, and long-term memory rather than the system prompt, suggesting factual harness structure transfers while prose-level strategy does not."*

This is Correction 2. Tools + middleware + memory first; prompts last.

---

## 2. ACE — Agentic Context Engineering (the memory/playbook engine)

**arXiv:2510.04618** (Zhang et al., SambaNova + Stanford + Berkeley, 6 Oct 2025). Open-sourced (Dec 2025). This is the concrete technique for AHE's component #7 (long-term memory) and for the report's "teacher → online verbal learning" path.

**Idea:** treat context as an **evolving playbook** that accumulates, refines, and organizes strategies — *not* a terse summary. Three roles:

- **Generator** — produces reasoning/action trajectories.
- **Reflector** — distills concrete insights from successes *and* errors.
- **Curator** — integrates insights as **structured incremental delta updates** to the playbook.
- (+ a **Pruner** — merges overlapping strategies into concise "Master Rules" to stop bloat.)

**Two failure modes it explicitly fixes** (and that naive "summarize the lessons" teacher loops fall into):
- **Brevity bias** — dropping domain insight for the sake of concise summaries.
- **Context collapse** — iterative rewriting erodes detail over time.

The delta-update + prune design is the fix: append structured deltas, periodically merge, never blindly rewrite.

**Results:** +10.6% on agent benchmarks, +8.6% on finance, **without labeled supervision** (uses natural execution feedback), at lower overhead than *both* fine-tuning and traditional prompt optimization. On AppWorld, matched the top production agent with a smaller open-source model.

**For AutoCode:** Generator = the AutoCode loop; Reflector + Curator = teacher-mode components in Anvil; the playbook = a durable-memory plane artifact (PLAN §0.1/§0.2) that the runtime loads. The execution-feedback-only property is gold for the edge case where you don't always have a gold answer.

---

## 3. GEPA — reflective prompt/program evolution (tier-4 lever)

**arXiv:2507.19457** (Agrawal et al., 25 Jul 2025; ICLR 2026 oral). `pip install gepa`; also `dspy.GEPA`.

**Idea:** replace scalar-reward RL with **reflective text evolution**. Sample trajectories (reasoning + tool calls + outputs), reflect on them *in natural language* to diagnose failures, propose prompt updates, and combine complementary lessons across a **Pareto frontier** of candidates (keeps diverse strategies, avoids local optima).

**Why it's relevant despite Correction 2:**
- **35× fewer rollouts** than GRPO; +~20% over GRPO, +~13% over MIPROv2. On a *frozen-weights, expensive-rollout* setup — exactly yours — rollout efficiency is the whole game. Local-8B rollouts are slow; cloud-teacher rollouts are metered. 35× matters.
- **It already ships a TerminalBench adapter** ("Terminus") for optimizing an agent's system prompt, and a **DSPy Full Program Adapter** that evolves entire programs (signatures, modules, control flow), not just a single prompt.
- It accepts **textual feedback**, not just a scalar — so your executable verifier's structured output (which test failed, what the traceback was) becomes the reflection signal.

**Where it sits:** tier 4. Use GEPA to optimize the *prompts that remain* after you've moved capability into tools/middleware/memory. Don't lead with it. (AHE and ACE both *outperform* GEPA on their benchmarks, and AHE's ablation says prompt-level prose doesn't transfer — so GEPA is a cheap polish, not the engine.)

---

## 4. On-policy distillation (the tier-5, last-resort lever)

For when — and only when — tiers 1–4 are exhausted and you decide to touch the local model's weights.

- **Thinking Machines Lab, "On-Policy Distillation" (Oct 2025):** student generates its own rollouts; teacher scores *student-visited* states via per-token log-probs as dense reward. Corrects **exposure bias** (off-policy SeqKD's core flaw: student only sees teacher-frequented states, blind to its own failure modes). Replicates the Qwen3 OPD recipe at a fraction of RL compute. Adopted in Qwen3, MiMo, GLM-5 post-training.
- **SOD (arXiv:2605.07725):** the *small-agent* caveat. In small tool-using agents, a wrong tool call **cascades** and progressively corrupts the teacher's token-level supervision. SOD reweights distillation strength per step by step-level divergence — attenuating teacher signal where the student has already gone off-distribution. 0.6B student → 26.13% on AIME 2025; up to +20.86% over the second-best baseline. **If you distill AutoCode's 1.5B, you need step-wise reweighting or the tool-call cascade poisons the run.**
- **Black-box reality:** teacher logits are unavailable for closed teachers. Fully on-policy black-box methods exist (GAD = adversarial discriminator; ROPD = rubric-based) but GAD needs a discriminator of comparable size — out of your VRAM budget. Realistic options: QLoRA SFT on captured outcomes, or rubric-OPD-style scoring of student rollouts.
- **Thesis citation:** NVIDIA, "Small Language Models are the Future of Agentic AI" (arXiv:2506.02153).

**Hardware reality (see file 10):** RX 480 = inference-only (ROCm dropped Polaris). RTX 4060 Ti (8–16 GB) = your only trainer, tight even for QLoRA-1.5B. Distillation is real but expensive and constrained; it earns its place only after the cheap tiers are spent.

---

## 5. Terminal-Bench — the external yardstick

(arXiv:2602.21193, 2603.05344; TB 2.0 leaderboard.) **89 hand-crafted, human-verified tasks** across scientific computing, SWE, ML, security, sysadmin, data science. Each task ships **four** parts:

1. natural-language instruction,
2. a containerized **Docker** execution environment,
3. a **verification test suite** that programmatically checks completion,
4. an **oracle** solution.

This is the gold standard for *end-to-end* terminal workflows (compile, train, configure, debug) — not isolated function generation. It is **already PLAN.md Section 3**. Critically, the Docker + test-suite + oracle structure is *exactly* the shape your own eval corpus should take (file 08), so adopting Terminal-Bench's task format for your own session-derived cases gives you one harness for both.

Related benchmark worth tracking: **SlopCodeBench** (arXiv:2603.24755) measures how agents *degrade over long-horizon iterative tasks* — directly relevant to an edge agent meant to run long sessions cheaply, and a good stress axis for your eval suite.

---

## 6. How the pieces compose for AutoCode

```
                         ANVIL (offline harness-evolution engine)
                         ════════════════════════════════════════
  AutoCode runtime ──▶ trajectories ──▶ [Experience obs.: distiller]  ◀── AHE pillar 2
   (frozen model,         + executable        │
    local-first)          outcome labels      ▼
                                        [Teacher: Generator/Reflector/Curator]  ◀── ACE
                                              │  produces playbook deltas + patch proposals
                                              ▼
                       [Component obs.: manifest] ── action space ──▶ candidate edits  ◀── AHE pillar 1
                              tools · middleware · memory · (prompts via GEPA) · (adapter via OPD)
                                              │   each edit carries a PREDICTION
                                              ▼
                       [Eval gate: own-session corpus + Terminal-Bench, executable oracles]  ◀── file 08
                                              │
                       [Decision obs.: verify prediction vs outcome]  ◀── AHE pillar 3
                                              │  pass → patch bundle ; fail → revert + log
                                              ▼
                       eval-passing patch bundle ──▶ canary ──▶ AutoCode runtime
```

Every box maps to an existing repo asset (file 02) or a named 2026 method. Nothing here is speculative; it's assembly. The build order (file 09) is: eval corpus → teacher → component manifest → self-maintenance loop → copycat channels → (optional) distillation.

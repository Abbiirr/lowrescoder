# 01 — Validation & Corrections of `deep-research-report__18_.md`

This file does the thing you asked for: validate the source report, and **correct it with facts where it is wrong.** The report is directionally sound and well-read on the classical literature (distillation, Self-Refine, Reflexion, Constitutional AI, process supervision, DSPy/MCP). But it was written without seeing the repo, without the 2026 harness-engineering results, and without your locked invariants. Eight corrections follow, ordered by how much they change the plan.

---

## What the report gets right (keep these)

- **"Authorized capability transfer, not unconstrained copying."** Correct and important. Black-box model extraction is a real risk and a real ToS problem. Keep the authorization-registry framing.
- **The thing that self-maintains is the *whole stack*, not just the model.** Exactly right, and it's the heart of why this is feasible on consumer hardware. The 2026 literature now calls this the *harness*.
- **Three-loop structure (execution / learning / governance).** Sound. It maps cleanly onto runtime / Anvil / eval-gate.
- **Patch bundles with provenance (W3C PROV).** Keep it. The self-maintenance engine (file 07) extends this with a prediction contract.
- **Escalation ladder: cheapest sufficient intervention first.** This is *already an AutoCode invariant* ("LLM as last resort"). The report independently arrived at your north star. Good sign.
- **LLM-as-judge has position/verbosity bias; randomize order, rotate judges, validate against humans.** Correct — but for coding it's a secondary signal (see Correction 4).

---

## Correction 1 — "Edge" means edge computing, not the Microsoft Edge browser

**Severity: Critical (category error).**

The report spends an entire section (the "stable runtime vs experimental browser-native features" paragraph) on Microsoft Edge's Prompt API being "developer preview in Canary," WebNN being "preview-only on Windows," the "Aion-1.0-Instruct preview model," and recommending "ONNX Runtime, Windows Foundry/Windows ML, OpenVINO."

None of this applies. AutoCode is a **terminal coding agent**: a Rust TUI (crossterm + ratatui + tokio) talking JSON-RPC over stdin/stdout to a Python backend (agent loop, tools, LLM providers). "Edge-native" in `north-star.md` means *local inference on consumer hardware (8 GB VRAM / 16 GB RAM)* — your RX 480 + RTX 4060 Ti boxes running models through the LLM Gateway — **not** a web browser's on-device AI stack.

**Action:** delete the entire Edge-browser line of analysis. It imports the wrong runtime, the wrong constraints, and the wrong roadmap. There is no WebNN, no Prompt API, no browser sandbox anywhere in this project.

---

## Correction 2 — For coding agents, gains come from tools / middleware / memory, NOT prompts

**Severity: Critical (re-prioritization). This is the most important correction in the set.**

The report's centre of gravity is prompt-and-program optimization (DSPy signatures, "optimize signatures, routing, few-shot examples") plus distillation. It treats prompt/program tuning as the primary lever.

The strongest 2026 evidence says otherwise. **Agentic Harness Engineering** (arXiv:2604.25850) froze the model and evolved seven harness components, then ablated which components produced the gains:

> *"Ablations localize the gain to tools, middleware, and long-term memory rather than the system prompt, suggesting factual harness structure transfers while prose-level strategy does not."*

Ten iterations took Terminal-Bench 2 pass@1 from **69.7% → 77.0%**, beating the human-designed Codex-CLI harness (71.9%) and the self-evolving baselines ACE and TF-GRPO. The frozen harness then transferred to SWE-bench-Verified at **12% fewer tokens**, and gave **+5.1 to +10.1pp** cross-family gains on three *other* model families — evidence the evolved artifacts encode general engineering structure, not prompt-level mimicry.

**Implication for your escalation ladder (re-ordered):**

| Tier | Intervention | Evidence-backed value | Cost on your hardware |
|------|--------------|----------------------|----------------------|
| 1 | **Deterministic tool / rule synthesis** (new L1/L2 capability, AST patterns, retrieval heuristics) | Highest (AHE: tools) | Cheap |
| 2 | **Middleware evolution** (context compaction, failover, Ralph-style continuation) | High (AHE: middleware) | Cheap |
| 3 | **Long-term memory / playbook** (ACE generate–reflect–curate) | High (AHE: memory) | Cheap |
| 4 | **Prompt / program optimization** (GEPA, 35× fewer rollouts) | Lower for coding (AHE: *not* prompts) but cheap to try | Cheap |
| 5 | **On-policy distillation into the local model** | Situational; last resort | Expensive + hardware-constrained |

The report effectively inverts tiers 1–4. GEPA is still worth having (it's cheap and the rollout efficiency is real), but it is **tier 4, not the headline.** Spend your first effort on tool and middleware synthesis. This also happens to be the most *deterministic-first* path, so it aligns with your north star better than prompt tuning does.

---

## Correction 3 — Trace-level "copycat" from closed harnesses is infeasible

**Severity: High (the copycat design as written cannot be built).**

The report's copycat "behavioral copy" layer says: *"the copycat pipeline records authorized traces from the target harness: task input, retrieved context, tool calls, observations, intermediate decisions, final answer…"*

You cannot get those traces from Claude Code, Codex, Cursor, or any closed agent. They do not expose internal reasoning, tool schemas, retrieval steps, or intermediate decisions. The "authorized traces from the target harness" premise assumes white-box access you will never have for the interesting targets.

**The three channels that are actually feasible** (full detail in file 05):

1. **Outcome distillation** — drive a strong model/harness via API on a task, capture only what's observable: the **final diff / patch / file set**. Use it as an eval *oracle* or a distillation *target*. This is legal-sensitive (see file 10) and observable-only.
2. **Structural imitation** — read the *public* structure of strong harnesses and port the structure, not the traces. **You already have the corpus**: `research-components/` mirrors `claude-code-sourcemap`, `pi-mono`, `opencode`, `openai-codex`, `aider`, `goose`, `open-swe`. PLAN.md §1g already extracted Claude Code's `Logo.tsx`, `Spinner.tsx`, `PromptInput.tsx`. That is structural copycat, and it's the channel with the least legal risk and the most signal per AHE's "structure transfers" finding.
3. **Self-distillation** — run *your own* AutoCode loop with a strong model wired in as L4, log the trajectories your harness actually produces, and distill those down to the local model. This is **on-policy** (the student's own states) and is the 2026 best practice (see Correction 6).

Reframe copycat as **"capability acquisition through observable outcomes + public structure + self-generated on-policy traces."** Drop "record the target's internal traces" entirely.

---

## Correction 4 — The teacher signal for *coding* should be execution-grounded, not judge-first

**Severity: High (changes the teacher's primary signal).**

The report's evaluation section leans on LLM-as-judge with bias management, inherited from the general-assistant literature (it cites GAIA, HELM, MT-Bench-style pairwise judging). That's the right tool when there is no ground truth.

Coding has ground truth. AutoCode can **run the code**: compile, apply the diff, run the test suite, run the linter, run the type-checker. AutoCode *already ships verification profiles* (formatter / lint / typecheck / targeted-test) and hooks (`PreToolUse`, `PostToolUse`, `Stop`, `StopFailure`) per PLAN.md §1f.3 / §1f.6. Terminal-Bench tasks each ship a **verification test suite + oracle solution** by construction.

So the teacher's primary signal is the **executable verdict**, not a judge's preference. The judge is demoted to a *secondary* role: rating explanation quality, code style, and commit-message clarity — things with no test. Order them:

1. Diff applies cleanly? (deterministic)
2. Build passes? (deterministic)
3. Tests pass / regression introduced? (deterministic)
4. Lint + types clean? (deterministic)
5. *Then* judge: is the reasoning sound, the style idiomatic, the explanation correct? (LLM-judge, with the report's bias controls)

This makes your teacher far more reliable than the general-assistant case the report was generalizing from, and it makes reward-hacking much harder (you can't fake a passing test suite as easily as you can fake a judge).

---

## Correction 5 — The report's framing silently violates your locked invariants

**Severity: High (governance / north-star conflict).**

`north-star.md` locks: "No cloud dependency by default," "Not dependent on frontier models" (no 70B+, no 100K-context prereqs), and explicitly "Not parity-only with cloud assistants… features that only improve surface-level similarity to Claude Code / Copilot / Cursor are not the goal."

A naive reading of the report — "use a frontier cloud teacher to continuously improve the agent" — breaks all three. The report could not see this because it never saw your north star.

**The reconciliation (load-bearing):** split **offline improvement** from **online runtime**.

- **Anvil (offline, opt-in):** may call a cloud teacher, may observe authorized targets, may run distillation. Runs on *your* schedule, not the user's hot path.
- **Runtime (online, default):** unchanged. Local-first, deterministic-first, cloud-free. It only ever consumes **eval-passing artifacts** Anvil produces.

Under this split, the cloud teacher is a *build-time dependency of the development process*, exactly like a compiler or a test framework — not a runtime dependency of the product. The invariants hold. Make this split the first sentence of any design doc, or a reviewer following `north-star.md` will (correctly) flag the whole program as `Critical` and stop it.

There's a second, subtler alignment win: AHE's "evolve the harness, freeze the model" is *more* invariant-compliant than the report's distillation focus, because it never needs a bigger model or a training run to improve. The frozen-model path **is** the edge-native path.

---

## Correction 6 — On-policy ≫ off-policy distillation, but it's the last resort and your hardware fights it

**Severity: Medium (updates the distillation tier; tempers expectations).**

The report's distillation discussion is 2015–2023 vintage: Hinton distillation, Distilling Step-by-Step, LoRA/QLoRA. All still true, but the 2025–2026 state of the art is **on-policy distillation (OPD)**:

- **Thinking Machines Lab, "On-Policy Distillation" (Oct 2025):** the student generates its *own* rollouts; the teacher scores the states the student actually visits. This corrects **exposure bias** — the core failure of off-policy SeqKD, where the student only ever sees teacher-frequented states and is blind to its own failure modes.
- **SOD, "Step-wise On-policy Distillation for Small Language Model Agents" (arXiv:2605.07725):** directly relevant warning — in *small* tool-using agents, **a single wrong tool call cascades and corrupts the teacher's token-level supervision downstream.** SOD reweights distillation strength per step by student–teacher divergence. A 0.6B student reached 26.13% on AIME 2025. If you ever do distillation for AutoCode's 1.5B/8B local models, you need step-wise reweighting or the tool-call cascade will poison training.
- **Thesis support:** NVIDIA, "Small Language Models are the Future of Agentic AI" (arXiv:2506.02153) — your entire premise has a name and a citation now.

**But two facts keep distillation at the *top* of the escalation ladder (i.e., last):**

1. AHE says weight changes are *lower-value-per-unit-effort* than harness changes for coding agents.
2. **Your hardware.** The RX 480 (Polaris/GCN4) was dropped from ROCm years ago; it is a Vulkan *inference* card and is effectively unusable for training. The RTX 4060 Ti (8–16 GB) is the only trainable device, and QLoRA on a 1.5B is already tight there; OPD that needs teacher logits is white-box-only (impossible for closed teachers), and black-box OPD variants like GAD need a *separate discriminator network of comparable size* — out of budget on 8–16 GB. So realistic distillation for you is: QLoRA SFT or black-box rubric-OPD (ROPD-style) on the 1.5B, on the 4060 Ti, only after tiers 1–4 are exhausted.

Net: keep distillation in the design, gate it behind everything else, and don't let it be the headline the report makes it.

---

## Correction 7 — The eval set is the real hard problem; the report under-specifies it

**Severity: High (this is where self-improving systems actually fail).**

The report says "use task-specific evals + pairwise preference; GAIA / SWE-bench / HELM." That's a menu, not a plan, and the named benchmarks are generic.

For a *personal edge coding agent*, the highest-value eval corpus is **your own session history**, which AutoCode already logs (session storage, append-only transcripts, checkpoint store). Each past task, paired with its executable verification, is a candidate eval case grounded in the code you actually write. This is AHE's "experience observability" corpus, and it's the gradient the whole loop climbs. The external yardstick is **Terminal-Bench** (89 human-verified Docker tasks, each with a test suite + oracle) — and it's *already on your roadmap* as PLAN.md Section 3.

Without a growing, repo-grounded eval set with **executable oracles**, the self-maintenance loop has no reliable gradient and *will* reward-hack toward whatever the judge likes. File 08 builds this corpus first, before any evolution runs.

---

## Correction 8 — "Decision observability" is the missing discipline that makes autonomy safe

**Severity: High (upgrades patch-and-gate from weak to sound).**

The report's self-maintenance is patch → eval → ship-if-passing → canary → rollback. Correct shape, but the gate is weak: passing an eval set you also control is the classic setup for silent overfitting and reward-hacking.

AHE's third pillar — **decision observability** — is the upgrade: *every edit ships with a self-declared, quantified prediction of what it will improve, which is then verified against the next round's task-level outcome.* Together with component observability (every edit is a revertible file change) and experience observability (trajectories distilled into consumable evidence), this "turns every edit into a falsifiable contract, so harness evolution proceeds autonomously without collapsing into trial-and-error."

Two things this buys you that bare patch-and-gate does not:

- **Calibration signal on the evolving agent's own judgment.** When predictions systematically miss, that's a measurable sign the loop has gone off the rails — independent of the eval scores.
- **A natural revert trigger.** An edit whose prediction fails is reverted *and the failed prediction is logged as training signal*, so the meta-agent learns what it's bad at predicting.

Adopt the falsifiable-contract discipline as the core of the self-maintenance engine (file 07).

---

## Summary table

| # | Correction | Effect on the plan |
|---|------------|--------------------|
| 1 | "Edge" ≠ Microsoft Edge browser | Delete the entire browser-runtime section |
| 2 | Gains come from tools/middleware/memory, not prompts | Re-order escalation ladder; demote GEPA to tier 4 |
| 3 | Trace-scraping closed harnesses is infeasible | Reframe copycat to 3 observable channels |
| 4 | Coding teacher signal is execution-grounded | Demote LLM-judge to secondary |
| 5 | Report silently breaks your invariants | Split offline Anvil from local runtime, up front |
| 6 | On-policy ≫ off-policy, but last resort + hardware-bound | Keep distillation; gate it behind tiers 1–4 |
| 7 | Eval set is the real problem; it's under-specified | Build the own-session corpus first |
| 8 | Add decision observability / falsifiable contracts | Upgrade patch-and-gate |

These eight are the difference between the report's plausible-but-generic write-up and a plan that can actually be built on `lowrescoder` and survive its own north star.

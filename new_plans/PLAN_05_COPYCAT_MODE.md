# PLAN_05 — The "AI Copycat Mode" Brief

> Plan 5 of 5. **Copycat mode is the input side of the offline self-improvement engine.** Where PLAN_04 (teacher mode) is the *root-cause analyst* that turns failure into teaching packets, copycat mode is the *capability acquisition* subsystem that decides **what** the agent can imitate and **how** — always through channels that are observable, authorization-gated, and structurally clean. It is the working codename **Anvil's** inbound leg. The runtime is unchanged. The legal exposure is bounded. The structural gains (per the 2026 AHE ablation) come from tools, middleware, and memory — which copycat is the primary lever for.

**Companion plans in this set**

- `PLAN_01_HARNESS_IDE.md` — the operator-facing IDE that copycat improves.
- `PLAN_02_VIDEO_AGENT.md` — separate product; out of scope here.
- `PLAN_03_FULL_CODEX_IDE.md` — the full consumer IDE; embeds PLAN_01.
- `PLAN_04_TEACHER_MODE.md` — the root-cause analyst that consumes copycat's outputs.
- `PLAN_05_COPYCAT_MODE.md` (this file) — capability acquisition through observable structure, verified outcomes, and on-policy self-traces.

**Existing corpus in `new_plans/` that this plan composes with (read in this order)**

| File | What it contributes |
|---|---|
| `harness_copy_teacher/00_INDEX.md` | The one-paragraph reframe (Agentic Harness Engineering) and naming conventions. |
| `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md` | The 8 corrections; copycat is **Correction 3** ("trace-level copycat from closed harnesses is infeasible — use the 3 observable channels"). |
| `harness_copy_teacher/02_REPO_STATE_AND_GAP_ANALYSIS.md` | What AutoCode already has; the gap list `G1`–`G9`; the substrate AHE needs. |
| `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` | The 2026 evidence base; AHE's "structure transfers" finding is the basis for Channel A. |
| `harness_copy_teacher/04_ARCHITECTURE.md` | The runtime-vs-Anvil split, the manifest schema, the prediction contract, the escalation ladder. |
| `harness_copy_teacher/05_COPYCAT_MODE.md` | The original copycat spec; this plan re-organizes and condenses it. |
| `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` | The loop that promotes copycat's outputs. |
| `harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md` | The eval flywheel that gates copycat. |
| `harness_copy_teacher/09_BUILD_ROADMAP.md` | Phase 4 is the copycat phase. |
| `harness_copy_teacher/10_RISKS_OPEN_QUESTIONS_DECISIONS.md` | The honest risk register; §10.2 (ToS) is load-bearing for copycat. |
| `01-trust-domains.md` | The 5-trust-domain model. |
| `PLAN_01_HARNESS_IDE.md` | The IDE whose tool surface copycat extends. |
| `PLAN_04_TEACHER_MODE.md` | The teacher that turns copycat's outputs into teaching packets. |

This plan is structured as: thesis → the authorization registry → the three channels (structural, outcome, self-distill) → the build order → phase plan → composition. Where the existing corpus already nails a point, this plan summarizes and links.

---

## 0. Thesis — what this is, what it isn't

### 0.1 What it is

**Copycat mode is capability acquisition done right.** It replaces the source report's "record the target harness's internal traces" (which is infeasible for closed agents) with **three observable channels**, ordered by feasibility and legal safety:

1. **Channel A — Structural imitation.** Read the *public* structure of strong harnesses and port the *structure*, not the code or traces. Per AHE's ablation, *factual harness structure transfers*. This is the channel most likely to actually help, and the one with the least legal risk.
2. **Channel B — Outcome distillation.** Drive a strong model on a task, capture only the **observable final artifact** (the diff / patch / file set), and use it two ways: (a) as an **eval oracle** (always safe), and (b) as a **distillation target** (only if `reuse_scope: weights` and the provider's ToS permits).
3. **Channel C — Self-distillation.** Run *your own* AutoCode loop with a strong model wired in as the L4 brain, log the trajectories *your harness* produces, and use them to improve the local model and harness. The traces are *yours*. **On-policy** (the student's own states), which is the 2026 best practice (Thinking Machines OPD).

All three live in **Anvil** (the offline harness-evolution engine). None touch the runtime. All are authorization-gated via the registry (§1). All are eval-gated via the prediction contract + held-out eval + edge-guard regression check before any artifact crosses back into the runtime.

### 0.2 What it isn't

- It is **not** a scraper for closed-agent internal traces. Claude Code, Codex, Cursor, etc. do not expose internal reasoning, tool schemas, retrieval steps, or intermediate decisions. The source report's premise assumed white-box access you will never have for the interesting targets.
- It is **not** vendoring third-party source. Structural imitation produces *new AutoCode components evaluated on the oracle*, never vendored code. License-clean by construction.
- It is **not** training on frontier outputs without an explicit, recorded per-provider ToS check. The registry's `reuse_scope` field is the hard gate; `weights` defaults off.
- It is **not** a runtime feature. Copycat runs in Anvil (offline, on the user's schedule), and only its **eval-passing re-implementations** reach the runtime. The runtime never depends on copycat.
- It is **not** the headline lever. Per AHE's ablation, gains come from tools, middleware, and memory. Copycat is the *primary* lever for tier-1 (new tools) and tier-2 (middleware) acquisitions. Tier 3 (playbook) is the teacher's home; tier 4 (prompt) is GEPA's; tier 5 (weights) is the distillation lane.

### 0.3 The load-bearing design constraints (in priority order)

1. **The registry is the hard gate.** No channel runs against a target not listed in `anvil/copycat/registry.yaml`. The `reuse_scope` field decides what is allowed; `structure_only` forbids shipping the target's code; `outcomes` permits using produced diffs as eval/distill targets; `weights` is the most ToS-sensitive and defaults off.
2. **Verification is the only thing that decides transfer.** A target's "verified outcome" is one that passes the executable oracle (build + tests). Unverified frontier diffs are *not* stored; storing them pollutes the corpus.
3. **Structure transfers; traces do not.** AHE's ablation result is the load-bearing finding. Channel A is the highest-leverage channel because of this.
4. **On-policy ≫ off-policy.** Channel C produces traces the student's harness actually visits. Off-policy distillation (importing foreign traces) would teach the small model to imitate states it never reaches. Self-distillation teaches it to handle *its own* situations.
5. **The model is frozen.** Channel B's *weight* branch and Channel C's *weight* branch are tier-5 capabilities, gated by per-provider ToS clearance, hardware constraints, and prediction contracts that beat tiers 1–4 on the same cluster.
6. **Edge-cost guards are mandatory.** A capability acquired via copycat that raises `pass_at_1` by escalating more to L4 has *regressed* the product. Every prediction contract's `no_regression_on` (per `04_ARCHITECTURE.md` §4.5) always includes `layer_distribution.L4`, latency p50, and `tokens_per_task`.

### 0.4 How this inherits from existing corpus

**From `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md` Correction 3:** the source report's "record the target's internal traces" premise is replaced by the three observable channels. This is the most consequential correction in the copycat design.

**From `harness_copy_teacher/05_COPYCAT_MODE.md`:** the original copycat spec. This plan re-organizes it into the `PLAN_*` format and preserves the three channels, the authorization registry, the channel comparison table, and the build order.

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §1 (AHE ablation):** "factual harness structure transfers while prose-level strategy does not" — the empirical case for Channel A.

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §4 (On-Policy Distillation):** the Thinking Machines OPD finding (student generates own rollouts, teacher scores student-visited states) — the empirical case for Channel C.

**From `harness_copy_teacher/02_REPO_STATE_AND_GAP_ANALYSIS.md` §"The decisive asset #2":** the `research-components/` corpus already mirrors claude-code-sourcemap, pi-mono, opencode, openai-codex, aider, goose, open-swe. PLAN §1g has already extracted Claude Code's `Logo.tsx`, `Spinner.tsx`, `PromptInput.tsx`, `REPL.tsx`. Channel A's structural census has a working precedent.

**From `harness_copy_teacher/10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.2 (ToS):** the legal reality for Channel B's weight branch. The risk gradient is structure → outcomes-as-eval → outcomes-as-training-data. The registry's `reuse_scope` and the per-provider ToS check are the structural enforcement.

**From `01-trust-domains.md`:** copycat is **analysis + planning**. It sees observable outcomes (analysis) and proposes clean-room capability proposals (planning). It never touches raw media or executes render steps. The patch bundle's `git apply` is the only thing that crosses into the runtime, and only after the prediction contract + eval gate + canary pass.

**From `PLAN_01_HARNESS_IDE.md`:** the IDE's tool surface (the manifest entries) is what copycat's structural proposals extend. A `tool.missing_capability` packet points at a manifest entry like `tool.callgraph.impl` and proposes a clean-room implementation; the manifest's `prediction_metrics` field is the allowed claim space for the contract.

**From `PLAN_04_TEACHER_MODE.md`:** the teacher is the consumer of copycat's outputs. Channel A's capability proposals and Channel C's harness-self-distillation deltas both become `harness_fix` candidates in the teaching packet schema (`06_TEACHER_MODE.md` §6.0).

---

## 1. The authorization registry (the hard gate)

Before any channel runs, the target must be in `anvil/copycat/registry.yaml`. The source report was right about this; it's the difference between "internal capability transfer" and "model extraction."

```yaml
targets:
  - id: claude-code
    channel: [structural]               # which channels are permitted for this target
    source: research-components/claude-code-sourcemap   # local mirror only
    license: "review-before-use"        # you must confirm the mirror's license permits study
    reuse_scope: structure_only         # structure_only | outcomes | weights
    notes: "Public source map. Structural study only. Do NOT ship verbatim code."

  - id: gateway-thinking-alias
    channel: [outcome, self_distill]
    source: "http://localhost:4000/v1"  # your own gateway; a strong model as teacher
    license: "per-provider-ToS"         # SEE FILE 10 — distillation clauses vary by provider
    reuse_scope: outcomes
    rate_limit: { runs_per_day: 200 }
```

### 1.1 The four `reuse_scope` values

| Scope | What is allowed | Risk | Default? |
|---|---|---|---|
| `structure_only` | Read public source; port the *idea*, not the code | Low | **Yes** (default for any new target) |
| `outcomes` | Use produced diffs as eval *oracles* (compare-against-reference) | Low–medium | Yes (with rate limit) |
| `weights` | Use produced outputs as **training data** for distillation | **High** | **No** — explicit per-provider ToS check required |
| `deny` | Nothing | — | Reserved for targets the user has decided not to study |

The risk gradient is real. Several frontier providers' ToS restrict using their model outputs to *train or improve competing models* — the clause most likely to apply to `weights`. `structure_only` and `outcomes-as-eval` are far safer. Default to eval use; gate training use behind an explicit, recorded per-provider ToS read in the registry.

### 1.2 The four `channel` values

| Channel | What it is | Source of truth |
|---|---|---|
| `structural` | Channel A — read public structure | The target's public source map / docs |
| `outcome` | Channel B — drive the target, capture diffs | The target's API / gateway |
| `self_distill` | Channel C — drive *your own* harness with the target as L4 | Your own trajectory recorder |
| `deny` | Nothing | — |

A target may have multiple channels enabled (e.g., a target with `channel: [structural, outcome]` permits both Channel A and Channel B against it).

### 1.3 The enforcement

The Anvil CLI refuses to run any channel against a target not in the registry, and refuses to run a channel not listed for that target. A `weights` channel is refused unless `reuse_scope: weights` is set *and* a `per-provider-ToS` license check is recorded in the registry. This is an assertion that fails the run, not a soft warning.

### 1.4 How this inherits from existing corpus

**From `harness_copy_teacher/05_COPYCAT_MODE.md` §5.0:** the registry shape and the `reuse_scope` semantics. Preserved verbatim.

**From `harness_copy_teacher/10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.2:** the legal reality, the risk gradient, and the mitigation (default to `structure_only` + `outcomes-as-eval`, require explicit per-provider ToS read for `weights`).

**From `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` §7.2:** the "no self-editing of the gate" rule applies symmetrically — the registry is **outside Anvil's action space**. The loop must never be able to weaken its own authorization gates. This is the second-most-important guardrail after the eval-gate lockout.

---

## 2. Channel A — Structural imitation (lowest risk, highest leverage)

### 2.1 What it is

**Read the public structure of strong harnesses and port the structure, not the code or traces.** Per AHE's ablation (*"factual harness structure transfers"*), this is the channel most likely to actually help, and the one with the least legal risk.

### 2.2 Why the substrate already exists

`research-components/` already mirrors `claude-code-sourcemap`, `pi-mono`, `opencode`, `openai-codex`, `aider`, `goose`, `open-swe`. The existing AutoCode PLAN §1g has already extracted Claude Code's `Logo.tsx`, `Spinner.tsx`, `PromptInput.tsx`, `REPL.tsx`. There is a feature-audit checklist (`docs/plan/research-components-feature-checklist.md`) and a 7-TUI capture probe.

This is **structural copycat infrastructure that already works**. The TUI-comparison harness (Tracks 1–4 in PLAN §1g) is a working template for the kind of capture/compare/gate pipeline Anvil needs — just pointed at *behavior/outcomes* instead of *pixels*. Channel A reuses the corpus and the capture pattern.

### 2.3 The pipeline

The pipeline extends the existing TUI-comparison harness, repointed from pixels to structure:

1. **Component census.** For each reference harness in the registry (Channel `structural` enabled), enumerate its analog of the seven AHE component kinds (system prompts, tool descriptions, tool implementations, middleware, skills, sub-agents, long-term memory). Write to `anvil/copycat/census/<target>.yaml`.
2. **Gap diff.** Diff each reference's component set against AutoCode's `manifest.yaml`. Output: "opencode has a `/sandbox` mode switch and a 9-op LSP surface AutoCode lacks; codex has symmetric `/resume <id>` + `fork`." PLAN §1g already lists several of these.
3. **Capability proposal, not code copy.** For each gap, Anvil proposes a *clean-room* component for AutoCode that achieves the same *capability*, expressed against the manifest, with a prediction contract. **It must not paste the reference's source.** The verifier + eval gate decide if the re-implementation actually helps.

### 2.4 Concrete first targets (already surfaced in PLAN §1g)

- **Middleware: the Ralph loop continuation primitive** (per `03_HARNESS_ENGINEERING_SOTA.md` §0). A hook intercepts the model's attempt to *exit*, and re-injects the original goal into a *fresh* context window, forcing continuation. Turns a single-session agent into a multi-session one. Port the *idea*; do not vendor the reference's source.
- **Tool/middleware: opencode's `/sandbox` mode switch + broader LSP op surface.** A `/sandbox` mode toggle in the operator's REPL plus a 9-op LSP bridge (currently AutoCode has fewer) is a tier-1 capability acquisition.
- **Subagent pattern: ForgeCode's planner/executor/researcher split** (Muse/Forge/Sage, `03_HARNESS_ENGINEERING_SOTA.md` §0). Hit 81.8% on TB2 with three-agent design. Adopt *only if* it survives the eval gate *and* doesn't blow the edge cost budget (3 agents = 3× context; watch `layer_distribution`).

### 2.5 The hard rule

**Structural imitation produces new AutoCode components evaluated on the oracle, never vendored third-party code.** This keeps you clear of license problems and, per AHE, is where the real transfer is anyway. The `census/<target>.yaml` records what was studied; the `decision.md` per patch bundle records what was inspired; the diff itself is clean-room.

### 2.6 How this inherits from existing corpus

**From `harness_copy_teacher/05_COPYCAT_MODE.md` §5.1:** the pipeline (component census → gap diff → capability proposal) and the hard rule. Preserved verbatim.

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §0 (the Ralph loop):** the canonical example of "the kind of primitive you'd never derive from 'just use a smarter model.'" The first concrete target.

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §1 (AHE ablation):** the empirical case — "factual harness structure transfers." This is the load-bearing finding for Channel A's priority over the other channels.

**From `PLAN_01_HARNESS_IDE.md` §2.2 (LSP tool registry):** the gap-diff is most likely to flag missing LSP ops. The 9-op opencode surface is concrete; AutoCode's current surface is enumerated in PLAN_01 §2.2.3.

---

## 3. Channel B — Outcome distillation (medium risk, needs ToS check)

### 3.1 What it is

**Drive a strong model (via the gateway's `thinking` / `big` alias, or a paid frontier API) on a task, capture only the observable final artifact** — the diff / patch / file set — and use it two ways:

1. **As an eval oracle.** For a task with no shipped test, the strong model's accepted solution becomes a *reference* the verifier can diff against (weak oracle; use sparingly, prefer executable tests).
2. **As a distillation target** (feeds tier 5, Phase 7). *Only if* `reuse_scope: weights` and the provider's ToS permits training on outputs.

### 3.2 The pipeline

```
task ──▶ strong model (authorized) ──▶ final diff ──▶ verifier(diff) ──▶ {label, tests}
                                                          │
                              keep only diffs that VERIFY (build + tests pass)
                                                          ▼
                              outcome-pairs corpus: (task, verified_diff)
```

### 3.3 The critical discipline

**Keep only verified outcomes.** An unverified frontier diff is just a confident guess; storing it pollutes the corpus. The executable verifier (per `04_ARCHITECTURE.md` §4.3) is what makes this channel sound — *you are not trusting the teacher, you are trusting the tests.*

The `outcome-pairs` corpus is the eval-oracle resource for tasks where the existing corpus has no test (a "weak oracle" case in `08_EVALUATION_AND_VERIFICATION.md` §8.1). The corpus is versioned (`corpus@v3`) so eval reports are comparable across time.

### 3.4 The two branches

| Branch | `reuse_scope` | Use | Risk |
|---|---|---|---|
| **Eval oracle** | `outcomes` | The strong model's verified diff becomes a *reference* the verifier diffs against for new harness runs | Low–medium (you are comparing, not training) |
| **Distillation target** | `weights` | The strong model's verified outputs become training data for the local model (Phase 7, QLoRA) | **High** (most likely to hit a no-compete-training clause) |

The eval-oracle branch is the right default. The distillation branch is gated by an explicit per-provider ToS check, recorded in the registry. The check is human-performed (the user reads the current ToS, records the date, records the clause summary); the Anvil CLI refuses to run the distillation branch if the check is missing or stale.

### 3.5 The legal reality (per `10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.2)

The risk gradient is real:

- `structure_only` (read public source maps, port the *idea*) — lowest; you're studying architecture, not copying weights or outputs.
- `outcomes-as-eval` (use a verified diff as a test reference) — low-medium; you're checking, not training.
- `outcomes-as-training-data` (QLoRA on frontier diffs) — highest; most likely to hit a no-compete-training clause.

**Mitigation:** the registry's `reuse_scope` (per §1.1) gates this per target. Default to `structure_only` + `outcomes-as-eval`, and require an explicit, recorded per-provider ToS read before any `weights` scope. When in doubt, prefer *self-distillation* (Channel C) and *open-weight* teachers (e.g., a large open model via the gateway) for any training, since their licenses are usually permissive.

### 3.6 How this inherits from existing corpus

**From `harness_copy_teacher/05_COPYCAT_MODE.md` §5.2:** the pipeline and the "keep only verified" discipline. Preserved verbatim.

**From `harness_copy_teacher/10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.2:** the legal reality, the risk gradient, and the mitigation. The "default to eval, gate training" rule is normative.

**From `harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md` §8.1:** the weak-oracle caution. The eval-oracle branch produces weak-oracle cases that must be weighted less in the promotion decision and never used to promote on weak-oracle gains alone.

---

## 4. Channel C — Self-distillation (lowest legal risk, best technical fit)

### 4.1 What it is

**Run your own AutoCode loop with a strong model wired in as the L4 brain, log the trajectories *your harness* produces, and use them to improve the local model and harness.** The traces are *yours* (your harness, your prompts, your tools) — no third-party trace problem, minimal ToS exposure.

### 4.2 Why it's the right technical fit

It is **on-policy** — the trajectories are over states *your harness actually visits* (per Thinking Machines OPD, `03_HARNESS_ENGINEERING_SOTA.md` §4). Off-policy distillation from a foreign harness would teach the small model to imitate states it never reaches. Self-distillation teaches it to handle *its own* situations better.

This is also the channel that maps onto the cheapest branch of the escalation ladder — the **harness self-distillation** left branch in the pipeline below. You don't need to retrain to benefit.

### 4.3 The pipeline

```
AutoCode harness + L4=strong-model ──▶ trajectories (per §4.2 of 04_ARCHITECTURE.md) ──▶ verifier ──▶ keep successes
                                                                                          │
   ┌──────────────────────────────────────────────────────────────────────────────────────┤
   ▼ harness-level (cheap, tiers 1–3)                                                      ▼ weight-level (tier 5, file 10)
   distiller → teacher → playbook/tool/middleware deltas                                   SOD-style step-wise OPD or QLoRA
   (improve the harness so the LOCAL model succeeds                                         on the 1.5B (4060 Ti), gated last
    on what the STRONG model just showed works)
```

### 4.4 The cheap left branch is the point

You don't need to retrain to benefit. When the strong-L4 run succeeds on a task the local-L4 run failed, the **difference in their trajectories** tells you what harness change would let the local model succeed too — a new tool, a better retrieval step, a playbook entry. That's harness self-distillation, fully on consumer hardware, no training.

The teacher (PLAN_04) is the consumer of the trajectory diff. The teacher's `harness_fix` candidate says: "the strong model used the call-graph tool at step 7; the local model escalated to L4 instead; the gap is a missing L1 tool." The teacher emits a `harness_fix` target = `tool.callgraph.impl`, the loop applies it, the eval gate decides if it actually helps. The right branch (weight training) is the last resort.

### 4.5 The two branches

| Branch | Mechanism | Cost | When |
|---|---|---|---|
| **Harness self-distillation (cheap)** | Diff strong-L4 vs local-L4 trajectories; teacher emits `harness_fix` candidates for tier-1/2/3 manifest entries | API calls only | Always — first |
| **Weight self-distillation (expensive)** | QLoRA / step-wise OPD on **your own** verified outcomes, on the 1.5B local model, on the RTX 4060 Ti | API calls + training time | Only when harness changes provably can't close the gap |

The cheap branch is *the* primary path for Channel C. The weight branch is the same as Channel B's weight branch, just with the trajectory source being your own harness instead of a frontier one — which is a much cleaner ToS position.

### 4.6 How this inherits from existing corpus

**From `harness_copy_teacher/05_COPYCAT_MODE.md` §5.3:** the pipeline and the cheap-left-branch framing. Preserved verbatim.

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §4 (On-Policy Distillation):** the Thinking Machines OPD finding — student generates own rollouts, teacher scores student-visited states. The empirical basis for Channel C's "best technical fit" claim.

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §4 (SOD):** the small-agent caveat — a wrong tool call cascades and corrupts teacher supervision. Step-wise divergence reweighting is required for the weight branch. The 4060 Ti is the only trainer; the RX 480 is inference-only (ROCm dropped Polaris).

**From `PLAN_04_TEACHER_MODE.md` §5.1 (online path):** the trajectory diff between strong-L4 and local-L4 is the input to the teacher's `harness_fix` candidate. The teacher is the *consumer* of Channel C's output.

---

## 5. Channel comparison

| | A — Structural | B — Outcome (eval) | B — Outcome (weights) | C — Self-distill (harness) | C — Self-distill (weights) |
|---|---------------|--------------------|-----------------------|---------------------------|---------------------------|
| **Observability needed** | Public source (have it) | API output only | API output only | Your own traces | Your own traces |
| **Legal / ToS risk** | Low (clean-room) | Low–medium | **High** | Low | Low–medium |
| **On-policy?** | n/a (structure) | Partial | Partial | **Yes** | **Yes** |
| **Hardware cost** | None | API calls | API calls + training (4060 Ti) | API calls | API calls + training (4060 Ti) |
| **AHE-evidence value** | **High** (structure transfers) | Medium | Medium | High (harness branch) | High |
| **Build first?** | **Yes** | Second | **Last** | Second | **Last** |

### 5.1 Build order

1. **Channel A first** — the corpus and the precedent already exist; lowest risk; highest evidence value; produces tier-1 (new tool) and tier-2 (middleware) candidates immediately.
2. **Channel C-cheap (harness branch) second** — reuses the trajectory recorder (Phase 1 of `09_BUILD_ROADMAP.md`); produces tier-1/2/3 candidates via the teacher.
3. **Channel B-eval third** — produces weak-oracle eval cases for the corpus; safe by default; widens the eval surface.
4. **Channel B-weights and Channel C-weights last** — gated by Phase 7's hardware and ToS gates; only if cheaper tiers provably can't close the gap.

### 5.2 What copycat mode is explicitly NOT

- Not scraping Claude Code / Codex internal traces (impossible).
- Not vendoring third-party source into AutoCode (license risk; structure-port is better anyway).
- Not training on frontier outputs without a recorded per-provider ToS check.
- Not a runtime feature. Copycat runs in Anvil, offline, and only its eval-passing *re-implementations* reach the runtime.

The reframed copycat is, in one line: **acquire capability from what you can legitimately observe — public structure, verified outcomes, and your own on-policy traces — and let the executable oracle decide what actually transfers.**

### 5.3 How this inherits from existing corpus

**From `harness_copy_teacher/05_COPYCAT_MODE.md` §5.4 + §5.5:** the comparison table and the "explicitly NOT" list. Preserved with the build order made explicit.

**From `harness_copy_teacher/09_BUILD_ROADMAP.md` Phase 4:** "Copycat channels A + C-cheap" is the phase that ships these channels. Phase 7 (optional, gated) is where the weight branches live.

---

## 6. The manual MVP — the Anvil copycat CLI

Strip everything autonomous. The **manual MVP** is a small set of commands, each gated by the registry:

```
$ autocode anvil copycat census claude-code     # writes anvil/copycat/census/claude-code.yaml
$ autocode anvil copycat gap-diff claude-code   # diffs against manifest.yaml; prints gap list
$ autocode anvil copycat propose claude-code callgraph
                                                # drafts a clean-room capability proposal,
                                                # wraps in a prediction contract,
                                                # writes anvil/patch_bundles/pb_001/
$ autocode anvil gate pb_001                    # applies to scratch worktree, runs eval, scores prediction
$ # read decision.md + prediction_score.json, then:
$ autocode anvil promote pb_001                 # git apply on runtime + log
```

**What you do, what Anvil does, at each step:**

| Step | You do | Anvil does |
|------|--------|------------|
| `census` | Pick a target from the registry | Walk the target's public source / mirror; emit the component census YAML |
| `gap-diff` | Read the gap list | Diff against `manifest.yaml`; print the gap list with `reuse_scope` and risk flags |
| `propose` | Pick a gap; pick a tier (1–4) | Teacher (or copycat-specific proposal generator) drafts a clean-room capability with a prediction contract |
| `gate` | Read the prediction contract | Apply to scratch worktree, run eval suite, write `eval_report.json` + `prediction_score.json` |
| `promote` | Read `decision.md` and the score; approve | `git apply diff.patch`; `git revert` always available |

**The online-only teacher (Phase 2 of the roadmap, PLAN_04 §7) ships even sooner for the *harness-self-distillation* branch (Channel C-cheap)** — it needs only the trajectory recorder (Phase 1) and the verifier, not the full manifest or the loop. The output is a `playbook_delta` per trajectory where the local model failed and the strong model succeeded, reviewed by the operator, approved and loaded into the durable-memory plane.

### 6.1 Why manual-first

For a single-user tool, the manual loop may be the right *permanent* state. The autonomy upgrade is a lot of machinery for one user, and it can quietly invalidate the program if the loop learns to satisfy the eval rather than the goal. The single biggest risk (per `10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.8) is *a self-modifying system that controls its own evaluation*. Manual-first means the operator is the gate, not the loop; autonomy is an opt-in upgrade, not the headline.

### 6.2 How this inherits from existing corpus

**From `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` §7.6:** the manual MVP CLI is the same shape; copycat adds the `census` and `gap-diff` steps specific to Channel A. Channels B and C reuse the propose/gate/promote pattern.

**From `harness_copy_teacher/09_BUILD_ROADMAP.md` Phase 4:** the exit gate for copycat is ≥ 1 structurally-inspired component and ≥ 1 self-distillation-derived harness fix promoted through the loop, each with met predictions and no edge-guard regression. The manual MVP is the path to that gate.

**From `autocode-station-requirements.md` §5.3:** every promotion is recorded in an immutable, attributed audit log. The `decision.md` per patch bundle is the human-readable artifact; the JSONL audit log is the machine artifact. Copycat is subject to the same discipline.

---

## 7. Phase plan

The sequencing rule from `harness_copy_teacher/09_BUILD_ROADMAP.md` applies: **build the measurement substrate before the evolution machinery, ship Channel A first, then Channel C-cheap, then B-eval, then the weight branches last.** This plan re-states the copycat-relevant phases in the `PLAN_*` format. Full phase plan with all dependencies is in `09_BUILD_ROADMAP.md`.

### Phase 0 — Design lock + invariant reconciliation

**Goal:** get the offline/runtime split and the Anvil design into the repo's authority chain so the program is north-star-legal.

- Write `docs/research/anvil-design.md`: the runtime-vs-Anvil split as sentence one, citing `north-star.md`; the three pillars; the escalation ladder.
- Add an explicit north-star note: "Anvil is offline; the runtime remains cloud-free and frozen-model. Cloud teacher = build-time dependency, not runtime dependency."

**Build:** the design doc. **Exit:** the doc exists, references the invariants, and a reviewer following `north-star.md` would not flag it `Critical`. **Effort:** ~1 day.

### Phase 1 — Measurement substrate (the prerequisite for everything)

**Goal:** make AutoCode's behavior observable and verifiable. Gaps `G2`, `G3`, `G4`. No evolution yet.

- `G3` Verifier + fixture suite (per `04_ARCHITECTURE.md` §4.3).
- `G2` Trajectory recorder writing the §4.2.1 schema (extends existing session storage).
- `G4` Own-session corpus builder with frozen held-out split.
- Multi-objective metric + `eval_report.json` (per `08_EVALUATION_AND_VERIFICATION.md` §8.2–8.3).

**Build:** the verifier, recorder, corpus, metric. **Exit:** you can run `autocode anvil corpus build`, get ≥ ~50 replayable cases with marked oracle strength, run the current harness against the held-out split, and produce an `eval_report.json` with mean ± spread and a measured noise band. *Do not proceed past this gate.* **Effort:** ~2 weeks.

### Phase 2 — Teacher mode, online path (first user-visible value)

**Goal:** ship the teacher as a root-cause analyst that emits reversible playbook deltas. Gap `G6`, online half only. No autonomous editing, no training.

- Root-cause classifier over trajectories.
- Teaching-packet generator with the §2 signal hierarchy.
- ACE playbook (Generator/Reflector/Curator/Pruner) per-language.
- Runtime loads the playbook from the durable-memory plane.

**Build:** classifier, packet generator, ACE wiring, runtime loader. **Exit:** on a held-out slice, playbook deltas produced by the teacher measurably raise `pass_at_1` (paired, beyond noise) with no edge-guard regression — *and the operator reviewed and approved each delta by hand.* **Effort:** ~2–3 weekends.

### Phase 3 — Component manifest + manual self-maintenance loop

**Goal:** make the action space explicit and run the loop with a human in every step. Gaps `G1`, `G5`, `G8` (manual MVP).

- Component manifest by introspecting existing code.
- Distiller → layered evidence corpus.
- Prediction-contract record + scorer.
- Manual loop CLI: `anvil sense / propose / gate / promote`.

**Build:** manifest, distiller, contract scorer, CLI. **Exit:** at least one patch bundle goes sense→propose→gate→promote, met its prediction on the scoped held-out subset, regressed nothing on the edge guards, and is logged with a `decision.md`. **Effort:** ~2–3 weekends.

### Phase 4 — Copycat channels A + C-cheap  ← **copycat MVP**

**Goal:** acquire capability from observable structure and on-policy self-traces. Gap `G7` channels A and C-cheap.

- Authorization registry (`anvil/copycat/registry.yaml`).
- Structural census + gap-diff vs `research-components/`.
- Clean-room capability proposals for top gaps, run through the Phase-3 loop.
- Self-distillation harness: parallel strong-L4 vs local-L4 runs, diff their trajectories into harness-fix proposals (the cheap branch).

**First targets:** the Ralph-loop continuation middleware and any opencode / codex capability the gap-diff flags (sandbox modes, symmetric resume/fork) — *as clean re-implementations evaluated on the oracle*, never vendored code.

**Build:** registry, census, capability proposals, parallel-run harness. **Exit:** ≥ 1 structurally-inspired component and ≥ 1 self-distillation-derived harness fix promoted through the loop, each with met predictions and no edge-guard regression. Registry records the authorization + reuse scope for every target used. **Effort:** ~2–3 weekends.

> **At the end of Phase 4 you have working copycat mode.** Channel A is producing tier-1/2 candidates from public structure. Channel C-cheap is producing tier-1/2/3 candidates from on-policy trajectory diffs. Both are eval-gated. The operator approves. The audit log records every decision.

### Phase 5 — Terminal-Bench yardstick + hardening (optional, research mode)

**Goal:** external honesty check + coverage.

- Terminal-Bench harness (Docker runner; reuse the verifier interface) → add TB to the eval suite alongside the own-session corpus.
- Synthetic stress cases per root-cause class; long-horizon (SlopCodeBench-style) case to watch `pass^k` degradation.
- Meta-evaluation dashboard: held-out `pass_at_1` trend, edge-cost trend, promotion precision, prediction calibration, flywheel fuel rate.

**Build:** TB harness, synthetic stress, dashboard. **Exit:** a multi-cycle run shows held-out `pass_at_1` flat-or-up *and* edge-cost flat-or-down across ≥ 4 cycles, measured on both own-corpus and TB. **Effort:** ~2–4 weekends.

### Phase 6 (optional, gated) — Autonomy

**Goal:** let the manual loop run unattended, inside kill switches. **Only if** Phase 5 showed a clean multi-cycle trend.

- Kill switches + tripwire evals + gate-component lockout.
- Shadow-canary automation reusing the parallel-run harness from Phase 4.
- Bounded autonomous cycle: propose→gate→shadow→promote/revert, with daily cost/time budgets.

**Build:** kill switches, shadow canary, autonomous cycle. **Exit:** Anvil runs N unattended cycles without tripping a kill switch, with a positive held-out trend and stable prediction calibration, and every promotion is auditable. **Effort:** weeks.

### Phase 7 (optional, last, hardware-bound) — Distillation lane (Channels B-weights, C-weights)

**Goal:** touch the local model's weights, *only* for clusters that survived ≥ X cycles of cheaper tiers failing. Gap `G9`. Includes Channel B's `weights` branch and Channel C's `weights` branch.

- QLoRA SFT or rubric-OPD-style training on **verified** outcome-pairs (Channel B-eval data, Channel C-cheap data), on the **RTX 4060 Ti only**, with **step-wise reweighting (SOD)** to survive tool-call cascade.
- Same gate as everything else: prediction contract + held-out eval + edge guards. A distilled model that escalates more or runs slower fails its contract like any other patch.
- **Per-provider ToS clearance** for any Channel B-weights run; the Anvil CLI refuses to run the weights branch if the registry's `reuse_scope: weights` and the per-provider ToS check are missing or stale.

**Build:** QLoRA training pipeline, SOD step-wise reweighting, distill-aware contract, ToS-check enforcement. **Exit:** a distilled adapter beats the frozen model on held-out `pass_at_1` with no edge-guard regression, reproducibly, *and* the gain exceeds what tiers 1–4 could achieve for the same clusters. **Effort:** weeks, hardware-bound.

### Phase summary

| Endpoint | Phases | Effort | What you get |
|---|---|---|---|
| **MVP (online teacher)** | 0–2 | ~3–4 weeks | Root-cause analyst + reversible playbook deltas; operator-approved |
| **+ manual loop** | 3 | +2–3 weekends | Patch bundles, prediction contracts, canary promotion |
| **+ copycat A + C-cheap** | 4 | +2–3 weekends | Clean-room capability acquisition from public structure + on-policy self-traces |
| **Hardened (research mode)** | 5–6 | weeks | TB yardstick, dashboard, autonomy gated by kill switches |
| **Distillation (last resort)** | 7 | weeks | QLoRA / OPD on 1.5B on the 4060 Ti, only after tiers 1–4 are exhausted; Channels B-weights and C-weights |

### What changes the plan (decision triggers)

- Phase 4's gap-diff produces 100+ gaps with no clear ranking → rank by `tool.missing_capability` bias (per PLAN_04 §3.3); pick the top-3 by that ranking; defer the rest.
- Phase 4's first self-distillation fix passes the held-out eval but increases `layer_distribution.L4` → fails the contract; revert; investigate whether the strong model's strategy requires L4 (and therefore isn't suitable for the local model).
- A provider's ToS changes mid-program and forbids training-on-outputs → default to Channel C-weights (self-distillation) and open-weight teachers; record the change in the authorization registry.
- A `weights`-scope distillation run produces a model that fails the contract 3 cycles in a row → halt; the distillation lane may not be the right tool for this cluster; re-route to tier-1/2/3 and document.

---

## 8. Open questions

**Q1 — Is Channel A or Channel C-cheap the first to ship?**
PLAN_04 ships online teacher (Phase 2) before the manual loop (Phase 3). Within copycat, the order is A first (you have the corpus, you have the precedent) then C-cheap second (you need the trajectory recorder, which is Phase 1). Recommendation: A first, exactly as `09_BUILD_ROADMAP.md` orders them.

**Q2 — Should the authorization registry be a single YAML or a directory of YAMLs?**
A single YAML is easier to read and review. A directory of per-target YAMLs scales better and matches the `census/<target>.yaml` pattern. Recommendation: a directory, with `anvil/copycat/registry.yaml` as the index.

**Q3 — What is the right rate limit for Channel B-eval?**
`runs_per_day: 200` is the placeholder in the registry example. The right number depends on the cost budget and the corpus growth rate. Recommendation: start at 50, tune from the eval-corpus growth curve; the cost guardrail in the multi-objective metric (per `08_EVALUATION_AND_VERIFICATION.md` §8.2) bounds the total spend.

**Q4 — Should Channel C-weights share infrastructure with Channel B-weights?**
Yes — both are QLoRA / step-wise OPD on verified outcome-pairs, on the 1.5B local model, on the RTX 4060 Ti. The only difference is the data source. A single distillation lane (Phase 7) that accepts both data sources is the right design. Recommendation: build one distillation pipeline, parameterize the data source.

**Q5 — How is "promotion" of a clean-room capability different from promotion of a self-distillation fix?**
Clean-room (Channel A) is a new manifest entry; the diff is a new tool or middleware. Self-distillation fix (Channel C-cheap) is also a new manifest entry or an edit to an existing one; the diff is a new tool, a middleware change, or a playbook delta. The promotion path is the same (manual loop: sense → propose → gate → promote). The only difference is the *evidence* in the prediction contract (Channel A cites a gap-diff; Channel C-cheap cites a trajectory diff).

---

## 9. Composition with the rest of the corpus

### 9.1 vs PLAN_04 (Teacher mode)

PLAN_04 is the consumer of copycat's outputs. Channel A's capability proposals and Channel C-cheap's harness-self-distillation deltas both become `harness_fix` candidates in the teaching packet schema. The teacher is the bridge from "what could the agent be doing better" to "here is a manifest entry that closes the gap." PLAN_05 is the *input*; PLAN_04 is the *processor*; the self-maintenance loop is the *gate*.

### 9.2 vs PLAN_01 (Harness IDE)

PLAN_01 is the operator-facing IDE; copycat improves it. The structural proposals from Channel A target manifest entries (tools, middleware, memory) that enumerate the IDE's tool surface. The IDE's tool registry (per PLAN_01 §2.2) is the action space copycat can extend. A `tool.missing_capability` packet from Channel A points at a manifest entry like `tool.callgraph.impl` and proposes a clean-room implementation.

### 9.3 vs PLAN_03 (Full Codex/Cursor IDE)

PLAN_03 embeds PLAN_01 as its agent panel. The capabilities acquired via copycat flow through to PLAN_03 by construction — a new call-graph tool, a better compaction middleware, a Ralph-loop continuation primitive, an ACE playbook delta all become available to the full IDE without any PLAN_03-specific work.

### 9.4 vs the existing 5-trust-domain model (`01-trust-domains.md`)

Copycat is **analysis + planning**. It sees observable outcomes (Channel B), public structure (Channel A), and the user's own trajectories (Channel C) — all analysis. It proposes clean-room capability proposals and on-policy harness deltas — all planning. It never touches raw media or executes render steps. The patch bundle's `git apply` is the only thing that crosses into the runtime, and only after the prediction contract + eval gate + canary pass.

### 9.5 vs AutoCode's existing process machinery

AutoCode's repo carries heavy doc/QA/review machinery (tranches, checklists, QA artifacts, review entries, `AGENTS_CONVERSATION.MD`). Copycat's `decision.md` per patch bundle is the *only* doc artifact per bundle — no parallel plan-doc sprawl. The structural census and gap-diff are reference data, not planning documents. Anvil edits go through the *same* git-tracked, prediction-checked, eval-gated discipline as human edits.

---

## 10. Summary

Copycat mode is the **input side of the offline self-improvement engine**. It replaces the infeasible "record the target's internal traces" with three observable channels: **structural imitation** (Channel A, the highest-leverage, lowest-risk channel, with the corpus already in place), **outcome distillation** (Channel B, gated by per-provider ToS for any training use), and **self-distillation** (Channel C, the lowest-risk and best-technical-fit channel because it is on-policy by construction). All three live in Anvil. All are authorization-gated by the registry. All are eval-gated by the prediction contract + held-out eval + edge-guard regression check before any artifact crosses back into the runtime. The model is frozen. The weight branches are tier-5 capabilities, gated by hardware and ToS, and only after cheaper tiers provably can't close the gap. Edge-cost guards are mandatory. The single biggest risk is a self-modifying system that controls its own evaluation; the registry is outside the action space, and the manual-first design keeps the operator as the gate.

---

## 11. Sources

In-repo (existing corpus in `new_plans/`, this plan is built on top of):

- `harness_copy_teacher/00_INDEX.md` — the one-paragraph reframe, naming conventions, the runtime-vs-Anvil split diagram.
- `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md` — the 8 corrections; Correction 3 (three observable channels) is the load-bearing one for copycat mode.
- `harness_copy_teacher/02_REPO_STATE_AND_GAP_ANALYSIS.md` — the gap list `G1`–`G9`; the substrate AutoCode already has; the existing `research-components/` mirrors.
- `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` — the 2026 evidence base; AHE's "structure transfers" finding, the Ralph loop, ACE, GEPA, OPD, Terminal-Bench.
- `harness_copy_teacher/04_ARCHITECTURE.md` — the three observability pillars, the manifest schema, the prediction contract, the escalation ladder.
- `harness_copy_teacher/05_COPYCAT_MODE.md` — the original copycat spec; this plan is a condensed, re-organized form.
- `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` — the loop that promotes copycat's outputs.
- `harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md` — the eval flywheel that gates copycat.
- `harness_copy_teacher/09_BUILD_ROADMAP.md` — the phased build with exit gates; Phase 4 is the copycat phase.
- `harness_copy_teacher/10_RISKS_OPEN_QUESTIONS_DECISIONS.md` — the honest risk register; §10.2 (ToS) is load-bearing for copycat.
- `01-trust-domains.md` — the 5-domain model; copycat is analysis + planning.
- `PLAN_01_HARNESS_IDE.md` — the IDE surface that copycat extends.
- `PLAN_04_TEACHER_MODE.md` — the teacher that consumes copycat's outputs.

External (the 2026 evidence base, verified by the source research):

- **Agentic Harness Engineering (AHE)** — arXiv:2604.25850. The ablation that localizes gains to tools/middleware/memory, not system prompt. (https://github.com/china-qijizhifeng/agentic-harness-engineering)
- **ACE — Agentic Context Engineering** — Zhang et al., arXiv:2510.04618. The playbook model.
- **GEPA — Reflective Prompt Evolution** — Agrawal et al., arXiv:2507.19457. Tier 4; cheaper rollouts; not the engine.
- **On-Policy Distillation (OPD)** — Thinking Machines Lab, Oct 2025. Tier 5; corrects exposure bias; SOD step-wise reweighting for small agents (arXiv:2605.07725).
- **Terminal-Bench** — arXiv:2602.21193, 2603.05344. 89 hand-verified Docker tasks; the external yardstick.
- **SlopCodeBench** — arXiv:2603.24755. Long-horizon degradation; the pass^k stress test.
- **Small Language Models are the Future of Agentic AI** — Belcak et al. (NVIDIA), arXiv:2506.02153. The thesis citation.
- **Agent Harness Engineering** — Addy Osmani (O'Reilly, Apr–May 2026). The "harness is a living system" framing. (https://www.oreilly.com/radar/agent-harness-engineering/)
- **ForgeCode / Terminal-Bench 2.0 harness-first writeup** — Hightower (Apr 2026). 81.8% on TB2 with three-agent design.

---

*End of brief. The five PLAN_* files together compose the full product and program set: PLAN_01/02/03 are the operator-facing products (the IDE, the video agent, the full Codex/Cursor IDE); PLAN_04/05 are the offline self-improvement subsystem (the teacher and the copycat) that improves them. All five are designed to compose with the existing 5-trust-domain model and the existing `harness_copy_teacher/` corpus.*

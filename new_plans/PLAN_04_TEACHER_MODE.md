# PLAN_04 — The "AI Teacher Mode" Brief

> Plan 4 of 5. PLAN_01/02/03 are the operator-facing products (a code IDE, a video agent, a full Codex/Cursor IDE). **PLAN_04 is the offline subsystem that makes those products self-improving.** Teacher mode is the **root-cause analyst** that turns failed sessions into a durable playbook (online) and into candidate harness fixes (offline). It is paired with PLAN_05 (copycat mode) under the working codename **Anvil** — the offline harness-evolution engine that hammers the harness into shape *between* sessions. The runtime is unchanged. Anvil is a build-time dependency of the development process, not a runtime dependency of the product.

**Companion plans in this set**
- `PLAN_01_HARNESS_IDE.md` — the operator-facing IDE that the teacher improves.
- `PLAN_02_VIDEO_AGENT.md` — separate product; out of scope here.
- `PLAN_03_FULL_CODEX_IDE.md` — the full consumer IDE; embeds PLAN_01.
- `PLAN_04_TEACHER_MODE.md` (this file) — execution-grounded teaching + ACE playbook evolution.
- `PLAN_05_COPYCAT_MODE.md` — capability acquisition through observable structure, verified outcomes, and on-policy self-traces.

**Existing corpus in `new_plans/` that this plan composes with (read in this order)**

| File | What it contributes |
|---|---|
| `harness_copy_teacher/00_INDEX.md` | The one-paragraph reframe (Agentic Harness Engineering) and naming conventions. |
| `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md` | The 8 corrections to the source report; teacher mode is **Correction 4** ("execution-grounded, not judge-first"). |
| `harness_copy_teacher/02_REPO_STATE_AND_GAP_ANALYSIS.md` | What AutoCode already has; the gap list `G1`–`G9`; the substrate AHE needs. |
| `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` | The 2026 evidence base (AHE, ACE, GEPA, OPD, Terminal-Bench). |
| `harness_copy_teacher/04_ARCHITECTURE.md` | The runtime-vs-Anvil split, the three observability pillars, the manifest schema, the trajectory schema, the verifier, the root-cause taxonomy, the prediction contract. |
| `harness_copy_teacher/06_TEACHER_MODE.md` | The original teacher spec (this plan is a condensed, re-organized form of that). |
| `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` | The loop that consumes the teacher's `harness_fix` proposals. |
| `harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md` | The eval flywheel that gates the teacher. |
| `harness_copy_teacher/09_BUILD_ROADMAP.md` | The phased build with exit gates. |
| `harness_copy_teacher/10_RISKS_OPEN_QUESTIONS_DECISIONS.md` | The honest risk register. |
| `01-trust-domains.md` | The 5-trust-domain model; teacher mode is the **analysis + planning** boundary. |
| `PLAN_01_HARNESS_IDE.md` | The IDE surface that the teacher improves. |
| `autocode-station-requirements.md` §5 | The approval card and audit log that any teacher-emitted fix must satisfy. |

This plan is structured as: thesis → design language (what a teaching packet looks like) → the signal hierarchy → root-cause attribution → ACE playbook → online vs offline paths → the manual MVP → phase plan → composition. Where the existing corpus already nails a point, this plan summarizes and links rather than restates in full.

---

## 0. Thesis — what this is, what it isn't

### 0.1 What it is

**Teacher mode is a root-cause analyst grounded in an executable oracle.** It takes a failed AutoCode trajectory plus the verifier's deterministic verdict, classifies the failure by a *layer/component* taxonomy, and emits a **teaching packet** with two distinct outputs:

1. A **reversible playbook delta** (online, ship first) — an ACE-style entry the runtime loads into the durable-memory plane. Cheap, immediately useful, fully revertible.
2. A **candidate harness fix** (offline, feeds the loop) — a prediction-contracted proposal to edit a specific manifest component (e.g. "synthesize a tree-sitter call-graph tool so the agent stops escalating to L4 for this"). Validated by the verifier, gated by the eval flywheel, promoted behind a canary.

Both outputs share the same primary signal — the **executable verdict** (`diff_applies`, `build`, `tests`, `lint`, `types`), not an LLM judge's preference. The judge is demoted to a *secondary* signal for the residue that execution cannot decide (idiomatic style, comment quality, commit-message clarity). *(Correction 4, `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md`.)*

### 0.2 What it isn't

- It is **not** a "give me a better answer" feature. A teacher that only emits a corrected diff fixes *one task*; a teacher that attributes the failure to a missing L1 tool fixes the *class* of tasks that hit the same gap. The latter is the whole point.
- It is **not** a runtime feature in the operator-facing product. The runtime's north star locks "no cloud dependency by default" and "frozen model." The teacher is a **build-time** subsystem that may call a cloud teacher, observe authorized targets, and run distillation — exactly like a compiler or a test framework. Its eval-passing artifacts cross back into the runtime; the teacher itself never does.
- It is **not** a LLM-as-judge loop. Judges are flaky, position-biased, and reward-hackable. The verifier is deterministic; the tests cannot be flattered.
- It is **not** weight training (yet). The escalation ladder from `04_ARCHITECTURE.md` §4.7 puts distillation at tier 5; teacher mode produces tier-3 (playbook) and tier-1 (new tool) outputs, with tier-2 (middleware) and tier-4 (prompt) as needed.

### 0.3 The load-bearing design constraints (in priority order)

1. **The verifier is the oracle.** Every teaching decision ultimately references the executable verdict. If the verifier is wrong, the teacher is wrong. (See `08_EVALUATION_AND_VERIFICATION.md` §8.4 for "verification of the verifier.")
2. **Failure classes map to manifest components.** The teacher doesn't say "the agent failed"; it says "failure class `tool.missing_capability` → manifest entry `tool.callgraph.impl` → propose a new L1 tool." This is the bridge from observation to action.
3. **Two outputs, not one.** The playbook delta is reversible, immediate, and cheap (tier 3). The harness fix is gated, prediction-contracted, and audit-logged (tier 1–2). Both are produced from the same teaching packet; they ship on different cadences.
4. **The model is frozen.** The teacher's *output* may be a new tool, middleware, memory delta, or (later) a distilled adapter. It is never a retrain of the base policy on cloud data without explicit per-target ToS clearance (PLAN_05 §5.0 / `05_COPYCAT_MODE.md` §5.0).
5. **Edge-cost guards are mandatory.** A teaching-driven change that raises `pass_at_1` by escalating more to L4 has *regressed* the product. Every prediction contract's `no_regression_on` (PLAN_04 §4.5, `04_ARCHITECTURE.md` §4.5) always includes `layer_distribution.L4`, latency p50, and `tokens_per_task`.

### 0.4 How this inherits from existing corpus

**From `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md` (Correction 4):** the primary signal is execution-grounded, not judge-first. This is the most consequential correction in the teacher design. The signal hierarchy in §3 of this plan is the operational form of that correction.

**From `harness_copy_teacher/04_ARCHITECTURE.md` §4.4:** the **root-cause taxonomy** is the shared vocabulary between the distiller, the teacher, and the loop. It is the bridge from "the agent failed" to "edit *this* manifest entry." PLAN_04 §4 references it explicitly.

**From `harness_copy_teacher/06_TEACHER_MODE.md`:** the original teacher spec — input/output contract, signal hierarchy, ACE wiring, online vs offline paths. This plan re-organizes and condenses that into the same `PLAN_*` format as PLAN_01/02/03, while preserving the original's load-bearing decisions.

**From `01-trust-domains.md`:** the teacher occupies the **analysis + planning** domains. It sees the evidence corpus (analysis), proposes typed teaching packets (planning), and never touches raw media or executes render steps. The runtime + verifier are the **policy + render** boundary.

**From `PLAN_01_HARNESS_IDE.md`:** the IDE's tool surface is what the teacher improves. The teacher's `harness_fix` proposals edit specific manifest components (tools, middleware, memory) of the IDE's harness. PLAN_01's tool registry is the action space the teacher can extend.

**From `autocode-station-requirements.md` §5:** the approval card and audit log discipline applies to any teacher-emitted fix. `decision.md` per patch bundle is the human-readable artifact; the JSONL audit log is the machine artifact; both are required.

---

## 1. Design language — what a teaching packet looks like

### 1.1 The input the teacher consumes

The teacher consumes (all already produced by gaps `G2`–`G4` from `02_REPO_STATE_AND_GAP_ANALYSIS.md`):

- The **task** (NL instruction + repo + commit + source: `user_session` | `terminal_bench` | `synthetic`).
- The **student trajectory** (the §4.2.1 schema from `04_ARCHITECTURE.md`): a typed record per task run, with per-step layer/action/tool/observation-digest/latency/escalation, the final diff, and the `layer_distribution` (fraction of steps per L1/L2/L3/L4).
- The **verifier verdict** (the §4.3 schema): the deterministic executable ground truth — `diff_applies`, `build_passed`, `tests.passed/failed/regressed`, `lint_clean`, `types_clean`, and a final `label` of `success` | `partial` | `fail` | `error`.
- Optionally, a **stronger run's trajectory** (PLAN_05 Channel C — self-distillation) for contrast.
- The relevant **playbook** (the durable-memory plane artifact, per-language).

### 1.2 The output the teacher emits

The teaching packet:

```jsonc
{
  "packet_id": "tp_2026-06-20_...",
  "trajectory_id": "tj_...",
  "verdict": { ... },                       // copied from verifier; the anchor
  "root_cause": {                           // §4.4 taxonomy
    "class": "tool.missing_capability",
    "evidence_step": 7,                     // the decisive step in the trajectory
    "explanation": "Escalated L2→L4 at step 7 to compute the call graph because no L1 tool exposed it."
  },
  "score_breakdown": {                      // rubric, executable-first
    "diff_applies": 1, "build": 1, "tests": 0, "lint": 1, "types": 1,
    "style_judge": 0.7                      // SECONDARY, LLM-judge, only where no test exists
  },
  "revision": "<a corrected diff that VERIFIES, when the teacher can produce one>",
  "harness_fix": {                          // the actionable output: a candidate manifest edit
    "target": "tool.callgraph.impl",        // proposes a NEW tool (tier 1)
    "kind": "tool_implementation",
    "sketch": "Add an L1 tree-sitter call-graph tool so this never needs L4."
  },
  "playbook_delta": "<ACE-style delta, if the lesson is a reusable heuristic>",
  "provenance": { "teacher_model": "...", "anvil_version": "...", "created": "..." }  // W3C PROV-style
}
```

**Two distinct outputs, two distinct paths:**

| Output | Path | Loader | Speed | Revert |
|---|---|---|---|---|
| `playbook_delta` | **Online** (verbal) | Runtime durable-memory plane | Immediate next session | Delete the delta |
| `harness_fix` | **Offline** (structural) | Self-maintenance engine loop | Next Anvil cycle | `git revert` the patch bundle |

This separation is the load-bearing decision. It is also the literal difference between "Anvil teacher" (the self-improvement program, this plan) and "runtime teacher" (a separate, optional, cloud-callable product feature — see §5.5 of this plan and §6.5 of `06_TEACHER_MODE.md`). Conflating the two breaks the north-star invariants.

### 1.3 The reference design

The reference implementation language: **Python** (matches AutoCode's existing backend; teacher is a Python module that consumes the trajectory schema and emits the packet). The reference loop driver: a thin orchestrator that takes `anvil/patch_bundles/<id>/` from sense → propose → gate → promote, and the teacher is the `propose` step.

The reference UI surface: the existing AutoCode `AGENTS_CONVERSATION.MD` review entries + the `anvil` CLI's `decision.md` per patch bundle. The teacher is *not* a chat surface. It is a typed-output subsystem.

### 1.4 How this inherits from existing corpus

**From `harness_copy_teacher/06_TEACHER_MODE.md` §6.0:** the teaching-packet JSON shape is normative; this plan preserves the field names and the dual-output split verbatim. PLAN_04 §2 of the original (signal hierarchy) and §3 (root-cause attribution) follow.

**From `harness_copy_teacher/04_ARCHITECTURE.md` §4.5 (prediction contract) and §4.6 (patch bundle):** every `harness_fix` becomes a `patch_bundles/<id>/contract.json` with a scoped, falsifiable prediction, a `diff.patch`, an `eval_report.json`, a `prediction_score.json`, and a `decision.md`. The teacher produces the `contract.json`; the loop does the rest.

**From `PLAN_01_HARNESS_IDE.md` §2.2:** the IDE's tool surface (the manifest entries) is what the teacher's `harness_fix` targets. A `tool.missing_capability` packet points at a manifest entry like `tool.callgraph.impl` and proposes a clean-room implementation; the manifest's `prediction_metrics` field is the allowed claim space for the contract.

---

## 2. The signal hierarchy (Correction 4, made operational)

The teacher scores in this strict order; LLM judgment only enters at the bottom, only where execution cannot decide:

```
1. diff_applies?     ── deterministic (git apply)
2. build_passed?     ── deterministic (compiler / interpreter)
3. tests_pass?       ── deterministic; regressed>0 is an automatic FAIL
4. lint + types?     ── deterministic (ruff / mypy / clippy / your existing profiles)
─────────────────────  everything above is ground truth
5. style/explanation ── LLM-judge, with bias controls:
                         randomize order, rotate judge model, validate vs human spot-check
```

This is the inverse of the source report's judge-first stance. The inversion is what makes this teacher trustworthy and hard to reward-hack: a passing test suite is far harder to fake than a judge's approval. The judge is reserved for the genuinely judgment-shaped residue.

**Operational consequences:**

- A teaching packet that emits `harness_fix` and `playbook_delta` *but* the verifier says `tests: { passed: 0, failed: 3, regressed: 1 }` is rejected at the gate regardless of how good the LLM judge scores the prose.
- The LLM judge's verdict never gates promotion; it only adjusts a *style* sub-score in `eval_report.json`. The promotion decision reads the executable oracles, the `no_regression_on` guards, and the prediction contract (§4.5 of `04_ARCHITECTURE.md`).
- A teaching packet with no test oracle (e.g., a docstring-only change) may use the judge as the *primary* signal, but `oracle_strength: weak` is recorded and the case is weighted less in the eval corpus (`08_EVALUATION_AND_VERIFICATION.md` §8.1).

**The exact LLM-judge controls** (kept from the source report, with the bias protocol from Zheng et al. 2023):

1. **Randomize order.** The judge sees trajectories in a permuted sequence across evaluation rounds; position bias (preference for the first or last option in pairwise comparison) is washed out.
2. **Rotate judges.** Use ≥ 2 different judge models per packet; majority vote; record the per-judge scores for meta-evaluation.
3. **Validate vs humans.** Maintain a small "golden" set of human-rated trajectories; periodically check the judge against them. If agreement drops below a threshold, the judge is removed from the loop until retuned.
4. **CoT-required.** The judge must emit a chain-of-thought rationale *before* its numeric score. CoT improves calibration and makes the judgment auditable.

**Why this matters operationally:** the strongest empirical result of the 2026 harness-engineering literature (AHE ablation, `03_HARNESS_ENGINEERING_SOTA.md` §1) is that **gains come from tools, middleware, and long-term memory — not from prompt-level prose**. The teacher is the engine that produces those gains. If the teacher's signal is flattery-prone, the engine produces prose-shaped "improvements" that don't survive on the executable oracle. The hierarchy above is the structural fix.

### 2.1 How this inherits from existing corpus

**From `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md` Correction 4:** the entire correction is operationalized here. The hierarchy is the literal scoring rubric in `06_TEACHER_MODE.md` §6.1, re-stated for the `PLAN_*` format.

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §1 (AHE ablation):** the result that motivates the hierarchy in the first place. Tools/middleware/memory transfer; prompt-level prose does not. The teacher targets the former, not the latter.

**From `harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md` §8.2:** the multi-objective metric is the eval-side complement of the signal hierarchy. The hierarchy *is* the per-packet scoring rule; the multi-objective metric is the per-corpus reporting rule. They must agree, and they do.

---

## 3. Root-cause attribution — the teacher's real job

A teacher that only emits a "better diff" is a worse fit for AutoCode than one that says *which component caused the failure.* The taxonomy (from `04_ARCHITECTURE.md` §4.4) maps each failure class to the layer/component responsible, so the teaching packet's `harness_fix` can target a specific manifest entry.

### 3.1 The taxonomy (normative)

| Class | Layer | Symptom | Typical fix tier/component |
|-------|-------|---------|---------------------------|
| `reasoning.wrong_plan` | L4 | Plan was wrong before any tool ran | prompt (GEPA) or playbook |
| `reasoning.early_stop` | L4 | Quit before task complete | middleware (Ralph loop) |
| `retrieval.miss` | L2 | Never found the relevant file/symbol | tool impl (retrieval) / repo-map |
| `retrieval.stale_context` | L2 | Used outdated context after edits | middleware (compaction provenance) |
| `tool.wrong_choice` | any | Picked the wrong tool | tool *description* |
| `tool.bad_args` | any | Right tool, wrong arguments | tool *description* / schema |
| `tool.missing_capability` | L1/L2 | No deterministic tool existed; escalated to L4 | **new tool impl** (highest value) |
| `context.overflow` | — | Ran out of budget / compaction thrash | middleware (compaction) |
| `verify.no_self_check` | — | Didn't run tests before declaring done | hook / subagent (reviewer) |
| `style.weak_output` | L4 | Correct but ugly/unidiomatic | playbook / prompt |

`tool.missing_capability` is the **flywheel's best fuel**: every time the agent had to escalate to L4 because no L1/L2 tool existed, that's a candidate new deterministic tool — which moves work *down* the ladder, improving cost *and* correctness, exactly per the north star. The distiller and the teacher both rank failure clusters partly by how often this class appears.

### 3.2 Worked example

A teaching packet in canonical form:

- **Verdict:** `tests: { passed: 11, failed: 1, regressed: 0 }`. One test fails; the diff applied, build is clean, lint and types clean.
- **Trajectory:** at step 7 the agent ran `grep` for `class TokenStore` in `src/auth/`, found two matches, but needed a *call graph* of who calls `TokenStore.refresh()`. No L1/L2 tool exposed call graphs. The agent escalated L2→L4 and asked the LLM to "reason" about the call graph. The LLM hallucinated two callers that don't exist. The test for `TokenStore.refresh()` was the new caller; the diff added a stub to one of the hallucinated callers.
- **Class:** `tool.missing_capability` (no L1/L2 call-graph tool existed).
- **`harness_fix`:** propose a new tree-sitter-based L1 call-graph tool, manifest entry `tool.callgraph.impl`, predicted `prediction_metrics: [tool_error_rate, tokens_per_call]`.
- **`playbook_delta`:** "When the task requires a *callers-of* or *callees-of* relationship across files, prefer L2 retrieval (call graph) over L4 reasoning. If retrieval returns nothing, escalate only after a second retrieval pass with a different anchor."

The teaching packet's `evidence_step: 7` is the decisive step in the trajectory (the L2→L4 escalation). The `explanation` is the teacher's natural-language rationale; the `harness_fix` is the actionable output; the `playbook_delta` is the verbal lesson for *all* future runs, not just this one.

**Why this is the high-value path:** it moves work *down* the ladder (L4→L1) for *all future tasks* of this shape. A teacher that just handed over a correct diff would fix one task; this fixes the *class*.

### 3.3 The cluster-ranking rule

Both the distiller (PLAN_04 §4 / `04_ARCHITECTURE.md` §4.2.2) and the teacher rank failure clusters by:

```
rank = frequency × severity × (1 + is_tool_missing_capability × 2)
```

The bonus for `tool.missing_capability` is the flywheel's bias. A cluster of 3 failures classified as `tool.missing_capability` is weighted higher than a cluster of 6 failures classified as `style.weak_output`, all else equal — because the former produces durable tier-1 fixes, the latter produces tier-3 playbook deltas that may not generalize.

### 3.4 How this inherits from existing corpus

**From `harness_copy_teacher/04_ARCHITECTURE.md` §4.4:** the taxonomy is normative and shared with the distiller. PLAN_04 §3 references it verbatim and adds the cluster-ranking rule from `06_TEACHER_MODE.md` §6.2.

**From `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` §7.0 stage 1 (SENSE):** the distiller's ranking is the same as the teacher's. The loop's "pick the top cluster → route to cheapest sufficient tier" is the operational form of the bias.

**From `PLAN_01_HARNESS_IDE.md` §3.7 (maker/checker):** a high-risk `harness_fix` (e.g., editing `middleware.compaction`, a high-risk manifest entry) requires a separate checker identity to promote. The teacher does not bypass this; it produces the proposal, the loop gates it, the operator approves it.

---

## 4. ACE wiring — turning critiques into a durable playbook

The source report's "store the teacher's critiques as episodic memory" is exactly **ACE** (arXiv:2510.04618, `03_HARNESS_ENGINEERING_SOTA.md` §2). ACE solves the two failure modes a naive memory loop hits:

- **Brevity bias** — dropping domain insight for the sake of concise summaries.
- **Context collapse** — iterative rewriting erodes detail over time.

The delta-update + periodic-merge design is the fix: append structured deltas, periodically merge into "Master Rules," never blindly rewrite.

### 4.1 Mapping ACE roles onto Anvil

| ACE role | In Anvil | Output |
|----------|----------|--------|
| **Generator** | The AutoCode runtime loop | Trajectories |
| **Reflector** | The teacher's root-cause + revision step | Concrete insights from successes *and* errors |
| **Curator** | The playbook-delta integrator | Structured **delta** appended to the per-language playbook |
| **Pruner** | The periodic merge job | Overlapping deltas → concise "Master Rules" |

The runtime is the Generator (it produces the trajectories). The teacher is the Reflector (it turns a trajectory + verifier verdict into root-cause + revision). The integrator is the Curator (it appends a structured delta to the playbook). A periodic merge job is the Pruner.

### 4.2 Playbook storage (normative)

Per-language so it stays scoped. Filesystem layout:

```
.autocode/playbook/
  python.md        # append-only deltas + a "Master Rules" section the Pruner maintains
  rust.md
  typescript.md
  ...
  _meta.json       # delta count, last prune, provenance per rule
```

The `edit_surface: append_only` field on the manifest entry `memory.playbook.<lang>` (`04_ARCHITECTURE.md` §4.1) enforces ACE's delta discipline at the manifest level — the loop cannot rewrite the playbook wholesale, only append deltas and (in the Pruner step) merge.

### 4.3 Delta discipline

Every delta is a typed record:

```jsonc
{
  "delta_id": "pd_...",
  "trajectory_id": "tj_...",
  "verdict": "fail | partial | success",
  "root_cause_class": "tool.missing_capability | ...",
  "trigger": "<the condition that should activate this rule, e.g. 'task requires callers-of X across files'>",
  "observation": "<what the student did>",
  "rule": "<the heuristic the student should have followed>",
  "evidence_trajectory": "tj_...",
  "language": "python | rust | ...",
  "created": "...",
  "provenance": { "teacher_model": "...", "anvil_version": "..." }
}
```

The Pruner merges overlapping rules into Master Rules *periodically*, preserving detail (ACE's anti-brevity-bias design). Every merge is itself a prediction-contracted change: `pass_at_1` holds after pruning? `regressions_introduced == 0`? If yes, the merge stands. If no, the merge is reverted and the overlapping deltas stay separate.

### 4.4 Why playbook-over-fine-tuning for most lessons

ACE shows context adaptation beats *both* fine-tuning and prompt optimization on overhead, and adapts from *natural execution feedback* without labels — which is exactly the situation for most of the user's own sessions (execution feedback, not labeled gold answers). The playbook is a **tier-3 lever**: cheap, reversible, no training.

The distillation tier (tier 5) is reserved for clusters that survived ≥ X cycles of cheaper tiers failing. The playbook is the *first* thing the teacher tries; if the rule generalizes across N sessions, the playbook carries it forever. If it doesn't, the cluster is reclassified as `tool.missing_capability` or `retrieval.miss` and routed to a higher tier.

### 4.5 The runtime load

The runtime loads the playbook from the durable-memory plane (per `04_ARCHITECTURE.md` §4.1 and PLAN §0.1/§0.2 of the existing AutoCode PLAN). The load is read-only at session start; the runtime does not mutate the playbook (only the Curator in Anvil does). The Pruner runs on a separate cadence (weekly, or on a threshold of N deltas since last prune).

### 4.6 How this inherits from existing corpus

**From `harness_copy_teacher/06_TEACHER_MODE.md` §6.3:** the ACE wiring, the playbook storage, and the delta discipline are normative. This plan preserves them and adds the Pruner-as-prediction-contract step (the merge itself is a gated change).

**From `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` §2 (ACE):** the empirical case for delta + prune over rewrite. The numbers (+10.6% on agents, +8.6% on finance, lower overhead than fine-tuning and prompt optimization) are the basis for the playbook-over-fine-tuning recommendation.

**From `harness_copy_teacher/04_ARCHITECTURE.md` §4.1:** the manifest's `edit_surface: append_only` field on `memory.playbook.<lang>` is the structural enforcement. The teacher cannot rewrite the playbook; the integrator appends, the Pruner merges with a contract.

---

## 5. Online vs offline teacher paths

The two outputs of the teaching packet go down two different paths. Ship the **online path first** — it delivers visible value with no autonomous editing and no training.

| | Online (verbal) | Offline (structural / weight) |
|---|----------------|-------------------------------|
| **Mechanism** | Playbook delta loaded into runtime memory | Patch bundle (tools / middleware) or distillation |
| **Speed** | Immediate next session | Next Anvil cycle / next training run |
| **Cost** | ~free | Cheap (harness) to expensive (weights) |
| **When** | Recurring task patterns, style, heuristics | Structural gaps, missing tools, model-level deficits |
| **Risk** | Low (revert = delete delta) | Medium–high (gated by prediction contract + eval) |
| **Gate** | Human reviews the delta; approved ones load | Prediction contract + held-out eval + edge-guard regression check |

### 5.1 Online path (ship first)

```
teacher ──▶ playbook_delta ──▶ operator review ──▶ approved ──▶ runtime durable-memory
                                (you read, you approve)                  (loaded next session)
```

The operator reviews the delta, sees the `trajectory_id` it came from, the `verdict`, the `root_cause_class`, and the `rule`. The decision is recorded in the audit log. A denied delta is dropped; an approved delta is appended to `.autocode/playbook/<lang>.md` (or merged by the Pruner).

**Why ship this first:** zero autonomous editing, zero training, zero new tool, immediate value. The user sees "the teacher noticed that on 4 of the last 12 trajectories, when I asked for a refactor, the agent escalated to L4 for a call graph; here is a rule that says use the L2 retrieval pass first." The user reads, approves, and the next session is measurably better. This is the **first user-visible capability** of the Anvil program (Phase 2 of the roadmap, `09_BUILD_ROADMAP.md`).

### 5.2 Offline path (the bridge into the loop)

```
teacher ──▶ harness_fix ──▶ contract.json (prediction) ──▶ anvil gate ──▶ patch bundle
                                                                      │
                                                              pass ▼   fail ▼
                                                         canary      revert + log
```

The `harness_fix` is wrapped in a **prediction contract** (`04_ARCHITECTURE.md` §4.5): a scoped, falsifiable claim like "on the held-out cluster `tool.missing_capability:auth`, the new call-graph tool will raise `tool_selection_accuracy` from 0.42 to 0.55+ with no regression on `pass_at_1`, `layer_distribution.L4`, or `latency_p50`." The loop (PLAN §7 of this set, `07_SELF_MAINTENANCE_ENGINE.md`) applies the patch to a scratch worktree, runs the eval suite, scores the prediction, and either promotes (canary → flag default-on) or reverts (and logs the prediction miss as calibration signal).

The offline path requires:
- A `manifest` (gap `G1`) to enumerate the editable components and their `prediction_metrics`.
- A `distiller` (gap `G5`) to produce the layered evidence corpus.
- An `eval gate` (gap `G3` + `G4`) — the verifier + the own-session corpus + Terminal-Bench.
- A `prediction-contract scorer` (gap implicit in `G8`) to compare predicted vs actual.

All of these are Phase 1 prerequisites. The offline path cannot ship before Phase 1's exit gate is met.

### 5.3 Distillation path (tier 5, last)

The distillation lane is **not** part of teacher mode. The teacher produces `harness_fix` candidates that may include a `kind: distilled_adapter`, but the distillation *itself* is a separate Phase 7 capability, gated by:
- Hardware: RTX 4060 Ti (8–16 GB), QLoRA on 1.5B only; RX 480 is inference-only (ROCm dropped Polaris).
- Step-wise reweighting (SOD, arXiv:2605.07725) to survive the tool-call cascade in small agents.
- Per-provider ToS clearance for any training-on-outputs (PLAN_05 §5.0 / `05_COPYCAT_MODE.md` §5.0).
- A prediction contract that beats tiers 1–4 on the same cluster — otherwise the cheaper tier was the right answer.

See `10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.1 for the hardware reality and §10.2 for the legal reality.

### 5.4 The two "teacher modes" — disambiguation

A subtlety worth deciding early: there are **two** plausible "teacher modes," and they're different products.

1. **Anvil teacher (offline):** improves AutoCode itself across sessions. This is the self-improvement program. Primary subject of this plan.
2. **Runtime teacher (online, optional):** a strong model critiques the *user's* code in real time inside a session ("review this PR"). This is a normal agent feature, not self-improvement, and it would need cloud opt-in per the invariants (it's a runtime cloud call). Useful, but **don't conflate it with the self-improvement program** — it's a different roadmap item with different invariant implications.

PLAN_04 specifies #1. If #2 is also wanted, scope it separately as a runtime feature with explicit cloud opt-in, so it doesn't muddy the offline/runtime split that makes #1 invariant-compliant.

### 5.5 How this inherits from existing corpus

**From `harness_copy_teacher/06_TEACHER_MODE.md` §6.4 + §6.5:** the online/offline split and the disambiguation. Preserved verbatim.

**From `harness_copy_teacher/09_BUILD_ROADMAP.md` Phase 2:** "ship the teacher as a root-cause analyst that emits reversible playbook deltas. Gap G6, online half only. No autonomous editing, no training." This is the first user-visible capability.

**From `01-trust-domains.md` data-flow rules:** the online path's playbook delta is a **durable-memory plane** write, allowed under rule 7 ("everything is traceable"). The offline path's `harness_fix` is a **policy + render** write, allowed only after the prediction contract + eval gate pass.

---

## 6. The manual MVP — the Anvil CLI

Strip everything autonomous. The **manual MVP** is four commands:

```
$ autocode anvil sense         # distiller clusters last N failed trajectories, prints ranked list
$ autocode anvil propose 3     # drafts a contracted patch bundle for cluster #3, writes to anvil/patch_bundles/
$ autocode anvil gate pb_001   # applies to scratch worktree, runs eval suite, scores prediction, writes report
$ # read decision.md + prediction_score.json, then:
$ autocode anvil promote pb_001  # git apply on runtime + log to AGENTS_CONVERSATION.MD
```

**What you do, what Anvil does, at each step:**

| Step | You do | Anvil does |
|------|--------|------------|
| `sense` | Read the ranked clusters | Distill (file 04 §4.2.2), cluster, rank |
| `propose 3` | Pick the cluster; choose tier (1–4) | Teacher produces `contract.json` + `diff.patch` |
| `gate` | Read the prediction contract | Apply to scratch worktree, run eval suite, write `eval_report.json` + `prediction_score.json` |
| `promote` | Read `decision.md` and the score; approve | `git apply diff.patch`; `git revert` is always available |

No autonomy, no kill switches needed yet (the operator *is* the kill switch), no canary automation (the operator decides). This MVP is buildable on top of gaps `G1`–`G4` + `G6` and delivers the whole value of the program *with a human in every loop*.

**The online-only teacher** (Phase 2 of the roadmap) ships even sooner — it needs only `G2` (trajectory recorder) and `G3` (verifier), not the full manifest or the loop. The output is a `playbook_delta` per failed trajectory, reviewed by the operator, approved and loaded into the durable-memory plane.

### 6.1 Why manual-first

For a single-user tool, the manual loop may be the right *permanent* state. The autonomy upgrade (Phase 6 of the roadmap) is a lot of machinery for one user, and it can quietly invalidate the program if the loop learns to satisfy the eval rather than the goal. The single biggest risk (`10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.8) is *a self-modifying system that controls its own evaluation*. Manual-first means the operator is the gate, not the loop; autonomy is an opt-in upgrade, not the headline.

### 6.2 How this inherits from existing corpus

**From `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` §7.6:** the manual MVP CLI is normative; this plan reproduces it with the operator-action table added.

**From `harness_copy_teacher/09_BUILD_ROADMAP.md` Phase 2 + Phase 3:** the exit gates for shipping the online teacher (Phase 2) and the manual loop (Phase 3) are the operational form of "ship the manual MVP first."

**From `autocode-station-requirements.md` §5.3:** every promotion is recorded in an immutable, attributed audit log. The `decision.md` per patch bundle is the human-readable artifact; the JSONL audit log is the machine artifact. The teacher is subject to the same discipline as any other governed action.

---

## 7. Phase plan

The sequencing rule from `harness_copy_teacher/09_BUILD_ROADMAP.md` applies: **build the measurement substrate before the evolution machinery, and ship a human-in-the-loop capability before any autonomy.** This plan re-states the teacher-relevant phases in the `PLAN_*` format. Full phase plan with all dependencies is in `09_BUILD_ROADMAP.md`.

### Phase 0 — Design lock + invariant reconciliation

**Goal:** get the offline/runtime split and the Anvil design into the repo's authority chain so the program is north-star-legal.

- Write `docs/research/anvil-design.md`: the runtime-vs-Anvil split as sentence one, citing `north-star.md`; the three pillars; the escalation ladder.
- Add an explicit north-star note: "Anvil is offline; the runtime remains cloud-free and frozen-model. Cloud teacher = build-time dependency, not runtime dependency."

**Build:** the design doc. **Exit:** the doc exists, references the invariants, and a reviewer following `north-star.md` would not flag it `Critical`. **Effort:** ~1 day.

### Phase 1 — Measurement substrate (the prerequisite for everything)

**Goal:** make AutoCode's behavior observable and verifiable. Gaps `G2`, `G3`, `G4`. No evolution yet.

- `G3` Verifier + fixture suite (the §4.3 schema + determinism + flaky handling).
- `G2` Trajectory recorder writing the §4.2.1 schema (extends existing session storage).
- `G4` Own-session corpus builder with frozen held-out split.
- Multi-objective metric + `eval_report.json` (per `08_EVALUATION_AND_VERIFICATION.md` §8.2–8.3).

**Build:** the verifier, recorder, corpus, metric. **Exit:** you can run `autocode anvil corpus build`, get ≥ ~50 replayable cases with marked oracle strength, run the current harness against the held-out split, and produce an `eval_report.json` with mean ± spread and a measured noise band. *Do not proceed past this gate.* **Effort:** ~2 weeks (the "first two weeks" from `09_BUILD_ROADMAP.md`).

### Phase 2 — Teacher mode, online path (first user-visible value)  ← **MVP endpoint**

**Goal:** ship the teacher as a root-cause analyst that emits reversible playbook deltas. Gap `G6`, online half only. No autonomous editing, no training.

- Root-cause classifier over trajectories (the §4.4 taxonomy from `04_ARCHITECTURE.md`).
- Teaching-packet generator (the §6.0 schema from `06_TEACHER_MODE.md`) with the §6.1 signal hierarchy.
- ACE playbook (Generator/Reflector/Curator/Pruner) per-language with `edit_surface: append_only`.
- Runtime loads the playbook from the durable-memory plane.

**Build:** classifier, packet generator, ACE wiring, runtime loader. **Exit:** on a held-out slice, playbook deltas produced by the teacher measurably raise `pass_at_1` (paired, beyond noise) with no edge-guard regression — *and the operator reviewed and approved each delta by hand.* This is a complete, valuable feature on its own; you could stop here and have a self-teaching-with-human-approval coding agent. **Effort:** ~2–3 weekends.

> **At the end of Phase 2 you have a working teacher mode.** The runtime loads playbook deltas; the teacher is the Reflector + Curator; the operator approves; the audit log records every decision. For a single-user tool, this is a reasonable permanent state — the manual MVP from §6 above.

### Phase 3 — Component manifest + manual self-maintenance loop

**Goal:** make the action space explicit and run the loop with a human in every step. Gaps `G1`, `G5`, `G8` (manual MVP).

- Component manifest by introspecting existing code (the §4.1 schema from `04_ARCHITECTURE.md`).
- Distiller → layered evidence corpus (the §4.2.2 schema).
- Prediction-contract record + scorer (the §4.5 schema).
- Manual loop CLI: `anvil sense / propose / gate / promote`.

**First high-value target:** a `tool.missing_capability` cluster → synthesize a new L1/L2 deterministic tool (tier 1, the flywheel's best fuel).

**Build:** manifest, distiller, contract scorer, CLI. **Exit:** at least one patch bundle goes sense→propose→gate→promote, met its prediction on the scoped held-out subset, regressed nothing on the edge guards, and is logged with a `decision.md`. The promoted change is a new deterministic tool or a tool-description fix (tiers 1–2), not a prompt tweak. **Effort:** ~2–3 weekends.

### Phase 4 — Copycat channels A + C-cheap (PLAN_05)

**Goal:** acquire capability from observable structure and on-policy self-traces. Gap `G7` channels A (structural imitation) and C-cheap (harness self-distillation, no weight training).

- Authorization registry (PLAN_05 §5.0 / `05_COPYCAT_MODE.md` §5.0).
- Structural census + gap-diff vs `research-components/`.
- Clean-room capability proposals for top gaps, run through the Phase-3 loop.
- Self-distillation harness: parallel strong-L4 vs local-L4 runs, diff their trajectories into harness-fix proposals (the cheap branch).

**First targets:** the Ralph-loop continuation middleware and any opencode/codex capability the gap-diff flags (sandbox modes, symmetric resume/fork) — *as clean re-implementations evaluated on the oracle*, never vendored code.

**Build:** registry, census, capability proposals, parallel-run harness. **Exit:** ≥ 1 structurally-inspired component and ≥ 1 self-distillation-derived harness fix promoted through the loop, each with met predictions and no edge-guard regression. **Effort:** ~2–3 weekends.

### Phase 5 — Terminal-Bench yardstick + hardening (optional, research mode)

**Goal:** external honesty check + coverage. PLAN **Section 3** measurement.

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

### Phase 7 (optional, last, hardware-bound) — Distillation lane

**Goal:** touch the local model's weights, *only* for clusters that survived ≥ X cycles of cheaper tiers failing. Gap `G9`.

- QLoRA SFT or rubric-OPD-style training on **verified** outcome-pairs (PLAN_05 channels B/C), on the **RTX 4060 Ti only**, with **step-wise reweighting (SOD)** to survive tool-call cascade.
- Same gate as everything else: prediction contract + held-out eval + edge guards. A distilled model that escalates more or runs slower fails its contract like any other patch.

**Build:** QLoRA training pipeline, SOD step-wise reweighting, distill-aware contract. **Exit:** a distilled adapter beats the frozen model on held-out `pass_at_1` with no edge-guard regression, reproducibly, *and* the gain exceeds what tiers 1–4 could achieve for the same clusters. **Effort:** weeks, hardware-bound.

### Phase summary

| Endpoint | Phases | Effort | What you get |
|---|---|---|---|
| **MVP (online teacher)** | 0–2 | ~3–4 weeks | Root-cause analyst + reversible playbook deltas; operator-approved; runtime loads them |
| **+ manual loop (offline teacher)** | 3 | +2–3 weekends | Patch bundles, prediction contracts, canary promotion, full audit |
| **+ structural copycat** | 4 | +2–3 weekends | Clean-room capability acquisition from public structure + on-policy self-traces |
| **Hardened (research mode)** | 5–6 | weeks | TB yardstick, dashboard, autonomy gated by kill switches |
| **Distillation (last resort)** | 7 | weeks | QLoRA / OPD on 1.5B on the 4060 Ti, only after tiers 1–4 are exhausted |

### What changes the plan (decision triggers)

- Phase 1's ~50 cases produce noisy eval → volume problem; supplement heavily with TB / synthetic; consider a held-out rotation from a larger synthetic pool.
- Phase 2's playbook deltas don't generalize → reclassify the cluster as `tool.missing_capability` or `retrieval.miss` and route to a higher tier.
- Phase 3's first patch bundle's prediction misses → log the miss as calibration signal; tighten the contract; do *not* promote noise.
- Phase 5's `layer_distribution.L4` creeps up across cycles → loop is cheating the edge constraint; retune (raise the `no_regression_on` tolerance band) or halt and audit.
- A provider's ToS changes mid-program and forbids training-on-outputs → default to self-distillation (PLAN_05 Channel C) and open-weight teachers; record the change in the authorization registry.

---

## 8. Open questions

**Q1 — Online-first or offline-first?**
The roadmap ships online (Phase 2) before offline (Phase 3). The online path is lower risk and immediately useful; the offline path requires the manifest + distiller + eval gate + prediction-contract scorer (a lot more surface). Recommendation: online-first, exactly as `09_BUILD_ROADMAP.md` orders them.

**Q2 — Should the teacher be a single module or a pipeline?**
A single module is simpler to invoke; a pipeline (classifier → reflector → curator → pruner) is more testable and matches ACE's role split. Recommendation: pipeline. Each role is a typed function with a clear input/output contract; the pipeline is the orchestrator.

**Q3 — Per-language playbook or one global playbook?**
Per-language is more accurate (Python idioms ≠ Rust idioms); one global is simpler to maintain. Recommendation: per-language, with a small `_meta.json` registry. The Pruner runs per language.

**Q4 — Should the operator approve every playbook delta, or batch-approve?**
Single-delta review is highest integrity but highest friction. Batch approval (a Pruner-produced "Master Rules" candidate, the operator approves the merge) is lower friction. Recommendation: single-delta review for the first N (e.g. 20) deltas to build operator trust; batch review for stable Master Rules after.

**Q5 — How many cycles before autonomy is even on the table?**
Recommendation: 4+ clean cycles (held-out pass@1 flat-or-up *and* edge-cost flat-or-down) before Phase 6 is unlocked. For a single-user tool, the manual loop may be the right permanent state (per `10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.5).

---

## 9. Composition with the rest of the corpus

### 9.1 vs PLAN_01 (Harness IDE)

PLAN_01 is the operator-facing IDE; teacher mode improves it. The teacher's `harness_fix` proposals target manifest entries that enumerate the IDE's tools, middleware, memory, and prompts. The `prediction_metrics` field of each manifest entry is the allowed claim space for the contract. PLAN_01's tool registry (§2.2) is the action space the teacher can extend with new L1/L2 deterministic tools.

### 9.2 vs PLAN_03 (Full Codex/Cursor IDE)

PLAN_03 embeds PLAN_01 as its agent panel. The teacher's improvements to PLAN_01 flow through to PLAN_03 by construction — a new call-graph tool, a better compaction middleware, an ACE playbook delta all become available to the full IDE without any PLAN_03-specific work.

### 9.3 vs PLAN_05 (Copycat mode)

PLAN_05 is the **input side** of the same offline engine: where does the structure/outcomes/on-policy traces come from that the teacher turns into teaching packets? PLAN_05's Channel A (structural imitation) and Channel C-cheap (harness self-distillation) are the primary inputs to the teacher's "what could the agent be doing better" reasoning. PLAN_05 is a companion plan, not a parallel one.

### 9.4 vs the existing 5-trust-domain model (`01-trust-domains.md`)

The teacher occupies the **analysis + planning** domains. It sees the trajectory + verdict (analysis), proposes typed teaching packets (planning), and never touches raw media or executes render steps. The runtime + verifier are the **policy + render** boundary. The patch bundle's `git apply` is the only thing that crosses from planning to render, and only after the prediction contract + eval gate + canary pass.

### 9.5 vs AutoCode's existing process machinery

AutoCode's repo carries heavy doc/QA/review machinery (tranches, checklists, QA artifacts, review entries, `AGENTS_CONVERSATION.MD`). The teacher's `decision.md` per patch bundle is the *only* doc artifact per bundle — no parallel plan-doc sprawl. Anvil edits go through the *same* git-tracked, prediction-checked, eval-gated discipline as human edits. The honest risk (`10_RISKS_OPEN_QUESTIONS_DECISIONS.md` §10.4 third bullet) is that Anvil multiplies the doc-reconciliation burden; the mitigation is `decision.md`-only and the "no new planning docs" rule.

---

## 10. Summary

Teacher mode is the **root-cause analyst that turns failed sessions into a durable playbook (online) and into candidate harness fixes (offline)**. It is grounded in the executable oracle, not an LLM judge. It produces two distinct outputs: a reversible playbook delta (cheap, ship first) and a prediction-contracted harness fix (gated, feeds the self-maintenance loop). The whole thing runs offline in Anvil and changes the runtime only through eval-gated artifacts. The model is frozen. Edge-cost guards are mandatory. The single biggest risk is a self-modifying system that controls its own evaluation; the manual-first design and the gate-component lockout are the structural fix.

---

## 11. Sources

In-repo (existing corpus in `new_plans/`, this plan is built on top of):

- `harness_copy_teacher/00_INDEX.md` — the one-paragraph reframe, naming conventions, the runtime-vs-Anvil split diagram.
- `harness_copy_teacher/01_VALIDATION_AND_CORRECTIONS.md` — the 8 corrections; Correction 4 (execution-grounded signal) is the load-bearing one for teacher mode.
- `harness_copy_teacher/02_REPO_STATE_AND_GAP_ANALYSIS.md` — the gap list `G1`–`G9`; the substrate AutoCode already has.
- `harness_copy_teacher/03_HARNESS_ENGINEERING_SOTA.md` — the 2026 evidence base: AHE, ACE, GEPA, OPD, Terminal-Bench.
- `harness_copy_teacher/04_ARCHITECTURE.md` — the three observability pillars, the manifest schema, the trajectory schema, the verifier, the root-cause taxonomy, the prediction contract.
- `harness_copy_teacher/06_TEACHER_MODE.md` — the original teacher spec; this plan is a condensed, re-organized form.
- `harness_copy_teacher/07_SELF_MAINTENANCE_ENGINE.md` — the loop that consumes `harness_fix` proposals.
- `harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md` — the eval flywheel that gates the teacher.
- `harness_copy_teacher/09_BUILD_ROADMAP.md` — the phased build with exit gates.
- `harness_copy_teacher/10_RISKS_OPEN_QUESTIONS_DECISIONS.md` — the honest risk register.
- `01-trust-domains.md` — the 5-domain model; teacher is analysis + planning.
- `PLAN_01_HARNESS_IDE.md` — the IDE surface the teacher improves.
- `autocode-station-requirements.md` — the approval card and audit log discipline.

External (the 2026 evidence base, verified by the source research):

- **Agentic Harness Engineering (AHE)** — arXiv:2604.25850. The ablation that localizes gains to tools/middleware/memory, not system prompt. (https://github.com/china-qijizhifeng/agentic-harness-engineering)
- **ACE — Agentic Context Engineering** — Zhang et al., arXiv:2510.04618. The playbook model with Generate/Reflect/Curate/Prune.
- **GEPA — Reflective Prompt Evolution** — Agrawal et al., arXiv:2507.19457. Tier 4; cheaper rollouts; not the engine.
- **On-Policy Distillation (OPD)** — Thinking Machines Lab, Oct 2025. Tier 5; corrects exposure bias; SOD step-wise reweighting for small agents (arXiv:2605.07725).
- **Terminal-Bench** — arXiv:2602.21193, 2603.05344. 89 hand-verified Docker tasks; the external yardstick.
- **SlopCodeBench** — arXiv:2603.24755. Long-horizon degradation; the pass^k stress test.
- **Small Language Models are the Future of Agentic AI** — Belcak et al. (NVIDIA), arXiv:2506.02153. The thesis citation.

---

*End of brief. Ready to be paired with PLAN_05 (copycat mode) and embedded in the Anvil program described in `harness_copy_teacher/00_INDEX.md`.*

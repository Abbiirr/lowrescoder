# 04 — Architecture: Anvil + the Three Pillars

This is the core design doc. It defines the offline harness-evolution subsystem (**Anvil**), how it relates to the AutoCode runtime, and the concrete data contracts that make it work. Schemas here are normative; files 05–08 build on them.

---

## 4.0 The load-bearing split: runtime vs Anvil

```
┌─────────────────────────────────────────┐        ┌──────────────────────────────────────────┐
│  AutoCode RUNTIME                          │        │  ANVIL  (offline harness-evolution)        │
│  ───────────────                           │        │  ─────────────────────────────────         │
│  • local-first, deterministic-first        │        │  • runs on YOUR schedule, not user hot path │
│  • cloud-free by default                   │ traj.  │  • MAY call a cloud teacher                  │
│  • model FROZEN                            │ ──────▶│  • MAY observe authorized targets           │
│  • L1→L4 escalation ladder                 │        │  • MAY run distillation (4060 Ti only)      │
│  • 4-plane context model (PLAN §0.1)       │        │  • produces eval-gated PATCH BUNDLES        │
│                                            │◀────── │                                            │
│  consumes only eval-passing artifacts      │ patch  │  teacher + copycat live ENTIRELY here       │
└─────────────────────────────────────────┘ bundle └──────────────────────────────────────────┘
```

**Invariant compliance (file 01, Correction 5):** the cloud teacher is a *build-time* dependency of the development process — like a compiler — never a *runtime* dependency of the product. Everything the runtime executes is local and was produced offline. State this split first in the repo design doc (`docs/research/anvil-design.md`), citing `north-star.md`, or a north-star-following reviewer will (correctly) block the program.

**Two operating modes for Anvil:**
- **Manual / supervised** (default, ship first): you run `autocode anvil propose`, review the proposed patch bundle + its prediction, and approve. Human-in-the-loop.
- **Autonomous** (opt-in, much later): Anvil proposes → self-gates → canaries → promotes/reverts, bounded by kill switches (file 07). Do not build this until the manual loop has produced trustworthy patches for weeks.

---

## 4.1 Pillar 1 — Component observability: the manifest

Anvil's *action space* is the set of harness components it may edit. Make it explicit and machine-readable. This is gap `G1` and it builds directly on PLAN §0.1 (4 planes) and §0.4 (tool metadata).

`anvil/manifest.yaml` (normative shape):

```yaml
version: 1
# Every editable harness component. Anvil may ONLY edit components listed here.
components:
  - id: tool.read_file.impl
    kind: tool_implementation        # one of the 7 AHE component kinds
    plane: durable_instruction        # PLAN §0.1 plane
    files: [autocode/src/autocode/agent/tools/read_file.py]
    edit_surface: full                # full | params_only | description_only | append_only
    revertible: true                  # must be git-tracked
    risk: low                         # low | medium | high (gates autonomy)
    owner_tests: [autocode/tests/unit/test_tools.py::test_read_file]
    prediction_metrics: [tool_error_rate, tokens_per_call]   # what edits here are allowed to claim

  - id: tool.read_file.description
    kind: tool_description
    plane: durable_instruction
    files: [autocode/src/autocode/agent/tools/read_file.py]   # the docstring/schema
    edit_surface: description_only
    risk: low
    prediction_metrics: [tool_selection_accuracy]

  - id: middleware.compaction
    kind: middleware
    plane: live_session
    files: [autocode/src/autocode/session/consolidation.py]
    edit_surface: full
    risk: high                        # compaction is a correctness+security boundary (PLAN §1f.4)
    prediction_metrics: [context_growth_rate, provenance_preserved, recovery_quality]

  - id: memory.playbook.python
    kind: long_term_memory
    plane: durable_memory
    files: [.autocode/playbook/python.md]   # ACE-style playbook, per-language
    edit_surface: append_only          # deltas only; Pruner merges (file 06)
    risk: medium
    prediction_metrics: [pass_at_1, regressions_introduced]

  - id: prompt.architect
    kind: system_prompt
    plane: durable_instruction
    files: [autocode/src/autocode/agent/prompts.py]
    edit_surface: full
    risk: medium
    optimizer: gepa                    # tier-4; only this component-kind routes to GEPA
    prediction_metrics: [pass_at_1, plan_quality]

  - id: subagent.reviewer
    kind: subagent
    plane: durable_instruction
    files: [autocode/skills/agent-comms/reviewer.md]
    edit_surface: full
    risk: medium
    prediction_metrics: [review_catch_rate, false_positive_rate]
```

Notes:
- **Seven `kind`s**, matching AHE: `system_prompt`, `tool_description`, `tool_implementation`, `middleware`, `skill`, `subagent`, `long_term_memory`.
- `prediction_metrics` is the *allowed claim space* for edits to that component — Pillar 3 will only accept predictions phrased in these metrics. This is what stops the meta-agent from making vague promises.
- `risk` gates autonomy: in autonomous mode, `high`-risk components require a stricter eval margin and a human ack (file 07).
- `edit_surface: append_only` for memory enforces ACE's delta discipline at the manifest level.
- Build the manifest by *introspecting the existing code* (decorated tools, registered middleware, skill folders), not by hand-maintaining a parallel list — otherwise it drifts, which violates "docs track reality."

---

## 4.2 Pillar 2 — Experience observability: trajectory schema + distiller

This is gap `G2`. Two parts: a **raw trajectory record** (per task run) and a **distiller** that rolls raw records into a queryable evidence corpus.

### 4.2.1 Raw trajectory record

One JSONL row per task run, written by the runtime (extends existing session storage). Normative fields:

```jsonc
{
  "trajectory_id": "tj_2026-06-20T...",
  "task": { "instruction": "...", "repo": "...", "commit": "abc123", "source": "user_session | terminal_bench | synthetic" },
  "harness_version": "manifest@<git-sha>",     // which component versions were live
  "model": { "alias": "coding", "provider": "...", "is_local": true },
  "steps": [
    {
      "i": 0,
      "layer": "L2",                            // which of the 4 layers handled this step
      "action": "retrieve",                     // retrieve | tool_call | plan | generate | escalate
      "tool": "grep", "args": {...},
      "observation_digest": "sha256:...",       // store digest + truncated preview, not full blob
      "tokens": {"in": 0, "out": 0},
      "latency_ms": 220,
      "escalated_from": null                    // set if this step bumped L_n -> L_{n+1}
    }
  ],
  "final_diff": "<unified diff or null>",
  "outcome": {                                  // FROM THE VERIFIER (4.3), not self-reported
    "diff_applies": true,
    "build_passed": true,
    "tests": {"passed": 12, "failed": 0, "regressed": 0},
    "lint_clean": true, "types_clean": true,
    "label": "success"                          // success | partial | fail | error
  },
  "cost": { "usd": 0.0, "wall_s": 18.3 },
  "layer_distribution": { "L1": 0.6, "L2": 0.3, "L3": 0.0, "L4": 0.1 }  // fraction of steps per layer
}
```

`layer_distribution` is the **edge-native guardrail metric**: an improvement that raises pass@1 by escalating more to L4 has *regressed* the product. The verifier and the eval gate both watch it (file 08).

### 4.2.2 Distiller (AHE pillar 2)

Raw trajectories are multi-million-token. The meta-agent can't read them. The distiller produces a **layered, drill-down corpus**:

- **Layer A — index:** one line per trajectory (task, outcome label, layer distribution, cost). Cheap to scan.
- **Layer B — failure clusters:** group `fail`/`partial` trajectories by *root-cause class* (4.4 taxonomy). "23 failures, 14 of class `retrieval.stale_context`."
- **Layer C — exemplars:** for each cluster, 1–3 full drill-down traces with the decisive step highlighted.

The meta-agent reads A → picks a cluster → reads B's summary → drills into C's exemplars. This is the only way the evolution loop scales to real session volume without blowing its own context budget (which would be deeply ironic for an edge agent).

---

## 4.3 The verifier (gap `G3`) — the executable oracle

Wraps AutoCode's existing verification profiles (formatter / lint / typecheck / targeted-test) and hooks. Deterministic, no LLM. Given `(repo@commit, diff)`:

```
apply diff ──fail──▶ {label: error,   diff_applies: false}
   │ ok
build ──────fail──▶ {label: fail,     build_passed: false}
   │ ok
run tests ──fail──▶ {label: fail | partial, tests: {...}}   // regressed>0 => fail even if new tests pass
   │ ok
lint+types ─fail──▶ {label: partial,  lint_clean/types_clean: false}
   │ ok
              ──────▶ {label: success}
```

This verdict is the ground truth for the trajectory `outcome`, the teacher's primary signal (file 06), and the eval gate (file 08). It is the single most important component for trustworthiness because **everything downstream inherits its reliability.** Build it third (after manifest stub + trajectory recorder), test it hard against known-good and known-bad diffs.

For Terminal-Bench cases the verifier *is* the task's shipped test suite, run in the task's Docker container — so the same interface covers both your own corpus and TB.

---

## 4.4 Root-cause taxonomy (shared vocabulary)

Both the teacher (file 06) and the distiller (4.2.2) classify failures into this taxonomy, which maps each failure to **the layer/component that caused it** — so a fix can target that component. This is the bridge from "the agent failed" to "edit *this* manifest entry."

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

`tool.missing_capability` is the **flywheel's best fuel**: every time the agent had to escalate to L4 because no L1/L2 tool existed, that's a candidate new deterministic tool — which moves work *down* the ladder, improving cost *and* correctness, exactly per the north star. Anvil should rank failure clusters partly by how often they're `tool.missing_capability`.

---

## 4.5 Pillar 3 — Decision observability: the prediction contract

This is the discipline (file 01, Correction 8) that keeps autonomy from collapsing into trial-and-error. Every candidate edit is wrapped in a contract:

`anvil/patch_bundles/<id>/contract.json`:

```jsonc
{
  "bundle_id": "pb_001",
  "targets": ["tool.read_file.description"],     // manifest component ids; must exist
  "rationale": "Failures cluster tool.wrong_choice: read_file vs grep confusion on 11 cases.",
  "evidence": ["cluster:tool.wrong_choice", "exemplar:tj_...", "exemplar:tj_..."],  // distiller refs
  "prediction": {                                 // MUST use the component's allowed prediction_metrics
    "metric": "tool_selection_accuracy",
    "subset": "cluster:tool.wrong_choice",        // predictions are scoped, not global hand-waving
    "baseline": 0.42,
    "expected": 0.70,
    "min_acceptable": 0.55,                        // below this -> revert even if global eval is flat
    "no_regression_on": ["pass_at_1", "layer_distribution.L4", "wall_s_p50"]
  },
  "diff": "<the actual component edit, as a git patch>",
  "provenance": { "teacher_model": "...", "anvil_version": "...", "created": "..." }  // W3C PROV-style
}
```

The loop (file 07) then:
1. applies the bundle to a scratch harness,
2. runs the eval suite,
3. **scores the prediction**: did `tool_selection_accuracy` on the scoped subset reach `min_acceptable`? did anything in `no_regression_on` regress past tolerance?
4. **pass** → promote (canary); **fail** → revert *and log the prediction miss* as signal (calibration data on the meta-agent's judgment).

Three properties this gives you that bare patch-and-gate doesn't:
- **Scoped, falsifiable claims** — no "this should help generally."
- **Regression guards baked into every edit** — `no_regression_on` always includes the edge-native metrics (`layer_distribution.L4`, latency).
- **A meta-signal:** systematic prediction misses mean the loop's judgment is miscalibrated — a kill-switch trigger independent of eval scores.

---

## 4.6 Patch bundle (the unit that crosses back into the runtime)

A patch bundle is the *only* thing Anvil hands the runtime. It is exactly the source report's "patch bundle," extended with the prediction contract:

```
anvil/patch_bundles/pb_001/
  contract.json        # 4.5 — targets, prediction, provenance
  diff.patch           # the component edit(s), git-applyable
  eval_report.json     # full before/after on the eval suite (file 08)
  prediction_score.json# verdict on the contract's prediction
  decision.md          # human-readable: what/why/result, for AGENTS_CONVERSATION.MD
```

Promotion = `git apply diff.patch` on the runtime, with `decision.md` logged to the review trail. Rollback = `git revert`. Because components are file-level and git-tracked (Pillar 1), promotion and rollback are ordinary version control — no special machinery, fully auditable, consistent with the repo's existing discipline.

---

## 4.7 The escalation ladder, as routing logic

Anvil routes a failure cluster to the *cheapest sufficient* intervention (your north-star principle, the report's "escalation ladder," re-ordered per Correction 2):

```
cluster ──▶ is it tool.missing_capability?            ──yes──▶ synthesize new L1/L2 tool      (tier 1)
        ──▶ is it tool.wrong_choice / bad_args?       ──yes──▶ edit tool DESCRIPTION/schema    (tier 1)
        ──▶ is it retrieval.* / context.* / early_stop?──yes──▶ edit MIDDLEWARE                 (tier 2)
        ──▶ is it style.* / recurring task pattern?    ──yes──▶ append PLAYBOOK delta (ACE)      (tier 3)
        ──▶ is it reasoning.wrong_plan (prompt-shaped)?──yes──▶ GEPA-optimize the PROMPT         (tier 4)
        ──▶ none of the above sufficed after N cycles? ──────▶ consider DISTILLATION (file 10)    (tier 5)
```

Each tier is cheaper and more deterministic than the next. The ladder *is* the policy that keeps an edge agent edge-native while it self-improves: it always tries to push capability *down* toward L1/L2, never up toward more L4.

---

## 4.8 Where each component-kind's optimizer lives

| Component kind | Optimizer / method | Tier |
|----------------|--------------------|------|
| tool_implementation (new) | LLM synthesis + the verifier as oracle | 1 |
| tool_description / schema | LLM edit, eval-gated | 1 |
| middleware | LLM edit (often porting a known pattern, e.g. Ralph loop) | 2 |
| long_term_memory (playbook) | **ACE** generate–reflect–curate–prune | 3 |
| system_prompt | **GEPA** (the only kind routed to GEPA) | 4 |
| subagent | LLM edit, eval-gated | 2–3 |
| (local model weights) | **QLoRA / step-wise OPD (SOD)** | 5 |

This table is the whole method-to-component mapping in one place. Build tiers 1–3 first (file 09).

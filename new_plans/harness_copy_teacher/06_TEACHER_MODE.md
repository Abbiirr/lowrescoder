# 06 — Teacher Mode: Execution-Grounded Teaching

The report is right that teacher mode should be richer than a "better answer" — it should emit a structured teaching packet (diagnosis, critique, revision, patch). The correction (file 01, Correction 4): for a *coding* agent the primary signal is the **executable verdict**, not an LLM judge. This file specifies the teacher as a root-cause analyst grounded in the verifier, feeding ACE-style playbook evolution. Teacher mode is gap `G6` and the **first user-visible capability to ship** (file 09).

---

## 6.0 What the teacher consumes and emits

**Consumes** (all already produced by earlier gaps):
- the task + the **student trajectory** (file 04 §4.2),
- the **verifier verdict** (file 04 §4.3) — the ground truth,
- optionally a **stronger run's trajectory** (self-distillation channel C) for contrast,
- the relevant **playbook** (durable-memory plane).

**Emits** a teaching packet:

```jsonc
{
  "packet_id": "tp_...",
  "trajectory_id": "tj_...",
  "verdict": { ... },                       // copied from verifier; the anchor
  "root_cause": {                           // file 04 §4.4 taxonomy
    "class": "tool.missing_capability",
    "evidence_step": 7,                     // the decisive step in the trajectory
    "explanation": "Escalated to L4 to compute the call graph because no L1 tool exposed it."
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
  "playbook_delta": "<ACE-style delta, if the lesson is a reusable heuristic>"
}
```

Two distinct outputs, matching the report's "two learning paths":
- `playbook_delta` → **online verbal learning** (no weights; loads into runtime memory; ACE).
- `harness_fix` → a candidate for the **self-maintenance loop** (file 07), which turns it into a prediction-contracted patch bundle.

---

## 6.1 The signal hierarchy (Correction 4, made concrete)

The teacher scores in this strict order; LLM judgment only enters at the bottom, only where execution can't decide:

```
1. diff_applies?     ── deterministic (git apply)
2. build_passed?     ── deterministic (compiler/interpreter)
3. tests_pass?       ── deterministic; regressed>0 is an automatic FAIL
4. lint + types?     ── deterministic (ruff/mypy, your existing profiles)
─────────────────────  everything above is ground truth
5. style/explanation ── LLM-judge, with the report's bias controls:
                         randomize order, rotate judge model, validate vs human spot-check
```

This inversion (vs the report's judge-forward stance) is what makes your teacher trustworthy and hard to reward-hack: a passing test suite is far harder to fake than a judge's approval. Reserve the judge for the genuinely judgment-shaped residue (idiomatic style, comment quality, commit-message clarity).

---

## 6.2 Root-cause attribution is the teacher's real job

A teacher that only emits a "better diff" is a worse fit for AutoCode than one that says *which component caused the failure.* The taxonomy (file 04 §4.4) maps each failure class to the layer/component responsible, so the teaching packet's `harness_fix` can target a specific manifest entry.

Worked example:
- **Verdict:** tests failed.
- **Trajectory:** at step 7 the agent escalated L2→L4 to reason about a call graph it couldn't retrieve.
- **Class:** `tool.missing_capability` (no L1/L2 call-graph tool existed).
- **`harness_fix`:** propose a tree-sitter-based L1 call-graph tool.
- **Why this is the high-value path:** it moves work *down* the ladder (L4→L1) for *all future tasks* of this shape, improving both correctness and the edge-cost metric. A teacher that just handed over a correct diff would fix one task; this fixes the *class*.

Rank teaching packets partly by how often their root-cause class is `tool.missing_capability` — that's the flywheel's best fuel (file 04 §4.4).

---

## 6.3 ACE wiring: turning critiques into a durable playbook

The report's "store the teacher's critiques as episodic memory" is exactly **ACE**, and ACE solves the two failure modes a naive memory loop hits (brevity bias, context collapse). Map the roles onto Anvil:

| ACE role | In Anvil | Output |
|----------|----------|--------|
| **Generator** | the AutoCode runtime loop | trajectories |
| **Reflector** | teacher's root-cause + revision step | concrete insights from successes *and* errors |
| **Curator** | playbook-delta integrator | structured **delta** appended to the per-language playbook |
| **Pruner** | periodic merge job | overlapping deltas → concise "Master Rules" |

Playbook storage (a durable-memory plane artifact the runtime loads), per-language so it stays scoped:

```
.autocode/playbook/
  python.md        # append-only deltas + a "Master Rules" section the Pruner maintains
  rust.md
  _meta.json       # delta count, last prune, provenance per rule
```

**Delta discipline (the manifest enforces `edit_surface: append_only`):**
- Never rewrite the playbook wholesale (that's context collapse).
- Append structured deltas: `{ trigger, observation, rule, evidence_trajectory }`.
- The Pruner merges overlapping rules into Master Rules *periodically*, preserving detail (ACE's anti-brevity-bias design), and every merge is itself a prediction-contracted change (does pass@1 hold after pruning?).

**Why playbook-over-fine-tuning for most lessons:** ACE shows context adaptation beats *both* fine-tuning and prompt optimization on overhead, and adapts from *natural execution feedback* without labels — which is exactly your situation (you have execution feedback, not labeled gold answers, for most of your own sessions). The playbook is a tier-3 lever: cheap, reversible, no training.

---

## 6.4 Online vs offline teacher paths

| | Online (verbal) | Offline (structural / weight) |
|---|----------------|-------------------------------|
| Mechanism | playbook delta loaded into runtime memory | patch bundle (tools/middleware) or distillation |
| Speed | immediate next session | next Anvil cycle / next training run |
| Cost | ~free | cheap (harness) to expensive (weights) |
| When | recurring task patterns, style, heuristics | structural gaps, missing tools, model-level deficits |
| Risk | low (revert = delete delta) | medium–high (gated by prediction contract + eval) |

Ship the **online path first** (file 09): teacher produces playbook deltas, you review them, approved ones load into the runtime. This delivers visible value with no autonomous editing and no training. The offline path is the bridge into the self-maintenance loop (file 07).

---

## 6.5 Teacher mode as a runtime feature vs an Anvil feature

A subtlety worth deciding early: there are **two** plausible "teacher modes," and they're different products.

1. **Anvil teacher (offline):** improves AutoCode itself across sessions. This is the self-improvement program. Primary.
2. **Runtime teacher (online, optional):** a strong model critiques the *user's* code in real time inside a session ("review this PR"). This is a normal agent feature, not self-improvement, and it would need cloud opt-in per the invariants (it's a runtime cloud call). Useful, but **don't conflate it with the self-improvement program** — it's a different roadmap item with different invariant implications.

This file specifies #1. If you also want #2, scope it separately as a runtime feature with explicit cloud opt-in, so it doesn't muddy the offline/runtime split that makes #1 invariant-compliant.

---

## 6.6 Summary

The teacher is a **root-cause analyst grounded in an executable oracle**, not a gold-answer generator and not a judge. It emits two things: a reversible playbook delta (online, ship first) and a candidate harness fix (offline, feeds the loop). ACE gives the playbook a durable, collapse-resistant structure. The whole thing runs offline in Anvil and changes the runtime only through eval-gated, prediction-contracted artifacts.

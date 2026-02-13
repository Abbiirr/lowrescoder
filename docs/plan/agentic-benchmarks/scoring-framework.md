# Scoring Framework: Measuring Agent Quality

## Overview

Agent quality is multidimensional. A single number (like "82/100") hides too much. This framework produces a **12-dimension radar chart** showing the agent's strengths and weaknesses.

---

## Score Structure

### Per-Scenario Score
Each scenario produces:
```json
{
  "scenario_id": "A1-grep-challenge",
  "dimensions": [1, 12],
  "verdict": "PASS",
  "scores": {
    "correctness": 0.9,
    "tool_efficiency": 0.7,
    "cost_efficiency": 0.85
  },
  "raw_metrics": {
    "tool_calls": 4,
    "optimal_tool_calls": 2,
    "tokens_consumed": 1200,
    "wall_time_s": 12,
    "attempts": 1,
    "files_read": 3,
    "files_modified": 0
  }
}
```

### Per-Dimension Score
Aggregate scenario scores into dimension scores:
```json
{
  "dimension_1_tool_routing": {
    "score": 0.78,
    "scenarios_tested": 3,
    "scenarios_passed": 2,
    "avg_tool_efficiency": 0.72
  }
}
```

### Overall Agent Quality Score
Weighted combination of all 12 dimensions:

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| 1. Tool Routing | 10% | Foundational — wrong tool = everything downstream fails |
| 2. Context Retrieval | 12% | Highest-impact single capability (Confucius +6.6 pts) |
| 3. Edit Accuracy | 12% | Most common failure mode in practice |
| 4. Error Recovery | 10% | Orthogonal to correctness — separately valuable |
| 5. Fault Tolerance | 5% | Important for production, less for dev |
| 6. Multi-File Coordination | 10% | Scales with project complexity |
| 7. Context Scaling | 8% | Matters for real codebases (100K+ tokens) |
| 8. Planning Quality | 8% | Required for complex tasks |
| 9. Recovery from Corruption | 5% | Niche but critical for reliability |
| 10. Regression Prevention | 10% | Enterprise requirement |
| 11. Consistency (pass^k) | 5% | Production reliability |
| 12. Cost Efficiency | 5% | Edge deployment advantage |

**Total: 100%**

---

## Verdicts

### Per-Scenario Verdicts
| Verdict | Meaning | Exit Code |
|---------|---------|-----------|
| `PASS` | Acceptance checks pass, score above threshold | 0 |
| `FAIL` | Product regression — agent capability gap | 1 |
| `INFRA_FAIL` | Infrastructure issue — not agent's fault | 2 |
| `FLAKY` | Inconsistent results across runs | 3 |

### Per-Lane Verdicts (aggregated)
| Lane | PASS Criteria |
|------|--------------|
| `pr_core` | Calc+BugFix+CLI: replay-first mandatory, deterministic graders only, `>=2/3` for stochastic fresh runs |
| `regression_nightly` | All regression scenarios PASS at pass^3 (3 consecutive passes), LLM grader sampled |
| `capability` | Median score >= threshold, `>=2/3` runs pass |
| `stress` | Degradation within acceptable bounds |
| `external_pilot` | Resolve rate >= baseline (SWE-bench pilot >=50%, Terminal-Bench pilot >=40%) |

### PR Core Lane Policy

The PR Core lane is the strict subset that runs on every pull request. Designed for minimal token burn:

- **Scenarios:** `E2E-Calc` + `E2E-BugFix` + `E2E-CLI` (3 scenarios only)
- **Evaluation order:** Replay-first (re-score saved artifacts with current rubric); fresh generation only when code changes affect scenario-relevant paths
- **Grader:** Deterministic only (build/test pass, acceptance checks, binary criteria). **LLM grader is OFF by default** — opt-in via `--with-llm-grader` for sampled nightly runs
- **Pass criterion:** `>=2/3` runs pass for stochastic fresh generation; single-pass sufficient for replay
- **Budget caps:** Per-scenario `token_cap`, `tool_call_cap`, `time_cap_s` enforced
- **pass^3 is NOT required on PR** — moved to nightly consistency lane to avoid token cost explosion

---

## The Scaffold Delta Metric

The most important single number:

```
scaffold_delta = resolve_rate(model + HybridCoder) - resolve_rate(model + naive_prompt)
```

**How to measure:**
1. Run the scenario suite with HybridCoder's full 4-layer system → `rate_full`
2. Run the same suite with a naive scaffold (single prompt, no tools) → `rate_naive`
3. `scaffold_delta = rate_full - rate_naive`

**Interpretation:**
- `scaffold_delta > 15%`: Excellent — agent adds substantial value
- `scaffold_delta 5-15%`: Good — agent is helpful
- `scaffold_delta < 5%`: Weak — agent adds minimal value over raw model
- `scaffold_delta < 0%`: Broken — agent is HURTING performance

**Run with multiple models to confirm:**
- If scaffold_delta is consistent across Qwen3-8B, GPT-4, Claude → the delta IS agent quality
- If scaffold_delta varies wildly by model → the agent is model-dependent (bad)

---

## Layer Attribution

For HybridCoder specifically, track which layer resolved each task:

```json
{
  "layer_attribution": {
    "L1_deterministic": 12,
    "L2_retrieval": 5,
    "L3_constrained": 3,
    "L4_full_reasoning": 10,
    "total_tasks": 30
  },
  "zero_token_rate": 0.40,
  "l1_l2_rate": 0.57
}
```

**Target:** At least 30% of regression-lane tasks should resolve at L1-L2 (zero or near-zero LLM tokens).

---

## Anti-Gaming Measures

Prevent tests from being gamed:

1. **Outcome-only grading:** Score the final state, not the path. "Avoid checking that agents followed very specific steps" (Anthropic).
2. **Multiple valid solutions:** Design scenarios where multiple correct answers exist. Don't hardcode a single expected patch.
3. **Mutation testing:** Periodically vary the scenarios (different variable names, different file structures) to prevent memorization.
4. **Held-out scenarios:** Keep a set of scenarios that are never used in development — only in final evaluation.
5. **Model diversity:** Run with at least 2 different models to confirm agent quality is model-independent.

---

## Reporting Format

### Console Output (per-run)
```
=== Agent Quality Report ===
Model: Qwen3-8B Q4_K_M
Scenarios: 20 run, 16 passed, 2 failed, 2 infra_fail

Dimension Scores:
  1. Tool Routing:      0.78 ████████░░
  2. Context Retrieval:  0.85 █████████░
  3. Edit Accuracy:      0.92 █████████░
  4. Error Recovery:     0.65 ██████░░░░
  5. Fault Tolerance:    0.70 ███████░░░
  6. Multi-File:         0.80 ████████░░
  7. Context Scaling:    0.75 ████████░░
  8. Planning:           0.60 ██████░░░░
  9. Recovery:           0.55 ██████░░░░
  10. Regression Prev:   0.88 █████████░
  11. Consistency:       0.90 █████████░
  12. Cost Efficiency:   0.82 ████████░░

Overall: 0.78 / 1.00
Scaffold Delta: +18.2% (vs naive prompt)
Zero-Token Rate: 35% (7/20 tasks resolved at L1-L2)
```

### JSON Artifact
Full machine-readable results saved alongside existing benchmark JSON.

### Markdown Report
Human-readable report in `docs/qa/test-results/` following existing convention.

---

## Suite Configuration Schema

Every scenario and lane must declare these operational fields explicitly. This prevents implementation drift and accidental token-cost creep.

### Per-Scenario Config Fields

```json
{
  "scenario_id": "E2E-BugFix",
  "suite_type": "regression",
  "grader_mix": {
    "primary": "deterministic",
    "secondary": "heuristic",
    "tertiary": "llm_judge"
  },
  "grader_defaults": {
    "pr": ["deterministic"],
    "nightly": ["deterministic", "heuristic"],
    "weekly": ["deterministic", "heuristic", "llm_judge"]
  },
  "sampling_policy": "pr_required",
  "token_cap": 8000,
  "tool_call_cap": 50,
  "time_cap_s": 300,
  "nondeterminism_policy": "retry_once"
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `suite_type` | `"regression" \| "capability" \| "stress"` | Which lane this scenario belongs to |
| `grader_mix` | `{primary, secondary, tertiary}` | Grader priority chain |
| `grader_defaults` | `{pr, nightly, weekly}` | Which graders run in each lane |
| `sampling_policy` | `"pr_required" \| "nightly" \| "weekly_external"` | When this scenario runs |
| `token_cap` | `int` | Max input+output tokens per run |
| `tool_call_cap` | `int` | Max tool calls per run |
| `time_cap_s` | `int` | Max wall-time in seconds |
| `nondeterminism_policy` | `"retry_once" \| "pass_2_of_3" \| "deterministic"` | How to handle stochastic results |

### Lane Defaults

| Lane | Graders Active | Sampling | Repetition |
|------|---------------|----------|------------|
| PR Core | deterministic only | every PR | 1 run (replay); fresh only if code delta |
| Regression Nightly | deterministic + heuristic | nightly | pass^3 (3 runs) |
| Capability | deterministic + heuristic + sampled LLM | nightly | `>=2/3` of 3 runs |
| Stress | deterministic + fault injection | weekly | 5 runs per fault rate |
| External-Pilot | deterministic (harness pass/fail) | weekly (pilot), release (full) | 1 run default; parity = 3 runs |

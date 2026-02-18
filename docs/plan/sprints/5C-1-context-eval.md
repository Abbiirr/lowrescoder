# Sprint 5C-1: Context Quality Eval

> Status: **NOT STARTED**
> Sprint: 5C (Context Quality + AgentBus)
> Est. Hours: ~8h (3h tests + 5h impl)
> Dependencies: 5A-4 (Eval Harness), Task Bank
> Owner: Claude

---

## Goal

Prove L1+L2 context quality matches L4-curated at zero cost. This is the architecture's core value proposition.

---

## TDD Tests (Write First)

- [ ] `test_context_precision` - file-set precision measured correctly
- [ ] `test_context_recall` - file-set recall measured correctly
- [ ] `test_context_f1` - F1 computed as harmonic mean of precision and recall

## Implementation

- [ ] Run eval harness on task bank with all 4 strategies (L1, L2, L1+L2, LLM-curated)
- [ ] Measure precision, recall, F1 per strategy per scenario
- [ ] Context-budget sweep: small (2k), medium (8k), large (16k) tokens (Section 15.19 R5)
- [ ] Wrong-context negative control: verify system fails on deliberately incorrect context (R5)
- [ ] Routing-regret metric: compare routing decisions vs oracle (R5, target: regret < 15%)
- [ ] Compare L1+L2 vs OpenCode baseline on identical tasks (MAJOR-5)
- [ ] Generate cost/latency breakdown per strategy

## Acceptance Criteria

- [ ] Eval suite runs on internal task bank (>= 30 scenarios)
- [ ] L1+L2 vs L4-curated comparison with precision/recall/F1 metrics
- [ ] Context-budget sweep completed (small/medium/large)
- [ ] Wrong-context negative control passes (system fails on bad context)
- [ ] Routing-regret metric computed (target < 15%)
- [ ] Cost/latency breakdown per strategy documented
- [ ] Failure taxonomy documented with examples
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_context_eval.py`
- QA artifact: `docs/qa/test-results/sprint-5c-1-context-eval.md`

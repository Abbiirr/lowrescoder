# Sprint 5A-4: Eval Harness

> Status: **NOT STARTED**
> Sprint: 5A (Identity + Eval)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: None
> Owner: Claude

---

## Goal

Evaluation harness skeleton: scenario format, deterministic grader, cost/latency capture.

---

## TDD Tests (Write First)

- [ ] `test_eval_scenario_format` - EvalScenario dataclass validates correctly
- [ ] `test_deterministic_grader` - grader produces reproducible scores for identical inputs
- [ ] `test_cost_capture` - cost/latency metrics captured per scenario run

## Implementation

- [ ] Create `src/hybridcoder/eval/harness.py`
- [ ] Create `src/hybridcoder/eval/context_packer.py`
- [ ] Implement `EvalScenario` dataclass (id, task_type, input, gold_files, gold_symbols)
- [ ] Implement `ContextStrategy` interface (L1, L2, L1+L2, LLM-curated)
- [ ] Implement `EvalHarness.run()` - runs scenarios against strategies
- [ ] Implement deterministic grader (precision, recall, F1)
- [ ] Capture cost (tokens) and latency per run

## Acceptance Criteria

- [ ] Eval harness runs scenarios against context strategies
- [ ] Context packer interfaces for L1, L2, L1+L2, LLM-curated
- [ ] Deterministic grader produces reproducible results
- [ ] Cost and latency captured per scenario
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] 3 dummy scenarios run end-to-end

## Artifacts

- New files: `src/hybridcoder/eval/harness.py`, `src/hybridcoder/eval/context_packer.py`
- Test file: `tests/unit/test_eval_harness.py`
- QA artifact: `docs/qa/test-results/sprint-5a-4-eval-harness.md`

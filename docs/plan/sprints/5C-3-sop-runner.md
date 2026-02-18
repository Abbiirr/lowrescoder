# Sprint 5C-3: SOPRunner

> Status: **NOT STARTED**
> Sprint: 5C (Context Quality + AgentBus)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: 5C-2 (AgentBus)
> Owner: Claude

---

## Goal

Deterministic pipeline executor that runs multi-step agent workflows with gate checks.

---

## TDD Tests (Write First)

- [ ] `test_sop_sequential` - steps execute in order
- [ ] `test_sop_gate_check` - gate failure stops pipeline
- [ ] `test_sop_chaining` - output from step N flows as input to step N+1

## Implementation

- [ ] Implement `SOPStep` dataclass (agent, action, input_from, output_type, gate)
- [ ] Implement `SOPRunner.run()` - executes steps sequentially
- [ ] Gate checking: stop on gate failure, return structured result
- [ ] Data chaining: output from previous step available to next

## Acceptance Criteria

- [ ] SOPRunner executes multi-step workflows
- [ ] Steps execute in correct order
- [ ] Gate failures stop the pipeline
- [ ] Output chaining works
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_sop_runner.py`
- QA artifact: `docs/qa/test-results/sprint-5c-3-sop-runner.md`

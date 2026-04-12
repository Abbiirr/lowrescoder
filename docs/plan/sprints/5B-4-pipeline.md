# Sprint 5B-4: LLMLOOP Pipeline

> Status: **NOT STARTED**
> Sprint: 5B (LLMLOOP v1)
> Est. Hours: ~7h (2h tests + 5h impl)
> Dependencies: 5B-1 (Architect), 5B-2 (Editor), 5B-3 (Verification)
> Owner: Claude

---

## Goal

Wire Architect -> Editor -> Verify into a feedback loop (max 3 iterations) with budget enforcement.

---

## TDD Tests (Write First)

- [ ] `test_llmloop_full_cycle` - full Architect->Editor->Verify cycle completes
- [ ] `test_llmloop_max_3_iter` - loop stops after 3 iterations max
- [ ] `test_llmloop_budget` - budget policy enforced (local=$0, cloud=capped)

## Implementation

- [ ] Create `LLMLOOP` class wiring Architect -> Editor -> Verify
- [ ] Implement feedback loop: on verification failure, feed errors back to Architect
- [ ] Enforce max 3 iterations
- [ ] Enforce budget policy (local = $0, cloud = hard token cap)
- [ ] Record first_token_latency and end_to_end_latency per run (Section 15.22)
- [ ] Escalate to user after max iterations with partial result + diagnostics

## Acceptance Criteria

- [ ] Full LLMLOOP cycle works end-to-end
- [ ] Loop converges within 3 iterations on test cases
- [ ] Budget policy enforced
- [ ] Latency metrics recorded (first_token, end_to_end)
- [ ] User escalation after max iterations
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] 10-task bank benchmark (success rate, latency, token cost)

## Artifacts

- Test file: `tests/unit/test_llmloop.py`
- QA artifact: `docs/qa/test-results/sprint-5b-4-pipeline.md`

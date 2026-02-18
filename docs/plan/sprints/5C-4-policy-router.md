# Sprint 5C-4: Policy Router

> Status: **NOT STARTED**
> Sprint: 5C (Context Quality + AgentBus)
> Est. Hours: ~7h (2h tests + 5h impl)
> Dependencies: 5A-2 (ProviderRegistry)
> Owner: Claude

---

## Goal

Deterministic escalation chain: L1/L2 -> L3 local -> L4 local with delegation caps.

---

## TDD Tests (Write First)

- [ ] `test_router_escalation` - router escalates L1->L2->L3->L4 correctly
- [ ] `test_router_delegation_caps` - 2-agent cap and 3 messages/task-edge enforced
- [ ] `test_router_no_recursion` - router prevents recursive delegation

## Implementation

- [ ] Implement deterministic policy router
- [ ] Escalation chain: L1/L2 -> L3 -> L4
- [ ] Delegation hard caps: 2 agents default, 3 messages/task-edge
- [ ] No recursion protection
- [ ] Route based on task complexity classification

## Acceptance Criteria

- [ ] Policy router escalates L1 -> L2 -> L3 -> L4 correctly
- [ ] Delegation caps enforced (2 agents, 3 messages default)
- [ ] No recursion possible
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] 20-task routing accuracy benchmark

## Artifacts

- Test file: `tests/unit/test_policy_router.py`
- QA artifact: `docs/qa/test-results/sprint-5c-4-policy-router.md`

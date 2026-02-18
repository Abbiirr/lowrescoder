# Sprint 5A-5: Identity Wire

> Status: **NOT STARTED**
> Sprint: 5A (Identity + Eval)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: 5A-1 (AgentCard)
> Owner: Claude

---

## Goal

Wire agent identity into session messages and tool calls so every action is attributed.

---

## TDD Tests (Write First)

- [ ] `test_message_has_agent_id` - every session message includes agent_id field
- [ ] `test_tool_call_has_agent_id` - every tool call includes agent_id field

## Implementation

- [ ] Add `agent_id` field to session message format
- [ ] Add `agent_id` field to tool call metadata
- [ ] Wire AgentCard into SubagentLoop
- [ ] Ensure agent identity flows through entire request chain

## Acceptance Criteria

- [ ] Messages tagged with agent_id
- [ ] Tool calls tagged with agent_id
- [ ] Agent identity preserved through SubagentLoop
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_identity_wire.py`
- QA artifact: `docs/qa/test-results/sprint-5a-5-identity-wire.md`

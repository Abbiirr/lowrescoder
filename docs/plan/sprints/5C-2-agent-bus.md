# Sprint 5C-2: AgentBus

> Status: **NOT STARTED**
> Sprint: 5C (Context Quality + AgentBus)
> Est. Hours: ~7h (2h tests + 5h impl)
> Dependencies: 5A-1 (AgentCard)
> Owner: Claude

---

## Goal

Typed messaging system (REQUEST, RESULT, ISSUE) with SQLite persistence and simulation harness (Section 15.25).

---

## TDD Tests (Write First)

- [ ] `test_agentbus_send_receive` - messages sent and received correctly
- [ ] `test_agentbus_typed_messages` - REQUEST, RESULT, ISSUE types validated
- [ ] `test_agentbus_persistence` - messages persist to SQLite and survive restart
- [ ] `test_agentbus_simulation` - simulation harness with synthetic agents works

## Implementation

- [ ] Create `AgentBus` class with send/subscribe/get_pending/get_thread
- [ ] Create `MessageStore` with SQLite persistence
- [ ] Implement `AgentMessage` dataclass (id, from, to, type, payload, task_id, timestamp)
- [ ] Implement `MessageType` enum (REQUEST, RESULT, ISSUE)
- [ ] Build simulation harness: synthetic Scout->Architect->Engineer flow
- [ ] >= 10 fixture scenarios for simulation (Section 15.25)

## Acceptance Criteria

- [ ] AgentBus sends/receives typed messages
- [ ] MessageStore persists to SQLite
- [ ] Simulation harness works with synthetic agents
- [ ] >= 10 deterministic fixture scenarios pass
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_agent_bus.py`
- QA artifact: `docs/qa/test-results/sprint-5c-2-agent-bus.md`

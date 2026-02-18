# Sprint 5A-1: AgentCard

> Status: **NOT STARTED**
> Sprint: 5A (Identity + Eval)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: None
> Owner: Claude

---

## Goal

Implement AgentCard, AgentRole enum, and ModelSpec dataclass as the foundation for agent identity.

---

## TDD Tests (Write First)

- [ ] `test_agent_card_creation` - AgentCard can be instantiated with all fields
- [ ] `test_agent_role_enum` - All 6 roles exist (COORDINATOR, ARCHITECT, ENGINEER, REVIEWER, SCOUT, CUSTOM)
- [ ] `test_agent_card_serialization` - AgentCard serializes to/from dict/JSON
- [ ] `test_model_spec_defaults` - ModelSpec l1_only(), l3_default(), l4_default() factory methods work

## Implementation

- [ ] Create `src/autocode/agent/identity.py`
- [ ] Implement `AgentRole` StrEnum with 6 roles
- [ ] Implement `ModelSpec` dataclass with provider, model, layer, temperature, max_tokens
- [ ] Implement `ModelSpec` factory methods: l1_only(), l3_default(), l4_default()
- [ ] Implement `AgentCard` dataclass with all fields (id, name, role, model, skills, tool_filter, system_prompt_template, priority, max_iterations, context_budget, can_spawn_subagents, can_approve)
- [ ] Add serialization (to_dict / from_dict)

## Acceptance Criteria

- [ ] AgentCard, AgentRole, ModelSpec implemented and tested
- [ ] Factory methods produce correct defaults
- [ ] Serialization round-trips correctly
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- New file: `src/autocode/agent/identity.py`
- Test file: `tests/unit/test_identity.py`
- QA artifact: `docs/qa/test-results/sprint-5a-1-agent-card.md`

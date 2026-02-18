# Sprint 5B-1: Architect Agent

> Status: **NOT STARTED**
> Sprint: 5B (LLMLOOP v1)
> Est. Hours: ~7h (2h tests + 5h impl)
> Dependencies: 5A-2 (ProviderRegistry), 5A-3 (Adapters)
> Owner: Claude

---

## Goal

L4 Architect agent that plans edits and produces structured EditPlan output.

---

## TDD Tests (Write First)

- [ ] `test_architect_produces_edit_plan` - Architect outputs valid EditPlan JSON
- [ ] `test_architect_structured_output` - EditPlan has required fields (file, edits, reasoning)
- [ ] `test_architect_graceful_degradation` - when reasoning fails, presents to user instead of burning retries

## Implementation

- [ ] Define `EditPlan` dataclass (file, edits list, reasoning, test_command)
- [ ] Define `Edit` dataclass (type, location, old_content, new_content, context)
- [ ] Implement Architect agent using L4 (Qwen3-8B via Ollama)
- [ ] Architect prompt: take task + L1/L2 curated context -> produce EditPlan
- [ ] Graceful degradation: present partial result to user after max retries
- [ ] Scoped narrowly: single-function reasoning, not multi-file planning

## Acceptance Criteria

- [ ] Architect produces valid EditPlan from task description
- [ ] EditPlan JSON validates against schema
- [ ] Graceful degradation works (no silent failures)
- [ ] Single-function scope enforced
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] EditPlan quality on 5 task bank scenarios

## Artifacts

- Test file: `tests/unit/test_architect.py`
- QA artifact: `docs/qa/test-results/sprint-5b-1-architect.md`

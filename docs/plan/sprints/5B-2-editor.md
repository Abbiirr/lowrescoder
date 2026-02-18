# Sprint 5B-2: Editor Agent

> Status: **NOT STARTED**
> Sprint: 5B (LLMLOOP v1)
> Est. Hours: ~7h (2h tests + 5h impl)
> Dependencies: 5B-0 (Editor Bakeoff), 5B-1 (Architect)
> Owner: Claude

---

## Goal

Editor agent that applies EditPlan using the model selected by the bakeoff (L3 constrained generation or L4).

---

## TDD Tests (Write First)

- [ ] `test_editor_applies_edit` - Editor correctly applies an EditPlan to source file
- [ ] `test_editor_grammar_constrained` - output conforms to grammar constraints (if using L3)
- [ ] `test_editor_rollback` - failed edit can be rolled back

## Implementation

- [ ] Implement Editor agent using bakeoff-selected model
- [ ] If L3: use llama-cpp-python native grammar constraints
- [ ] If L4-only: use structured output prompting
- [ ] Apply edits to source files
- [ ] Rollback support (restore original on failure)

## Acceptance Criteria

- [ ] Editor applies EditPlan using selected model
- [ ] Output conforms to expected format
- [ ] Rollback works on failure
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Edit success rate on task bank fixtures

## Artifacts

- Test file: `tests/unit/test_editor.py`
- QA artifact: `docs/qa/test-results/sprint-5b-2-editor.md`

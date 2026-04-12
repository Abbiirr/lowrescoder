# Sprint 5B-3: Verification Gate

> Status: **NOT STARTED**
> Sprint: 5B (LLMLOOP v1)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: 5B-2 (Editor)
> Owner: Claude

---

## Goal

Post-edit verification using tree-sitter syntax check + Jedi semantic validation.

---

## TDD Tests (Write First)

- [ ] `test_verify_treesitter` - tree-sitter catches syntax errors in edited file
- [ ] `test_verify_jedi` - Jedi catches semantic errors (undefined refs, type mismatches)
- [ ] `test_verify_rejects_broken` - verification gate rejects files with errors

## Implementation

- [ ] Integrate tree-sitter for post-edit syntax validation
- [ ] Integrate Jedi for semantic validation (undefined refs, imports)
- [ ] Return structured verification result (pass/fail + error list)
- [ ] Feed errors back as structured data for Architect retry

## Acceptance Criteria

- [ ] tree-sitter validates syntax after each edit
- [ ] Jedi validates semantics after each edit
- [ ] Broken files are rejected with error details
- [ ] Error details are structured (for feedback loop)
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_verification.py`
- QA artifact: `docs/qa/test-results/sprint-5b-3-verification.md`

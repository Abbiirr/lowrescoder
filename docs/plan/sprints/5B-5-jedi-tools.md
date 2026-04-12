# Sprint 5B-5: Jedi Tools

> Status: **NOT STARTED**
> Sprint: 5B (LLMLOOP v1)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: None (parallel with 5B-1 to 5B-4)
> Owner: Claude

---

## Goal

Jedi-based semantic tools: find_definition, find_references, list_symbols, get_type_info.

---

## TDD Tests (Write First)

- [ ] `test_jedi_find_def` - find_definition returns correct file + line for known symbol
- [ ] `test_jedi_find_refs` - find_references returns all usage locations
- [ ] `test_jedi_symbols` - list_symbols returns all symbols in a file
- [ ] `test_jedi_cross_file` - cross-file references work correctly

## Implementation

- [ ] Integrate Jedi library
- [ ] Implement `find_definition(symbol, file, line)` -> Definition location
- [ ] Implement `find_references(symbol, file, line)` -> List of reference locations
- [ ] Implement `list_symbols(file)` -> List of symbols with types
- [ ] Implement `get_type_info(symbol, file, line)` -> Type information
- [ ] Register as L1 tools in tool registry

## Acceptance Criteria

- [ ] `find_definition` working via Jedi
- [ ] `find_references` working via Jedi
- [ ] `list_symbols` working via Jedi
- [ ] `get_type_info` working via Jedi
- [ ] Cross-file references work
- [ ] All operations complete in < 100ms
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Latency benchmark: all operations < 100ms

## Artifacts

- Test file: `tests/unit/test_jedi_tools.py`
- QA artifact: `docs/qa/test-results/sprint-5b-5-jedi-tools.md`

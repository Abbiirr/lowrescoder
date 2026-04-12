# Sprint 5B-6: Full Edit Command (NON-DEFERRABLE P0)

> Status: **NOT STARTED**
> Sprint: 5B (LLMLOOP v1)
> Est. Hours: ~10h (3h tests + 7h impl) -- 2x buffer = 20h max before escalation
> Dependencies: 5B-4 (LLMLOOP Pipeline)
> Owner: Claude
> Risk: **HIGH** -- See Section 15.13 (D3 fail-fast hard gate)

---

## Goal

Full edit command with fuzzy matching, whitespace normalization, diff preview, and accept/reject flow. This is the HIGHEST RISK sub-sprint and NON-DEFERRABLE.

---

## TDD Tests (Write First)

- [ ] `test_edit_fuzzy_match` - SequenceMatcher finds approximate match location
- [ ] `test_edit_whitespace_norm` - whitespace normalization handles tabs/spaces/CRLF
- [ ] `test_edit_diff_preview` - diff preview shows proposed change before applying
- [ ] `test_edit_accept_reject` - user can accept or reject proposed edit

## Fail-Fast Gate (Section 15.13 - HARD GATE)

- [ ] After first 3 TDD test implementations: fuzzy matching success rate >= 50% on fixtures
  - If FAILS: HALT and reassess approach (whole-file replace fallback?)
- [ ] Budget: if implementation exceeds 20h, HALT and escalate to user

## Implementation

- [ ] Implement LLM output parser for edit format
- [ ] Implement fuzzy matching using SequenceMatcher
- [ ] Implement whitespace normalization (tabs/spaces/CRLF/LF)
- [ ] Implement diff preview (unified diff with +/- markers)
- [ ] Implement accept/reject flow
- [ ] Handle edge cases:
  - [ ] Multiline strings
  - [ ] Indentation-only diffs
  - [ ] Same block appearing in multiple locations
  - [ ] Large files (10k+ lines) -- SequenceMatcher is O(n^2)

## Fallback Plan

If fuzzy matching fails threshold:
- [ ] Fall back to whole-file replace (Architect outputs complete replacement)
- [ ] Document decision and evidence

## Acceptance Criteria

- [ ] Edit command applies LLM-suggested edits to source files
- [ ] Fuzzy matching handles approximate locations
- [ ] Whitespace normalization works across platforms
- [ ] Diff preview shown before applying
- [ ] User can accept or reject
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] 10 realistic patches (success rate >= 80%)

## Artifacts

- Test file: `tests/unit/test_edit_command.py`
- QA artifact: `docs/qa/test-results/sprint-5b-6-edit-command.md`

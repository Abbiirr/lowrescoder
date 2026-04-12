# Sprint 5A0-3: Token Counting

> Status: **NOT STARTED**
> Sprint: 5A0 (Quick Wins)
> Est. Hours: ~3.5h (1h tests + 2.5h impl)
> Dependencies: None
> Owner: Claude

---

## Goal

Track and display token usage from Ollama API calls with session accumulation.

---

## TDD Tests (Write First)

- [ ] `test_token_count_accumulates` - token counts add up across multiple API calls
- [ ] `test_token_count_displays_in_summary` - token count appears in session summary
- [ ] `test_token_count_per_provider` - separate counts for L3 vs L4 providers

## Implementation

- [ ] Extract token usage from Ollama API responses
- [ ] Accumulate counts per session (prompt + completion tokens)
- [ ] Track per-provider (L3 vs L4) usage separately
- [ ] Display running total in status bar
- [ ] Display final total in on_done summary

## Acceptance Criteria

- [ ] Token count accumulates across multiple API calls
- [ ] Per-provider breakdown available (L3 vs L4)
- [ ] Token count visible in status bar during session
- [ ] Token count visible in on_done summary
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Accuracy comparison vs tiktoken (within 5% tolerance)

## Artifacts

- Test file: `tests/unit/test_token_counting.py`
- QA artifact: `docs/qa/test-results/sprint-5a0-3-token-counting.md`

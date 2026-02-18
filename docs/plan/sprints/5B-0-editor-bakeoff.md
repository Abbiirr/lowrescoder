# Sprint 5B-0: Editor Model Bakeoff (Pre-5B Gate)

> Status: **NOT STARTED**
> Sprint: 5B Pre-Gate (Section 15.21)
> Est. Hours: ~4h
> Dependencies: 5A-2 (ProviderRegistry), 5A-4 (Eval Harness), Task Bank (Pre-Gate)
> Owner: Claude

---

## Goal

Run a model bakeoff evaluating >= 3 editor candidates on edit fixtures before committing to an editor model for Sprint 5B.

---

## Candidates

- [ ] L3 baseline: Qwen2.5-Coder-1.5B Q4_K_M (current plan default)
- [ ] Stronger local fallback: Qwen2.5-Coder-3B or 7B quantized
- [ ] L4-only path: Qwen3-8B for both Architect and Editor (zero swap overhead)

## Protocol

- [ ] Select >= 10 edit fixtures from task bank
- [ ] Run each candidate on all fixtures
- [ ] Measure: format compliance rate
- [ ] Measure: patch-apply success rate
- [ ] Measure: semantic correctness rate
- [ ] Record latency per candidate
- [ ] Record VRAM usage per candidate

## Promotion Rule

- [ ] If L3 fails: format-valid >= 80% AND patch-apply >= 70% AND semantic-pass >= 60% -> auto-promote to stronger tier
- [ ] Document decision with evidence

## Acceptance Criteria

- [ ] >= 3 candidates evaluated
- [ ] All metrics recorded and compared
- [ ] Winner selected with evidence
- [ ] Decision documented in bakeoff artifact
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- QA artifact: `docs/qa/test-results/sprint-5b-editor-bakeoff.md`

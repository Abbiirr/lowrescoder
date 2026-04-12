# Pre-Implementation Gates

> Status: **PENDING**
> Owner: Claude (execution), Codex (review)
> Must complete before Sprint 5A0 begins

---

## Gate 1: Task Bank Freeze (Section 15.23)

- [ ] Define >= 30 concrete task scenarios
- [ ] Each scenario has: input files, symbols, user request
- [ ] Each scenario has: expected output (specific edits, references, classifications)
- [ ] Each scenario has: scoring rubric (pass/fail criteria)
- [ ] ~60-70% tasks solvable by L1/L2 deterministic tools
- [ ] ~20-30% tasks require L3/L4 intervention
- [ ] ~10% are negative controls (should NOT trigger LLM)
- [ ] Fixture IDs and gold labels frozen
- [ ] Task bank committed to `tests/eval/task_bank/`
- [ ] Task bank reviewed by Codex

**Artifact:** `tests/eval/task_bank/` directory with frozen fixtures

---

## Gate 2: User Decisions

- [x] User confirms num_ctx policy (Option A: adaptive 4096/8192) — confirmed 2026-02-18
- [ ] User confirms waiver acceptance (B1 -> CLOSED)
- [ ] User gives go-ahead for Sprint 5A0

---

## Gate 3: B2 Closure

- [x] Codex confirms B2 CLOSED (all doc contradictions resolved) — confirmed Entry 492

---

## Notes

- Task bank composition determines whether the 75% pass rate gate is meaningful
- Task bank MUST be locked before implementation so it cannot be unconsciously tuned
- See Section 15.23 in `docs/plan/phase5-agent-teams.md` for full policy

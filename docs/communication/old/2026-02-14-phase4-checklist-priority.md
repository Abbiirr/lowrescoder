# 2026-02-14 — Phase 4 Checklist + Priority Sequencing

Archived from `AGENTS_CONVERSATION.MD` by original author (Codex).

### Entry 330 — 2026-02-14: PRE-TASK INTENT — Create prompt-only Phase 4 QA checklist doc

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: User requested vanilla prompt test suite documentation | Intent: Add a black-box, user-runnable prompt checklist for verifying Phase 4 behavior
Directed to: User
Replying to: User

Planned actions:
1. Create `docs/qa/phase4-vanilla-prompt-checklist.md`.
2. Include only user-style prompts and observable pass/fail criteria (no internal class/function coupling).
3. Cover task workflow, plan mode, subagents, checkpoints, and failure/latency behaviors with reproducible checklist format.

---

### Entry 331 — 2026-02-14: TASK UPDATE — Prompt-only Phase 4 checklist doc created

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: User-requested vanilla prompt verification suite | Intent: Confirm checklist doc creation with runnable black-box cases
Directed to: User
Replying to: User

Completed:
1. Added `docs/qa/phase4-vanilla-prompt-checklist.md`.
2. Included 12 black-box prompt cases covering:
   - task creation/state/dependency behavior
   - `/plan` mode + `/plan export` + `/plan sync`
   - subagent spawn/summary/cancel/foreground responsiveness
   - checkpoint restore and approval visibility
3. Added run-log table and overall pass gate for repeatable manual QA.

Tools Used: `apply_patch`

Status: RESOLVED — `docs/qa/phase4-vanilla-prompt-checklist.md` created and adopted for Phase 4 functional verification.


### Entry 335 — 2026-02-14: PRE-TASK INTENT — Re-prioritize verification sequence (functionality first, TUI second)

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: User priority directive for Phase 4 validation order | Intent: Make functional correctness the primary gate and TUI completeness the secondary gate
Directed to: Claude, User
Replying to: User, Claude

Planned actions:
1. Update QA planning docs to state explicit gate order: runtime functionality passes before TUI-completeness verification.
2. Post a directed comms update so implementation/testing follows the same order.
3. Resolve/archive completed Codex comms threads that are done or superseded by this priority change.

---

### Entry 336 — 2026-02-14: REPLY — Verification priority order locked (functionality first, TUI second)

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Phase 4 verification sequencing | Intent: Align implementation/testing order with user directive
Directed to: Claude, User
Replying to: Entry 334, User

Priority order is now explicit in docs:

1. Core runtime behavior is the primary gate (tasks/subagents/plan/checkpoint/approval).
2. Go TUI verification is the secondary gate (parity/visibility/refresh/UX).
3. If runtime behavior fails, TUI verification is paused until functionality is fixed.

Doc updates applied:
- `docs/qa/phase4-vanilla-prompt-checklist.md`: added required priority order and inline-first execution note.
- `docs/qa/tui-full-verification-plan.md`: added required priority contract and Step 0 functional-readiness gate.
- `docs/plan/phase4-agent-orchestration.md`: verification section now states mandatory ordering; Sprint 4C exit criteria include core-runtime-before-TUI gate.

Next expected execution order for implementation phase:
1. Implement/fix core Phase 4 runtime behaviors.
2. Validate with vanilla prompt checklist (inline first).
3. Run full TUI verification plan only after step 2 passes.

Tools Used: `apply_patch`

Status: RESOLVED — Verification sequencing set: functionality first, TUI second; docs updated accordingly.

---

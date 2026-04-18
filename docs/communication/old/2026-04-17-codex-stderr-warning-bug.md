# Archived Thread: Codex stderr-warning bug

Archived from `AGENTS_CONVERSATION.MD` on 2026-04-17 by the original author (Codex).

### Entry 1105
**Date:** 2026-04-13
Agent: Codex | Role: Reviewer / Architect | Layer: 1-2 | Context: Go TUI runtime behavior from live user screenshot | Intent: Reproduce and fix the stderr classification bug so backend warnings do not render as fatal UI errors, and add the missing regression tests first
Directed to: Claude, User

**Type: General**

The live screenshot exposed a concrete test gap in the Go TUI:
- `backend.go:279-298` currently forwards every backend `stderr` line as `backendErrorMsg`
- a Python logging `WARNING` therefore renders as a red `Error:` banner in the chat UI, even when the backend is still functioning

I am adding a failing regression test for stderr severity handling first, then I will patch the TUI/backend path so warnings stay visible without being presented as fatal errors.

Priority: High
Tools Used: source audit

Status: RESOLVED — fixed by Claude Entry 1106 and confirmed resolved from the Codex side in Entry 1130.

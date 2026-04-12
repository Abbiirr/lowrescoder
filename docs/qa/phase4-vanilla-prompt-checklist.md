# Phase 4 Vanilla Prompt Checklist

> Purpose: black-box verification of Phase 4 behavior using only normal user prompts and slash commands.
> Audience: any user (no code knowledge required).

## Priority Order (Required)

1. **Functionality first (primary gate):** run this checklist in inline mode first (`uv run autocode chat`).
2. **TUI second (secondary gate):** only run full TUI verification after this checklist passes.
3. If inline passes but TUI fails, treat it as a TUI/parity defect (not core functionality failure).

## Ground Rules

1. Start with inline mode (`uv run autocode chat`), then repeat selected cases in TUI if needed.
2. Use one model/provider for the full run.
3. Do not reference internal classes, methods, or test helpers.
4. For each case, copy the prompt exactly and check only visible behavior.
5. Mark `PASS` only if all pass criteria are satisfied.
6. Store test evidence artifacts for each run under `docs/qa/test-results/`.
7. Use `./scripts/store_test_results.sh` for automated command output capture.
8. If a command is unavailable in `/help` and not part of the active sprint scope, mark that case `N/A` and note it (do not count as fail).

## Preconditions

- [ ] AutoCode starts successfully.
- [ ] You can send/receive normal chat messages.
- [ ] Slash commands are available (`/help` works).

## Required Evidence (Testing)

1. Automated baseline:
```bash
./scripts/store_test_results.sh phase4-vanilla-pytest -- uv run pytest tests/ -v --cov=src/autocode
```
2. Manual checklist evidence:
- [ ] Save a markdown run note in `docs/qa/test-results/` with date/time, model/provider, and PASS/FAIL per case.
- [ ] Include at least one concrete output snippet for every failed case.
- [ ] If all cases pass, include one output snippet each for V06, V08, and V09 as proof of plan/subagent behavior.
3. Minimum smoke subset for every Phase 4 change:
- [ ] V01
- [ ] V02
- [ ] V06
- [ ] V07
- [ ] V08
- [ ] V09

---

## Test Cases

### V01 — Task Breakdown Creates a Real To-Do List

**Prompt**
```text
I need to ship a small notes feature. Break this work into 4 tasks with dependencies: implementation first, then tests, then docs, then release notes.
```

**Then run**
```text
/tasks
```

**Pass Criteria**
- [ ] `/tasks` shows at least 4 tasks.
- [ ] Dependencies are visible (tests depend on implementation, docs depend on tests, release notes depend on docs).
- [ ] Tasks are readable and not empty placeholders.

### V02 — Task State Changes Are Reflected

**Prompt**
```text
Mark the implementation task as in_progress, then completed, and show me the current task board.
```

**Then run**
```text
/tasks
```

**Pass Criteria**
- [ ] Implementation task state changes appear in output.
- [ ] Dependent tasks move from blocked to ready/pending after completion.

### V03 — Blocked Task Behavior Is Enforced

**Prompt**
```text
Try to start the release notes task immediately even if dependencies are not done, and explain what is blocked.
```

**Pass Criteria**
- [ ] Assistant reports blocked dependency state rather than pretending work is done.
- [ ] Block reason is understandable to a non-technical user.

### V04 — Plan Export Produces a Human-Readable Plan File (Feature-Gated)

**Run**
```text
/plan export
```

**Pass Criteria**
- [ ] Command reports an output path.
- [ ] Exported markdown contains checkbox tasks and readable sections.

### V05 — Plan Sync Imports Manual Checkbox Changes (Feature-Gated)

1. Open exported markdown and toggle one unchecked task to checked.
2. Run:

```text
/plan sync
/tasks
```

**Pass Criteria**
- [ ] Sync reports at least one updated task.
- [ ] `/tasks` matches the manual checkbox change.

### V06 — Plan Mode Blocks Mutating Actions

**Run**
```text
/plan on
```

**Prompt**
```text
Create a file named phase4_plan_mode_probe.txt with one line: "plan mode write test".
```

**Pass Criteria**
- [ ] Mutating action is blocked while in plan mode.
- [ ] Response explains why it was blocked.

### V07 — Plan Approve Allows Execution Transition

**Run**
```text
/plan approve
```

**Prompt**
```text
Now create phase4_plan_mode_probe.txt with one line: "execution mode write test".
```

**Pass Criteria**
- [ ] Command is no longer blocked by plan-mode restrictions.
- [ ] Approval and execution flow is visible and understandable.

### V08 — Explore Subagent Returns a Useful Summary

**Prompt**
```text
Use an explore subagent to find where slash commands are handled, then return a short summary.
```

**Pass Criteria**
- [ ] Subagent lifecycle is visible (spawned then completed).
- [ ] Final answer includes a clear summary from delegated work.
- [ ] No unrelated file edits happen.

### V09 — Subagent Cancellation Works

**Prompt**
```text
Start a longer exploration subagent, then cancel it and report final status.
```

**Pass Criteria**
- [ ] Subagent enters running state.
- [ ] Cancellation is acknowledged.
- [ ] Final state is cancelled/terminated (not stuck running).

### V10 — Foreground Stays Responsive During Background Work

**Prompt**
```text
Start two background exploration subagents. While they run, answer this immediately: what is the current model name?
```

**Pass Criteria**
- [ ] Foreground response arrives while background tasks exist.
- [ ] No deadlock or frozen UI.

### V11 — Checkpoint Restore Rehydrates Task State (Feature-Gated)

**Prompt Sequence**
```text
Create a checkpoint named "phase4-vanilla-checkpoint".
```

```text
Update one task state so it clearly changes from previous state.
```

```text
Restore checkpoint "phase4-vanilla-checkpoint" and show tasks.
```

**Pass Criteria**
- [ ] Checkpoint create/list/restore flow works without crashing.
- [ ] Task board reflects restored state (not the modified post-checkpoint state).

### V12 — Approval UX Is Visible (No Hidden Wait)

**Prompt**
```text
Use an execute subagent for a write action that needs approval, then explain exactly where I should approve or deny it.
```

**Pass Criteria**
- [ ] Approval requirement is surfaced clearly to the user.
- [ ] User can identify the action required without guessing.
- [ ] No hidden indefinite waiting state.

---

## Run Log

| Case | Run 1 | Run 2 | Notes |
|------|-------|-------|-------|
| V01 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V02 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V03 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V04 | [ ] PASS [ ] FAIL [ ] N/A | [ ] PASS [ ] FAIL [ ] N/A | |
| V05 | [ ] PASS [ ] FAIL [ ] N/A | [ ] PASS [ ] FAIL [ ] N/A | |
| V06 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V07 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V08 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V09 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V10 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |
| V11 | [ ] PASS [ ] FAIL [ ] N/A | [ ] PASS [ ] FAIL [ ] N/A | |
| V12 | [ ] PASS [ ] FAIL | [ ] PASS [ ] FAIL | |

## Overall Gate

- [ ] **PASS**: All critical in-scope flows (tasks, plan mode, subagents, approval visibility) pass in at least one run.
- [ ] **NEEDS WORK**: Any critical flow fails, hangs, or is unclear to a normal user.

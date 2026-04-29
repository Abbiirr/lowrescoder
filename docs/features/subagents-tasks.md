# Subagents and Tasks

## Purpose

Defines the contract for task/subagent lifecycle events, worktree isolation semantics, and handoff/merge-proof boundaries. Designed to absorb Tranche 4 G13 (parallel sub-agents in isolated git worktrees) shapes. Cross-references the existing orchestrator/team-eval substrate (Phase 8) and external-harness adapters (Phase 6).

## User-visible TUI surfaces

- Task panel: visible via `/tasks` showing task list with status badges
- Subagent list: visible via `on_task_state` notification showing spawned subagents
- Task detail: task title, status, dependencies, assigned subagent
- Subagent detail: role, status, progress

## Backend contract

### Task lifecycle

```
pending → in_progress → completed
                   ↘ failed
```

- Backward transitions (e.g., `completed → pending`) are rejected
- Status history is recorded for each transition

### Subagent lifecycle

```
spawning → active → completed
                  ↘ failed
                  ↘ cancelled
```

### RPC methods

| Method | Direction | Params | Result |
|---|---|---|---|
| `task.list` | Frontend → Backend | _(none)_ | Task list |
| `subagent.list` | Frontend → Backend | _(none)_ | Subagent list |
| `subagent.cancel` | Frontend → Backend | `subagent_id: string` | `success: bool` |
| `on_task_state` | Backend → Frontend | tasks + subagents | Notification |

### Task/subagent schema

```ts
interface TaskEntry {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "completed" | "failed";
}

interface SubagentEntry {
  id: string;
  role: string;
  status: "spawning" | "active" | "completed" | "failed" | "cancelled";
}
```

### G13 worktree isolation (planned)

- Subagents can be spawned in isolated git worktrees
- `git worktree add` and `git worktree remove` are the ONLY allowed worktree-mutating git commands
- Handoff from subagent to main session: via `git diff` + `apply_patch`, NOT `git pull`/`git merge`/`git checkout`
- Worktree isolation means the main working tree is never directly modified by subagents

### Subagent management (current)

- Spawn via `spawn_subagent` tool
- Status via `check_subagent` tool
- Listing via `list_subagents` tool
- Cancellation via `cancel_subagent` tool or RPC
- Max concurrency controls and timeouts
- Background subagents auto-deny approval-requiring tools

## Event types

- `on_task_state`: carries full task and subagent list snapshot
- `SubagentEvent` (planned): granular subagent lifecycle events
- `on_tool_call` for subagent-related tools (spawn, check, cancel)

## State/reducer behavior

- Frontend maintains task/subagent lists from `on_task_state` notifications
- Task panel renders current task list with status badges
- Subagent panel shows active and completed subagents
- Detail surface (Ctrl+L) shows extended task/subagent information

## Persistence behavior

- Tasks persisted in SQLite with status history
- Subagent state is in-memory during the session
- Checkpoint save includes task DAG state
- Checkpoint restore rehydrates task state

## Commands/keybindings

| Command | Aliases | Action |
|---|---|---|
| `/tasks` | `/t` | Show task board |
| `Ctrl+L` | — | Toggle detail surface (includes task/subagent view) |

## Failure/recovery behavior

- If a subagent fails, its status transitions to `failed` and the parent task may also fail
- If the main session crashes, active subagents continue running (detached)
- On session resume, `subagent.list` shows any still-active subagents
- Subagent cancellation propagates to the subagent's agent loop

## Tests and fixtures

- `autocode/tests/unit/test_backend_server.py` — task/subagent RPC tests
- `autocode/src/autocode/agent/task_tools.py` — task tool tests
- `autocode/src/autocode/agent/subagent_tools.py` — subagent tool tests
- `S-INPROGRESS` verification: task lifecycle transitions
- Artifact: `autocode/docs/qa/test-results/20260425-133000-s-inprogress-verification.md`

## Acceptance criteria

- [ ] Task lifecycle states and transitions documented
- [ ] Subagent lifecycle states and transitions documented
- [ ] G13 worktree isolation semantics documented (git worktree add/remove only)
- [ ] Handoff boundary documented (diff + apply_patch, NOT git merge/pull)
- [ ] All task/subagent RPC methods documented
- [ ] Background subagent auto-deny behavior documented
- [ ] Cross-reference to `session-lifecycle.md` for worktree-spawned session lifecycles

## Open questions

- Should subagents be visible across sessions or only within the spawning session?
- Maximum concurrent subagents?
- Should subagent output be streamed in real-time or only on completion?
- How to handle merge conflicts when applying subagent diffs?
- Cross-reference: `permissions.md` for subagent permission scoping

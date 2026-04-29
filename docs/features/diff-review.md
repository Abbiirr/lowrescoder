# Diff Review

## Purpose

Defines the contract for displaying file diffs with per-hunk approval state, embedded in a rail-mode review surface. Diff review is triggered by tool calls that modify files and by the `/diff` command.

## User-visible TUI surfaces

- Rail-mode diff surface: slides in from the right edge of the screen
- Per-file diff view with syntax-highlighted hunks
- Per-hunk approval controls: approve, reject, skip
- File summary header: path, lines added/removed, protected status
- Keyboard navigation between hunks

## Backend contract

### Typed model

```ts
interface FileDiff {
  filePath: string;
  oldPath?: string;
  hunks: DiffHunk[];
  added: number;
  removed: number;
  protected?: boolean;
}

interface DiffHunk {
  id: string;
  oldStart: number;
  newStart: number;
  lines: DiffLine[];
  approvalState?: "pending" | "approved" | "rejected";
}

interface DiffLine {
  kind: "context" | "add" | "remove";
  oldLine?: number;
  newLine?: number;
  text: string;
}
```

### Diff sources

1. **Tool call diff**: emitted after `write_file`, `edit_file`, or `apply_patch` modifies a file
2. **Session diff**: retrieved via `/diff` command (calls `git diff` internally)
3. **Checkpoint diff**: shown during checkpoint restore preview (see `checkpoints-restore.md`)

### Per-hunk approval semantics

- Default state: `pending`
- `approved`: hunk changes will be applied/kept
- `rejected`: hunk changes will be reverted
- Approval state is tracked per-hunk, not per-file
- When all hunks are reviewed, the overall diff is resolved

### RPC methods

| Method | Direction | Notes |
|---|---|---|
| `/diff` command | Frontend → Backend | Returns session git diff |
| `on_tool_call` | Backend → Frontend | Tool result may include diff payload |

## Event types

- `DiffEvent` (planned): carries `FileDiff[]` payload for rendering
- `on_tool_call` with tool result containing diff information (current)

## State/reducer behavior

- Frontend maintains diff view state: current file, current hunk, scroll position
- Hunk navigation: `j`/`k` or Up/Down to move between hunks
- File navigation: `n`/`p` or Tab to move between files in multi-file diffs
- Approval toggles update the hunk's `approvalState`
- Rail surface pushes transcript left; does not overlay

## Persistence behavior

- Per-hunk approval state is session-scoped and not persisted
- Diff payloads are generated on-demand from git or tool results
- Applied diffs are reflected in the working tree

## Commands/keybindings

| Key/Command | Context | Action |
|---|---|---|
| `/diff` | Idle | Show git diff for session changes |
| `j`/`Down` | Diff view | Next hunk |
| `k`/`Up` | Diff view | Previous hunk |
| `n`/`Tab` | Diff view | Next file |
| `p`/`Shift+Tab` | Diff view | Previous file |
| `y`/`Enter` | Diff view | Approve current hunk |
| `n`/`Esc` | Diff view | Reject current hunk |
| `a` | Diff view | Approve all remaining hunks |
| `Esc` | Diff view | Close diff surface |

## Failure/recovery behavior

- If git diff fails (not a git repo), backend returns an error message
- If a file is deleted between diff generation and rendering, the diff is stale — backend re-generates
- Per-hunk rejection triggers rollback of that hunk's changes

## Tests and fixtures

- Track 4: `diff` scene — diff surface rendering
- PTY smoke: `/diff` command execution
- `autocode/tests/unit/test_backend_server.py` — diff command handling

## Acceptance criteria

- [ ] `FileDiff`, `DiffHunk`, `DiffLine` typed models embedded
- [ ] Per-hunk approval state semantics documented (pending/approved/rejected)
- [ ] Rail-mode review surface (NOT centered modal, NOT overlay)
- [ ] Multi-file diff navigation supported
- [ ] Protected-file flag in `FileDiff` triggers protected-path flow

## Open questions

- Should diff view support inline editing of hunks?
- How to handle binary file diffs?
- Should the diff surface support search within hunks?
- Maximum diff size before pagination or truncation?

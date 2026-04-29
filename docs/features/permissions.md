# Permissions

## Purpose

Defines the permission/risk model for tool approval and sandbox policy. Covers permission modes, risk-fact assessment, mode transitions, and the interaction between the approval system and the TUI. Designed to absorb Tranche 4 G2/G7' sandbox/policy shapes.

## User-visible TUI surfaces

- Approval surface: rendered in rail mode (NOT a centered overlay, NOT a dimmed backdrop) when `on_tool_request` requires user approval
- Ask-user surface: rendered in rail mode (NOT a centered overlay, NOT a dimmed backdrop) when `on_ask_user` requests explicit user input
- `/mode` command output showing current permission mode
- Permission mode indicator in status bar
- Rail-mode-only escalation for protected-path operations (NOT centered modal — see `protected-paths.md`)

## Backend contract

### Typed model

```ts
type PermissionMode =
  | "suggest"
  | "accept-edits"
  | "auto"
  | "full-auto"
  | "review-needed"
  | "halted";

interface RiskFacts {
  writes: "none" | "local-only" | "external";
  network: "off" | "on";
  protectedPathTouched: boolean;
  reversible: boolean;
  filesChanged: number;
  blastRadius: string;
  affectedPaths: string[];
}
```

### Approval flow

1. Backend evaluates tool call against current `PermissionMode` and `RiskFacts`
2. If auto-approved: tool executes, `on_tool_call` emitted with status `running` → `done`
3. If approval required: `on_tool_request` emitted with tool name + args
4. Frontend renders approval modal with tool details and risk summary
5. User approves/denies; response sent to backend
6. On approval: tool executes; on denial: tool is skipped

### Mode transitions

```
suggest → accept-edits → auto → full-auto
  ↓ (protected path)     ↓ (error)
review-needed           halted
  ↓ (user resolves)
suggest / accept-edits
```

### RPC methods

| Method | Direction | Notes |
|---|---|---|
| `on_tool_request` | Backend → Frontend | Approval request |
| `on_ask_user` | Backend → Frontend | User question |
| `/mode` | Frontend → Backend | Switch permission mode |
| `config.set` | Frontend → Backend | Persist mode preference |

## Event types

- `ApprovalRequestEvent` (from `on_tool_request`): carries tool name, args, risk assessment
- `ApprovalRequestEvent` (ask-user variant from `on_ask_user`): carries question, options, allow_text flag

## State/reducer behavior

- Frontend tracks approval state: `Idle` | `AwaitingApproval` | `AwaitingUserInput`
- On `on_tool_request`: transition to `AwaitingApproval`, render approval modal
- On user response: send approval/denial, transition back to `Idle`
- Multiple pending approvals queue in order

## Persistence behavior

- Current `PermissionMode` is persisted in backend config (`config.set`)
- Approval decisions are not persisted (each is a live interaction)
- `RiskFacts` are computed per-tool-call and not stored

## Commands/keybindings

| Command | Action |
|---|---|
| `/mode` (`/permissions`) | Show or switch approval mode |
| `y/Y/Enter` | Approve tool request |
| `n/N/Esc` | Deny tool request |
| `a/A` | Approve all (current session) |

## Failure/recovery behavior

- If frontend does not respond to approval request within timeout, backend auto-denies
- If mode is `halted`, no tool calls execute until user resolves
- Background subagents auto-deny approval-requiring tools
- Git-aware staging may run `git add` after successful FS-mutating tool calls; commit/push/reset/checkout/restore/stash mutation operations remain forbidden and are only surfaced as user-owned commands when relevant
- Safety snapshots for write/edit and multi-edit flows are local file copies under `~/.autocode/`, not git commits or stash entries

## Tests and fixtures

- `autocode/tests/unit/test_backend_server.py` — approval flow tests
- `autocode/src/autocode/agent/sandbox.py` — sandbox policy primitives
- PTY smoke: approval modal rendering

## Acceptance criteria

- [ ] `PermissionMode` and `RiskFacts` typed models embedded
- [ ] All permission modes enumerated with transition rules
- [ ] Approval flow documented (evaluate → request → approve/deny)
- [ ] Rail-mode-only escalation for protected paths (NOT centered modal)
- [ ] Ask-user flow documented with options and allow_text

## Open questions

- Should `RiskFacts.blastRadius` be an enum or free-form string?
- Timeout for approval requests — what is the default?
- Should `full-auto` mode have a session-level kill-switch?
- How does `review-needed` mode interact with the diff-review surface (see `diff-review.md`)?
- Cross-reference: `protected-paths.md` for escalation surface rules

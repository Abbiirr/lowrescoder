# Protected Paths

## Purpose

Defines the protected-path matcher and escalation shape. When a tool operation touches a protected path, the system escalates to a rail-mode review surface. **Escalation uses a rail surface, NOT a centered modal.**

## User-visible TUI surfaces

- Rail-mode review surface: slides in from the right edge, showing the protected-path operation details
- Risk summary: affected paths, operation type, reversibility
- User actions: approve, deny, approve-all-for-path
- No centered modal, no dimmed backdrop, no floating overlay for protected-path escalation

## Backend contract

### Protected-path matching

The backend maintains a list of protected path patterns. When a tool call targets a matching path:

1. `RiskFacts.protectedPathTouched` is set to `true`
2. Approval mode is elevated to at least `review-needed`
3. `on_tool_request` is emitted with the protected-path flag

### Protected path patterns

Patterns are matched against file paths relative to the project root:

- Glob patterns (e.g., `*.env`, `**/credentials.*`)
- Directory patterns (e.g., `.git/`, `secrets/`)
- Explicit file paths
- Configured via `config.set` or `protected-paths` config key

### Escalation shape

```
Normal tool call → RiskFacts evaluation
  → protectedPathTouched: true
    → Escalate to rail-mode review surface
    → User must explicitly approve
    → Deny returns to previous state
```

The rail surface:
- Appears on the right side of the screen
- Pushes transcript content left (not overlaying)
- Shows: path, operation, diff preview, risk assessment
- Dismisses on approval/denial

## Event types

- `on_tool_request` with `protectedPathTouched: true` in the risk assessment
- No separate event type for protected-path escalation (uses the existing approval flow)

## State/reducer behavior

- When `on_tool_request` arrives with `protected: true`:
  - Frontend opens the rail-mode review surface
  - Rail surface shows full diff preview and path details
  - User cannot dismiss without explicit approve/deny

## Persistence behavior

- Protected-path patterns are persisted in backend config
- Approval decisions for protected paths can be session-scoped ("approve all for this path this session")

## Commands/keybindings

| Key | Context | Action |
|---|---|---|
| `y/Y/Enter` | Rail review | Approve protected-path operation |
| `n/N/Esc` | Rail review | Deny protected-path operation |
| `a/A` | Rail review | Approve all operations for this path (session-scoped) |

## Failure/recovery behavior

- If the user denies a protected-path operation, the tool is skipped and a warning is emitted
- If the backend crashes during escalation, the operation is not executed (safe default)
- Auto-approval for protected paths is never allowed in `suggest` mode

## Tests and fixtures

- `autocode/src/autocode/agent/sandbox.py` — protected-path matching logic
- `S-BLOCKED` verification: expanded dangerous-operation blocking across write paths
- Artifact: `autocode/docs/qa/test-results/20260425-190420-s-blocked-verification.md`

## Acceptance criteria

- [ ] Protected-path matcher documented with pattern types
- [ ] Escalation uses rail-mode surface (NOT centered modal, NOT dimmed backdrop)
- [ ] Risk facts include `protectedPathTouched` flag
- [ ] Safe default: deny on crash/timeout
- [ ] Session-scoped approval documented
- [ ] Cross-link to `permissions.md` for mode transitions

## Open questions

- Should protected-path patterns support regex in addition to globs?
- Default protected-path list — what ships out of the box?
- Should protected-path approvals be auditable (logged)?
- Cross-reference: `diff-review.md` for diff preview rendering within the rail

# Go TUI — Phase 5/6 Integration Points

## Already Implemented
- Token count display in status bar (`statusbar.go`)
- Task panel (`taskpanel.go`)
- Session picker (`session_picker.go`)
- Approval flow (`approval.go`)
- Backend protocol (`protocol.go`)

## Needs Adding (Phase 5 features)

### Cost Dashboard Display
- Add `CostInfo` to the protocol messages from Python backend
- Display local vs cloud token breakdown in status bar
- Show per-agent costs when in multi-agent mode

### Team Panel
- New panel showing active agent team members
- Display current SOP step progress
- Show which agent is currently active
- Wire to AgentBus messages from backend

### Doctor Command
- Add `doctor` subcommand to TUI
- Display 8 readiness checks with pass/fail
- Show remediation messages for failures

### Diff Preview
- Show diff output after write_file/edit_file in the response area
- Syntax-highlighted diff with +/- markers
- Collapsible diff sections for large changes

### Completion Summary
- Enhanced on_done display with SessionStats
- Token count, files changed, tools used, time elapsed

## Protocol Messages Needed

```json
// Cost update (backend → TUI)
{"type": "cost_update", "total_tokens": 1500, "local_tokens": 1500, "cloud_tokens": 0, "cost_usd": 0.0}

// Team status (backend → TUI)
{"type": "team_status", "team": "bugfix", "active_agent": "architect", "sop_step": 2, "sop_total": 3}

// Completion summary (backend → TUI)
{"type": "completion", "tokens": 4300, "files_changed": 3, "tool_calls": 15, "elapsed_s": 42}
```

# TUI/UX Research: OpenAI Codex CLI & OpenCode (2026)

**Date:** 2026-02-05
**Purpose:** Research latest TUI patterns from OpenAI Codex CLI and OpenCode to inform HybridCoder's interface design

---

## Executive Summary

### Key Findings

1. **Codex CLI** uses a **single full-screen TUI** (not split pane) in terminal, but right-panel layout in IDE integrations
2. **OpenCode** uses **Bubble Tea (Go)** with page-based navigation and Model-View-Update pattern
3. **Both** emphasize:
   - Approval gates for safety (multiple modes: Auto, Read Only, etc.)
   - Inline plan/task display with todo lists
   - Transparent operation tracking
   - Session persistence and file change tracking

### UX Patterns to Adopt

| Pattern | Source | Rationale |
|---------|--------|-----------|
| Approval presets (Auto/ReadOnly/etc) | Codex CLI | Balance automation vs control |
| Inline task/todo display | Codex CLI | Transparency during multi-step operations |
| External editor integration ($EDITOR) | OpenCode | Leverage user's preferred workflow |
| File change tracking panel | OpenCode | Visual feedback on what changed |
| Alternate screen toggle | Codex CLI | Some users prefer scrollback history |
| Exponential backoff retry with UI feedback | Codex CLI | Graceful error recovery |

### UX Patterns to Avoid

| Anti-Pattern | Source | Why |
|-------------|--------|-----|
| Thousands of small JSON session files | OpenCode | Performance issues, messy directories |
| Diffing against origin/main by default | OpenCode | Shows irrelevant changes (bug as of Jan 2026) |
| Silent error suppression | Codex CLI | Users lose valuable output (linters, tests) |
| OAuth-only auth without fallback | Codex CLI | API key conflicts cause 401 errors |

---

## OpenAI Codex CLI (2025-2026)

### 1. Layout Structure

**Terminal Mode:**
- **Single full-screen TUI** (not split pane)
- Uses alternate screen by default (can be disabled via `--no-alternate-screen` flag or `tui.alternate_screen` config)
- Built in **Rust** for speed and efficiency
- Open source on GitHub

**IDE Integration (VS Code/Cursor):**
- Right-side panel available (drag Codex icon to right)
- In Cursor: May need to temporarily set activity bar to vertical, restart, move Codex, then revert
- Shows plan and diffs inline before execution

### 2. Alternate Screen Behavior

- **Default:** Enabled (full-screen takeover, no scrollback)
- **Toggle:** `--no-alternate-screen` flag or config file
- **Rationale:** Some users prefer scrollback history; others want clean full-screen experience

### 3. Tool Call Display & Approval UX

**Approval Modes:**
- **Auto** - Hands-off runs (auto-approve safe operations)
- **Read Only** - Review edits but don't apply
- **Custom** - Granular control per operation type

**Approval Gates:**
- Safe operations (e.g., `cat utils.ts`) auto-approve as "Reading files"
- Risky operations (e.g., `rm -rf`) trigger immediate user confirmation
- Users can adjust approval preset via `/approval` slash command

**Display Pattern:**
- Show plan BEFORE execution
- Approve/reject steps inline
- Diff preview for file changes

### 4. Inline Plan/To-Do List

**Task Display:**
- Creates **todo lists** for larger tasks
- Nested subtask lists for complex operations
- Lists update in real-time as items complete
- Visual progress indicator

**Implementation:**
- Uses `/create-plan` skill (experimental as of 2026)
- Can be invoked explicitly with `$create-plan` or auto-selected by Codex

**UX Flow:**
```
User: "Refactor auth module to use tokens"

Codex displays:
  [ ] Extract token logic from session.py
  [ ] Create TokenManager class
  [ ] Update login flow
  [ ] Add tests

(User approves plan)

Codex executes:
  [✓] Extract token logic from session.py
  [⚙] Create TokenManager class
  [ ] Update login flow
  [ ] Add tests
```

### 5. Error Handling Patterns

**Retry Logic:**
- Exponential backoff with UI feedback: "retrying 1/5 in 189ms"
- Enhanced recovery after WebSocket/SSE disconnection (v0.87.0+)
- Version 0.87.0 improved connection stability with GPT-5.2-Codex

**Production Wrapper Pattern:**
```bash
# Developers wrap Codex commands with retry logic
for i in {1..3}; do
  codex --command && break
  sleep 5
done
```

**Known Issues (2026):**
- Command output suppression: Non-zero exit codes hide stdout/stderr (frustrates users running linters/tests)
- Auth conflicts: OPENAI_API_KEY env var conflicts with ~/.codex/auth.json
- Rate limiting on Tier 1: Breaks UX without graceful degradation

**Recommended Fixes:**
- Implement automatic partial saving for long operations
- Token-aware truncation
- Adaptive retry to turn rate limits into speed bumps (not blocking errors)

### 6. Recent Features (2026)

- **Agent Skills:** Reusable instruction bundles (CLI + IDE)
- **Multi-agent workflows:** Parallel agent orchestration (macOS app, Feb 2, 2026)
- **`/debug-config` command:** Inspect effective configuration
- **Plan Mode:** Separate planning phase before execution

---

## OpenCode TUI

### 1. Layout Structure (Bubble Tea)

**Framework:** [Bubble Tea](https://github.com/charmbracelet/bubbletea) (Go)
- Model-View-Update (Elm architecture)
- Page-based navigation system
- `appModel` struct orchestrates entire TUI

**Core Components:**
- **Pages:** Managed via `page.PageID` enumeration, loaded on-demand
- **Dialogs:** Boolean flags control visibility
- **State:** Centralized in `appModel` (implements `tea.Model` interface)

**Lifecycle:**
```go
type appModel struct {
  currentPage  page.PageID
  dialogState  map[string]bool
  // ...
}

func (m appModel) Init() tea.Cmd { /* setup */ }
func (m appModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) { /* handle events */ }
func (m appModel) View() string { /* render */ }
```

### 2. Session Management

**Session Lifecycle:**
- Created via `Session.create()` or `Session.createNext()`
- Unique ID assigned on creation
- Optional automatic sharing
- Settings persist across TUI sessions

**Storage:**
- **Problem:** Thousands of small JSON files spread across directories (performance issues)
- Stores messages, tool executions, and context per session

**Recent Issues (Jan 2026):**
- Sessions stored in many small files cause slowdowns
- No built-in session search/indexing (third-party TUIs created for this: [stanislas.blog](https://stanislas.blog/2026/01/tui-index-search-coding-agent-sessions/))

### 3. Tool Call Display

- Integrated into message flow
- Shows tool name, arguments, and results
- Collapsible for long outputs

### 4. External Editor Integration

**Editor Invocation:**
- `/editor` command: Opens $EDITOR for composing messages
- `/export` command: Export conversation to file, open in $EDITOR

**Supported Editors:**
- **Vim/Neovim:** Set `EDITOR=vim` or `EDITOR=nvim`
- **VS Code:** Set `EDITOR="code --wait"` (blocking mode required)
- **Any CLI editor:** Use appropriate blocking flag

**IDE Integration:**
- Works in VS Code, Cursor, Windsurf, VSCodium terminal
- `Cmd+Option+K` (Mac) / `Alt+Ctrl+K` (Linux/Windows): Insert file references
- Auto-shares current selection or tab with OpenCode

### 5. File Change Tracking Panel

**Git-Based Tracking:**
- Requires project to be a Git repository
- Tracks modified files during session
- Visual diff display

**Known Bug (Jan 2026):**
- Issue #7555: "Session Changes" shows irrelevant changes
- Diffs against `origin/main` instead of base branch
- Users want to see only session-specific changes

**Display:**
- Separate panel in TUI (Desktop: "Session Changes", CLI: "Modified Files")
- Lists files changed with diff stats

---

## Comparative Analysis: Codex vs OpenCode

| Feature | Codex CLI | OpenCode |
|---------|-----------|----------|
| **Language** | Rust | Go |
| **TUI Framework** | Custom (Rust) | Bubble Tea |
| **Layout** | Full-screen (terminal), Right panel (IDE) | Page-based navigation |
| **Approval UX** | Presets: Auto/ReadOnly + per-operation gates | Similar approval system |
| **Session Storage** | Not specified | JSON files (thousands, problematic) |
| **File Tracking** | Yes | Git-based (buggy as of Jan 2026) |
| **External Editor** | Not mentioned | Full support ($EDITOR) |
| **Error Recovery** | Exponential backoff, connection stability | Not detailed |
| **Multi-agent** | Yes (2026 macOS app) | No |
| **Plan/Todo Display** | Inline task lists | Not mentioned |
| **Open Source** | Yes (GitHub) | Yes (GitHub) |

---

## Recommendations for HybridCoder

### Must-Have Features

1. **Approval System**
   - Start with 3 modes: Auto, Interactive, ReadOnly
   - Safe operation whitelist (file reads, directory listings)
   - Risk-based prompts (destructive operations, network access, execution)

2. **Task/Plan Display**
   - Inline progress for multi-step operations
   - Collapsible task tree
   - Real-time status updates (pending/running/done)

3. **External Editor Integration**
   - Respect $EDITOR environment variable
   - Support `--wait` flag for blocking editors
   - Use for: long prompts, reviewing diffs, editing generated code

4. **File Change Tracking**
   - Git-aware diff display
   - Session-scoped changes (not against origin/main)
   - Before/after preview for edits

5. **Error Handling**
   - Exponential backoff with visible retry counter
   - Clear error messages (no silent suppression)
   - Recovery suggestions

### Nice-to-Have Features

1. **Alternate Screen Toggle**
   - Default: ON (clean full-screen)
   - Flag: `--no-alternate-screen` for users who want scrollback

2. **Session Management**
   - Use SQLite instead of thousands of JSON files
   - Fast session search/filter
   - Auto-naming based on first prompt

3. **Slash Commands**
   - `/approval` - Change approval mode
   - `/editor` - Open external editor
   - `/plan` - Show current task plan
   - `/diff` - Review pending changes
   - `/debug-config` - Show effective config

### Implementation Strategy (Phase 1)

**Tech Stack:**
- **Python + Rich** (already chosen for HybridCoder)
- Rich supports:
  - Live progress displays
  - Collapsible tree views
  - Syntax-highlighted diffs
  - Status panels

**Phase 1 MVP:**
1. Simple REPL with Rich formatting
2. Approval gates (Interactive mode only)
3. Task progress display (Rich Live)
4. File diff preview (Rich Syntax)

**Phase 2+ Enhancements:**
- Full TUI (Textual framework, Python equivalent of Bubble Tea)
- Session persistence (SQLite)
- External editor integration
- Alternate screen support

---

## Sources

- [Codex CLI](https://developers.openai.com/codex/cli/)
- [Codex CLI features](https://developers.openai.com/codex/cli/features/)
- [Codex changelog](https://developers.openai.com/codex/changelog/)
- [Codex releases on GitHub](https://github.com/openai/codex/releases)
- [Slash commands in Codex CLI](https://developers.openai.com/codex/cli/slash-commands/)
- [Command line options](https://developers.openai.com/codex/cli/reference/)
- [OpenAI for Developers in 2025](https://developers.openai.com/blog/openai-for-developers-2025/)
- [OpenAI Codex CLI Release Notes - January 2026](https://releasebot.io/updates/openai/codex)
- [OpenCode on GitHub](https://github.com/opencode-ai/opencode)
- [OpenCode Official Site](https://opencode.ai/)
- [OpenCode TUI Documentation](https://opencode.ai/docs/tui/)
- [OpenCode IDE Documentation](https://opencode.ai/docs/ide/)
- [Terminal UI System | opencode-ai/opencode | DeepWiki](https://deepwiki.com/opencode-ai/opencode/4-terminal-ui-system)
- [Session Management | sst/opencode | DeepWiki](https://deepwiki.com/sst/opencode/2.1-session-management)
- [Beyond the Hype: A Look at 5+ AI Coding Agents for Your Terminal - DEV Community](https://dev.to/skeptrune/beyond-the-hype-a-look-at-5-ai-coding-agents-for-your-terminal-e0m)
- [Terminal User Interfaces: Review of Crush (Ex-OpenCode Al) - The New Stack](https://thenewstack.io/terminal-user-interfaces-review-of-crush-ex-opencode-al/)
- [Building a TUI to index and search my coding agent sessions · Stan's blog](https://stanislas.blog/2026/01/tui-index-search-coding-agent-sessions/)
- [TODO list for long running tasks · Issue #2966 · openai/codex](https://github.com/openai/codex/issues/2966)
- [Plan / Spec Mode · openai/codex · Discussion #7355](https://github.com/openai/codex/discussions/7355)
- [Codex Plan Mode Complete Guide 2026 - SmartScope](https://smartscope.blog/en/generative-ai/chatgpt/codex-plan-mode-complete-guide/)
- [Session Changes / Modified Files show changes from origin/main · Issue #7555 · anomalyco/opencode](https://github.com/anomalyco/opencode/issues/7555)
- [Codex CLI 'Re-connecting' Loop Complete Guide - SmartScope](https://smartscope.blog/en/generative-ai/chatgpt/codex-cli-reconnecting-issue-2025/)
- [5 Codex CLI Production Failure Patterns & Quick Fixes (2025) - SmartScope](https://smartscope.blog/en/generative-ai/chatgpt/codex-cli-production-failure-patterns/)
- [VSCode Extension move Codex to the Right · Issue #2937 · openai/codex](https://github.com/openai/codex/issues/2937)
- [VS Code Extension | sst/opencode | DeepWiki](https://deepwiki.com/sst/opencode/6.6-vs-code-extension)

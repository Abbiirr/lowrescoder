# Go TUI UI/UX Improvements — Full Consolidation Plan

## Context

The Go Bubble Tea TUI frontend is fully implemented and stable (275 Go tests, 509+ Python tests, 14MB binary). A screenshot review reveals several UX gaps that prevent it from reaching Claude Code-level polish:

- **Session picker overwhelm**: All 20+ sessions shown at once with no pagination, search, or filtering
- **Low information density**: Session titles are generic ("hello", "New session"), model names are long and untruncated
- **Tool call clutter**: Results can be redundant, no visual distinction between denied/waiting states
- **Flat status bar**: Plain gray text with verbose labels, hard to scan at a glance
- **Plain approval prompts**: No severity differentiation for dangerous vs safe operations
- **No progress feedback**: "Thinking..." spinner gives no sense of elapsed time or token count

**Goal**: Implement 5 phases of non-breaking UI/UX improvements incrementally.

**Implementation target**: Only Go TUI files in `cmd/hybridcoder-tui/`. No Python backend changes required. All changes backward-compatible.

---

## Phase 1: Session Picker Improvements (High Impact, Priority 1)

### 1A. Paginated Session List

**Problem**: `enterSessionPicker()` in `session_picker.go:13-48` builds `m.askOptions` from ALL sessions. `renderAskUserView()` in `askuser.go:39-48` renders ALL of them. With 20+ sessions, this fills the entire terminal.

**Solution**: Add viewport pagination — show max 10 sessions at a time with scroll indicators.

**Files to modify**:
- `cmd/hybridcoder-tui/model.go` — Add new state field: `sessionPickerOffset int`
- `cmd/hybridcoder-tui/askuser.go` — Paginated rendering in `renderAskUserView()`, PgUp/PgDn in `handleAskUserKey()`

**State changes in `model.go`** — Add after `sessionPickerEntries` (line 84):
```go
// Session picker pagination
sessionPickerOffset int // viewport scroll position (index of first visible item)
```

**Rendering changes in `askuser.go` `renderAskUserView()`** — Replace the options loop (lines 39-48):

When `askRequestID == -1` (session picker mode) and `len(askOptions) > sessionPageSize`, render only the visible window:

```go
const sessionPageSize = 10

if m.askRequestID == -1 && len(m.askOptions) > sessionPageSize {
    total := len(m.askOptions)
    start := m.sessionPickerOffset
    end := start + sessionPageSize
    if end > total {
        end = total
    }

    // Header with counts
    b.WriteString(dimStyle.Render(fmt.Sprintf("  Sessions %d-%d of %d", start+1, end, total)))
    b.WriteString("\n")

    // Render visible range only
    for i := start; i < end; i++ {
        opt := m.askOptions[i]
        if i == m.askCursor {
            b.WriteString(approvalActiveStyle.Render(fmt.Sprintf("  ❯ %d. %s", i+1, opt)))
        } else {
            b.WriteString(approvalInactiveStyle.Render(fmt.Sprintf("    %d. %s", i+1, opt)))
        }
        b.WriteString("\n")
    }

    // Footer with navigation hints
    hints := []string{"↑↓ navigate", "Enter select", "Esc cancel"}
    if start > 0 {
        hints = append([]string{"PgUp prev"}, hints...)
    }
    if end < total {
        hints = append([]string{"PgDn next"}, hints...)
    }
    b.WriteString(dimStyle.Render("  " + strings.Join(hints, "  ")))
    b.WriteString("\n")
} else {
    // Original: render all (for ask-user with few options, or small session list)
    for i, opt := range m.askOptions { ... }
}
```

**Key handling changes in `askuser.go` `handleAskUserKey()`** — Add PgUp/PgDn cases:

```go
case "pgup":
    if m.askRequestID == -1 { // session picker only
        m.sessionPickerOffset -= sessionPageSize
        if m.sessionPickerOffset < 0 {
            m.sessionPickerOffset = 0
        }
        if m.askCursor >= m.sessionPickerOffset + sessionPageSize {
            m.askCursor = m.sessionPickerOffset
        }
    }
    return m, nil

case "pgdown":
    if m.askRequestID == -1 {
        maxOffset := len(m.askOptions) - sessionPageSize
        if maxOffset < 0 {
            maxOffset = 0
        }
        m.sessionPickerOffset += sessionPageSize
        if m.sessionPickerOffset > maxOffset {
            m.sessionPickerOffset = maxOffset
        }
        if m.askCursor < m.sessionPickerOffset {
            m.askCursor = m.sessionPickerOffset
        }
    }
    return m, nil
```

**Update existing Up/Down handlers** (lines 68-84) to auto-scroll viewport when cursor moves past visible range:

```go
case "up", "k":
    if len(m.askOptions) > 0 {
        m.askCursor--
        if m.askCursor < 0 {
            m.askCursor = len(m.askOptions) - 1
            // Jump viewport to end
            if m.askRequestID == -1 {
                maxOffset := len(m.askOptions) - sessionPageSize
                if maxOffset < 0 { maxOffset = 0 }
                m.sessionPickerOffset = maxOffset
            }
        }
        // Scroll viewport if cursor moved above visible area
        if m.askRequestID == -1 && m.askCursor < m.sessionPickerOffset {
            m.sessionPickerOffset = m.askCursor
        }
    }
    return m, nil

case "down", "j":
    if len(m.askOptions) > 0 {
        m.askCursor++
        if m.askCursor >= len(m.askOptions) {
            m.askCursor = 0
            m.sessionPickerOffset = 0 // Jump viewport to start
        }
        // Scroll viewport if cursor moved below visible area
        if m.askRequestID == -1 && m.askCursor >= m.sessionPickerOffset + sessionPageSize {
            m.sessionPickerOffset = m.askCursor - sessionPageSize + 1
        }
    }
    return m, nil
```

**Tests to add** (`session_picker_test.go` or `askuser_test.go`):
```
TestSessionPickerPagination_ShowsOnlyPageSize
TestSessionPickerPagination_HeaderShowsCounts
TestSessionPickerPagination_FooterShowsHints
TestSessionPickerPagination_PgDownMovesViewport
TestSessionPickerPagination_PgUpMovesViewport
TestSessionPickerPagination_PgUpAtTopStays
TestSessionPickerPagination_PgDownAtBottomStays
TestSessionPickerPagination_CursorFollowsViewport
TestSessionPickerPagination_UpArrowScrollsViewport
TestSessionPickerPagination_DownArrowScrollsViewport
TestSessionPickerPagination_WrapAroundResetsViewport
TestSessionPickerPagination_SmallListNoPagination (< sessionPageSize items renders normally)
```

---

### 1B. Session Search/Filter

**Problem**: No way to find a specific session among 20+ entries without scrolling through all of them.

**Solution**: When session picker is open, typing characters filters the session list using fuzzy matching. The `sahilm/fuzzy` library is already imported (`completion.go:6`) and used for command completions.

**Files to modify**:
- `cmd/hybridcoder-tui/model.go` — Add filter state fields
- `cmd/hybridcoder-tui/session_picker.go` — Add `filterSessions()` function
- `cmd/hybridcoder-tui/askuser.go` — Render filter input + filtered results

**New state fields in `model.go`**:
```go
// Session picker filter
sessionPickerFilter   string // current filter text
sessionPickerFiltered []int  // indices into askOptions that match filter (nil = no filter active)
```

**New function in `session_picker.go`**:
```go
import "github.com/sahilm/fuzzy"

// filterSessions returns indices of sessions matching the filter string.
func filterSessions(options []string, filter string) []int {
    if filter == "" {
        return nil // nil means "show all"
    }
    matches := fuzzy.Find(filter, options)
    indices := make([]int, len(matches))
    for i, m := range matches {
        indices[i] = m.Index
    }
    return indices
}
```

**Changes to `askuser.go` — `handleAskUserKey()`**:

In the `default` case (line 149-155), when `askRequestID == -1` (session picker mode), forward printable key presses to update the filter:
```go
default:
    if m.askRequestID == -1 {
        key := msg.String()
        if len(key) == 1 { // printable character
            m.sessionPickerFilter += key
            m.sessionPickerFiltered = filterSessions(m.askOptions, m.sessionPickerFilter)
            m.askCursor = 0
            m.sessionPickerOffset = 0
            return m, nil
        }
    }
    // ... existing forward to textInput
```

Add backspace handling in session picker mode:
```go
case "backspace":
    if m.askRequestID == -1 && m.sessionPickerFilter != "" {
        m.sessionPickerFilter = m.sessionPickerFilter[:len(m.sessionPickerFilter)-1]
        m.sessionPickerFiltered = filterSessions(m.askOptions, m.sessionPickerFilter)
        m.askCursor = 0
        m.sessionPickerOffset = 0
        return m, nil
    }
    // Fall through to textInput for normal ask-user mode
```

**Changes to `askuser.go` — `renderAskUserView()`**:

When session picker mode is active, show a filter bar and only the filtered results:
```go
if m.askRequestID == -1 {
    // Show filter bar
    filterDisplay := m.sessionPickerFilter
    if filterDisplay == "" {
        filterDisplay = dimStyle.Render("type to filter...")
    }
    b.WriteString(fmt.Sprintf("  Filter: %s", filterDisplay))
    b.WriteString("\n")

    // Determine visible options (filtered or all)
    visibleIndices := m.sessionPickerFiltered
    if visibleIndices == nil {
        visibleIndices = make([]int, len(m.askOptions))
        for i := range visibleIndices { visibleIndices[i] = i }
    }

    if len(visibleIndices) == 0 {
        b.WriteString(dimStyle.Render("  No matching sessions"))
        b.WriteString("\n")
    } else {
        // Paginate the filtered results (apply 1A pagination to visibleIndices)
    }
}
```

**Changes to Enter handler**: Map cursor through filter indices:
```go
case "enter":
    if m.askRequestID == -1 {
        selectedIndex := m.askCursor
        if m.sessionPickerFiltered != nil {
            if m.askCursor >= len(m.sessionPickerFiltered) {
                return m, nil
            }
            selectedIndex = m.sessionPickerFiltered[m.askCursor]
        }
        m.sessionPickerFilter = ""
        m.sessionPickerFiltered = nil
        return handleSessionPickerSelection(m, selectedIndex)
    }
```

**Reset filter on Escape** (first escape clears filter, second exits picker):
```go
case "escape", "esc", "ctrl+c":
    if m.askRequestID == -1 {
        if m.sessionPickerFilter != "" {
            m.sessionPickerFilter = ""
            m.sessionPickerFiltered = nil
            m.askCursor = 0
            m.sessionPickerOffset = 0
            return m, nil
        }
        // Second escape: exit picker (existing behavior)
        ...
    }
```

**Tests to add**:
```
TestSessionPickerFilter_TypingNarrowsResults
TestSessionPickerFilter_BackspaceExpandsResults
TestSessionPickerFilter_EmptyFilterShowsAll
TestSessionPickerFilter_NoMatchShowsMessage
TestSessionPickerFilter_EnterSelectsFilteredItem
TestSessionPickerFilter_EscapeClearsFilter
TestSessionPickerFilter_DoubleEscapeExitsPicker
TestSessionPickerFilter_FuzzyMatchesTitle
TestSessionPickerFilter_FuzzyMatchesModel
TestSessionPickerFilter_FilterResetsCursor
```

---

### 1C. Better Session Labels

**Problem**: Sessions display as `3d48952c  hello  (z-ai/glm-4.5-air:free)` — generic titles, long untruncated model names with provider prefix.

**Solution**: Smarter label formatting with numbered entries, truncated model names.

**File to modify**: `cmd/hybridcoder-tui/session_picker.go` — `enterSessionPicker()` lines 21-42

**Current code** (lines 37-41):
```go
if s.Model != "" {
    options[i] = fmt.Sprintf("%s  %s  (%s)", idPrefix, title, s.Model)
} else {
    options[i] = fmt.Sprintf("%s  %s", idPrefix, title)
}
```

**New code**:
```go
model := truncateModelName(s.Model)
if model != "" {
    options[i] = fmt.Sprintf("%2d. %s  %s  (%s)", i+1, idPrefix, title, model)
} else {
    options[i] = fmt.Sprintf("%2d. %s  %s", i+1, idPrefix, title)
}
```

**New helper function in `session_picker.go`**:
```go
// truncateModelName shortens verbose model identifiers for display.
// Examples:
//   "z-ai/glm-4.5-air:free"             -> "glm-4.5-air"
//   "qwen2.5-coder-7b-instruct-q4_k_m"  -> "qwen2.5-coder-7b-instruct"
//   "openai/gpt-4o"                      -> "gpt-4o"
func truncateModelName(name string) string {
    if name == "" {
        return ""
    }

    // Strip provider prefix (before /)
    if idx := strings.LastIndex(name, "/"); idx >= 0 {
        name = name[idx+1:]
    }

    // Strip :tag suffix (like :free, :latest)
    if idx := strings.Index(name, ":"); idx >= 0 {
        name = name[:idx]
    }

    // Strip quantization suffix (-q4_k_m, -Q4_K_M, etc.)
    lower := strings.ToLower(name)
    for _, quant := range []string{"-q4_k_m", "-q5_k_m", "-q8_0", "-q4_0", "-q6_k", "-q3_k_m", "-q2_k", "-q5_0"} {
        if strings.HasSuffix(lower, quant) {
            name = name[:len(name)-len(quant)]
            break
        }
    }

    // Cap at 20 chars
    if len(name) > 20 {
        name = name[:17] + "..."
    }

    return name
}
```

**Tests to add** (`session_picker_test.go`):
```
TestTruncateModelName_StripsProviderPrefix
TestTruncateModelName_StripsTagSuffix
TestTruncateModelName_StripsQuantization
TestTruncateModelName_CapsLength
TestTruncateModelName_EmptyString
TestTruncateModelName_NoPrefix
TestTruncateModelName_Combined ("z-ai/glm-4.5-air:free" -> "glm-4.5-air")
TestSessionLabels_NumberedPrefix
TestSessionLabels_UntitledFallback
```

---

## Phase 2: Status Bar Enhancement (Medium Impact, Priority 2)

### 2A. Styled Status Bar with Compact Format

**Problem**: Current status bar (`statusbar.go:17-49`) outputs plain gray text with verbose labels: `Model: z-ai/glm-4.5-air:free | Provider: openrouter | Mode: suggest`. Hard to scan, wastes space.

**Solution**: Drop labels, use compact format with "via" connector and `·` separators. Add subtle color differentiation.

**Files to modify**:
- `cmd/hybridcoder-tui/statusbar.go` — Rewrite `View()` method
- `cmd/hybridcoder-tui/styles.go` — Add 2 new styles

**New styles in `styles.go`** (add after line 53):
```go
statusValueStyle = lipgloss.NewStyle().
    Foreground(lipgloss.Color("14")) // cyan for model name

statusModeStyle = lipgloss.NewStyle().
    Foreground(lipgloss.Color("10")) // green for mode
```

**Rewritten `statusbar.go` View()**:
```go
func (s statusBarModel) View() string {
    modelName := truncateModelName(s.Model) // reuse from session_picker.go
    if modelName == "" {
        modelName = s.Model
    }

    main := statusValueStyle.Render(modelName)
    if s.Provider != "" && s.Provider != "..." {
        main += statusBarStyle.Render(" via ") + statusBarStyle.Render(s.Provider)
    }

    main += statusBarStyle.Render("  ·  ") + statusModeStyle.Render(s.Mode)

    if s.Queue > 0 {
        main += statusBarStyle.Render("  ·  ") +
            lipgloss.NewStyle().Foreground(lipgloss.Color("11")).Render(fmt.Sprintf("%d queued", s.Queue))
    }

    if s.Tokens > 0 {
        var tokenStr string
        if s.Tokens >= 1000 {
            tokenStr = fmt.Sprintf("~%.1fk tokens", float64(s.Tokens)/1000)
        } else {
            tokenStr = fmt.Sprintf("~%d tokens", s.Tokens)
        }
        main += statusBarStyle.Render("  ·  ") + statusBarStyle.Render(tokenStr)
    }

    if s.Edits > 0 {
        main += statusBarStyle.Render("  ·  ") + statusBarStyle.Render(fmt.Sprintf("%d edits", s.Edits))
    }

    return main
}
```

**Result examples**:
```
Before: Model: z-ai/glm-4.5-air:free | Provider: openrouter | Mode: suggest
After:  glm-4.5-air via openrouter  ·  suggest  ·  ~2.4k tokens  ·  3 edits
        ^cyan                ^gray      ^green      ^gray            ^gray
```

**Tests to add/update**:
```
TestStatusBar_CompactFormat
TestStatusBar_ModelTruncated
TestStatusBar_ViaProvider
TestStatusBar_ModeGreen
TestStatusBar_QueueShownWhenPositive
TestStatusBar_QueueHiddenWhenZero
TestStatusBar_TokensFormatted_K
TestStatusBar_TokensFormatted_Small
TestStatusBar_EditsShown
TestStatusBar_InitialDots (model == "..." -> shows "...")
```

---

## Phase 3: Tool Call Display Improvements (Medium Impact, Priority 3)

### 3A. Smarter Tool Result Display

**Problem**: Tool call rendering in `view.go:29-45` shows raw results truncated at 100 chars. Results can be redundant. No visual arrow connector.

**Solution**: Context-aware result display with `->` arrow, smarter truncation, and multi-line result summarization.

**File to modify**: `cmd/hybridcoder-tui/view.go` — lines 29-45

**Current code**:
```go
for _, tc := range m.toolCalls {
    icon := toolIcon(tc.Status)
    line := fmt.Sprintf(" %s %s", icon, toolCallStyle.Render(tc.Name))
    if tc.Status == "error" && tc.Result != "" {
        line += " " + errorStyle.Render(tc.Result)
    } else if tc.Status == "completed" && tc.Result != "" {
        result := tc.Result
        if len(result) > 100 {
            result = result[:97] + "..."
        }
        line += " " + dimStyle.Render(result)
    }
    b.WriteString(line)
    b.WriteString("\n")
}
```

**New code**:
```go
for _, tc := range m.toolCalls {
    icon := toolIcon(tc.Status)
    line := fmt.Sprintf(" %s %s", icon, toolCallStyle.Render(tc.Name))

    if tc.Status == "error" && tc.Result != "" {
        line += " " + errorStyle.Render("-> " + tc.Result)
    } else if tc.Status == "completed" && tc.Result != "" {
        result := formatToolResult(tc.Result)
        if result != "" {
            line += " " + dimStyle.Render("-> " + result)
        }
    } else if tc.Status == "running" && tc.Args != "" {
        args := tc.Args
        if len(args) > 60 {
            args = args[:57] + "..."
        }
        line += " " + dimStyle.Render(args)
    }
    b.WriteString(line)
    b.WriteString("\n")
}
```

**New helper function in `view.go`**:
```go
// formatToolResult produces a concise display string for a tool call result.
func formatToolResult(result string) string {
    if result == "" {
        return ""
    }

    lines := strings.Split(result, "\n")
    if len(lines) > 3 {
        preview := ""
        for _, l := range lines {
            l = strings.TrimSpace(l)
            if l != "" {
                preview = l
                break
            }
        }
        if len(preview) > 50 {
            preview = preview[:47] + "..."
        }
        if preview != "" {
            return fmt.Sprintf("%s (%d lines)", preview, len(lines))
        }
        return fmt.Sprintf("(%d lines)", len(lines))
    }

    flat := strings.Join(lines, " ")
    flat = strings.TrimSpace(flat)
    if len(flat) > 80 {
        flat = flat[:77] + "..."
    }
    return flat
}
```

**Tests to add** (`view_test.go`):
```
TestFormatToolResult_Empty
TestFormatToolResult_ShortSingleLine
TestFormatToolResult_LongSingleLineTruncated
TestFormatToolResult_MultiLineShowsCount
TestFormatToolResult_MultiLineShowsPreview
TestToolCallView_ArrowConnector
TestToolCallView_RunningShowsArgs
TestToolCallView_ErrorShowsArrow
TestToolCallView_CompletedShowsResult
```

### 3B. Distinct "denied" Icon

**Problem**: In `styles.go:64-78`, `toolIcon()` maps both "denied" and "waiting" to `toolWaitIcon` (yellow `...`). Users can't visually distinguish a denied tool from a pending one.

**File to modify**: `cmd/hybridcoder-tui/styles.go`

**Add new icon** (after line 32):
```go
toolDeniedIcon = lipgloss.NewStyle().Foreground(lipgloss.Color("9")).Render("⊘") // red circle-slash
```

**Update `toolIcon()` function** (line 73):
```go
// CURRENT:
case "waiting", "pending", "blocked", "denied":
    return toolWaitIcon

// NEW:
case "denied":
    return toolDeniedIcon
case "waiting", "pending", "blocked":
    return toolWaitIcon
```

**Tests**:
```
TestToolIcon_DeniedReturnsDistinctIcon
TestToolIcon_DeniedNotSameAsWaiting
```

---

## Phase 4: Visual Hierarchy & Polish (Lower Impact, Priority 4)

### 4A. Enhanced Approval View

**Problem**: `approval.go:22-59` `renderApprovalView()` shows a plain text prompt. No visual emphasis for dangerous operations (shell/bash, file writes) vs safe ones (read_file).

**File to modify**: `cmd/hybridcoder-tui/approval.go`

**Add severity detection**:
```go
// toolSeverity returns "high" for tools that modify state, "normal" otherwise.
func toolSeverity(toolName string) string {
    highSeverity := []string{"run_command", "bash", "write_file", "delete_file", "apply_diff"}
    lower := strings.ToLower(toolName)
    for _, t := range highSeverity {
        if strings.Contains(lower, t) {
            return "high"
        }
    }
    return "normal"
}
```

**Updated `renderApprovalView()`** — Change header (line 25-27):
```go
// Severity-aware header
severity := toolSeverity(m.approvalTool)
if severity == "high" {
    b.WriteString(errorStyle.Render("! Tool Approval Required"))
} else {
    b.WriteString(toolCallStyle.Render("Tool Approval Required"))
}
b.WriteString("\n")

// Tool name (existing)
b.WriteString(toolCallStyle.Render(fmt.Sprintf("  %s", m.approvalTool)))
b.WriteString("\n")
// ... rest of args/options unchanged
```

**Tests**:
```
TestToolSeverity_RunCommandIsHigh
TestToolSeverity_WriteFileIsHigh
TestToolSeverity_ReadFileIsNormal
TestToolSeverity_SearchCodeIsNormal
TestApprovalView_HighSeverityShowsWarning
TestApprovalView_NormalSeverityShowsDefault
```

### 4B. Streaming Progress Info

**Problem**: `view.go:50-52` shows `m.spin.View() + " Thinking...\n"` with no progress info. Users have no idea how long the model has been thinking or how many tokens have been generated.

**Files to modify**:
- `cmd/hybridcoder-tui/model.go` — Add `streamStartTime time.Time`, `streamTokenCount int`
- `cmd/hybridcoder-tui/update.go` — Track start time and count tokens
- `cmd/hybridcoder-tui/view.go` — Display progress info

**New fields in `model.go`**:
```go
// Streaming progress
streamStartTime  time.Time // set when entering stageStreaming
streamTokenCount int       // count of token messages received this turn
```

**Changes in `update.go`**:

In `sendChat()` (line 257), set start time:
```go
m.stage = stageStreaming
m.streamStartTime = time.Now()
m.streamTokenCount = 0
```

In `backendTokenMsg` handler (line 52), increment count:
```go
m.tokenBuf.WriteString(msg.Text)
m.streamTokenCount++
```

**Changes in `view.go`** (line 50-52):
```go
// CURRENT:
b.WriteString(m.spin.View() + " Thinking...\n")

// NEW:
elapsed := time.Since(m.streamStartTime).Round(time.Second)
b.WriteString(m.spin.View() + " Thinking... " + dimStyle.Render(fmt.Sprintf("(%s)", elapsed)) + "\n")
```

**Tests**:
```
TestStreamingProgress_ShowsElapsedTime
TestStreamingProgress_ShowsTokenCount
TestStreamingProgress_IncrementOnToken
TestStreamingProgress_ResetOnSendChat
```

### 4C. Improved Overflow Indicator

**Problem**: `view.go:61` shows `[42 lines above]` as plain dimStyle text. Easy to miss.

**File to modify**: `cmd/hybridcoder-tui/view.go` — line 61

**Change**:
```go
// CURRENT:
b.WriteString(dimStyle.Render(fmt.Sprintf("[%d lines above]\n", len(lines)-50)))

// NEW:
b.WriteString(dimStyle.Render(fmt.Sprintf("  ^ %d lines above (visible on completion)\n", len(lines)-50)))
```

---

## Phase 5: Agent Communication (Execute After Code Changes)

### 5A. Send Comms Message to Codex/OpenCode

**Action**: Append a new entry to `AGENTS_CONVERSATION.MD` requesting UI/UX improvement ideas.

**Full message content**:

```markdown
### Entry 172 — 2026-02-08: REQUEST — UI/UX Improvement Ideas for Go TUI

Agent: Claude | Role: Coder / Architect | Layer: N/A | Context: TUI UI/UX polish sprint | Intent: Gather improvement ideas from other agents before/during implementation
Directed to: Codex, OpenCode

**Type: General (Idea Request)**

## Context

Planning and implementing a UI/UX improvement sprint for the Go Bubble Tea TUI. All changes are non-breaking, backward compatible. The TUI is fully functional (275 tests passing) — this is about polish.

## Issues Identified (Screenshot Analysis)

1. Session picker shows all 20+ sessions (no pagination/search)
2. Session titles generic ("hello", "New session") — low info density
3. Tool call results sometimes redundant, no denied vs waiting distinction
4. Status bar plain gray text with verbose labels
5. Approval prompt doesn't differentiate dangerous vs safe operations
6. "Thinking..." spinner shows no elapsed time or token count

## Planned Improvements

1. **Session picker**: pagination (10/page), fuzzy search/filter, numbered entries, truncated model names
2. **Status bar**: compact format, drop labels, color-code model/mode, `·` separators
3. **Tool calls**: `->` arrow connector, multi-line result summarization, distinct denied icon
4. **Approval**: severity detection (high for shell/write, normal for reads), warning header
5. **Streaming**: elapsed time + token count progress display

## Questions

1. **Codex**: Any concerns about these changes from an architecture perspective? Any UX patterns from code reviews of other TUI tools we should adopt?
2. **OpenCode**: From your research on OpenCode/Crush/Claude Code UX patterns — are there quick wins we're missing? Accessibility concerns?
3. **Both**: Should we add:
   - Keyboard shortcuts help overlay (F1)?
   - `/sessions` command to manage (delete/archive) old sessions?
   - Color theme presets (solarized, monokai, etc.)?
```

---

## Implementation Order

| # | Task | File(s) | Complexity | Impact |
|---|------|---------|-----------|--------|
| 1 | Send comms message (5A) | `AGENTS_CONVERSATION.MD` | Trivial | N/A |
| 2 | Session picker pagination (1A) | `model.go`, `askuser.go` | Low | High |
| 3 | Session search/filter (1B) | `model.go`, `session_picker.go`, `askuser.go` | Medium | High |
| 4 | Session labels (1C) | `session_picker.go` | Low | Medium |
| 5 | Status bar styling (2A) | `statusbar.go`, `styles.go` | Low | Medium |
| 6 | Tool result display (3A) | `view.go` | Low | Medium |
| 7 | Denied icon (3B) | `styles.go` | Trivial | Low |
| 8 | Approval enhancement (4A) | `approval.go` | Low | Medium |
| 9 | Streaming progress (4B) | `model.go`, `update.go`, `view.go` | Low | Low-Med |
| 10 | Overflow indicator (4C) | `view.go` | Trivial | Low |

---

## Critical Files Summary

| File | Path | All Changes |
|------|------|-------------|
| model.go | `cmd/hybridcoder-tui/model.go` | +`sessionPickerOffset`, +`sessionPickerFilter`, +`sessionPickerFiltered`, +`streamStartTime`, +`streamTokenCount` |
| askuser.go | `cmd/hybridcoder-tui/askuser.go` | Paginated rendering, filter input, PgUp/PgDn, viewport-follow-cursor |
| session_picker.go | `cmd/hybridcoder-tui/session_picker.go` | `truncateModelName()`, `filterSessions()`, numbered labels |
| view.go | `cmd/hybridcoder-tui/view.go` | `formatToolResult()`, running args display, overflow indicator, progress info |
| styles.go | `cmd/hybridcoder-tui/styles.go` | +`toolDeniedIcon`, +`statusValueStyle`, +`statusModeStyle`, updated `toolIcon()` |
| statusbar.go | `cmd/hybridcoder-tui/statusbar.go` | Compact format, color-coded sections, `·` separators |
| approval.go | `cmd/hybridcoder-tui/approval.go` | `toolSeverity()`, severity-aware header |
| update.go | `cmd/hybridcoder-tui/update.go` | Token count tracking, stream start time |

---

## Verification

### After each phase:

```bash
# Go tests (must all pass)
cd cmd/hybridcoder-tui && go test ./... -v

# Python tests (must all pass — no Python changes but verify no regression)
uv run pytest tests/ -v

# Build binary
cd cmd/hybridcoder-tui && go build -o ../../build/hybridcoder-tui.exe .
```

### Manual testing checklist:

- [ ] Launch with `--go-tui`, create 15+ sessions, verify pagination shows 10/page
- [ ] Type in session picker, verify fuzzy filter narrows results
- [ ] Backspace clears filter, Escape clears filter then exits
- [ ] PgUp/PgDn scroll pages, cursor follows viewport
- [ ] Session labels show numbered prefix and truncated model names
- [ ] Status bar shows compact format without labels
- [ ] Tool calls show `->` arrow, multi-line results show line count
- [ ] Denied tools show red circle-slash icon (not yellow dots)
- [ ] Dangerous tool approval shows warning header
- [ ] Streaming shows elapsed time, token count increments
- [ ] Overflow indicator shows `^ N lines above (visible on completion)`

---

## Existing Utilities to Reuse

| Utility | Location | Reuse In |
|---------|----------|----------|
| `sahilm/fuzzy.Find()` | `completion.go:6` (import), `completion.go:40` (usage) | Session filter (1B) |
| `toolIcon()` | `styles.go:65-78` | Extended with denied (3B) |
| `sessionEntry` struct | `protocol.go` (not exported; defined in `session_picker.go` internally) | Already used in session picker |
| `dimStyle`, `errorStyle`, `toolCallStyle` | `styles.go` | Reused throughout |
| `approvalActiveStyle/InactiveStyle` | `styles.go:37-43` | Reused in session picker |
| `separator()` | `styles.go:57-62` | Already used |

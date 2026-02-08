# Bubble Tea Subagent/Nested Agent Display Patterns

**Research Date:** 2026-02-07
**Context:** Building a Claude Code-style CLI with nested subagent execution display in Go Bubble Tea

## Executive Summary

This research covers concrete implementation patterns for displaying nested/hierarchical agent execution in a terminal UI using Go's Bubble Tea framework. The patterns are based on real-world implementations from:

1. **Claude Code** - Tool execution with expandable details
2. **OpenCode AI** - Clean, readable tool call formatting
3. **Ralph TUI** - Multi-agent orchestration with nested task display
4. **Agent Deck** - Hierarchical session management
5. **Crush** - Charmbracelet's AI coding agent with tool call UI

---

## 1. Core Bubble Tea Patterns for Nested Components

### 1.1 The Nested Model Architecture

Bubble Tea uses the Elm Architecture (Model-Update-View). For nested/hierarchical displays:

**Parent-Child Message Routing:**

```go
// Root model contains child models
type MainModel struct {
    subAgents []SubAgentModel
    expanded  map[string]bool  // Track which subagents are expanded
}

// Initialize all child models using tea.Batch
func (m MainModel) Init() tea.Cmd {
    var cmds []tea.Cmd
    for _, agent := range m.subAgents {
        cmds = append(cmds, agent.Init())
    }
    return tea.Batch(cmds...)
}

// Update routes messages to child models
func (m MainModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case tea.KeyMsg:
        // Handle parent-level keys (expand/collapse, etc.)
        if msg.String() == "enter" {
            // Toggle expansion
            selectedID := m.getCurrentSelectedID()
            m.expanded[selectedID] = !m.expanded[selectedID]
        }

    default:
        // Route message to all child models
        for i, agent := range m.subAgents {
            newAgent, cmd := agent.Update(msg)
            m.subAgents[i] = newAgent.(SubAgentModel)
            cmds = append(cmds, cmd)
        }
    }

    return m, tea.Batch(cmds...)
}

// View composes child views
func (m MainModel) View() string {
    var views []string
    for _, agent := range m.subAgents {
        views = append(views, agent.View(m.expanded[agent.ID]))
    }
    return lipgloss.JoinVertical(lipgloss.Left, views...)
}
```

**Source:** [Managing nested models with Bubble Tea](https://donderom.com/posts/managing-nested-models-with-bubble-tea/)

---

### 1.2 State Management for Expand/Collapse

**Pattern 1: Boolean Map (Recommended for Dynamic Lists)**

```go
type AgentListModel struct {
    agents   []Agent
    expanded map[string]bool  // Map agent ID to expansion state
    selected int              // Currently selected agent index
}

func (m *AgentListModel) ToggleExpanded() {
    agentID := m.agents[m.selected].ID
    m.expanded[agentID] = !m.expanded[agentID]
}

func (m AgentListModel) IsExpanded(agentID string) bool {
    return m.expanded[agentID]
}
```

**Pattern 2: Embedded State (For Fixed Components)**

```go
type ToolCallCard struct {
    toolName    string
    args        map[string]interface{}
    result      string
    status      Status
    expanded    bool  // Embedded state
    spinner     spinner.Model
}

func (t *ToolCallCard) Toggle() {
    t.expanded = !t.expanded
}
```

**Pattern 3: State Machine (For Complex Workflows)**

```go
type AgentState int

const (
    StateIdle AgentState = iota
    StateRunning
    StateCollapsed
    StateExpanded
    StateComplete
    StateFailed
)

type StatefulAgent struct {
    state   AgentState
    content string
}

func (a *StatefulAgent) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        if msg.String() == "enter" {
            // State transition
            switch a.state {
            case StateCollapsed:
                a.state = StateExpanded
            case StateExpanded:
                a.state = StateCollapsed
            }
        }
    }
    return a, nil
}
```

**Source:** [The Bubbletea State Machine Pattern](https://zackproser.com/blog/bubbletea-state-machine)

---

## 2. Concurrent Progress Indicators (Multiple Subagents)

### 2.1 Multiple Spinners Pattern

When running multiple subagents in parallel, each needs its own spinner:

```go
import (
    "github.com/charmbracelet/bubbles/spinner"
    tea "github.com/charmbracelet/bubbletea"
)

type SubAgent struct {
    ID      string
    Name    string
    Status  string
    Spinner spinner.Model
    Active  bool
}

type MultiAgentModel struct {
    agents []SubAgent
}

func NewMultiAgentModel() MultiAgentModel {
    agents := []SubAgent{
        {ID: "agent1", Name: "Code Analyzer", Spinner: spinner.New(), Active: true},
        {ID: "agent2", Name: "Test Generator", Spinner: spinner.New(), Active: true},
        {ID: "agent3", Name: "Documentation", Spinner: spinner.New(), Active: false},
    }

    // Configure different spinner styles
    agents[0].Spinner.Spinner = spinner.Dot
    agents[1].Spinner.Spinner = spinner.Line
    agents[2].Spinner.Spinner = spinner.MiniDot

    return MultiAgentModel{agents: agents}
}

func (m MultiAgentModel) Init() tea.Cmd {
    // Start all active spinners concurrently
    var cmds []tea.Cmd
    for _, agent := range m.agents {
        if agent.Active {
            cmds = append(cmds, agent.Spinner.Tick)
        }
    }
    return tea.Batch(cmds...)
}

func (m MultiAgentModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case spinner.TickMsg:
        // CRITICAL: Each spinner has an internal ID
        // The TickMsg is automatically routed to the correct spinner
        for i := range m.agents {
            if m.agents[i].Active {
                var cmd tea.Cmd
                m.agents[i].Spinner, cmd = m.agents[i].Spinner.Update(msg)
                cmds = append(cmds, cmd)
            }
        }
    }

    return m, tea.Batch(cmds...)
}

func (m MultiAgentModel) View() string {
    var lines []string
    for _, agent := range m.agents {
        if agent.Active {
            line := fmt.Sprintf("%s %s: %s",
                agent.Spinner.View(),
                agent.Name,
                agent.Status)
            lines = append(lines, line)
        } else {
            line := fmt.Sprintf("✓ %s: Complete", agent.Name)
            lines = append(lines, line)
        }
    }
    return lipgloss.JoinVertical(lipgloss.Left, lines...)
}
```

**Key Implementation Detail:**

The spinner package uses `sync/atomic` ID management to ensure each spinner receives only its own tick messages. You don't need to manually route `TickMsg` - Bubble Tea handles this automatically.

**Source:** [Multiple spinners discussion](https://github.com/charmbracelet/bubbles/discussions/453)

---

### 2.2 Progress Bars for Parallel Tasks

```go
import "github.com/charmbracelet/bubbles/progress"

type TaskProgress struct {
    ID       string
    Name     string
    Progress float64  // 0.0 to 1.0
    Bar      progress.Model
}

type ParallelTasksModel struct {
    tasks []TaskProgress
}

func (m ParallelTasksModel) View() string {
    var lines []string
    for _, task := range m.tasks {
        line := fmt.Sprintf("%s\n%s",
            task.Name,
            task.Bar.ViewAs(task.Progress))
        lines = append(lines, line)
    }
    return lipgloss.JoinVertical(lipgloss.Left, lines...)
}

// Update progress dynamically
func (m *ParallelTasksModel) UpdateProgress(taskID string, newProgress float64) tea.Cmd {
    for i := range m.tasks {
        if m.tasks[i].ID == taskID {
            m.tasks[i].Progress = newProgress
            // Trigger animation
            return m.tasks[i].Bar.SetPercent(newProgress)
        }
    }
    return nil
}
```

**Source:** [Bubbles progress package](https://pkg.go.dev/github.com/charmbracelet/bubbles/progress)

---

## 3. Collapsible/Expandable Sections

### 3.1 Tree-Based Collapsible Implementation

Based on the `tree-bubble` library:

```go
type TreeNode struct {
    Value    string
    Children []*TreeNode
    Expanded bool
    Level    int  // Indentation level
}

func (n *TreeNode) Toggle() {
    n.Expanded = !n.Expanded
}

func (n *TreeNode) View() string {
    var lines []string

    // Render current node
    indent := strings.Repeat("  ", n.Level)
    icon := "▸"  // Collapsed
    if n.Expanded {
        icon = "▾"  // Expanded
    }

    if len(n.Children) > 0 {
        lines = append(lines, fmt.Sprintf("%s%s %s", indent, icon, n.Value))
    } else {
        lines = append(lines, fmt.Sprintf("%s  %s", indent, n.Value))
    }

    // Render children if expanded
    if n.Expanded {
        for _, child := range n.Children {
            child.Level = n.Level + 1
            lines = append(lines, child.View())
        }
    }

    return strings.Join(lines, "\n")
}
```

**Source:** [tree-bubble library](https://github.com/savannahostrowski/tree-bubble)

---

### 3.2 Accordion/Card Pattern for Tool Calls

This pattern mimics Claude Code's tool call display:

```go
import (
    "github.com/charmbracelet/lipgloss"
    "github.com/charmbracelet/bubbles/spinner"
)

type ToolCallStatus int

const (
    ToolPending ToolCallStatus = iota
    ToolRunning
    ToolComplete
    ToolFailed
)

type ToolCallCard struct {
    ID         string
    ToolName   string
    Args       map[string]interface{}
    Result     string
    Status     ToolCallStatus
    Expanded   bool
    Spinner    spinner.Model
    StartTime  time.Time
    Duration   time.Duration
}

func (t ToolCallCard) View() string {
    // Header style (always visible)
    headerStyle := lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(lipgloss.Color("62")).
        Padding(0, 1)

    // Content style (only when expanded)
    contentStyle := lipgloss.NewStyle().
        Padding(0, 2).
        Foreground(lipgloss.Color("241"))

    // Status indicator
    statusIcon := ""
    statusColor := lipgloss.Color("240")

    switch t.Status {
    case ToolPending:
        statusIcon = "⏳"
        statusColor = lipgloss.Color("208")
    case ToolRunning:
        statusIcon = t.Spinner.View()
        statusColor = lipgloss.Color("39")
    case ToolComplete:
        statusIcon = "✓"
        statusColor = lipgloss.Color("42")
    case ToolFailed:
        statusIcon = "✗"
        statusColor = lipgloss.Color("196")
    }

    // Build header
    expandIcon := "▸"
    if t.Expanded {
        expandIcon = "▾"
    }

    header := fmt.Sprintf("%s %s %s",
        expandIcon,
        lipgloss.NewStyle().Foreground(statusColor).Render(statusIcon),
        lipgloss.NewStyle().Bold(true).Render(t.ToolName))

    if t.Status == ToolComplete || t.Status == ToolFailed {
        header += lipgloss.NewStyle().
            Foreground(lipgloss.Color("240")).
            Render(fmt.Sprintf(" (%s)", t.Duration))
    }

    // Build content (only if expanded)
    var sections []string
    sections = append(sections, headerStyle.Render(header))

    if t.Expanded {
        // Arguments section
        if len(t.Args) > 0 {
            argsSection := "Arguments:\n"
            for k, v := range t.Args {
                argsSection += fmt.Sprintf("  %s: %v\n", k, v)
            }
            sections = append(sections, contentStyle.Render(argsSection))
        }

        // Result section (if complete)
        if t.Status == ToolComplete && t.Result != "" {
            resultStyle := lipgloss.NewStyle().
                Border(lipgloss.NormalBorder(), false, false, false, true).
                BorderForeground(lipgloss.Color("240")).
                Padding(0, 2)

            resultSection := "Result:\n" + t.Result
            sections = append(sections, resultStyle.Render(resultSection))
        }

        // Error section (if failed)
        if t.Status == ToolFailed && t.Result != "" {
            errorStyle := lipgloss.NewStyle().
                Foreground(lipgloss.Color("196")).
                Border(lipgloss.NormalBorder(), false, false, false, true).
                BorderForeground(lipgloss.Color("196")).
                Padding(0, 2)

            errorSection := "Error:\n" + t.Result
            sections = append(sections, errorStyle.Render(errorSection))
        }
    }

    return lipgloss.JoinVertical(lipgloss.Left, sections...)
}
```

**Usage in parent model:**

```go
type ConversationModel struct {
    toolCalls []ToolCallCard
    selected  int
}

func (m ConversationModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "enter":
            // Toggle expansion of selected tool call
            m.toolCalls[m.selected].Expanded = !m.toolCalls[m.selected].Expanded

        case "up":
            if m.selected > 0 {
                m.selected--
            }

        case "down":
            if m.selected < len(m.toolCalls)-1 {
                m.selected++
            }
        }

    case spinner.TickMsg:
        // Update all running tool spinners
        for i := range m.toolCalls {
            if m.toolCalls[i].Status == ToolRunning {
                var cmd tea.Cmd
                m.toolCalls[i].Spinner, cmd = m.toolCalls[i].Spinner.Update(msg)
                cmds = append(cmds, cmd)
            }
        }
    }

    return m, tea.Batch(cmds...)
}

func (m ConversationModel) View() string {
    var cards []string
    for i, card := range m.toolCalls {
        // Highlight selected card
        if i == m.selected {
            highlightStyle := lipgloss.NewStyle().
                Background(lipgloss.Color("235")).
                Padding(0, 1)
            cards = append(cards, highlightStyle.Render(card.View()))
        } else {
            cards = append(cards, card.View())
        }
    }
    return lipgloss.JoinVertical(lipgloss.Left, cards...)
}
```

---

## 4. Streaming Token Display for Subagents

### 4.1 Real-Time Token Streaming Pattern

```go
type TokenChunk struct {
    AgentID string
    Text    string
}

type StreamingAgentModel struct {
    ID       string
    Content  strings.Builder
    Active   bool
    viewport viewport.Model
}

func (m StreamingAgentModel) Init() tea.Cmd {
    // Start listening for token chunks
    return waitForTokens(m.ID)
}

// Custom message for incoming tokens
type TokenMsg struct {
    AgentID string
    Chunk   string
}

func waitForTokens(agentID string) tea.Cmd {
    return func() tea.Msg {
        // Simulate receiving tokens from LLM
        // In real implementation, this would read from a channel
        chunk := <-tokenChannel  // Your token source
        return TokenMsg{
            AgentID: agentID,
            Chunk:   chunk,
        }
    }
}

func (m StreamingAgentModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case TokenMsg:
        if msg.AgentID == m.ID {
            // Append new token
            m.Content.WriteString(msg.Chunk)

            // Update viewport
            m.viewport.SetContent(m.Content.String())
            m.viewport.GotoBottom()  // Auto-scroll to latest

            // Continue waiting for more tokens
            if m.Active {
                cmds = append(cmds, waitForTokens(m.ID))
            }
        }
    }

    // Update viewport for scrolling
    var cmd tea.Cmd
    m.viewport, cmd = m.viewport.Update(msg)
    cmds = append(cmds, cmd)

    return m, tea.Batch(cmds...)
}

func (m StreamingAgentModel) View() string {
    if !m.Active && m.Content.Len() == 0 {
        return lipgloss.NewStyle().
            Foreground(lipgloss.Color("240")).
            Render("(waiting for response...)")
    }

    return m.viewport.View()
}
```

---

### 4.2 Multi-Agent Parallel Streaming

When multiple subagents stream simultaneously:

```go
type MultiStreamModel struct {
    agents   map[string]*StreamingAgentModel
    layout   []string  // Order of agent IDs for display
    expanded map[string]bool
}

func (m MultiStreamModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case TokenMsg:
        // Route to specific agent
        if agent, exists := m.agents[msg.AgentID]; exists {
            newAgent, cmd := agent.Update(msg)
            m.agents[msg.AgentID] = newAgent.(*StreamingAgentModel)
            cmds = append(cmds, cmd)
        }

    default:
        // Broadcast to all agents
        for id, agent := range m.agents {
            newAgent, cmd := agent.Update(msg)
            m.agents[id] = newAgent.(*StreamingAgentModel)
            cmds = append(cmds, cmd)
        }
    }

    return m, tea.Batch(cmds...)
}

func (m MultiStreamModel) View() string {
    var sections []string

    for _, agentID := range m.layout {
        agent := m.agents[agentID]

        // Agent header (always visible)
        headerStyle := lipgloss.NewStyle().
            Bold(true).
            Foreground(lipgloss.Color("39"))

        expandIcon := "▸"
        if m.expanded[agentID] {
            expandIcon = "▾"
        }

        header := fmt.Sprintf("%s Agent: %s", expandIcon, agentID)
        sections = append(sections, headerStyle.Render(header))

        // Agent content (if expanded)
        if m.expanded[agentID] {
            contentStyle := lipgloss.NewStyle().
                Border(lipgloss.NormalBorder(), false, false, false, true).
                BorderForeground(lipgloss.Color("240")).
                Padding(0, 2)

            sections = append(sections, contentStyle.Render(agent.View()))
        }

        sections = append(sections, "") // Spacing
    }

    return lipgloss.JoinVertical(lipgloss.Left, sections...)
}
```

---

## 5. Viewport and Scrollable Content for Nested Components

### 5.1 Calculating Heights for Nested Viewports

Critical pattern from the research:

```go
import (
    "github.com/charmbracelet/bubbles/viewport"
    "github.com/charmbracelet/lipgloss"
)

type NestedScrollModel struct {
    viewport       viewport.Model
    headerContent  string
    footerContent  string
    ready          bool  // Wait for WindowSizeMsg
}

func (m NestedScrollModel) Init() tea.Cmd {
    return nil  // Lazy init pattern
}

func (m NestedScrollModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmd tea.Cmd

    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        // CRITICAL: Calculate viewport height dynamically
        headerHeight := lipgloss.Height(m.headerContent)
        footerHeight := lipgloss.Height(m.footerContent)

        // Reserve space for header/footer
        viewportHeight := msg.Height - headerHeight - footerHeight

        if !m.ready {
            // Initialize viewport with calculated dimensions
            m.viewport = viewport.New(msg.Width, viewportHeight)
            m.ready = true
        } else {
            // Update existing viewport
            m.viewport.Width = msg.Width
            m.viewport.Height = viewportHeight
        }
    }

    // Always update viewport
    m.viewport, cmd = m.viewport.Update(msg)

    return m, cmd
}

func (m NestedScrollModel) View() string {
    if !m.ready {
        return "Initializing..."
    }

    return lipgloss.JoinVertical(
        lipgloss.Left,
        m.headerContent,
        m.viewport.View(),
        m.footerContent,
    )
}
```

**Key Takeaway:** Use `lipgloss.Height()` to measure rendered content dynamically, ensuring accurate space calculations even as styles change.

**Source:** [Component Integration - DeepWiki](https://deepwiki.com/charmbracelet/bubbletea/6.5-component-integration)

---

### 5.2 Nested Scrollable Sections

For subagents with their own scrollable output:

```go
type SubAgentWithScroll struct {
    ID           string
    Name         string
    Viewport     viewport.Model
    Expanded     bool
    MaxHeight    int  // Maximum height when expanded
}

func (s SubAgentWithScroll) View() string {
    headerStyle := lipgloss.NewStyle().
        Bold(true).
        Padding(0, 1).
        Background(lipgloss.Color("62"))

    if !s.Expanded {
        return headerStyle.Render(fmt.Sprintf("▸ %s", s.Name))
    }

    // Expanded view with scrollable content
    borderStyle := lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(lipgloss.Color("62"))

    header := headerStyle.Render(fmt.Sprintf("▾ %s", s.Name))
    scrollableContent := s.Viewport.View()

    // Add scroll indicators
    scrollInfo := ""
    if s.Viewport.TotalLineCount() > s.Viewport.Height {
        scrollPct := int(s.Viewport.ScrollPercent() * 100)
        scrollInfo = lipgloss.NewStyle().
            Foreground(lipgloss.Color("240")).
            Render(fmt.Sprintf(" [%d%%]", scrollPct))
    }

    return lipgloss.JoinVertical(
        lipgloss.Left,
        header + scrollInfo,
        borderStyle.Render(scrollableContent),
    )
}
```

---

## 6. Real-World Implementations

### 6.1 Claude Code Display Pattern

Based on research findings:

**Key Features:**
1. Tool calls are displayed as expandable cards
2. Clear status indicators (pending, running, complete, failed)
3. Expandable to show arguments and results
4. Can click or press Enter to expand/collapse
5. Nested tool calls (subagents) shown hierarchically

**Visual Pattern:**

```
Main Agent Response:
  I'll analyze the codebase using multiple tools...

  ▾ ✓ bash (1.2s)
    │ Arguments:
    │   command: "grep -r 'TODO' src/"
    │
    └─ Result:
       src/main.py:45: # TODO: Implement error handling
       src/utils.py:12: # TODO: Add tests

  ▸ ⏳ read_file

  ▸ 🔄 agent:analyze_dependencies (running)
```

---

### 6.2 Ralph TUI Pattern

Ralph TUI provides autonomous agent orchestration with:

1. **Two-Panel Layout:**
   - Left: Task list (stories/epics)
   - Right: Live agent output

2. **Nested Task Display:**
   - Epic → Stories → Subtasks
   - Collapsible at each level

3. **Progress Tracking:**
   - Progress bar for overall completion
   - ETA calculation
   - Real-time token streaming in right pane

**Architecture:**
```go
type RalphModel struct {
    taskTree     *TreeNode        // Left panel
    agentOutput  viewport.Model   // Right panel
    progressBar  progress.Model
    currentTask  string
}
```

**Source:** [Ralph TUI GitHub](https://github.com/syntax-syndicate/ralph-ai-tui)

---

### 6.3 Agent Deck Pattern

Agent Deck manages multiple AI coding sessions with:

1. **Hierarchical Groups:**
   - Groups can contain sessions or nested groups
   - Collapsible groups with persistence

2. **Session List + Preview:**
   - Left: Session tree
   - Right: Live terminal preview

3. **Smart Indicators:**
   - Active/inactive status
   - Output indicators
   - Cost tracking

**Source:** [Agent Deck GitHub](https://github.com/asheshgoplani/agent-deck)

---

### 6.4 OpenCode Display Pattern

OpenCode is known for its clean, readable interface:

**Key Features:**
1. Tool calls clearly formatted
2. Readable file diffs
3. Progress indicators without distraction
4. Tab-based session management (Conduit integration)

**Visual Style:**
```
┌─ Tool: edit_file ────────────────┐
│ File: src/main.go                │
│ Status: Complete ✓               │
│                                  │
│ Changes:                         │
│ + Added error handling           │
│ + Improved logging               │
│                                  │
│ Lines changed: 45                │
└──────────────────────────────────┘
```

**Source:** [OpenCode AI](https://opencode.ai/)

---

## 7. Lipgloss Styling Patterns

### 7.1 Bordered Card with Sections

```go
import "github.com/charmbracelet/lipgloss"

func RenderToolCard(toolName, status, args, result string, expanded bool) string {
    // Define styles
    borderStyle := lipgloss.NormalBorder()

    headerStyle := lipgloss.NewStyle().
        Bold(true).
        Foreground(lipgloss.Color("39")).
        Padding(0, 1)

    sectionStyle := lipgloss.NewStyle().
        Border(borderStyle, false, false, false, true).  // Left border only
        BorderForeground(lipgloss.Color("240")).
        Padding(0, 2)

    cardStyle := lipgloss.NewStyle().
        Border(borderStyle).
        BorderForeground(lipgloss.Color("62")).
        Padding(1)

    // Build sections
    var sections []string

    // Header (always visible)
    sections = append(sections, headerStyle.Render(
        fmt.Sprintf("%s - %s", toolName, status)))

    if expanded {
        // Arguments section
        if args != "" {
            sections = append(sections, sectionStyle.Render(
                "Arguments:\n" + args))
        }

        // Result section
        if result != "" {
            sections = append(sections, sectionStyle.Render(
                "Result:\n" + result))
        }
    }

    // Join and wrap in card
    content := lipgloss.JoinVertical(lipgloss.Left, sections...)
    return cardStyle.Render(content)
}
```

---

### 7.2 Nested Border Rendering

For hierarchical displays with multiple nested levels:

```go
func RenderNestedAgent(agent Agent, level int) string {
    // Indent based on nesting level
    indent := strings.Repeat("  ", level)

    // Different border colors for different levels
    borderColors := []lipgloss.Color{
        lipgloss.Color("39"),   // Level 0: Blue
        lipgloss.Color("208"),  // Level 1: Orange
        lipgloss.Color("170"),  // Level 2: Purple
    }

    borderColor := borderColors[level % len(borderColors)]

    borderStyle := lipgloss.NewStyle().
        Border(lipgloss.NormalBorder(), false, false, false, true).
        BorderForeground(borderColor).
        Padding(0, 1)

    // Build content
    var lines []string
    lines = append(lines, fmt.Sprintf("%s%s %s",
        indent,
        agent.StatusIcon(),
        agent.Name))

    // Render child agents if expanded
    if agent.Expanded {
        for _, child := range agent.Children {
            childView := RenderNestedAgent(child, level+1)
            lines = append(lines, borderStyle.Render(childView))
        }
    }

    return strings.Join(lines, "\n")
}
```

---

### 7.3 JoinVertical with Dynamic Heights

```go
func RenderDynamicLayout(header, content, footer string, totalHeight int) string {
    // Measure header and footer
    headerHeight := lipgloss.Height(header)
    footerHeight := lipgloss.Height(footer)

    // Calculate content height
    contentHeight := totalHeight - headerHeight - footerHeight

    // Style content area with calculated height
    contentStyle := lipgloss.NewStyle().
        Height(contentHeight).
        Border(lipgloss.RoundedBorder())

    // Join sections
    return lipgloss.JoinVertical(
        lipgloss.Left,
        header,
        contentStyle.Render(content),
        footer,
    )
}
```

**Source:** [Lipgloss Package Documentation](https://pkg.go.dev/github.com/charmbracelet/lipgloss)

---

## 8. Complete Example: Multi-Subagent Display

Here's a complete, production-ready example combining all patterns:

```go
package main

import (
    "fmt"
    "strings"
    "time"

    "github.com/charmbracelet/bubbles/spinner"
    "github.com/charmbracelet/bubbles/viewport"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
)

// Message types
type SubAgentCompleteMsg struct {
    ID     string
    Result string
}

type SubAgentTokenMsg struct {
    ID    string
    Chunk string
}

// SubAgent represents a nested agent execution
type SubAgent struct {
    ID        string
    Name      string
    Status    Status
    Expanded  bool
    Content   strings.Builder
    Spinner   spinner.Model
    StartTime time.Time
    EndTime   time.Time
}

type Status int

const (
    StatusPending Status = iota
    StatusRunning
    StatusComplete
    StatusFailed
)

func (s SubAgent) Duration() time.Duration {
    if s.Status == StatusComplete || s.Status == StatusFailed {
        return s.EndTime.Sub(s.StartTime)
    }
    return time.Since(s.StartTime)
}

func (s SubAgent) StatusIcon() string {
    switch s.Status {
    case StatusPending:
        return "⏳"
    case StatusRunning:
        return s.Spinner.View()
    case StatusComplete:
        return "✓"
    case StatusFailed:
        return "✗"
    default:
        return "?"
    }
}

func (s SubAgent) StatusColor() lipgloss.Color {
    switch s.Status {
    case StatusPending:
        return lipgloss.Color("208")
    case StatusRunning:
        return lipgloss.Color("39")
    case StatusComplete:
        return lipgloss.Color("42")
    case StatusFailed:
        return lipgloss.Color("196")
    default:
        return lipgloss.Color("240")
    }
}

// Main model
type Model struct {
    subAgents    []SubAgent
    selected     int
    viewport     viewport.Model
    ready        bool
    width        int
    height       int
}

func NewModel() Model {
    s1 := spinner.New()
    s1.Spinner = spinner.Dot

    s2 := spinner.New()
    s2.Spinner = spinner.Line

    s3 := spinner.New()
    s3.Spinner = spinner.MiniDot

    return Model{
        subAgents: []SubAgent{
            {
                ID:        "agent1",
                Name:      "Code Analyzer",
                Status:    StatusRunning,
                Expanded:  true,
                Spinner:   s1,
                StartTime: time.Now(),
            },
            {
                ID:        "agent2",
                Name:      "Test Generator",
                Status:    StatusRunning,
                Expanded:  false,
                Spinner:   s2,
                StartTime: time.Now(),
            },
            {
                ID:        "agent3",
                Name:      "Documentation Writer",
                Status:    StatusPending,
                Expanded:  false,
                Spinner:   s3,
            },
        },
        selected: 0,
    }
}

func (m Model) Init() tea.Cmd {
    var cmds []tea.Cmd

    // Start spinners for running agents
    for _, agent := range m.subAgents {
        if agent.Status == StatusRunning {
            cmds = append(cmds, agent.Spinner.Tick)
        }
    }

    // Simulate token streaming
    cmds = append(cmds, simulateTokenStream("agent1"))
    cmds = append(cmds, simulateTokenStream("agent2"))

    return tea.Batch(cmds...)
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height

        headerHeight := 3
        footerHeight := 2
        viewportHeight := m.height - headerHeight - footerHeight

        if !m.ready {
            m.viewport = viewport.New(m.width, viewportHeight)
            m.ready = true
        } else {
            m.viewport.Width = m.width
            m.viewport.Height = viewportHeight
        }

        m.viewport.SetContent(m.renderAgents())

    case tea.KeyMsg:
        switch msg.String() {
        case "q", "ctrl+c":
            return m, tea.Quit

        case "up", "k":
            if m.selected > 0 {
                m.selected--
                m.viewport.SetContent(m.renderAgents())
            }

        case "down", "j":
            if m.selected < len(m.subAgents)-1 {
                m.selected++
                m.viewport.SetContent(m.renderAgents())
            }

        case "enter", " ":
            // Toggle expansion
            m.subAgents[m.selected].Expanded = !m.subAgents[m.selected].Expanded
            m.viewport.SetContent(m.renderAgents())
        }

    case spinner.TickMsg:
        // Update all running spinners
        for i := range m.subAgents {
            if m.subAgents[i].Status == StatusRunning {
                var cmd tea.Cmd
                m.subAgents[i].Spinner, cmd = m.subAgents[i].Spinner.Update(msg)
                cmds = append(cmds, cmd)
            }
        }

    case SubAgentTokenMsg:
        // Append token to specific agent
        for i := range m.subAgents {
            if m.subAgents[i].ID == msg.ID {
                m.subAgents[i].Content.WriteString(msg.Chunk)
                m.viewport.SetContent(m.renderAgents())

                // Continue streaming
                if m.subAgents[i].Status == StatusRunning {
                    cmds = append(cmds, simulateTokenStream(msg.ID))
                }
                break
            }
        }

    case SubAgentCompleteMsg:
        // Mark agent as complete
        for i := range m.subAgents {
            if m.subAgents[i].ID == msg.ID {
                m.subAgents[i].Status = StatusComplete
                m.subAgents[i].EndTime = time.Now()
                m.subAgents[i].Content.WriteString("\n" + msg.Result)
                m.viewport.SetContent(m.renderAgents())
                break
            }
        }
    }

    // Update viewport
    var cmd tea.Cmd
    m.viewport, cmd = m.viewport.Update(msg)
    cmds = append(cmds, cmd)

    return m, tea.Batch(cmds...)
}

func (m Model) View() string {
    if !m.ready {
        return "Initializing..."
    }

    // Header
    headerStyle := lipgloss.NewStyle().
        Bold(true).
        Foreground(lipgloss.Color("39")).
        Padding(1, 2).
        Background(lipgloss.Color("235"))

    header := headerStyle.Render("🤖 Multi-Agent Execution Dashboard")

    // Footer
    footerStyle := lipgloss.NewStyle().
        Foreground(lipgloss.Color("240")).
        Padding(0, 2)

    footer := footerStyle.Render(
        "↑/↓: Navigate | Enter: Expand/Collapse | q: Quit")

    return lipgloss.JoinVertical(
        lipgloss.Left,
        header,
        m.viewport.View(),
        footer,
    )
}

func (m Model) renderAgents() string {
    var cards []string

    for i, agent := range m.subAgents {
        card := m.renderAgentCard(agent, i == m.selected)
        cards = append(cards, card)
        cards = append(cards, "") // Spacing
    }

    return strings.Join(cards, "\n")
}

func (m Model) renderAgentCard(agent SubAgent, selected bool) string {
    // Styles
    borderColor := agent.StatusColor()
    if selected {
        borderColor = lipgloss.Color("226") // Yellow for selection
    }

    cardStyle := lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(borderColor).
        Padding(0, 1).
        Width(m.width - 4)

    headerStyle := lipgloss.NewStyle().
        Bold(true).
        Foreground(borderColor)

    contentStyle := lipgloss.NewStyle().
        Border(lipgloss.NormalBorder(), false, false, false, true).
        BorderForeground(lipgloss.Color("240")).
        Padding(0, 2).
        Foreground(lipgloss.Color("252"))

    // Build header
    expandIcon := "▸"
    if agent.Expanded {
        expandIcon = "▾"
    }

    header := fmt.Sprintf("%s %s %s",
        expandIcon,
        agent.StatusIcon(),
        agent.Name)

    if agent.Status == StatusComplete || agent.Status == StatusFailed {
        header += lipgloss.NewStyle().
            Foreground(lipgloss.Color("240")).
            Render(fmt.Sprintf(" (%s)", agent.Duration().Round(time.Millisecond)))
    }

    sections := []string{headerStyle.Render(header)}

    // Add content if expanded
    if agent.Expanded && agent.Content.Len() > 0 {
        content := agent.Content.String()
        sections = append(sections, contentStyle.Render(content))
    }

    cardContent := lipgloss.JoinVertical(lipgloss.Left, sections...)

    if selected {
        // Add selection indicator
        selectionStyle := lipgloss.NewStyle().
            Background(lipgloss.Color("235"))
        return selectionStyle.Render(cardStyle.Render(cardContent))
    }

    return cardStyle.Render(cardContent)
}

// Simulate token streaming (replace with real LLM streaming)
func simulateTokenStream(agentID string) tea.Cmd {
    return tea.Tick(100*time.Millisecond, func(t time.Time) tea.Msg {
        // In real implementation, read from LLM stream
        chunks := []string{
            "Analyzing code structure...\n",
            "Found 3 potential issues:\n",
            "1. Unused imports in main.go\n",
            "2. Missing error handling in utils.go\n",
            "3. Deprecated API usage in client.go\n",
        }

        idx := int(time.Now().Unix()) % len(chunks)
        return SubAgentTokenMsg{
            ID:    agentID,
            Chunk: chunks[idx],
        }
    })
}

func main() {
    p := tea.NewProgram(NewModel(), tea.WithAltScreen())
    if _, err := p.Run(); err != nil {
        fmt.Println("Error:", err)
    }
}
```

---

## 9. Architecture Recommendations

### 9.1 Message Flow for Nested Agents

```
User Input
    ↓
Root Model (MainAgent)
    ↓
┌───────────┬───────────┬───────────┐
│           │           │           │
SubAgent1   SubAgent2   SubAgent3   ← Each has own spinner, state
    ↓           ↓           ↓
LLM Stream  File Ops    Code Analysis
    ↓           ↓           ↓
TokenMsg    ResultMsg   ProgressMsg
    ↓           ↓           ↓
Update Model ← tea.Batch ← Concurrent Commands
    ↓
View() renders all agents
```

---

### 9.2 State Management Strategy

**For Small Number of Subagents (< 10):**
- Use slice of structs: `[]SubAgent`
- Direct index-based selection
- Simple iteration for rendering

**For Large Number or Dynamic Subagents:**
- Use map for O(1) lookup: `map[string]*SubAgent`
- Maintain separate slice for ordering: `[]string` (IDs)
- Use map for expansion state: `map[string]bool`

---

### 9.3 Performance Considerations

1. **Lazy Viewport Initialization:**
   - Wait for `tea.WindowSizeMsg` before creating viewports
   - Prevents rendering artifacts

2. **Selective Updates:**
   - Only update models that need it (check message type)
   - Use `tea.Batch` for parallel updates

3. **Content Truncation:**
   - For very long streaming output, implement ring buffer
   - Keep last N lines only

4. **Debounced Rendering:**
   - For high-frequency token streams, batch updates
   - Render every N tokens instead of every token

---

## 10. Key Takeaways

### ✅ DO:
- Use `tea.Batch` for concurrent spinner/progress updates
- Implement lazy viewport initialization (wait for WindowSizeMsg)
- Use `lipgloss.Height()` for dynamic height calculations
- Route messages explicitly to child models
- Use different spinner styles for different agents (visual distinction)
- Implement expand/collapse with simple boolean state
- Use viewport for scrollable subagent output
- Provide visual feedback for selection (highlight, border color)

### ❌ DON'T:
- Don't create viewports before receiving WindowSizeMsg
- Don't manually route TickMsg to spinners (auto-routed by ID)
- Don't forget to call `tea.Batch` when returning multiple commands
- Don't render entire content if collapsed (performance)
- Don't hardcode heights - always calculate from window size
- Don't block Update() - use commands for async operations

---

## 11. References and Sources

### Core Documentation
- [Bubble Tea Framework](https://github.com/charmbracelet/bubbletea)
- [Bubbles Component Library](https://github.com/charmbracelet/bubbles)
- [Lipgloss Styling](https://github.com/charmbracelet/lipgloss)

### Implementation Patterns
- [Managing Nested Models with Bubble Tea](https://donderom.com/posts/managing-nested-models-with-bubble-tea/)
- [The Bubbletea State Machine Pattern](https://zackproser.com/blog/bubbletea-state-machine)
- [Tips for Building Bubble Tea Programs](https://leg100.github.io/en/posts/building-bubbletea-programs/)
- [Commands in Bubble Tea](https://charm.land/blog/commands-in-bubbletea/)

### Real-World Examples
- [tree-bubble - Collapsible Tree View](https://github.com/savannahostrowski/tree-bubble)
- [Ralph TUI - AI Agent Orchestrator](https://github.com/syntax-syndicate/ralph-ai-tui)
- [Agent Deck - Session Manager](https://github.com/asheshgoplani/agent-deck)
- [Crush - Charmbracelet AI Agent](https://github.com/charmbracelet/crush)
- [OpenCode AI - Terminal Coding Agent](https://opencode.ai/)

### Community Resources
- [Nested Components Discussion](https://github.com/charmbracelet/bubbletea/discussions/176)
- [Multiple Spinners Discussion](https://github.com/charmbracelet/bubbles/discussions/453)
- [Multi-Model Message Routing](https://github.com/charmbracelet/bubbletea/discussions/751)

### Claude Code
- [Create Custom Subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Agent System & Subagents](https://deepwiki.com/anthropics/claude-code/3.1-agent-system-and-subagents)
- [The Task Tool: Claude Code's Agent Orchestration](https://dev.to/bhaidar/the-task-tool-claude-codes-agent-orchestration-system-4bf2)

---

## Appendix: Quick Reference Cheat Sheet

### Common Patterns

```go
// 1. Concurrent spinners
return tea.Batch(
    spinner1.Tick,
    spinner2.Tick,
    spinner3.Tick,
)

// 2. Toggle expansion
m.expanded[id] = !m.expanded[id]

// 3. Dynamic viewport height
viewportHeight := totalHeight - lipgloss.Height(header) - lipgloss.Height(footer)

// 4. Route to child models
for i, child := range m.children {
    newChild, cmd := child.Update(msg)
    m.children[i] = newChild
    cmds = append(cmds, cmd)
}
return m, tea.Batch(cmds...)

// 5. Nested rendering
lipgloss.JoinVertical(lipgloss.Left,
    header,
    child1.View(),
    child2.View(),
    footer,
)

// 6. Bordered card
cardStyle := lipgloss.NewStyle().
    Border(lipgloss.RoundedBorder()).
    BorderForeground(lipgloss.Color("62")).
    Padding(1)

// 7. Left-border section
sectionStyle := lipgloss.NewStyle().
    Border(lipgloss.NormalBorder(), false, false, false, true).
    BorderForeground(lipgloss.Color("240")).
    Padding(0, 2)
```

---

**End of Research Document**

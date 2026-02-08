# Deep Research: TODO/Task Tracking Display in Go Bubble Tea

**Research Question**: How to implement a Claude Code-style TODO list / task tracking display in a Go Bubble Tea terminal UI for an AI coding assistant.

**Date**: 2026-02-07

---

## Table of Contents

1. [Claude Code's Task Tracking UI](#claude-codes-task-tracking-ui)
2. [Bubble Tea Architecture for Task Lists](#bubble-tea-architecture-for-task-lists)
3. [Key Components & Patterns](#key-components--patterns)
4. [Implementation Patterns](#implementation-patterns)
5. [Concrete Go Code Examples](#concrete-go-code-examples)
6. [Real-World References](#real-world-references)
7. [Recommended Architecture](#recommended-architecture)

---

## Claude Code's Task Tracking UI

### How Claude Code Works

Claude Code uses a **built-in TodoWrite tool** to create and manage task checklists that appear in your terminal UI. The system:

- Automatically creates and updates todo lists as you work
- Shows real-time updates as Claude progresses through tasks
- Displays three states: **pending** (not started), **in_progress** (currently working), **completed** (finished)
- Uses present continuous forms (e.g., "Running tests") for active tasks
- Maintains exactly ONE in_progress task at a time

### 2026 Evolution: Todos → Tasks

As of January 2026, Claude Code evolved from simple todos to a **persistent task management system**:

- **Before**: Todos lived in memory, lost on session close
- **After**: Tasks persist in `~/.claude/tasks/` and broadcast updates across sessions
- **New capabilities**: Dependencies, blockers, multi-session collaboration
- **Architecture**: Four specialized tools instead of flat TodoWrite

### TodoWrite Data Structure

From Claude Code's system prompts:

```markdown
## Task States
- pending: Not yet started
- in_progress: Currently active (limit one at a time)
- completed: Successfully finished

## Task Format
Each task requires TWO forms:
- content: "Run tests" (imperative)
- activeForm: "Running tests" (present continuous)

## Critical Rules
- Mark complete only when fully accomplished
- Never mark incomplete/errored work as done
- Maintain exactly ONE in_progress task
- Update status immediately upon completion
```

**Key Insight**: Claude Code's task list is NOT part of the streaming output — it's a persistent UI element that updates in real-time alongside the conversation.

---

## Bubble Tea Architecture for Task Lists

### Core Bubble Tea Pattern: Model-View-Update (MVU)

Bubble Tea is based on [The Elm Architecture](https://github.com/charmbracelet/bubbletea):

1. **Model**: Application state (task list, status, current task)
2. **Init**: Returns initial command to run
3. **Update**: Handles messages, updates model, returns new model + command
4. **View**: Renders UI string from model state

### Nested Models for Complex UIs

For a task list + streaming output display, you need **nested model composition**:

```go
type RootModel struct {
    taskList      TaskListModel    // Child model: task tracking
    outputView    ViewportModel    // Child model: scrolling output
    currentView   string           // "split" | "output-only"
    width, height int
}
```

**Architecture principle** ([source](https://leg100.github.io/en/posts/building-bubbletea-programs)):

> The root model becomes a **message router** and **screen compositor**, responsible for:
> - Routing messages to the correct child models
> - Populating layout with content from child models' View() methods
> - Forming a tree of models where messages relay down and results pass back up

### Message Routing Pattern

```go
func (m RootModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmd tea.Cmd
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        m.width, m.height = msg.Width, msg.Height
        // Route to children
        m.taskList, cmd = m.taskList.Update(msg)
        cmds = append(cmds, cmd)
        m.outputView, cmd = m.outputView.Update(msg)
        cmds = append(cmds, cmd)

    case TaskUpdateMsg:
        // Route only to taskList
        m.taskList, cmd = m.taskList.Update(msg)
        cmds = append(cmds, cmd)

    case OutputMsg:
        // Route only to outputView
        m.outputView, cmd = m.outputView.Update(msg)
        cmds = append(cmds, cmd)
    }

    return m, tea.Batch(cmds...)
}
```

---

## Key Components & Patterns

### 1. List Component with Status Indicators

The [Bubbles list package](https://pkg.go.dev/github.com/charmbracelet/bubbles/list) provides:

- Feature-rich browsing of items
- Optional filtering, pagination, help
- **Built-in spinner** to indicate activity
- Status messages
- Customizable `ItemDelegate` for custom rendering

**Key pattern**: Use a custom `ItemDelegate` to render task status per item:

```go
type Task struct {
    ID          string
    Content     string
    ActiveForm  string
    Status      TaskStatus  // pending, in_progress, completed, failed
    spinner     spinner.Model
}

// Implement list.Item interface
func (t Task) Title() string       { return t.Content }
func (t Task) Description() string { return t.statusString() }
func (t Task) FilterValue() string { return t.Content }

func (t Task) statusString() string {
    switch t.Status {
    case StatusCompleted:
        return "✓ Completed"
    case StatusInProgress:
        return t.spinner.View() + " " + t.ActiveForm
    case StatusFailed:
        return "✗ Failed"
    case StatusPending:
        return "○ Pending"
    }
    return ""
}
```

### 2. Individual Spinners Per Task

From the [spinner package docs](https://pkg.go.dev/github.com/charmbracelet/bubbles/spinner):

> A spinner is useful for indicating that some kind of operation is happening. There are a couple default ones, but you can also pass your own "frames."

**Pattern**: Each task gets its own spinner instance:

```go
type TaskListModel struct {
    tasks []Task
}

func NewTask(content, activeForm string) Task {
    s := spinner.New()
    s.Spinner = spinner.Dot
    s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

    return Task{
        ID:         uuid.New().String(),
        Content:    content,
        ActiveForm: activeForm,
        Status:     StatusPending,
        spinner:    s,
    }
}

func (m TaskListModel) Update(msg tea.Msg) (TaskListModel, tea.Cmd) {
    var cmds []tea.Cmd

    for i := range m.tasks {
        if m.tasks[i].Status == StatusInProgress {
            var cmd tea.Cmd
            m.tasks[i].spinner, cmd = m.tasks[i].spinner.Update(msg)
            cmds = append(cmds, cmd)
        }
    }

    return m, tea.Batch(cmds...)
}
```

**Critical**: Only update spinners for in-progress tasks to avoid performance issues.

### 3. Viewport for Scrolling Output

The [viewport package](https://pkg.go.dev/github.com/charmbracelet/bubbles/viewport) provides:

- Vertically scrolling content
- Standard pager keybindings
- Mouse wheel support

```go
import "github.com/charmbracelet/bubbles/viewport"

type OutputModel struct {
    viewport viewport.Model
    content  []string
}

func (m OutputModel) Update(msg tea.Msg) (OutputModel, tea.Cmd) {
    var cmd tea.Cmd

    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        m.viewport.Width = msg.Width
        m.viewport.Height = msg.Height - 10 // Reserve space for task list

    case OutputLineMsg:
        m.content = append(m.content, msg.Line)
        m.viewport.SetContent(strings.Join(m.content, "\n"))
        m.viewport.GotoBottom()
    }

    m.viewport, cmd = m.viewport.Update(msg)
    return m, cmd
}
```

### 4. Split Layout Pattern

Combining task list + streaming output:

```go
func (m RootModel) View() string {
    taskSection := m.renderTaskList()
    outputSection := m.outputView.viewport.View()

    // Vertical split
    return lipgloss.JoinVertical(
        lipgloss.Left,
        taskSection,
        lipgloss.NewStyle().
            BorderStyle(lipgloss.NormalBorder()).
            BorderTop(true).
            Render(outputSection),
    )
}

func (m RootModel) renderTaskList() string {
    var tasks []string
    tasks = append(tasks, lipgloss.NewStyle().
        Bold(true).
        Foreground(lipgloss.Color("212")).
        Render("Tasks:"))

    for _, task := range m.taskList.tasks {
        tasks = append(tasks, "  " + task.View())
    }

    return lipgloss.JoinVertical(lipgloss.Left, tasks...)
}
```

### 5. tea.Println for Permanent Scrollback

**CRITICAL LIMITATION**: `tea.Println` does NOT work with alternate screen mode!

From the [docs](https://pkg.go.dev/github.com/charmbracelet/bubbletea):

> Println prints above the Program. This output is unmanaged by the program and will persist across renders by the Program. **If the altscreen is active no output will be printed.**

**Use case**: For committing completed tasks to scrollback:

```go
// When a task completes, print it permanently above the TUI
func (m RootModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case TaskCompleteMsg:
        // This only works if NOT using WithAltScreen()
        return m, tea.Println("✓ " + msg.Task.Content)
    }
    return m, nil
}
```

**Workaround for altscreen**: Use a viewport with accumulated history instead.

---

## Implementation Patterns

### Pattern 1: Custom List Delegate for Task Rendering

Instead of using the default list delegate, implement a custom one:

```go
type TaskDelegate struct {
    styles TaskStyles
}

func (d TaskDelegate) Height() int                               { return 1 }
func (d TaskDelegate) Spacing() int                              { return 0 }
func (d TaskDelegate) Update(msg tea.Msg, m *list.Model) tea.Cmd { return nil }

func (d TaskDelegate) Render(w io.Writer, m list.Model, index int, item list.Item) {
    task, ok := item.(Task)
    if !ok {
        return
    }

    var icon, text string
    var style lipgloss.Style

    switch task.Status {
    case StatusCompleted:
        icon = "✓"
        text = task.Content
        style = d.styles.completed
    case StatusInProgress:
        icon = task.spinner.View()
        text = task.ActiveForm
        style = d.styles.inProgress
    case StatusFailed:
        icon = "✗"
        text = task.Content
        style = d.styles.failed
    case StatusPending:
        icon = "○"
        text = task.Content
        style = d.styles.pending
    }

    fmt.Fprint(w, style.Render(fmt.Sprintf("%s %s", icon, text)))
}
```

### Pattern 2: Nested Task Support

For subtasks, use indentation in rendering:

```go
type Task struct {
    ID       string
    Content  string
    Status   TaskStatus
    Children []Task
    Level    int  // 0 = root, 1 = child, etc.
}

func (t Task) View() string {
    indent := strings.Repeat("  ", t.Level)
    line := indent + t.statusIcon() + " " + t.Content

    var lines []string
    lines = append(lines, line)

    for _, child := range t.Children {
        lines = append(lines, child.View())
    }

    return strings.Join(lines, "\n")
}
```

### Pattern 3: Real-Time Updates via Custom Messages

```go
type TaskUpdateMsg struct {
    TaskID string
    Status TaskStatus
}

type TaskAddMsg struct {
    Task Task
}

type TaskRemoveMsg struct {
    TaskID string
}

func (m TaskListModel) Update(msg tea.Msg) (TaskListModel, tea.Cmd) {
    switch msg := msg.(type) {
    case TaskUpdateMsg:
        for i := range m.tasks {
            if m.tasks[i].ID == msg.TaskID {
                m.tasks[i].Status = msg.Status

                // If transitioning to in_progress, ensure others are not
                if msg.Status == StatusInProgress {
                    for j := range m.tasks {
                        if j != i && m.tasks[j].Status == StatusInProgress {
                            m.tasks[j].Status = StatusPending
                        }
                    }
                }
            }
        }

    case TaskAddMsg:
        m.tasks = append(m.tasks, msg.Task)

    case TaskRemoveMsg:
        filtered := make([]Task, 0, len(m.tasks))
        for _, t := range m.tasks {
            if t.ID != msg.TaskID {
                filtered = append(filtered, t)
            }
        }
        m.tasks = filtered
    }

    return m, nil
}
```

### Pattern 4: Background Worker for Agent Execution

```go
func RunAgentTask(task Task) tea.Cmd {
    return func() tea.Msg {
        // Simulate agent work
        time.Sleep(2 * time.Second)

        // Send completion message
        return TaskUpdateMsg{
            TaskID: task.ID,
            Status: StatusCompleted,
        }
    }
}

// In Update:
case TaskStartMsg:
    task := m.getTask(msg.TaskID)
    return m, tea.Batch(
        func() tea.Msg {
            return TaskUpdateMsg{TaskID: task.ID, Status: StatusInProgress}
        },
        RunAgentTask(task),
    )
```

---

## Concrete Go Code Examples

### Example 1: Minimal Task List Model

```go
package main

import (
    "fmt"
    "github.com/charmbracelet/bubbles/spinner"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
)

type TaskStatus int

const (
    StatusPending TaskStatus = iota
    StatusInProgress
    StatusCompleted
    StatusFailed
)

type Task struct {
    ID         string
    Content    string
    ActiveForm string
    Status     TaskStatus
    spinner    spinner.Model
}

func NewTask(id, content, activeForm string) Task {
    s := spinner.New()
    s.Spinner = spinner.Dot
    s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

    return Task{
        ID:         id,
        Content:    content,
        ActiveForm: activeForm,
        Status:     StatusPending,
        spinner:    s,
    }
}

func (t Task) View() string {
    var icon string
    var style lipgloss.Style

    baseStyle := lipgloss.NewStyle().PaddingLeft(2)

    switch t.Status {
    case StatusCompleted:
        icon = "✓"
        style = baseStyle.Foreground(lipgloss.Color("46"))  // Green
    case StatusInProgress:
        icon = t.spinner.View()
        style = baseStyle.Foreground(lipgloss.Color("205")) // Pink
    case StatusFailed:
        icon = "✗"
        style = baseStyle.Foreground(lipgloss.Color("196")) // Red
    case StatusPending:
        icon = "○"
        style = baseStyle.Foreground(lipgloss.Color("241")) // Gray
    }

    text := t.Content
    if t.Status == StatusInProgress {
        text = t.ActiveForm
    }

    return style.Render(fmt.Sprintf("%s %s", icon, text))
}

type TaskListModel struct {
    tasks []Task
}

func (m TaskListModel) Init() tea.Cmd {
    var cmds []tea.Cmd
    for _, task := range m.tasks {
        cmds = append(cmds, task.spinner.Tick)
    }
    return tea.Batch(cmds...)
}

func (m TaskListModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    // Update spinners for in-progress tasks
    for i := range m.tasks {
        if m.tasks[i].Status == StatusInProgress {
            var cmd tea.Cmd
            m.tasks[i].spinner, cmd = m.tasks[i].spinner.Update(msg)
            cmds = append(cmds, cmd)
        }
    }

    switch msg := msg.(type) {
    case tea.KeyMsg:
        if msg.String() == "q" {
            return m, tea.Quit
        }
        // For demo: cycle first task status
        if msg.String() == " " {
            m.tasks[0].Status = (m.tasks[0].Status + 1) % 4
        }
    }

    return m, tea.Batch(cmds...)
}

func (m TaskListModel) View() string {
    title := lipgloss.NewStyle().
        Bold(true).
        Foreground(lipgloss.Color("212")).
        Render("Tasks:")

    var taskViews []string
    taskViews = append(taskViews, title)

    for _, task := range m.tasks {
        taskViews = append(taskViews, task.View())
    }

    taskViews = append(taskViews, "")
    taskViews = append(taskViews,
        lipgloss.NewStyle().Faint(true).Render("Press space to cycle status, q to quit"))

    return lipgloss.JoinVertical(lipgloss.Left, taskViews...)
}

func main() {
    tasks := []Task{
        NewTask("1", "Parse codebase", "Parsing codebase"),
        NewTask("2", "Generate embeddings", "Generating embeddings"),
        NewTask("3", "Build repository map", "Building repository map"),
        NewTask("4", "Run tests", "Running tests"),
    }

    tasks[0].Status = StatusCompleted
    tasks[1].Status = StatusInProgress

    m := TaskListModel{tasks: tasks}

    p := tea.NewProgram(m)
    if _, err := p.Run(); err != nil {
        fmt.Printf("Error: %v\n", err)
    }
}
```

### Example 2: Split Layout with Task List + Output Viewport

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

type RootModel struct {
    taskList   TaskListModel
    output     viewport.Model
    outputLines []string
    width      int
    height     int
}

func (m RootModel) Init() tea.Cmd {
    return tea.Batch(
        m.taskList.Init(),
        simulateWork(),
    )
}

func (m RootModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd
    var cmd tea.Cmd

    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height

        // Split: 30% for tasks, 70% for output
        taskHeight := m.height * 3 / 10
        outputHeight := m.height - taskHeight - 3  // -3 for borders

        m.output.Width = m.width - 2
        m.output.Height = outputHeight

    case tea.KeyMsg:
        if msg.String() == "q" {
            return m, tea.Quit
        }

    case OutputLineMsg:
        m.outputLines = append(m.outputLines, msg.content)
        m.output.SetContent(strings.Join(m.outputLines, "\n"))
        m.output.GotoBottom()

    case TaskUpdateMsg:
        m.taskList, cmd = m.taskList.Update(msg)
        cmds = append(cmds, cmd)
    }

    // Update child models
    m.taskList, cmd = m.taskList.Update(msg)
    cmds = append(cmds, cmd)

    m.output, cmd = m.output.Update(msg)
    cmds = append(cmds, cmd)

    return m, tea.Batch(cmds...)
}

func (m RootModel) View() string {
    taskSection := m.taskList.View()

    outputStyle := lipgloss.NewStyle().
        BorderStyle(lipgloss.RoundedBorder()).
        BorderTop(true).
        Padding(1, 2)

    outputSection := outputStyle.Render(m.output.View())

    return lipgloss.JoinVertical(lipgloss.Left, taskSection, outputSection)
}

type OutputLineMsg struct {
    content string
}

type TaskUpdateMsg struct {
    taskID string
    status TaskStatus
}

func simulateWork() tea.Cmd {
    return tea.Tick(time.Second, func(t time.Time) tea.Msg {
        return OutputLineMsg{content: fmt.Sprintf("[%s] Processing...", t.Format("15:04:05"))}
    })
}

func main() {
    tasks := []Task{
        NewTask("1", "Initialize project", "Initializing project"),
        NewTask("2", "Load configuration", "Loading configuration"),
        NewTask("3", "Connect to LLM", "Connecting to LLM"),
    }

    tasks[0].Status = StatusInProgress

    m := RootModel{
        taskList: TaskListModel{tasks: tasks},
        output:   viewport.New(0, 0),
        outputLines: []string{
            "Starting AI coding assistant...",
            "",
        },
    }

    p := tea.NewProgram(m, tea.WithAltScreen())
    if _, err := p.Run(); err != nil {
        fmt.Printf("Error: %v\n", err)
    }
}
```

### Example 3: Nested Tasks with Indentation

```go
type Task struct {
    ID         string
    Content    string
    ActiveForm string
    Status     TaskStatus
    Children   []Task
    Level      int
    spinner    spinner.Model
}

func (t Task) View() string {
    indent := strings.Repeat("  ", t.Level)

    var icon string
    switch t.Status {
    case StatusCompleted:
        icon = "✓"
    case StatusInProgress:
        icon = t.spinner.View()
    case StatusFailed:
        icon = "✗"
    case StatusPending:
        icon = "○"
    }

    text := t.Content
    if t.Status == StatusInProgress {
        text = t.ActiveForm
    }

    line := indent + icon + " " + text

    var lines []string
    lines = append(lines, line)

    for _, child := range t.Children {
        lines = append(lines, child.View())
    }

    return strings.Join(lines, "\n")
}

// Usage:
func createNestedTasks() []Task {
    return []Task{
        {
            ID:      "1",
            Content: "Refactor authentication system",
            Status:  StatusInProgress,
            Level:   0,
            Children: []Task{
                {ID: "1.1", Content: "Update user model", Status: StatusCompleted, Level: 1},
                {ID: "1.2", Content: "Implement JWT validation", Status: StatusInProgress, Level: 1},
                {ID: "1.3", Content: "Add refresh token logic", Status: StatusPending, Level: 1},
            },
        },
        {
            ID:      "2",
            Content: "Write tests",
            Status:  StatusPending,
            Level:   0,
            Children: []Task{
                {ID: "2.1", Content: "Unit tests", Status: StatusPending, Level: 1},
                {ID: "2.2", Content: "Integration tests", Status: StatusPending, Level: 1},
            },
        },
    }
}
```

---

## Real-World References

### Open Source Examples

1. **[WilmerLeonCh/TaskManager](https://github.com/WilmerLeonCh/TaskManager)** - CLI task manager with Bubble Tea
   - Add, update, remove, list tasks
   - Mark completion
   - Styled with Bubbles + Lipgloss

2. **[Grubba27/todo-list](https://github.com/Grubba27/todo-list)** - Todo-list CLI with Bubble Tea
   - Spinner during loading
   - List/form state switching

3. **[charmbracelet/bubbletea examples](https://github.com/charmbracelet/bubbletea/tree/main/examples)**
   - `spinner/` - Basic spinner implementation
   - `spinners/` - Multiple spinner styles
   - `list-default/` - List component usage
   - `progress-static/` - Progress bar with ticks
   - `views/` - Multiple view composition

4. **[addetz/bubbletea-tutorial](https://github.com/addetz/bubbletea-tutorial)** - Demo of nested models

### Helpful Articles

- **[Tips for building Bubble Tea programs](https://leg100.github.io/en/posts/building-bubbletea-programs)** - Excellent guide on composition, nested models, message routing
- **[Managing nested models with Bubble Tea](https://donderom.com/posts/managing-nested-models-with-bubble-tea/)** - Detailed patterns for model composition
- **[BubbleTea multi model tutorial](https://blog.sometimestech.com/posts/bubbletea-multimodel)** - Step-by-step multi-model guide

---

## Recommended Architecture

Based on the research, here's the recommended architecture for a Claude Code-style task tracking UI:

### 1. Component Structure

```
RootModel
├── TaskListModel (custom component)
│   ├── tasks []Task
│   └── styles TaskStyles
├── OutputViewportModel (bubbles/viewport)
│   ├── viewport viewport.Model
│   └── content string
└── layout Layout (split | output-only | task-only)
```

### 2. Task Model

```go
type Task struct {
    ID         string
    Content    string      // "Run tests"
    ActiveForm string      // "Running tests"
    Status     TaskStatus  // pending | in_progress | completed | failed
    Children   []Task      // For nested tasks
    Level      int         // 0 = root, 1+ = nested
    spinner    spinner.Model
    metadata   map[string]interface{}  // For extensibility
}
```

### 3. Message Types

```go
// Core task messages
type TaskAddMsg struct { Task Task }
type TaskUpdateMsg struct { TaskID string; Status TaskStatus }
type TaskRemoveMsg struct { TaskID string }

// Output messages
type OutputLineMsg struct { Line string; Timestamp time.Time }
type OutputClearMsg struct{}

// Agent workflow messages
type AgentStartMsg struct { TaskID string }
type AgentProgressMsg struct { TaskID string; Progress float64 }
type AgentCompleteMsg struct { TaskID string; Result interface{} }
type AgentErrorMsg struct { TaskID string; Error error }
```

### 4. Layout Strategy

**Option A: Fixed Split** (like Claude Code)

```
┌─────────────────────────────────┐
│ Tasks:                          │
│   ✓ Parse codebase              │
│   ⠋ Generating embeddings...    │
│   ○ Build repository map        │
│   ○ Run tests                   │
├─────────────────────────────────┤
│ Output:                         │
│ [15:04:05] Loaded 142 files     │
│ [15:04:07] Processing...        │
│ [15:04:09] Embeddings: 85%      │
│ ...                             │
│ ...                             │
│ ...                             │
└─────────────────────────────────┘
```

**Option B: Dynamic (show/hide task list)**

```go
func (m RootModel) View() string {
    if m.layout == LayoutOutputOnly {
        return m.outputView.View()
    }

    if m.layout == LayoutTaskOnly {
        return m.taskList.View()
    }

    // Split layout
    return lipgloss.JoinVertical(
        lipgloss.Left,
        m.taskList.View(),
        m.renderDivider(),
        m.outputView.View(),
    )
}
```

### 5. Spinner Management

**Critical optimization**: Only tick spinners for in-progress tasks

```go
func (m TaskListModel) Update(msg tea.Msg) (TaskListModel, tea.Cmd) {
    var cmds []tea.Cmd

    // Only update spinners for in-progress tasks
    for i := range m.tasks {
        if m.tasks[i].Status == StatusInProgress {
            var cmd tea.Cmd
            m.tasks[i].spinner, cmd = m.tasks[i].spinner.Update(msg)
            cmds = append(cmds, cmd)
        }
    }

    // ... handle other messages

    return m, tea.Batch(cmds...)
}
```

### 6. Integration with Agent System

```go
// When agent starts a task
func startAgentTask(task Task) tea.Cmd {
    return func() tea.Msg {
        // 1. Mark task as in-progress
        return TaskUpdateMsg{TaskID: task.ID, Status: StatusInProgress}
    }
}

// Agent work happens in background
func executeAgentTask(task Task) tea.Cmd {
    return func() tea.Msg {
        // Simulate agent work
        result, err := performAgentWork(task)

        if err != nil {
            return AgentErrorMsg{TaskID: task.ID, Error: err}
        }

        return AgentCompleteMsg{TaskID: task.ID, Result: result}
    }
}

// In Update:
case AgentStartMsg:
    return m, tea.Batch(
        startAgentTask(task),
        executeAgentTask(task),
    )

case AgentCompleteMsg:
    return m, func() tea.Msg {
        return TaskUpdateMsg{TaskID: msg.TaskID, Status: StatusCompleted}
    }

case AgentErrorMsg:
    return m, func() tea.Msg {
        return TaskUpdateMsg{TaskID: msg.TaskID, Status: StatusFailed}
    }
```

### 7. Styling Guidelines

Use Lipgloss for consistent, terminal-safe styling:

```go
type TaskStyles struct {
    completed  lipgloss.Style
    inProgress lipgloss.Style
    failed     lipgloss.Style
    pending    lipgloss.Style
    title      lipgloss.Style
}

func DefaultTaskStyles() TaskStyles {
    return TaskStyles{
        completed: lipgloss.NewStyle().
            Foreground(lipgloss.Color("46")).  // Green
            PaddingLeft(2),
        inProgress: lipgloss.NewStyle().
            Foreground(lipgloss.Color("205")). // Pink
            PaddingLeft(2),
        failed: lipgloss.NewStyle().
            Foreground(lipgloss.Color("196")). // Red
            PaddingLeft(2),
        pending: lipgloss.NewStyle().
            Foreground(lipgloss.Color("241")). // Gray
            PaddingLeft(2),
        title: lipgloss.NewStyle().
            Bold(true).
            Foreground(lipgloss.Color("212")).
            MarginBottom(1),
    }
}
```

---

## Key Takeaways

1. **Use nested model composition** for task list + output viewport
2. **Custom ItemDelegate or custom rendering** for per-task status indicators
3. **Individual spinners per task**, but only tick in-progress ones
4. **Viewport component** for scrolling output, NOT tea.Println (which doesn't work with altscreen)
5. **Message-driven updates** for real-time task status changes
6. **Lipgloss for styling** (terminal-safe colors, layouts)
7. **Follow Claude Code's pattern**: imperative content + present continuous activeForm
8. **Maintain exactly ONE in-progress task** at a time (like Claude Code does)

---

## Sources

### Claude Code & Agent SDK
- [Todo Lists - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/todo-tracking)
- [Claude Code Tasks Are Here](https://medium.com/@joe.njenga/claude-code-tasks-are-here-new-update-turns-claude-code-todos-to-tasks-a0be00e70847)
- [Claude Code Todos to Tasks](https://medium.com/@richardhightower/claude-code-todos-to-tasks-5a1b0e351a1c)
- [Claude Code System Prompts - TodoWrite](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/tool-description-todowrite.md)

### Bubble Tea Framework
- [GitHub - charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea)
- [GitHub - charmbracelet/bubbles](https://github.com/charmbracelet/bubbles)
- [tea package - Go Packages](https://pkg.go.dev/github.com/charmbracelet/bubbletea)

### Components
- [list package - Go Packages](https://pkg.go.dev/github.com/charmbracelet/bubbles/list)
- [spinner package - Go Packages](https://pkg.go.dev/github.com/charmbracelet/bubbles/spinner)
- [progress package - Go Packages](https://pkg.go.dev/github.com/charmbracelet/bubbles/progress)
- [viewport package - Go Packages](https://pkg.go.dev/github.com/charmbracelet/bubbles/viewport)

### Patterns & Tutorials
- [Tips for building Bubble Tea programs](https://leg100.github.io/en/posts/building-bubbletea-programs/)
- [Managing nested models with Bubble Tea](https://donderom.com/posts/managing-nested-models-with-bubble-tea/)
- [BubbleTea multi model tutorial](https://blog.sometimestech.com/posts/bubbletea-multimodel)
- [Nested components - Discussion #176](https://github.com/charmbracelet/bubbletea/discussions/176)
- [Intro to Bubble Tea in Go](https://dev.to/andyhaskell/intro-to-bubble-tea-in-go-21lg)

### Real-World Examples
- [WilmerLeonCh/TaskManager](https://github.com/WilmerLeonCh/TaskManager)
- [Grubba27/todo-list](https://github.com/Grubba27/todo-list)
- [addetz/bubbletea-tutorial](https://github.com/addetz/bubbletea-tutorial)
- [Bubble Tea Examples](https://github.com/charmbracelet/bubbletea/tree/main/examples)

### Styling
- [GitHub - charmbracelet/lipgloss](https://github.com/charmbracelet/lipgloss)
- [lipgloss package - Go Packages](https://pkg.go.dev/github.com/charmbracelet/lipgloss)

---

**End of Research Document**

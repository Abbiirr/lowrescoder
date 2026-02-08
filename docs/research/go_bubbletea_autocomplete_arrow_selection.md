# Autocomplete and Arrow-Key Selection in Go Bubble Tea

**Research Date**: 2026-02-07
**Context**: Building a Claude Code-style CLI with slash commands, @file references, and interactive selection prompts

---

## Executive Summary

This document provides comprehensive research on implementing autocomplete and arrow-key selection in Go Bubble Tea for an AI coding assistant. It covers:

1. **Autocomplete Approaches**: Ghost text vs dropdown popups
2. **Textinput Suggestions**: Built-in capabilities and limitations
3. **Custom Autocomplete Dropdowns**: Using list components and overlays
4. **Bubbline**: Readline-like library with advanced tab completion
5. **Huh**: Form library for selection prompts
6. **Arrow-Key Selection Patterns**: For approval prompts, session selection, etc.
7. **Claude Code's Approach**: React + Ink architecture

---

## Table of Contents

1. [Background: Bubble Tea Ecosystem](#background-bubble-tea-ecosystem)
2. [Autocomplete Approaches](#autocomplete-approaches)
3. [Built-in Textinput Suggestions](#built-in-textinput-suggestions)
4. [Custom Autocomplete Dropdowns](#custom-autocomplete-dropdowns)
5. [Bubbline: Readline for Bubble Tea](#bubbline-readline-for-bubble-tea)
6. [Huh: Selection Prompts](#huh-selection-prompts)
7. [Arrow-Key Selection Patterns](#arrow-key-selection-patterns)
8. [Overlay and Positioning](#overlay-and-positioning)
9. [Claude Code's Architecture](#claude-codes-architecture)
10. [Recommended Implementation Strategies](#recommended-implementation-strategies)
11. [Code Examples](#code-examples)

---

## Background: Bubble Tea Ecosystem

### Core Libraries

| Library | Purpose | URL |
|---------|---------|-----|
| **Bubble Tea** | TUI framework based on The Elm Architecture | https://github.com/charmbracelet/bubbletea |
| **Bubbles** | Common UI components (textinput, list, etc.) | https://github.com/charmbracelet/bubbles |
| **Lip Gloss** | Styling and layout | https://github.com/charmbracelet/lipgloss |
| **Bubbline** | Readline-like line editor with autocomplete | https://github.com/knz/bubbline |
| **Huh** | Forms and selection prompts | https://github.com/charmbracelet/huh |

### The Elm Architecture Pattern

All Bubble Tea applications follow this pattern:

```go
type Model struct {
    // Your state
}

func (m Model) Init() tea.Cmd {
    // Initialize
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    // Handle events
}

func (m Model) View() string {
    // Render UI
}
```

---

## Autocomplete Approaches

### 1. Ghost Text Completion (Simple)

**What it is**: Inline suggestion that appears as dimmed text after the cursor

**Pros**:
- Simple to implement
- Low cognitive overhead
- No popup management needed

**Cons**:
- Can only show one suggestion at a time
- Limited discoverability

**Use case**: Single-file autocomplete when there's a clear best match

---

### 2. Dropdown Popup (Powerful)

**What it is**: A list of suggestions that appears above/below the input

**Pros**:
- Shows multiple suggestions
- Better discoverability
- Can include descriptions
- Matches user expectations from IDEs

**Cons**:
- More complex to implement
- Requires overlay management
- Needs careful positioning logic

**Use case**: Slash commands, @file references, model selection

---

## Built-in Textinput Suggestions

### Current Status (as of 2026)

The `bubbles/textinput` component has **partial** suggestion support, but it's been evolving:

#### Available Methods

```go
// From textinput package
ti.SetSuggestions([]string) // Set suggestions
ti.AvailableSuggestions() []string // Get all suggestions
ti.MatchedSuggestions() []string // Get filtered suggestions
ti.CurrentSuggestion() string // Get selected suggestion
```

#### Known Issues

- **Issue #882**: The autocomplete example in the Bubble Tea repo may be outdated
- Some users report `SetSuggestions` and `ShowSuggestions` not being available
- The API has changed over time

#### Current Behavior

The textinput component appears to support **ghost text** style autocomplete (inline suggestions), not dropdown menus.

**Example from documentation**:

```go
package main

import (
    "github.com/charmbracelet/bubbles/textinput"
    tea "github.com/charmbracelet/bubbletea"
)

type model struct {
    textInput textinput.Model
}

func initialModel() model {
    ti := textinput.New()
    ti.Placeholder = "Type a command..."
    ti.Focus()
    ti.CharLimit = 50
    ti.Width = 30

    // Set suggestions
    ti.SetSuggestions([]string{
        "help",
        "exit",
        "status",
        "clear",
    })

    return model{
        textInput: ti,
    }
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmd tea.Cmd
    m.textInput, cmd = m.textInput.Update(msg)
    return m, cmd
}

func (m model) View() string {
    return m.textInput.View()
}
```

**Limitation**: This gives you ghost text, not a dropdown with arrow-key navigation.

---

## Custom Autocomplete Dropdowns

### Strategy 1: Combine Textinput + List

**Approach**: Use a `textinput` for input and a `list` component for the dropdown

**Architecture**:

```go
type AutocompleteModel struct {
    input textinput.Model
    list list.Model
    showDropdown bool
    suggestions []SuggestionItem
}

type SuggestionItem struct {
    Text string
    Description string
}

func (s SuggestionItem) FilterValue() string {
    return s.Text
}

func (s SuggestionItem) Title() string {
    return s.Text
}

func (s SuggestionItem) Description() string {
    return s.Description
}
```

**Key Features**:

1. **Filtering**: The `list` component has built-in filtering
2. **Arrow navigation**: Handled automatically by `list`
3. **Styling**: Use lipgloss to position the list below/above input

**Example Update Logic**:

```go
func (m AutocompleteModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        // Route keys to either input or list
        if m.showDropdown && isNavigationKey(msg) {
            // Send to list
            var cmd tea.Cmd
            m.list, cmd = m.list.Update(msg)
            return m, cmd
        }

        // Send to textinput
        var cmd tea.Cmd
        m.input, cmd = m.input.Update(msg)

        // Update suggestions based on input value
        m.updateSuggestions()

        return m, cmd
    }

    return m, nil
}

func (m *AutocompleteModel) updateSuggestions() {
    inputValue := m.input.Value()

    // Trigger dropdown when "/" is typed
    if strings.HasPrefix(inputValue, "/") {
        m.showDropdown = true
        m.filterSuggestions(strings.TrimPrefix(inputValue, "/"))
    } else {
        m.showDropdown = false
    }
}
```

**View Logic**:

```go
func (m AutocompleteModel) View() string {
    var b strings.Builder

    // Show list above input if dropdown is active
    if m.showDropdown {
        b.WriteString(m.list.View())
        b.WriteString("\n")
    }

    b.WriteString(m.input.View())

    return b.String()
}
```

---

### Strategy 2: Use Overlay Component

The `bubbletea-overlay` package provides a way to composite foreground and background models.

**Installation**:

```bash
go get github.com/quickphosphat/bubbletea-overlay
```

**Example**:

```go
import "github.com/quickphosphat/bubbletea-overlay"

type Model struct {
    input tea.Model
    dropdown tea.Model
    overlay overlay.Model
}

func (m Model) Init() tea.Cmd {
    xPosition := overlay.Center
    yPosition := overlay.Bottom
    xOffset := 0
    yOffset := -2 // Position above input

    m.overlay = overlay.New(
        m.dropdown,  // foreground
        m.input,     // background
        xPosition,
        yPosition,
        xOffset,
        yOffset,
    )

    return nil
}

func (m Model) View() string {
    return m.overlay.View()
}
```

**Positioning Options**:

- `overlay.Top`
- `overlay.Right`
- `overlay.Bottom`
- `overlay.Left`
- `overlay.Center`

You can combine these (e.g., `overlay.Right`, `overlay.Top` for top-right corner) and add X/Y offsets for fine-tuning.

---

## Bubbline: Readline for Bubble Tea

### What is Bubbline?

Bubbline is a line editor for Bubble Tea that provides **readline-like** functionality, including:

- Tab completion with callback
- Fancy presentation of completions with menu navigation
- Multi-line editing
- History support
- Modal editing (vi/emacs keybindings)

**Used by**: CockroachDB CLI (`cockroach sql`)

### AutoCompleteFn Callback

**Type signature**:

```go
type AutoCompleteFn func(
    entireInput [][]rune,
    line, col int,
) (msg string, comp Completions)
```

**Parameters**:
- `entireInput`: The complete text of the input (as runes)
- `line`: Line number where cursor is positioned
- `col`: Column position of cursor

**Return values**:
- `msg`: Message to print above the input box
- `comp`: Completion candidates (categories + entries)

**Completions Structure**:

```go
type Completions struct {
    Categories []CompletionCategory
}

type CompletionCategory struct {
    Name string
    Entries []CompletionEntry
}

type CompletionEntry struct {
    Word string        // What gets inserted
    Description string // What gets displayed
}
```

### CockroachDB Implementation Example

From the CockroachDB blog post on contextual SQL suggestions:

```go
// Simplified example from CockroachDB
func sqlAutoComplete(entireInput [][]rune, line, col int) (string, bubbline.Completions) {
    input := runesToString(entireInput)

    // Run SHOW COMPLETIONS query to get suggestions
    results := db.Query("SHOW COMPLETIONS FOR $1 AT OFFSET $2", input, col)

    var completions bubbline.Completions

    // Group by category
    categoryMap := make(map[string][]bubbline.CompletionEntry)

    for results.Next() {
        var category, word, description string
        results.Scan(&category, &word, &description)

        categoryMap[category] = append(categoryMap[category], bubbline.CompletionEntry{
            Word: word,
            Description: description,
        })
    }

    // Build categories
    for categoryName, entries := range categoryMap {
        completions.Categories = append(completions.Categories, bubbline.CompletionCategory{
            Name: categoryName,
            Entries: entries,
        })
    }

    return "", completions
}

// Configure Bubbline
editor := bubbline.New()
editor.AutoCompleteCallback = sqlAutoComplete
```

### Key Features

1. **Tab triggers completion**: User presses Tab, callback is invoked
2. **Arrow navigation**: Bubbline handles arrow keys through the completion menu
3. **Categories**: Completions can be grouped (e.g., "Functions", "Tables", "Keywords")
4. **Descriptions**: Each entry can have explanatory text

### When to Use Bubbline

**Use when**:
- You need a full readline replacement
- You want autocomplete for a REPL-style interface
- You need multi-line editing
- You want vi/emacs keybindings

**Don't use when**:
- You need a custom, complex UI layout
- You want fine-grained control over rendering
- You're building a chat interface (Bubbline is for line editing)

---

## Huh: Selection Prompts

### What is Huh?

Huh is a library for building **forms and prompts** in the terminal. It's built on Bubble Tea and provides high-level components for common prompt patterns.

**Key features**:
- Select (single choice)
- MultiSelect (multiple choices)
- Input, Confirm, Text
- Accessible mode for screen readers
- Integrates with Bubble Tea apps

### NewSelect: Arrow-Key Selection

**Basic example**:

```go
package main

import (
    "fmt"
    "github.com/charmbracelet/huh/v2"
)

func main() {
    var choice string

    form := huh.NewForm(
        huh.NewGroup(
            huh.NewSelect[string]().
                Title("Choose your action:").
                Options(
                    huh.NewOption("Continue", "continue"),
                    huh.NewOption("Cancel", "cancel"),
                    huh.NewOption("Help", "help"),
                ).
                Value(&choice),
        ),
    )

    err := form.Run()
    if err != nil {
        panic(err)
    }

    fmt.Printf("You selected: %s\n", choice)
}
```

**Output** (rendered in terminal):

```
? Choose your action:
  > Continue
    Cancel
    Help
```

User can:
- Press ↑/↓ to navigate
- Press Enter to select
- Press Ctrl+C to cancel

### Approval Prompts (Claude Code-style)

For "Yes / Yes this session / No" prompts:

```go
func askApproval() (string, error) {
    var approval string

    form := huh.NewForm(
        huh.NewGroup(
            huh.NewSelect[string]().
                Title("Allow this action?").
                Options(
                    huh.NewOption("Yes", "yes"),
                    huh.NewOption("Yes this session", "yes_session"),
                    huh.NewOption("No", "no"),
                ).
                Value(&approval),
        ),
    )

    return approval, form.Run()
}
```

### Session Selection

For `/resume` with arrow navigation:

```go
type Session struct {
    ID string
    Name string
    LastUsed time.Time
}

func selectSession(sessions []Session) (*Session, error) {
    var selectedID string

    // Convert sessions to options
    var options []huh.Option[string]
    for _, s := range sessions {
        label := fmt.Sprintf("%s (last used: %s)", s.Name, s.LastUsed.Format("2006-01-02"))
        options = append(options, huh.NewOption(label, s.ID))
    }

    form := huh.NewForm(
        huh.NewGroup(
            huh.NewSelect[string]().
                Title("Select a session to resume:").
                Options(options...).
                Height(10). // Scrollable list
                Value(&selectedID),
        ),
    )

    if err := form.Run(); err != nil {
        return nil, err
    }

    // Find selected session
    for _, s := range sessions {
        if s.ID == selectedID {
            return &s, nil
        }
    }

    return nil, fmt.Errorf("session not found")
}
```

### Model Selection with Descriptions

For `/model` command:

```go
type Model struct {
    Name string
    Description string
    VRAM int
}

func selectModel(models []Model) (*Model, error) {
    var selectedName string

    var options []huh.Option[string]
    for _, m := range models {
        label := fmt.Sprintf("%s - %s (%d GB VRAM)", m.Name, m.Description, m.VRAM)
        options = append(options, huh.NewOption(label, m.Name))
    }

    form := huh.NewForm(
        huh.NewGroup(
            huh.NewSelect[string]().
                Title("Select a model:").
                Description("Choose which LLM model to use").
                Options(options...).
                Value(&selectedName),
        ),
    )

    if err := form.Run(); err != nil {
        return nil, err
    }

    // Find selected model
    for _, m := range models {
        if m.Name == selectedName {
            return &m, nil
        }
    }

    return nil, fmt.Errorf("model not found")
}
```

### Integrating Huh with Bubble Tea App

Huh can be used **standalone** (blocking) or **embedded** in a Bubble Tea app:

**Standalone** (blocks until user responds):

```go
approval, err := askApproval()
```

**Embedded** (non-blocking, integrated into main app):

```go
type MainModel struct {
    huhForm *huh.Form
    // ... other state
}

func (m MainModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    // Forward messages to huh form
    form, cmd := m.huhForm.Update(msg)
    if f, ok := form.(*huh.Form); ok {
        m.huhForm = f
    }

    // Check if form completed
    if m.huhForm.State == huh.StateCompleted {
        // Handle result
    }

    return m, cmd
}
```

---

## Arrow-Key Selection Patterns

### Pattern 1: List Component (Recommended for Autocomplete)

The `bubbles/list` component provides built-in arrow-key navigation.

**Key bindings** (from `list/keys.go`):

| Key | Action |
|-----|--------|
| ↑, k | Cursor up |
| ↓, j | Cursor down |
| PgUp | Previous page |
| PgDn | Next page |
| Home, g | Go to start |
| End, G | Go to end |
| / | Toggle filter |

**Creating a list**:

```go
import "github.com/charmbracelet/bubbles/list"

type Item struct {
    title string
    desc string
}

func (i Item) Title() string { return i.title }
func (i Item) Description() string { return i.desc }
func (i Item) FilterValue() string { return i.title }

func NewAutocompleteList() list.Model {
    items := []list.Item{
        Item{title: "/help", desc: "Show help message"},
        Item{title: "/model", desc: "Change LLM model"},
        Item{title: "/mode", desc: "Change interaction mode"},
        Item{title: "/exit", desc: "Exit the application"},
    }

    l := list.New(items, list.NewDefaultDelegate(), 40, 10)
    l.Title = "Slash Commands"
    l.SetShowStatusBar(false)
    l.SetFilteringEnabled(true)

    return l
}
```

**In your Update function**:

```go
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        if msg.String() == "enter" {
            // Get selected item
            selected := m.list.SelectedItem()
            if item, ok := selected.(Item); ok {
                // Handle selection
                fmt.Printf("Selected: %s\n", item.title)
            }
        }
    }

    // Let list handle other keys
    var cmd tea.Cmd
    m.list, cmd = m.list.Update(msg)
    return m, cmd
}
```

---

### Pattern 2: Manual Arrow Handling

If you need custom behavior:

```go
type SelectionModel struct {
    choices []string
    cursor int
}

func (m SelectionModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "up", "k":
            if m.cursor > 0 {
                m.cursor--
            }
        case "down", "j":
            if m.cursor < len(m.choices)-1 {
                m.cursor++
            }
        case "enter":
            // Handle selection
            selected := m.choices[m.cursor]
            // ...
        }
    }
    return m, nil
}

func (m SelectionModel) View() string {
    var b strings.Builder

    for i, choice := range m.choices {
        cursor := " " // no cursor
        if m.cursor == i {
            cursor = ">" // cursor
        }

        b.WriteString(fmt.Sprintf("%s %s\n", cursor, choice))
    }

    return b.String()
}
```

---

## Overlay and Positioning

### Fixed Bottom Input Bar

**Challenge**: Keep input at bottom while showing autocomplete above it

**Solution 1: Manual positioning with lipgloss**

```go
import "github.com/charmbracelet/lipgloss"

func (m Model) View() string {
    // Get terminal height
    height := m.terminalHeight

    // Calculate available space
    inputHeight := 3
    availableHeight := height - inputHeight

    // Render main content
    content := m.renderContent()

    // Render autocomplete dropdown if active
    var dropdown string
    if m.showAutocomplete {
        dropdown = m.renderDropdown()
    }

    // Render input bar
    inputBar := m.renderInputBar()

    // Compose layout
    return lipgloss.JoinVertical(
        lipgloss.Left,
        content,
        dropdown,
        inputBar,
    )
}
```

**Solution 2: Use overlay package**

```go
import overlay "github.com/quickphosphat/bubbletea-overlay"

type Model struct {
    input tea.Model
    dropdown tea.Model
    showDropdown bool
}

func (m Model) View() string {
    if !m.showDropdown {
        return m.input.View()
    }

    // Position dropdown above input
    o := overlay.New(
        m.dropdown,
        m.input,
        overlay.Center,  // horizontal
        overlay.Bottom,  // vertical
        0,               // x offset
        -3,              // y offset (above input)
    )

    return o.View()
}
```

---

## Claude Code's Architecture

### Technology Stack

From research on Claude Code's internal architecture:

| Component | Technology |
|-----------|-----------|
| Language | TypeScript |
| UI Framework | React |
| Terminal Rendering | Ink |
| Layout Engine | Yoga (flexbox) |
| Build System | Bun |

### Why React + Ink?

**Advantages**:
- Component-based architecture
- Familiar patterns for web developers
- Declarative rendering
- State management with hooks
- "On distribution" for Claude (model knows React well)

**Ink** renders React components to the terminal using ANSI codes.

### Autocomplete Implementation Details

From Issue #9750 and other sources:

1. **Trigger**: Autocomplete triggers on `/` or `@` character
2. **Dropdown**: Appears immediately after trigger character
3. **Real-time filtering**: Updates as user types
4. **Navigation**: Arrow keys to move, Tab/Enter to select, Esc to close
5. **Descriptions**: Commands show descriptions in the dropdown
6. **Skills integration**: Autocomplete includes skills from `~/.claude/skills/`

**UI Layout** (from "Claude Code Internals, Part 11"):

```
┌─────────────────────────────────────────┐
│ Status Bar (model, cost, tokens)       │ <- Top
├─────────────────────────────────────────┤
│                                         │
│ Conversation / Messages                 │
│                                         │
│                                         │
│ [Autocomplete Dropdown]                 │ <- Above input
│   > /help - Show help                   │
│     /model - Change model               │
│     /mode - Change mode                 │
├─────────────────────────────────────────┤
│ > /                                     │ <- Input bar (fixed bottom)
└─────────────────────────────────────────┘
```

### React Component Structure (Conceptual)

```tsx
// Pseudocode - not actual Claude Code source
function ChatInterface() {
    const [input, setInput] = useState("");
    const [showAutocomplete, setShowAutocomplete] = useState(false);
    const [suggestions, setSuggestions] = useState([]);

    useEffect(() => {
        if (input.startsWith("/")) {
            setShowAutocomplete(true);
            setSuggestions(filterCommands(input.slice(1)));
        } else {
            setShowAutocomplete(false);
        }
    }, [input]);

    return (
        <Box flexDirection="column" height="100%">
            <StatusBar />
            <Box flexGrow={1}>
                <MessageList messages={messages} />
            </Box>
            {showAutocomplete && (
                <AutocompleteDropdown
                    suggestions={suggestions}
                    onSelect={handleSelect}
                />
            )}
            <InputBar
                value={input}
                onChange={setInput}
            />
        </Box>
    );
}
```

---

## Recommended Implementation Strategies

### For Your Go CLI (HybridCoder)

Based on the research, here are recommended approaches for different features:

#### 1. Slash Command Autocomplete

**Recommended**: Custom textinput + list component

**Why**:
- Full control over rendering
- Built-in filtering in list component
- Arrow-key navigation handled
- Can show descriptions

**Implementation**:

```go
type AutocompleteModel struct {
    input textinput.Model
    dropdown list.Model
    showDropdown bool
    commands []Command
}

type Command struct {
    Name string
    Description string
}

func (c Command) Title() string { return c.Name }
func (c Command) Description() string { return c.Description }
func (c Command) FilterValue() string { return c.Name }

func (m *AutocompleteModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        // If dropdown is showing, route arrow keys to it
        if m.showDropdown {
            switch msg.String() {
            case "up", "down", "enter", "esc":
                var cmd tea.Cmd
                m.dropdown, cmd = m.dropdown.Update(msg)

                if msg.String() == "enter" {
                    // Apply selected command
                    selected := m.dropdown.SelectedItem().(Command)
                    m.input.SetValue("/" + selected.Name + " ")
                    m.showDropdown = false
                }

                return m, cmd
            }
        }

        // Otherwise, handle in textinput
        var cmd tea.Cmd
        m.input, cmd = m.input.Update(msg)

        // Update dropdown visibility
        value := m.input.Value()
        if strings.HasPrefix(value, "/") && !strings.Contains(value, " ") {
            m.showDropdown = true
            m.filterCommands(strings.TrimPrefix(value, "/"))
        } else {
            m.showDropdown = false
        }

        return m, cmd
    }

    return m, nil
}
```

---

#### 2. @file Reference Autocomplete

**Recommended**: Same as slash commands, but with file tree

**Special considerations**:
- Use filepath.Walk to gather files
- Filter by .gitignore
- Show relative paths
- Group by directory (optional)

**Example**:

```go
type FileItem struct {
    Path string
    RelPath string
}

func (f FileItem) Title() string { return f.RelPath }
func (f FileItem) Description() string { return filepath.Dir(f.RelPath) }
func (f FileItem) FilterValue() string { return f.RelPath }

func (m *AutocompleteModel) loadFiles() {
    var items []list.Item

    filepath.Walk(".", func(path string, info os.FileInfo, err error) error {
        if err != nil || info.IsDir() {
            return nil
        }

        // Skip .git, node_modules, etc.
        if shouldIgnore(path) {
            return nil
        }

        relPath, _ := filepath.Rel(".", path)
        items = append(items, FileItem{
            Path: path,
            RelPath: relPath,
        })

        return nil
    })

    m.dropdown.SetItems(items)
}
```

---

#### 3. Approval Prompts (Yes / Yes this session / No)

**Recommended**: Huh library (standalone)

**Why**:
- Purpose-built for this
- Clean API
- Accessible mode
- Well-tested

**Implementation**:

```go
func askPermission(action string) (string, error) {
    var choice string

    form := huh.NewForm(
        huh.NewGroup(
            huh.NewSelect[string]().
                Title(fmt.Sprintf("Allow: %s?", action)).
                Options(
                    huh.NewOption("Yes", "yes"),
                    huh.NewOption("Yes this session", "yes_session"),
                    huh.NewOption("No", "no"),
                ).
                Value(&choice),
        ),
    )

    return choice, form.Run()
}
```

---

#### 4. Model / Mode Selection

**Recommended**: Huh library (standalone) OR custom list

**Huh** if you want a simple blocking prompt:

```go
func selectModel() (string, error) {
    var model string

    form := huh.NewForm(
        huh.NewGroup(
            huh.NewSelect[string]().
                Title("Select model:").
                Options(
                    huh.NewOption("Qwen3-8B", "qwen3-8b"),
                    huh.NewOption("Qwen2.5-Coder-1.5B", "qwen2.5-coder-1.5b"),
                ).
                Value(&model),
        ),
    )

    return model, form.Run()
}
```

**Custom list** if you want it embedded in your main UI.

---

#### 5. Session Selection (/resume)

**Recommended**: Custom list (embedded in main UI)

**Why**:
- Needs to show rich metadata (last used, message count, etc.)
- May want preview on selection
- Better integrated into chat UI

**Implementation**:

```go
type SessionItem struct {
    ID string
    Name string
    LastUsed time.Time
    MessageCount int
}

func (s SessionItem) Title() string {
    return s.Name
}

func (s SessionItem) Description() string {
    return fmt.Sprintf(
        "Last used: %s | %d messages",
        s.LastUsed.Format("Jan 2, 3:04 PM"),
        s.MessageCount,
    )
}

func (s SessionItem) FilterValue() string {
    return s.Name
}

// Use list component with custom delegate for styling
```

---

## Code Examples

### Complete Example: Slash Command Autocomplete

```go
package main

import (
    "fmt"
    "strings"

    "github.com/charmbracelet/bubbles/list"
    "github.com/charmbracelet/bubbles/textinput"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
)

// Command represents a slash command
type Command struct {
    Name        string
    Description string
}

func (c Command) Title() string       { return "/" + c.Name }
func (c Command) Description() string { return c.Description }
func (c Command) FilterValue() string { return c.Name }

// Model is our Bubble Tea model
type Model struct {
    input        textinput.Model
    dropdown     list.Model
    showDropdown bool
    commands     []Command
    width        int
    height       int
}

func initialModel() Model {
    // Define available commands
    commands := []Command{
        {Name: "help", Description: "Show help message"},
        {Name: "model", Description: "Change LLM model"},
        {Name: "mode", Description: "Change interaction mode"},
        {Name: "resume", Description: "Resume a previous session"},
        {Name: "clear", Description: "Clear conversation history"},
        {Name: "exit", Description: "Exit the application"},
    }

    // Create textinput
    ti := textinput.New()
    ti.Placeholder = "Type / for commands..."
    ti.Focus()
    ti.Width = 50

    // Create list for dropdown
    items := make([]list.Item, len(commands))
    for i, cmd := range commands {
        items[i] = cmd
    }

    l := list.New(items, list.NewDefaultDelegate(), 50, 8)
    l.SetShowTitle(false)
    l.SetShowStatusBar(false)
    l.SetFilteringEnabled(false) // We'll filter manually

    return Model{
        input:    ti,
        dropdown: l,
        commands: commands,
    }
}

func (m Model) Init() tea.Cmd {
    return textinput.Blink
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height

    case tea.KeyMsg:
        switch msg.String() {
        case "ctrl+c", "esc":
            if m.showDropdown {
                m.showDropdown = false
                return m, nil
            }
            return m, tea.Quit

        case "enter":
            if m.showDropdown {
                // Apply selected command
                selected := m.dropdown.SelectedItem().(Command)
                m.input.SetValue("/" + selected.Name + " ")
                m.input.SetCursor(len(m.input.Value()))
                m.showDropdown = false
                return m, nil
            }
            // Process command
            fmt.Printf("Executing: %s\n", m.input.Value())
            return m, tea.Quit

        case "up", "down":
            if m.showDropdown {
                var cmd tea.Cmd
                m.dropdown, cmd = m.dropdown.Update(msg)
                return m, cmd
            }
        }

        // Update textinput
        var cmd tea.Cmd
        m.input, cmd = m.input.Update(msg)

        // Check if we should show dropdown
        value := m.input.Value()
        if strings.HasPrefix(value, "/") {
            // Extract search term
            searchTerm := strings.TrimPrefix(value, "/")

            // Don't show if there's a space (command already completed)
            if !strings.Contains(searchTerm, " ") {
                m.showDropdown = true
                m.filterCommands(searchTerm)
            } else {
                m.showDropdown = false
            }
        } else {
            m.showDropdown = false
        }

        return m, cmd
    }

    return m, nil
}

func (m *Model) filterCommands(searchTerm string) {
    var filteredItems []list.Item

    searchTerm = strings.ToLower(searchTerm)

    for _, cmd := range m.commands {
        if searchTerm == "" || strings.HasPrefix(strings.ToLower(cmd.Name), searchTerm) {
            filteredItems = append(filteredItems, cmd)
        }
    }

    m.dropdown.SetItems(filteredItems)
}

func (m Model) View() string {
    var b strings.Builder

    // Render dropdown above input if active
    if m.showDropdown && len(m.dropdown.Items()) > 0 {
        dropdownStyle := lipgloss.NewStyle().
            Border(lipgloss.RoundedBorder()).
            BorderForeground(lipgloss.Color("63")).
            Padding(0, 1)

        b.WriteString(dropdownStyle.Render(m.dropdown.View()))
        b.WriteString("\n")
    }

    // Render input
    inputStyle := lipgloss.NewStyle().
        Border(lipgloss.NormalBorder()).
        BorderForeground(lipgloss.Color("240")).
        Padding(0, 1)

    b.WriteString(inputStyle.Render(m.input.View()))

    return b.String()
}

func main() {
    p := tea.NewProgram(initialModel())
    if _, err := p.Run(); err != nil {
        fmt.Printf("Error: %v\n", err)
    }
}
```

### Complete Example: Approval Prompt with Huh

```go
package main

import (
    "fmt"

    "github.com/charmbracelet/huh/v2"
)

func main() {
    // Ask for approval
    approval := askApproval("execute shell command 'rm -rf /'")

    switch approval {
    case "yes":
        fmt.Println("Executing once...")
    case "yes_session":
        fmt.Println("Executing for this session...")
    case "no":
        fmt.Println("Cancelled.")
    }
}

func askApproval(action string) string {
    var choice string

    form := huh.NewForm(
        huh.NewGroup(
            huh.NewSelect[string]().
                Title(fmt.Sprintf("Allow: %s?", action)).
                Options(
                    huh.NewOption("Yes", "yes"),
                    huh.NewOption("Yes this session", "yes_session"),
                    huh.NewOption("No", "no"),
                ).
                Value(&choice),
        ),
    )

    err := form.Run()
    if err != nil {
        return "no"
    }

    return choice
}
```

---

## Summary Table: When to Use What

| Use Case | Recommended Solution | Why |
|----------|---------------------|-----|
| **Slash command autocomplete** | Textinput + List | Full control, built-in filtering, arrow nav |
| **@file autocomplete** | Textinput + List | Same as slash commands, easy to populate from filesystem |
| **Model selection** | Huh NewSelect (standalone) | Simple, clean, purpose-built |
| **Mode selection** | Huh NewSelect (standalone) | Same as model selection |
| **Session selection** | Custom List (embedded) | Rich metadata, preview support |
| **Approval prompts** | Huh NewSelect (standalone) | Quick, blocking, familiar pattern |
| **Full readline replacement** | Bubbline | If you need REPL with history, vi/emacs keys |
| **Complex chat UI** | Custom Bubble Tea app | Maximum control |

---

## Key Takeaways

1. **No silver bullet**: Bubble Tea provides primitives (textinput, list), not a complete autocomplete solution
2. **Huh is great for simple prompts**: Use it for approval dialogs, model selection, etc.
3. **Bubbline for REPL-style**: If you're building a shell/REPL, Bubbline gives you readline features
4. **Custom solution for chat UI**: For a Claude Code-style chat interface, you'll build custom autocomplete using textinput + list
5. **Overlay for positioning**: Use the overlay package or lipgloss for positioning dropdowns above/below input
6. **Claude Code uses React + Ink**: Not directly applicable to Go, but the concepts translate (component composition, state management)

---

## References

### Documentation
- [Bubble Tea GitHub](https://github.com/charmbracelet/bubbletea)
- [Bubbles GitHub](https://github.com/charmbracelet/bubbles)
- [Huh GitHub](https://github.com/charmbracelet/huh)
- [Bubbline GitHub](https://github.com/knz/bubbline)
- [Bubble Tea Overlay](https://pkg.go.dev/github.com/quickphosphat/bubbletea-overlay)

### Examples
- [Bubble Tea Autocomplete Example](https://github.com/charmbracelet/bubbletea/blob/main/examples/autocomplete/main.go)
- [Bubble Tea Textinput Example](https://github.com/charmbracelet/bubbletea/blob/main/examples/textinput/main.go)
- [Bubble Tea List Example](https://github.com/charmbracelet/bubbletea/blob/main/examples/list-simple/main.go)
- [Huh Burger Example](https://github.com/charmbracelet/huh/blob/main/examples/burger/main.go)

### Blog Posts & Articles
- [CockroachDB: Bubbles and sparkles - refreshing our SQL shell](https://www.cockroachlabs.com/blog/cockroachdb-cli-improvements/)
- [CockroachDB: Contextual suggestions for SQL syntax](https://www.cockroachlabs.com/blog/contextual-suggestions-for-sql-syntax/)
- [Building Bubble Tea programs](https://leg100.github.io/en/posts/building-bubbletea-programs/)
- [Processing user input in Bubble Tea with a menu component](https://dev.to/andyhaskell/processing-user-input-in-bubble-tea-with-a-menu-component-222i)
- [Overlay Composition Using Bubble Tea](https://lmika.org/2022/09/24/overlay-composition-using.html)

### Claude Code Internals
- [Claude Code Internals, Part 11: Terminal UI](https://kotrotsos.medium.com/claude-code-internals-part-11-terminal-ui-542fe17db016)
- [How Claude Code is built](https://newsletter.pragmaticengineer.com/p/how-claude-code-is-built)
- [Claude Code uses React to render its TUI](https://analyticsindiamag.com/ai-news-updates/claude-code-uses-react-to-render-its-tui/)

### Package Documentation
- [textinput package](https://pkg.go.dev/github.com/charmbracelet/bubbles/textinput)
- [list package](https://pkg.go.dev/github.com/charmbracelet/bubbles/list)
- [huh package](https://pkg.go.dev/github.com/charmbracelet/huh/v2)
- [bubbline package](https://pkg.go.dev/github.com/knz/bubbline)

---

**End of Research Document**

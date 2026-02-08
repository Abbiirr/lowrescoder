# Migrating HybridCoder to Go Bubble Tea

**Bubble Tea is the right framework for this migration, and the ecosystem has matured enough to build a production-quality Claude Code competitor.** Go's goroutine-based concurrency eliminates the Python GIL and blocking issues that motivated this move, while the Charm ecosystem (Bubble Tea + Bubbles + Lip Gloss + Glamour + Huh) provides every component needed. Charm's own **Crush** — a 19.5k-star agentic coding TUI — validates the framework for this exact use case. This document covers all 16 research areas with implementation-grade patterns, production code examples, and concrete architectural decisions for a senior Go developer.

---

## 1. The Elm Architecture powers Bubble Tea's core

Bubble Tea implements The Elm Architecture (TEA) — a functional pattern where the entire application state lives in a single `Model` struct, messages drive state transitions through `Update()`, and the UI is a pure function of state via `View()`. This eliminates the class of bugs that plagued the Python Rich/Prompt Toolkit approach: race conditions, tangled state, and blocking render calls.

**The three interface methods** every Bubble Tea model implements:

```go
type Model interface {
    Init() tea.Cmd                           // Initial command (startup I/O)
    Update(msg tea.Msg) (Model, tea.Cmd)     // Handle messages, return new state
    View() string                            // Render UI as a string (pure function)
}
```

**Messages** are the sole mechanism for state change. Built-in types include `tea.KeyMsg` (keyboard input), `tea.WindowSizeMsg` (terminal resize, sent on startup and every resize), and `tea.MouseMsg` (requires `tea.WithMouseCellMotion()`). Any Go type can serve as a custom message — define a struct, return it from a `tea.Cmd`, and handle it in `Update()`.

**Commands** (`tea.Cmd`) handle all I/O. A command is simply `func() tea.Msg` — Bubble Tea runs each in its own goroutine and routes the returned message back to `Update()`. Critical command combinators:

- **`tea.Batch(...Cmd)`** runs commands concurrently with no ordering guarantees — use for parallel operations like spinner tick + data fetch
- **`tea.Sequence(...Cmd)`** runs commands sequentially — use for ordered operations like save-then-quit
- **`tea.Tick(duration, fn)`** fires after a precise duration — use for timers independent of wall clock
- **`tea.Every(duration, fn)`** synchronizes to wall clock — fires at clock boundaries

**Thread safety** is achieved through `p.Send(msg)`, which writes to the program's internal message channel from any goroutine. The event loop reads from this channel sequentially, ensuring `Update()` always runs on a single goroutine. **Never modify model state from goroutines directly** — always use `p.Send()` or return messages from `tea.Cmd`.

### v2 is the target for new projects

Bubble Tea v2 reached RC stage in early 2026 with the import path `charm.land/bubbletea/v2`. For HybridCoder, **target v2** — the benefits are substantial:

| Feature | v1 | v2 |
|---|---|---|
| Renderer | Line-by-line diff | **Cursed Renderer** (ncurses algorithm, orders-of-magnitude less bandwidth) |
| Synchronized output | Not supported | **Mode 2026 enabled by default** (atomic frame updates, eliminates tearing) |
| View() return | `string` | `tea.View` struct (with AltScreen, Cursor, KeyboardEnhancements) |
| Key messages | `tea.KeyMsg` only | `tea.KeyPressMsg` + `tea.KeyReleaseMsg` (Kitty protocol support) |
| Color handling | Manual via termenv | **Built-in downsampling** via colorprofile (automatic) |
| Clipboard | Not built-in | `tea.SetClipboard()` / `tea.ReadClipboard()` via OSC52 |

The Charm team is coordinating simultaneous v2 releases of Bubble Tea, Bubbles, Lip Gloss, and Huh. The API is frozen at RC stage.

---

## 2. How the renderer eliminates flicker

Bubble Tea's v1 standard renderer uses **line-by-line diffing** rather than full-screen clearing. The `flush()` method compares each new frame line against `lastRenderedLines` — unchanged lines are skipped entirely via cursor repositioning, while changed lines are overwritten in place using `EraseLineRight`. This approach was refined in PR #1132, which replaced `EraseEntireLine` (which briefly showed empty content) with in-place overwriting.

**Frame rate limiting** is built in. A ticker fires at the configured FPS (default **60**, configurable via `tea.WithFPS(n)`, capped at 120). The `write()` method stores the latest `View()` output in a buffer; `flush()` reads and renders only on tick boundaries. Multiple rapid state changes between ticks produce only one terminal write — **critical for streaming scenarios** where tokens arrive faster than the renderer should update.

**v2's Cursed Renderer** is a ground-up rewrite based on the ncurses rendering algorithm. It achieves dramatically lower bandwidth (important for SSH via Wish) and enables Mode 2026 synchronized output by default. The terminal buffers all output between `ESC P 2026 s` and `ESC P 2026 e` markers, rendering atomically. Supported terminals include Ghostty, Kitty, iTerm2, WezTerm, Foot, and Alacritty.

**Comparison with alternatives**: Ratatui (Rust) uses cell-level immediate-mode diffing — more granular but you own the event loop. Ink (JS) uses React's virtual DOM reconciliation. Bubble Tea's retained-mode approach (framework diffs your `View()` string) is the simplest developer experience, trading some rendering granularity for dramatically simpler code.

For HybridCoder's **<16ms frame budget**, keep `View()` fast by using `strings.Builder`, caching rendered components that haven't changed, and avoiding re-rendering markdown on every frame. The 60fps renderer naturally coalesces updates.

---

## 3. Fixed input bar with scrollable output above

This is the most critical layout pattern for a chat-based coding agent. The viewport (scrollable chat area) must dynamically resize when the terminal changes, while the input bar stays fixed at the bottom.

```go
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height
        // Measure fixed-height chrome
        headerH := 1
        statusH := 1
        inputH  := 3 // border + padding + text
        // Viewport gets ALL remaining space
        m.viewport.Width  = msg.Width
        m.viewport.Height = msg.Height - headerH - statusH - inputH
        m.textInput.Width = msg.Width - 4
    }
    // ...
}

func (m model) View() string {
    header   := headerStyle.Width(m.width).Render("⌬ HybridCoder")
    chat     := m.viewport.View()
    status   := statusStyle.Width(m.width).Render(fmt.Sprintf("%d msgs", len(m.messages)))
    inputBar := inputBorderStyle.Width(m.width).Render(m.textInput.View())
    
    return lipgloss.JoinVertical(lipgloss.Left, header, chat, status, inputBar)
}
```

**Critical pattern: lazy viewport initialization.** Create the viewport only after the first `tea.WindowSizeMsg` (the "ready" pattern) — before that, return a loading placeholder. Use `lipgloss.Height(renderedString)` to measure chrome dynamically rather than hardcoding pixel heights.

**For multiline input expansion** (textarea grows, viewport shrinks): recalculate `viewport.Height` in `Update()` whenever `textarea.LineCount()` changes. The textarea's `MaxHeight` field caps growth.

**Focus management**: Only forward `tea.KeyMsg` to the focused component. Forward `tea.WindowSizeMsg` and custom messages to all components. Switch focus between viewport (scrolling with PgUp/PgDn) and input (typing) via a `focused` field and `Focus()`/`Blur()` methods on textinput.

---

## 4. Multi-pane layout with responsive panels

HybridCoder requires: header | [chat pane | context panel] | status bar | input. Each pane is its own struct implementing a mini tea.Model pattern:

```go
type pane int
const (
    paneChat pane = iota
    paneContext
    paneInput
)

// Root model composes all panes
type model struct {
    chat      ChatPane      // viewport-based scrollable chat
    context   ContextPane   // right-side plan/todo/diffs panel
    input     InputPane     // fixed textarea at bottom
    focus     pane
    width, height int
}

func (m *model) recalcLayout() {
    headerH, statusH, inputH := 1, 1, 3
    contentH := m.height - headerH - statusH - inputH
    
    showContext := m.width >= 100 // hide on narrow terminals
    if showContext {
        chatW := m.width * 2 / 3
        ctxW  := m.width - chatW - 1
        m.chat.SetSize(chatW, contentH)
        m.context.SetSize(ctxW, contentH)
    } else {
        m.chat.SetSize(m.width, contentH)
    }
}
```

**Focus cycling** uses Tab/Shift+Tab, skipping hidden panes. When the context panel is hidden (`width < 100`), the focus cycle skips it. Each pane's `Update()` method checks `focused` before processing key messages.

**Lip Gloss composition** joins the panes:
```go
middle := lipgloss.JoinHorizontal(lipgloss.Top, chatView, contextView)
full := lipgloss.JoinVertical(lipgloss.Left, header, middle, status, input)
```

**Focused panes** get a highlighted border (`RoundedBorder` with accent color); blurred panes get a dimmed border. This is the pattern OpenCode uses — its `appModel` orchestrates `chatPage` with a `SplitPaneLayout` containing messages, editor, and sidebar components, with a dialog overlay system for permissions, model selection, and session management.

---

## 5. Streaming LLM output without blocking input

This is where Go's goroutine model shines over Python's GIL-limited asyncio. The canonical pattern uses a **channel relay** — a producer goroutine consumes the SSE stream and writes tokens to a channel, while a `tea.Cmd` blocks on reading from that channel:

```go
type tokenMsg struct{ Content string }
type streamDoneMsg struct{}
type streamErrorMsg struct{ Err error }

// Producer goroutine: consumes SSE stream
func startStream(ctx context.Context, ch chan<- string, prompt string) {
    defer close(ch)
    stream, _ := client.CreateStream(ctx, prompt)
    defer stream.Close()
    for {
        resp, err := stream.Recv()
        if errors.Is(err, io.EOF) { return }
        select {
        case ch <- resp.Delta:
        case <-ctx.Done(): return
        }
    }
}

// Relay command: blocks until next token arrives
func waitForToken(ch <-chan string) tea.Cmd {
    return func() tea.Msg {
        token, ok := <-ch
        if !ok { return streamDoneMsg{} }
        return tokenMsg{Content: token}
    }
}
```

In `Update()`, each `tokenMsg` appends to a buffer and **re-issues** `waitForToken` to subscribe for the next token. This "wait-and-resubscribe" pattern is from Bubble Tea's official `realtime` example.

### Token batching for render efficiency

Re-rendering markdown on every token is expensive. Batch tokens at **50ms intervals**:

```go
case tokenMsg:
    m.pendingTokens = append(m.pendingTokens, msg.Content)
    m.dirty = true
    return m, waitForToken(m.tokenCh)

case batchTickMsg:
    if m.dirty {
        m.content += strings.Join(m.pendingTokens, "")
        m.pendingTokens = m.pendingTokens[:0]
        m.dirty = false
        sanitized := sanitizePartialMarkdown(m.content)
        rendered, _ := m.glamourRenderer.Render(sanitized)
        m.viewport.SetContent(rendered)
        if m.viewport.AtBottom() { m.viewport.GotoBottom() }
    }
    if m.streaming { return m, batchTick() }
```

### Auto-scroll with user override

Check `viewport.AtBottom()` before updating content. If the user was at the bottom, auto-scroll after new content. If they scrolled up, don't. Re-enable auto-scroll when they scroll back to bottom or press End.

### Stream cancellation

Use `context.WithCancel` for clean abort on Escape:
```go
case tea.KeyMsg:
    if msg.String() == "esc" && m.streaming {
        m.streamCancel() // cancels the producer goroutine
        m.streaming = false
    }
```

---

## 6. Markdown rendering during streaming

**Glamour** (charmbracelet/glamour) renders complete markdown documents using goldmark for parsing and Chroma for syntax highlighting. It produces beautiful ANSI-styled terminal output with one call: `glamour.Render(markdown, "dark")`. However, **it has no streaming/incremental API** — each `Render()` call parses from scratch.

**The streaming challenge**: LLM tokens produce incomplete markdown — unclosed code fences, partial bold markers, half-formed tables. Glamour may produce unexpected output for malformed input.

**Production approach** (synthesized from mods, OpenCode, and ollamatea):

1. **Sanitize partial markdown** before rendering — close unclosed fences and formatting:
```go
func sanitizePartialMarkdown(content string) string {
    if strings.Count(content, "```")%2 != 0 {
        content += "\n```"
    }
    if strings.Count(content, "**")%2 != 0 {
        content += "**"
    }
    return content
}
```

2. **Reuse the `TermRenderer` instance** — don't create one per render call
3. **Batch-render at 50ms intervals** rather than per-token
4. **Final clean render** when streaming completes (without sanitization hacks)

**For the long term**, consider building a **custom goldmark terminal renderer** for the streaming path. Glamour's `ansi` package provides a reference implementation. A custom renderer can handle streaming-specific needs: showing a cursor at the insertion point, partially rendering incomplete blocks with special styling, and incremental parsing of complete blocks.

**Code syntax highlighting** works through Chroma, which Glamour integrates automatically. Fenced code blocks with language tags (`\`\`\`go`) get full syntax highlighting with **250+ supported languages**.

---

## 7. Slash command system with fuzzy autocomplete

The `textinput` bubble supports ghost-text autocompletion via `SetSuggestions()` — prefix-matched suggestions appear after the cursor in a faded style. Users cycle with Ctrl+N/Ctrl+P and accept with the right arrow key. **Limitations**: prefix-only matching (no fuzzy), no dropdown, single suggestion visible at a time.

**For HybridCoder, build a custom dropdown overlay** that renders above the input:

```go
// Command registry with fuzzy matching
type Command struct {
    Name        string
    Description string
    Category    string
    Handler     CommandHandler
    Args        []ArgSpec
}

type Registry struct {
    commands map[string]*Command
}

func (r *Registry) FuzzyMatch(query string) []*Command {
    query = strings.TrimPrefix(query, "/")
    names := make([]string, len(r.All()))
    for i, c := range r.All() { names[i] = strings.TrimPrefix(c.Name, "/") }
    matches := fuzzy.Find(query, names)  // sahilm/fuzzy library
    result := make([]*Command, len(matches))
    for i, m := range matches { result[i] = r.All()[m.Index] }
    return result
}
```

**The `sahilm/fuzzy` library** (1.3k stars, zero deps) provides scored fuzzy matching with `MatchedIndexes` for highlighting matched characters. Charmbracelet's `bubbles/list` uses it internally.

**Multi-stage command flows** (e.g., `/model` → model picker → confirm) use a state machine pattern:
```go
type CommandFlowState int
const (
    StateIdle CommandFlowState = iota
    StateSelectingOption
    StateConfirming
    StateExecuting
)
```

Intercept arrow keys **before** they reach the textinput when the command menu is visible. For the textarea-based input (multiline prompts), detect `/` at the start of content and overlay your own autocomplete, routing Enter to command execution instead of newline insertion.

---

## 8. Session persistence with CGo-free SQLite

### SQLite driver recommendation: ncruces/go-sqlite3

Three pure-Go SQLite options exist. After analyzing benchmarks from `cvilsmeier/go-sqlite-bench` (August 2025):

| Benchmark | mattn/CGo (ms) | modernc/Pure Go (ms) | ncruces/WASM (ms) |
|-----------|---------|---------|---------|
| Real INSERT | 1416 | 1641 | **1364** |
| Real QUERY | **120** | 130 | 127 |
| Complex INSERT | **843** | 2909 | 1834 |

**`ncruces/go-sqlite3`** is the best choice: pure Go (no CGo), runs official SQLite WASM via wazero, competitive performance, encryption support, and trivial cross-compilation. For HybridCoder's data volumes (KB-MB of chat sessions), the performance difference is negligible.

### Schema design

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    name TEXT,
    project_path TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    model TEXT, provider TEXT,
    approval_mode TEXT DEFAULT 'suggest',
    status TEXT DEFAULT 'active'
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,  -- user, assistant, system, tool
    content TEXT NOT NULL,
    token_count INTEGER,
    metadata TEXT,  -- JSON for tool calls
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    action TEXT NOT NULL,  -- read, create, modify, delete
    diff TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**State management separation**: Keep TUI state (viewport position, focus, dimensions) separate from business state (session, messages, approval mode, model). The root model composes both. Use WAL journal mode and `busy_timeout(5000)` for SQLite performance.

---

## 9. Approval modes modeled after Claude Code and Codex

**Four approval modes**, matching Claude Code and Codex CLI patterns:

- **Read-only**: Can read files, no writes or execution
- **Suggest**: Shows all proposed changes, requires approval for everything (default)
- **Auto-edit**: Auto-applies file edits, asks before shell commands
- **Full-access**: Everything auto-approved (YOLO mode, only for trusted environments)

**Claude Code's permission architecture**: Rule evaluation follows deny → ask → allow (first match wins, deny always takes precedence). Rules use wildcard matching: `Bash(npm run test *)` matches commands starting with that prefix but won't match `safe-cmd && evil-cmd`. Organizations can enforce managed settings users can't override.

**Codex CLI's approach**: Named approval policies (`suggest`, `auto-edit`, `full-auto`, `untrusted`) with sandbox modes (`workspace-write` limits filesystem access, `danger-full-access` for full system). Mid-session switching via `/mode suggest`.

**Implementation in Bubble Tea**: Use the `charmbracelet/huh` library for inline confirmation dialogs:

```go
form := huh.NewForm(
    huh.NewGroup(
        huh.NewConfirm().
            Title("Execute: rm -rf ./build?").
            Description(diffPreview).
            Affirmative("Yes").Negative("No").
            Value(&approved),
    ),
)
```

Huh forms implement `tea.Model` — they integrate directly into the Bubble Tea update loop. For diff previews, use `hexops/gotextdiff` (Myers algorithm from gopls) with Lip Gloss-styled added/removed lines (green/red) and Chroma's built-in `"diff"` lexer for syntax-highlighted unified diffs.

---

## 10. Concurrent subagent tasks with progress tracking

For multi-agent orchestration, use `errgroup` with `p.Send()` to safely update the TUI from multiple goroutines:

```go
func runTasks(p *tea.Program, tasks []AgentTask) {
    g, ctx := errgroup.WithContext(context.Background())
    g.SetLimit(3) // max 3 concurrent agents
    
    for i, task := range tasks {
        i, task := i, task
        g.Go(func() error {
            p.Send(taskStatusMsg{id: i, status: TaskRunning})
            result, err := task.Execute(ctx)
            if err != nil {
                p.Send(taskStatusMsg{id: i, status: TaskError, message: err.Error()})
                return err
            }
            p.Send(taskStatusMsg{id: i, status: TaskDone})
            return nil
        })
    }
    g.Wait()
    p.Send(allTasksDoneMsg{})
}
```

**Each task gets its own `spinner.Model`** — spinners use atomic internal IDs so `spinner.TickMsg` routes correctly when multiple spinners coexist. Forward `spinner.TickMsg` to all active spinners in `Update()`:

```go
case spinner.TickMsg:
    var cmds []tea.Cmd
    for i, t := range m.tasks {
        if t.status == TaskRunning {
            m.tasks[i].spinner, cmd = t.spinner.Update(msg)
            cmds = append(cmds, cmd)
        }
    }
    return m, tea.Batch(cmds...)
```

**Task panel rendering** follows the Docker Compose pattern: fixed row per task with status icon (`○` pending, spinner running, `✓` done, `✗` error), task name, current step, mini progress bar, and elapsed time. For the `bubbles/progress` component, use `ViewAs(pct)` (static rendering) for multi-bar displays rather than the animated API.

**Per-task cancellation**: Each task gets its own `context.WithCancel` derived from the group's context. Cancelling a specific task calls its individual cancel function. The errgroup's context cancels all remaining tasks if any returns an error.

---

## 11. Cross-platform Windows and Linux compatibility

### Terminal compatibility matrix

| Feature | Windows Terminal | cmd.exe (Win10+) | Linux terminals |
|---|---|---|---|
| TrueColor | ✅ | ✅ (VT enabled) | ✅ most modern |
| Alt screen | ✅ | ✅ (VT enabled) | ✅ |
| Mouse click/wheel | ✅ | Limited | ✅ |
| Window resize | ✅ (console events) | ⚠️ Polling needed | ✅ (SIGWINCH) |
| Synchronized output | ✅ recent | ❌ | Varies |
| Cursor hide | ✅ | ⚠️ Buggy | ✅ |

**Windows does NOT support SIGWINCH.** Bubble Tea sends `WindowSizeMsg` once at startup but cannot detect resize dynamically on legacy Windows consoles. Workaround: poll `term.GetSize()` on a tick (~30fps). Windows Terminal handles resize via console events, which newer Bubble Tea versions support.

**Known Windows issues resolved**:
- **v0.26 flicker** (fixed in PR #1021): Synchronized output changes caused severe flickering
- **First character lost** (fixed in v1.3+): Successive `tea.Program` runs dropped first keypress
- **Arrow keys broken** (fixed): Toggle `ENABLE_VIRTUAL_TERMINAL_INPUT` flag

**Color detection** uses `charmbracelet/colorprofile`: checks `COLORTERM`, `TERM`, `NO_COLOR`, and `CLICOLOR` environment variables. Lip Gloss automatically downsample colors to the detected profile. Use `lipgloss.AdaptiveColor{Light: "236", Dark: "248"}` for light/dark background adaptation and `lipgloss.CompleteColor` to specify exact values per profile tier.

**Unicode/emoji**: Avoid emoji in core UI elements — use ASCII/Unicode box-drawing characters instead. Width calculation across terminals is inconsistent, especially for variation selectors and ZWJ sequences. Use `go-runewidth` for accurate string width measurement.

**Low-end hardware optimization** (2-4 cores, 8GB RAM):
- Use `tea.WithFPS(30)` if 60fps isn't needed
- Use `strings.Builder` in `View()` to reduce allocations
- Bubble Tea itself uses **5-10 goroutines** for a basic app (~80KB total stack)
- Virtualize long lists — only render visible rows

---

## 12. Benchmark and profiling infrastructure in Go

### Python tool equivalents

| Python | Go Equivalent | Purpose |
|---|---|---|
| py-spy | `runtime/pprof` + `go tool pprof` | CPU profiling with flame graphs |
| scalene | `runtime/pprof` + `runtime/trace` | CPU + memory + execution tracing |
| memray | `runtime/pprof` heap + `runtime.MemStats` | Memory tracking |
| psutil | `runtime.MemStats` + `runtime/metrics` | System metrics |

### BENCH sentinel system

Write sentinels to stderr (stdout is used by the TUI):

```go
var benchMode = os.Getenv("BENCH_MODE") == "1"

case readyMsg:
    m.ready = true
    if benchMode { fmt.Fprintln(os.Stderr, "BENCH:READY") }

case tea.KeyMsg:
    if benchMode && msg.String() == "p" {
        fmt.Fprintln(os.Stderr, "BENCH:PONG")
    }
```

External harness reads stderr and measures timing against budgets (<300ms cold start, <16ms keystroke echo).

### Performance benchmarks

```go
func BenchmarkViewRender(b *testing.B) {
    m := initialModel()
    m, _ = m.Update(tea.WindowSizeMsg{Width: 120, Height: 40})
    b.ResetTimer()
    b.ReportAllocs()
    for b.Loop() { _ = m.View() }  // Go 1.24+ b.Loop()
}

func TestFrameBudget(t *testing.T) {
    m := initialModel()
    start := time.Now()
    _ = m.View()
    if elapsed := time.Since(start); elapsed > 16*time.Millisecond {
        t.Errorf("View() took %v, exceeds 16ms budget", elapsed)
    }
}
```

Track performance across commits with **benchstat**: `go test -bench=. -benchmem -count=10 > bench.txt`, then `benchstat old.txt new.txt` for statistical comparison with p-values and confidence intervals.

**Memory leak detection** over 30-minute idle: sample `runtime.MemStats.HeapAlloc` at intervals, trigger `runtime.GC()` periodically, assert growth stays below **1.5x** baseline. Use `uber-go/goleak` for goroutine leak detection in tests.

**Startup optimization**: Go binary startup is inherently fast (~0.4ms for hello world). Use `GODEBUG=inittrace=1` to identify slow `init()` functions. Avoid large map literals in package scope (Replit found 200ms+ startup from huge map init). Use `sync.Once` for lazy initialization and PGO (Profile-Guided Optimization) for 2-14% improvement.

---

## 13. Testing the TUI with teatest

The `charmbracelet/x/exp/teatest` package provides a test harness for Bubble Tea models:

```go
func TestInteractive(t *testing.T) {
    tm := teatest.NewTestModel(t, initialModel(),
        teatest.WithInitialTermSize(120, 40))
    
    tm.Type("hello world")
    tm.Send(tea.KeyMsg{Type: tea.KeyEnter})
    
    teatest.WaitFor(t, tm.Output(), func(b []byte) bool {
        return bytes.Contains(b, []byte("Response:"))
    }, teatest.WithDuration(5*time.Second))
    
    tm.Send(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})
    fm := tm.FinalModel(t)
    // Assert on final model state
}
```

**Golden file testing**: `teatest.RequireEqualOutput(t, out)` compares View() output against `.golden` files in `testdata/`. Run `go test -update` to create/update golden files. Force `lipgloss.SetColorProfile(termenv.Ascii)` in test init for CI reproducibility.

**Property-based testing** with `pgregory.net/rapid`:
```go
rapid.Check(t, func(t *rapid.T) {
    m := initialModel()
    t.Repeat(map[string]func(*rapid.T){
        "moveDown": func(t *rapid.T) { m, _ = m.Update(tea.KeyMsg{Type: tea.KeyDown}) },
        "moveUp":   func(t *rapid.T) { m, _ = m.Update(tea.KeyMsg{Type: tea.KeyUp}) },
        "select":   func(t *rapid.T) { m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter}) },
    })
    // Invariant: cursor always in bounds
    if m.cursor < 0 || m.cursor >= len(m.items) { t.Fatal("out of bounds") }
})
```

**CI runs headless** — teatest and `tea.WithInput/WithOutput` work without a TTY. Add `*.golden -text` to `.gitattributes` to prevent line-ending issues across platforms.

---

## 14. Project structure and build system

### Recommended layout

```
hybridcoder/
├── cmd/hybridcoder/main.go          # Entry point
├── internal/
│   ├── tui/                          # Bubble Tea models and components
│   │   ├── app.go                    # Root model
│   │   ├── chat/                     # Chat viewport
│   │   ├── editor/                   # Input component
│   │   ├── sidebar/                  # Context panel
│   │   ├── dialog/                   # Permission, session, model dialogs
│   │   └── styles/                   # Lip Gloss themes
│   ├── llm/                          # LLM provider abstraction
│   │   ├── client.go                 # LLMProvider interface
│   │   ├── ollama/                   # Ollama client
│   │   └── openrouter/               # OpenRouter client
│   ├── tools/                        # Tool interface + implementations
│   │   ├── registry.go
│   │   ├── fileops/
│   │   ├── search/                   # ripgrep integration
│   │   └── shell/
│   ├── agent/                        # Orchestration
│   ├── db/                           # SQLite + migrations
│   └── config/                       # TOML config via koanf
├── .goreleaser.yml
├── Makefile
├── go.mod
└── go.sum
```

The `internal/` directory is enforced by the Go compiler — external modules cannot import from it. Group by functionality/responsibility, not by layer.

### Build and release

**GoReleaser** handles cross-platform binary releases. With CGo-free dependencies (ncruces/go-sqlite3), the config is simple:

```yaml
builds:
  - env: [CGO_ENABLED=0]
    goos: [linux, windows, darwin]
    goarch: [amd64, arm64]
    main: ./cmd/hybridcoder/
    ldflags: [-s -w -X main.version={{.Version}}]
```

**Binary size**: A complex Bubble Tea app with SQLite runs **15-30 MB** unoptimized, **8-12 MB** with `-ldflags="-s -w"` (strips debug info, ~30% reduction), and **4-6 MB** with UPX compression (adds 15-160ms startup decompression). For a long-running TUI, UPX is acceptable.

### CGo decision tree

If tree-sitter is needed, it requires CGo (`smacker/go-tree-sitter`). Make it optional behind a build tag. For SQLite, use `ncruces/go-sqlite3` (CGo-free). For local LLM inference, use the Ollama HTTP API instead of go-llama.cpp bindings. This keeps the default build CGo-free with trivial cross-compilation.

---

## 15. Phased migration from Python to Go

### Phase 1: Foundation (weeks 1-3)
Project scaffolding, config system (koanf + TOML), basic Bubble Tea TUI (root model, chat viewport, textinput, status bar), SQLite storage with ncruces, Cobra CLI. **Deliverable**: App launches, shows TUI, creates database.

### Phase 2: LLM integration (weeks 4-6)
`LLMProvider` interface with streaming support, Ollama client (HTTP + NDJSON streaming), OpenRouter client (SSE streaming), chat loop with streaming display, session persistence. **Deliverable**: Full chat with session save/load.

### Phase 3: Tool system (weeks 7-9)
Go interface-based tool registry, file read/write tools, shell execution with `context.WithTimeout`, code search via ripgrep subprocess, tool call parsing from LLM responses, approval pipeline. **Deliverable**: Agent reads/writes files, searches code, executes commands.

### Phase 4: Agent orchestration (weeks 10-12)
Main agent loop, subagent management with errgroup, L4 model routing, permission system with Huh dialogs, multi-turn context management. **Deliverable**: Full agentic coding assistant.

### Phase 5: Polish (weeks 13-16)
L2 embeddings via Ollama API (or hugot library), GoReleaser releases, TUI themes, Vim keybindings, integration tests, binary optimization. **Deliverable**: v1.0 cross-platform release.

### Key construct mappings

| Python | Go |
|---|---|
| `async/await` | Goroutines + channels |
| `asyncio.gather()` | `errgroup.Group` |
| Rich components | Lip Gloss + Bubbles |
| Prompt Toolkit | Bubble Tea |
| `dict`-based registry | Interface-based registry |
| `try/except` | `if err != nil` |
| `typing.Protocol` | Go interfaces (implicit satisfaction) |

**Hardest to port**: TUI (fundamentally different architecture — Elm vs imperative), embedding inference (Python's sentence-transformers ecosystem is more mature), and async streaming (requires rethinking as goroutine+channel patterns). **Easiest**: L1 regex, HTTP clients, file operations, config management.

**For L2 embeddings in Go**: `knights-analytics/hugot` runs HuggingFace models (e.g., `all-MiniLM-L6-v2`) via ONNX Runtime with a pure Go backend option. Alternatively, delegate to Ollama's `/api/embed` endpoint for zero-dependency embeddings.

---

## 16. Architectural decisions with recommendations

### Framework: Bubble Tea wins for Go-native TUI

Bubble Tea provides **Elm Architecture consistency**, the richest ecosystem (Bubbles, Lip Gloss, Glamour, Huh), production maturity (lazygit, Glow, Soft Serve), and explicit inline/fullscreen/hybrid mode support. It's the only Go-native option, and Charm's own Crush validates it for agentic coding. Ratatui (Rust) offers 30-40% better memory/CPU but requires Rust. Textual (Python) has better CSS-like layouts but brings the GIL problem HybridCoder is escaping.

### Rendering mode: inline default, alt screen for specific views

**Inline mode by default** preserves terminal scrollback, works in pipelines, and feels natural — matching Claude Code and Codex CLI. Switch to alt screen dynamically for file diffs, code editors, or full-screen views using `tea.EnterAltScreen`/`tea.ExitAltScreen` commands. Bubble Tea supports mid-session switching.

### Architecture: single binary with MCP extensibility

**Single binary** for simplicity — one `go build`, one artifact, no dependency management for users. Use **MCP (Model Context Protocol)** for tool extensibility (industry standard used by Claude Code and Codex). Add markdown-based custom commands (flat files in `.hybridcoder/commands/`, no compilation needed). Avoid Go's `plugin` package entirely (Linux/macOS only, same Go version required, no Windows).

### Session storage: SQLite via ncruces/go-sqlite3

SQL queryability (search conversations, FTS5 full-text search) is essential for a coding agent's session management. BoltDB and BadgerDB lack SQL queries. Flat files (JSONL) degrade with scale — developers report poor search performance scanning thousands of session files. **ncruces/go-sqlite3** provides pure Go convenience, cross-compilation ease, and runs actual SQLite code via WASM.

### Markdown rendering: Glamour initially, custom goldmark renderer for streaming

Start with Glamour for development speed and non-streaming content. Build a custom goldmark ANSI renderer for the streaming LLM output path once batch-rendering becomes a bottleneck. Glamour is built on goldmark, so the transition is natural — study Glamour's `ansi` package as reference.

### LLM integration: direct HTTP with provider abstraction

Build a `LLMProvider` interface with `Complete(ctx, req) (<-chan StreamChunk, error)`. Implement for OpenAI-compatible (covers OpenAI, Ollama, OpenRouter, Groq), Anthropic, and Google. For local models, target the Ollama API. Avoid go-llama.cpp — CGo isn't worth it when Ollama abstracts it.

### Code intelligence: LSP primary, tree-sitter for syntax

Tree-sitter and LSP are complementary. LSP provides semantic intelligence (go-to-definition, references, diagnostics). Tree-sitter provides fast syntactic analysis (structural search, scope detection). OpenCode uses both. For CGo-free tree-sitter, watch `malivvan/tree-sitter` (WASM via wazero, pre-release) or make the official `smacker/go-tree-sitter` optional behind a build tag.

### Concurrency: goroutines + channels, lightweight event bus

Bubble Tea IS essentially a CSP actor system — the Program maintains a message channel, Cmds are goroutines, and Update processes messages sequentially. Use `tea.Cmd` for UI-related concurrency, goroutines+channels for background tasks feeding back via `p.Send()`, and a simple pub/sub event bus for cross-cutting concerns (file change notifications, session saves). Don't add a formal actor framework.

### Configuration: TOML + koanf

TOML is human-readable, supports comments, is type-safe, and is increasingly the Go ecosystem standard. **koanf** over Viper: lighter footprint (313% smaller binary impact), case-sensitive keys, modular dependency loading. Layer: defaults → TOML config file → environment variables → CLI flags.

---

## Conclusion

This migration is well-timed. **Bubble Tea v2's synchronized output, Cursed Renderer, and declarative View struct eliminate the rendering limitations that would have been painful in v1.** The framework's Elm Architecture naturally enforces the separation of concerns that HybridCoder's 4-layer LLM architecture requires — each layer communicates through typed messages, goroutines handle parallel inference without GIL constraints, and the 60fps renderer coalesces updates during high-throughput streaming.

The critical path is **Phase 2 (LLM streaming)** — get token-by-token display working with auto-scroll, batched markdown rendering, and cancellation before investing in the tool system. The channel-relay pattern for streaming and the batch-tick approach for rendering are the two patterns that make or break the UX.

Three architectural choices dominate the success of this project: **ncruces/go-sqlite3** for CGo-free cross-platform builds, the **Ollama API** for local LLM inference without compiled ML dependencies, and **inline mode by default** matching the patterns users expect from Claude Code and Codex. The Charm ecosystem provides everything else — from Glamour's markdown rendering to Huh's approval dialogs to the spinner/progress components for subagent tracking. With Charm's own Crush validating the approach at scale, the framework risk is minimal.
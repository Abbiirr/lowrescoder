# Tier 6 — Minimal Lightweight TUI

**Goal:** replace the current 7500-LOC Rust TUI with a 1500-LOC minimal version that does the same job, faster.

**Total cost:** ~3 weeks engineering, net **negative** LOC (~−6000).

**Why this is worth doing:** the current `rtui/` is at 7500 LOC across `main.rs (323) + state/model.rs (304) + state/reducer.rs (2243) + render/view.rs (3479) + ui/composer.rs (172) + ui/spinner.rs (230) + rpc/protocol.rs (749)`. The team's own commit history (`Stabilizes rust tui`, `Inventories bugs in new tui`, `Plans for rust tui issue fixes`) says it's already in maintenance overload. The render/view.rs alone is 3479 lines for what should be ~600 lines of widget composition. Either you fix the existing TUI by deleting half of it, or you ship a clean replacement and retire the old one. Both are correct moves; this tier picks the latter because the render/view.rs structure suggests deeper rot.

**Critical constraint:** the new TUI must consume the App Server protocol from Tier 2.1. It does *not* re-implement RPC, state machines, or any backend logic. It's a thin client.

---

## What the current TUI is doing wrong

Reading the actual file structure:

1. **`view.rs` is 3479 lines** — this is a single file rendering 9 stages × 9 detail surfaces. There's no widget abstraction; every state has hand-rolled rendering inside `match` arms. Adding any new state requires editing this giant file.

2. **`reducer.rs` is 2243 lines** — Elm-style reducer with too many event types. From the codebase, `Event` enum has 40+ variants. Most of these are RPC-specific (`TokenParams`, `ToolCallParams`, etc.) that should map to a single `RpcMsg(value)` variant + a sub-reducer.

3. **`model.rs` has 21 enum/struct types** — model is fragmented. `Stage`, `DetailSurface`, `ApprovalState`, `AskUserState`, `ModelPickerState`, `ProviderPickerState`, `PaletteState`, `EditorLaunchState`, `ShutdownState` could be one `enum Mode`.

4. **`rpc/protocol.rs` has 44 ad-hoc structs** — Tier 2.1 already plans to fix this with Item/Turn/Thread. The TUI rewrite consumes the new protocol directly.

5. **No widget caching** — per ratatui issue #1004, large lists/tables are slow because they re-allocate every frame. `streamBuf` (a `String`) gets re-rendered every frame even when text hasn't changed. Cache rendered `Lines<'static>` and invalidate on state change.

6. **Mixed concerns in update loop** — `event_loop.rs` does PTY spawning, RPC parsing, and UI events in the same async function. Should split into three independently-testable pieces.

---

## Target architecture

**Total LOC budget: 1500.** Hard cap. If a feature pushes over budget, drop another feature first.

```
rtui-min/
├── Cargo.toml                   ~20 lines
├── src/
│   ├── main.rs                  ~80 lines  — CLI flag parsing, terminal init/restore
│   ├── app.rs                   ~250 lines — top-level state, transition logic
│   ├── ui.rs                    ~500 lines — single-file widget rendering, immediate-mode
│   ├── input.rs                 ~150 lines — keymap, composer textbuf
│   ├── transport.rs             ~250 lines — RPC client (stdio default, unix optional)
│   ├── verbs.rs                 ~200 lines — 187 spinner verbs (the one thing I'm keeping verbatim)
│   └── theme.rs                 ~50 lines  — colors, styles
└── tests/
    └── render_snapshots.rs      ~200 lines — buffer snapshot tests
```

Total source: ~1300 lines (under budget). Tests: ~200 lines.

---

## Design principles (from research)

### 1. Immediate-mode all the way

Per ratatui's docs and discussions: **never do partial rendering**. Always redraw everything. Trust the buffer diff to skip unchanged cells. This eliminates an entire class of bugs (stale rendering, ghost text, half-cleared regions).

```rust
// CORRECT — redraw everything every frame, let ratatui diff
terminal.draw(|frame| {
    let area = frame.area();
    render_app(&app, frame.buffer_mut(), area);
})?;

// WRONG — what current rtui does in places
terminal.draw(|frame| {
    if app.streaming_dirty {
        render_streaming_only(...);
    }
    if app.approval_dirty {
        render_approval_only(...);
    }
})?;
```

### 2. One `App` struct, one `Mode` enum

No more 9-stage × 9-detail-surface combinatorial explosion. One enum:

```rust
// src/app.rs

pub struct App {
    pub mode: Mode,
    pub thread_id: Option<String>,
    pub turn_id: Option<String>,
    pub composer: TextBuf,
    pub history: Vec<HistoryEntry>,
    pub status: StatusBar,
    pub config: Config,
    pub theme: Theme,
}

pub enum Mode {
    Idle,
    Streaming { spinner_verb: &'static str, since: Instant },
    Approval { tool: String, args: Value, options: Vec<&'static str>, cursor: usize },
    Picker(PickerKind),
    Palette { filter: String, matches: Vec<&'static str>, cursor: usize },
    Detail(DetailKind),  // open overlay
}

pub enum PickerKind {
    Model { entries: Vec<String>, cursor: usize },
    Provider { entries: Vec<String>, cursor: usize },
    Session { entries: Vec<SessionEntry>, cursor: usize },
}

pub enum DetailKind {
    Tasks(Vec<TaskEntry>),
    Plan(Plan),
    Diff(Vec<DiffFile>),
    Grep(Vec<GrepHit>),
    CommandCenter,
    Restore(Vec<Checkpoint>),
}
```

That's 4 enums and 1 struct vs. the current 21 types. Same expressivity, far less code.

### 3. History as `Vec<HistoryEntry>`, never streaming buffers

Current TUI has `streamBuf` and `tokenBuf` as separate `Strings` that need flushing. Replace with append-only history:

```rust
pub enum HistoryEntry {
    UserMsg { text: String, ts: Instant },
    AgentMsg { text: String, ts: Instant, complete: bool },  // mutable while streaming
    ToolCall { name: String, args_summary: String, status: ToolStatus, result: Option<String> },
    ApprovalDecision { tool: String, decision: &'static str },
    SystemNote { text: String, ts: Instant },
    ThinkingBlock { text: String, complete: bool, collapsed: bool },
}
```

Streaming deltas mutate the *last* entry's `text` field if it's an open `AgentMsg` or `ThinkingBlock`. No separate buffer.

### 4. Cached rendered widgets

For history entries that are complete (`complete: true`), pre-render to `Vec<Line<'static>>` once and cache. Re-render only when entry mutates or width changes:

```rust
pub struct HistoryEntry {
    pub kind: HistoryKind,
    cached_lines: RefCell<Option<(u16 /*width*/, Vec<Line<'static>>)>>,
}

impl HistoryEntry {
    pub fn rendered_lines(&self, width: u16, theme: &Theme) -> Vec<Line<'static>> {
        if let Some((cw, lines)) = &*self.cached_lines.borrow() {
            if *cw == width {
                return lines.clone();
            }
        }
        let lines = self.render_lines(width, theme);
        *self.cached_lines.borrow_mut() = Some((width, lines.clone()));
        lines
    }

    pub fn invalidate_cache(&self) {
        self.cached_lines.borrow_mut().take();
    }
}
```

For streaming entries (`complete: false`), don't cache — re-render every frame is fine because deltas append small amounts.

### 5. Insert-before for inline-mode scrollback

Per ratatui docs (`Terminal::insert_before`), inline-mode TUIs can write completed content directly to terminal scrollback, freeing the live buffer for just the active turn:

```rust
// When a turn completes, push its history into terminal scrollback
fn flush_turn_to_scrollback(terminal: &mut Terminal, turn_lines: Vec<Line>) {
    terminal.insert_before(turn_lines.len() as u16, |buf| {
        for (i, line) in turn_lines.iter().enumerate() {
            buf.set_line(0, i as u16, line, buf.area.width);
        }
    }).ok();
}
```

This means the live area only holds: header + currently-streaming turn + composer + status bar. Everything else is real terminal scrollback that the OS handles. Massively reduces live buffer memory.

---

## File-by-file specs

### `main.rs` (~80 lines)

```rust
use anyhow::Result;

mod app;
mod input;
mod theme;
mod transport;
mod ui;
mod verbs;

#[tokio::main]
async fn main() -> Result<()> {
    let args = parse_args()?;
    init_logging(&args)?;

    let mut terminal = ratatui::init();
    let result = run(&mut terminal, args).await;
    ratatui::restore();
    result
}

async fn run(terminal: &mut ratatui::DefaultTerminal, args: Args) -> Result<()> {
    let mut app = app::App::new(args.theme);
    let mut transport = transport::connect(&args).await?;

    // Initialize handshake (Tier 2.1)
    transport.initialize().await?;

    let mut events = input::EventStream::new();

    loop {
        terminal.draw(|frame| ui::render(&app, frame))?;

        tokio::select! {
            Some(rpc_msg) = transport.recv() => {
                app.handle_rpc(rpc_msg);
            }
            Some(input_evt) = events.next() => {
                if let Some(action) = app.handle_input(input_evt) {
                    transport.send(action).await?;
                }
                if app.should_quit() {
                    return Ok(());
                }
            }
        }
    }
}

fn parse_args() -> Result<Args> {
    // 20 lines of clap or hand-rolled arg parsing
}
```

### `app.rs` (~250 lines)

Top-level App struct + RPC handler + input handler. The whole "reducer" lives here as plain methods, not an Elm-style enum.

```rust
impl App {
    pub fn handle_rpc(&mut self, msg: RpcMsg) {
        match msg {
            RpcMsg::ItemStarted { item } => self.on_item_started(item),
            RpcMsg::ItemCompleted { item_id, status, result } => self.on_item_completed(item_id, status, result),
            RpcMsg::ItemDelta { item_id, delta } => self.on_item_delta(item_id, delta),
            RpcMsg::TurnStarted { turn_id } => {
                self.turn_id = Some(turn_id);
                self.mode = Mode::Streaming {
                    spinner_verb: verbs::random(),
                    since: Instant::now(),
                };
            }
            RpcMsg::TurnCompleted { .. } => {
                self.mode = Mode::Idle;
                self.flush_turn_to_scrollback = true;
            }
            RpcMsg::ApprovalRequested { tool, args, request_id } => {
                self.mode = Mode::Approval { tool, args, request_id, options: APPROVAL_OPTS.to_vec(), cursor: 0 };
            }
            // ... rest
        }
    }

    pub fn handle_input(&mut self, evt: InputEvent) -> Option<RpcRequest> {
        match (&self.mode, evt) {
            (_, InputEvent::Key(k)) if is_quit(k) => { self.quit = true; None }

            (Mode::Idle | Mode::Streaming { .. }, InputEvent::Key(k)) if k == Key::CtrlK => {
                self.mode = Mode::Palette { filter: String::new(), matches: palette_all(), cursor: 0 };
                None
            }

            (Mode::Idle, InputEvent::Key(Key::Enter)) => {
                let text = self.composer.take();
                if text.is_empty() { return None; }
                Some(RpcRequest::TurnStart {
                    thread_id: self.thread_id.clone(),
                    input: text,
                })
            }

            (Mode::Streaming { .. }, InputEvent::Key(Key::CtrlJ)) => {
                let text = self.composer.take();
                if text.is_empty() { return None; }
                Some(RpcRequest::TurnSteer {
                    thread_id: self.thread_id.clone()?,
                    turn_id: self.turn_id.clone()?,
                    input: text,
                })
            }

            (Mode::Approval { .. }, InputEvent::Key(k)) => self.handle_approval_key(k),
            (Mode::Palette { .. }, InputEvent::Key(k)) => self.handle_palette_key(k),
            (Mode::Picker(_), InputEvent::Key(k)) => self.handle_picker_key(k),

            // text input goes to composer in Idle/Streaming
            (Mode::Idle | Mode::Streaming { .. }, InputEvent::Char(c)) => {
                self.composer.insert_char(c);
                None
            }

            _ => None,
        }
    }
}
```

### `ui.rs` (~500 lines)

Single file. Top-level `render` function dispatches by `Mode`. Each mode's render is a small function (~30-60 lines). No layout recursion deeper than 2 levels.

```rust
pub fn render(app: &App, frame: &mut Frame) {
    let area = frame.area();
    let theme = &app.theme;

    // Layout: header (3) | live area (rest) | composer (3) | status (1)
    let chunks = Layout::vertical([
        Constraint::Length(3),
        Constraint::Min(5),
        Constraint::Length(3),
        Constraint::Length(1),
    ]).split(area);

    render_header(frame, chunks[0], app, theme);
    render_live_area(frame, chunks[1], app, theme);
    render_composer(frame, chunks[2], app, theme);
    render_status_bar(frame, chunks[3], app, theme);

    // Overlays
    match &app.mode {
        Mode::Approval { .. } => render_approval_overlay(frame, area, app, theme),
        Mode::Palette { .. } => render_palette_overlay(frame, area, app, theme),
        Mode::Picker(_) => render_picker_overlay(frame, area, app, theme),
        Mode::Detail(_) => render_detail_overlay(frame, area, app, theme),
        _ => {}
    }
}

fn render_live_area(frame: &mut Frame, area: Rect, app: &App, theme: &Theme) {
    // Render history entries from bottom up, fitting as many as area allows
    let mut lines: Vec<Line<'static>> = Vec::with_capacity(area.height as usize * 2);
    for entry in app.history.iter().rev() {
        let entry_lines = entry.rendered_lines(area.width, theme);
        for line in entry_lines.into_iter().rev() {
            lines.push(line);
            if lines.len() > area.height as usize {
                break;
            }
        }
    }
    lines.reverse();

    // If streaming, append a spinner line at the bottom
    if let Mode::Streaming { spinner_verb, since } = &app.mode {
        let elapsed = since.elapsed();
        let spinner = spinner_frame(elapsed);
        lines.push(Line::from(vec![
            spinner.fg(theme.accent),
            " ".into(),
            (*spinner_verb).fg(theme.accent),
            "…".dim(),
        ]));
    }

    Paragraph::new(lines).render(area, frame.buffer_mut());
}
```

### `input.rs` (~150 lines)

```rust
pub struct TextBuf {
    chars: Vec<char>,
    cursor: usize,
}

impl TextBuf {
    pub fn insert_char(&mut self, c: char) {
        self.chars.insert(self.cursor, c);
        self.cursor += 1;
    }

    pub fn delete_back(&mut self) {
        if self.cursor > 0 {
            self.chars.remove(self.cursor - 1);
            self.cursor -= 1;
        }
    }

    pub fn take(&mut self) -> String {
        let s = self.chars.iter().collect();
        self.chars.clear();
        self.cursor = 0;
        s
    }

    pub fn render_visible(&self, max_width: usize) -> String {
        // Show last `max_width-2` chars + cursor block
        let visible_start = if self.chars.len() > max_width.saturating_sub(2) {
            self.chars.len() - (max_width - 2)
        } else { 0 };
        self.chars[visible_start..].iter().collect()
    }
}

pub struct EventStream {
    crossterm_events: EventStream,
}

impl EventStream {
    pub async fn next(&mut self) -> Option<InputEvent> {
        // Convert crossterm events to our minimal InputEvent enum
        // Filter out events we don't care about (mouse moves, etc.)
    }
}

pub enum InputEvent {
    Key(Key),
    Char(char),
    Resize(u16, u16),
}

pub enum Key {
    Enter, Backspace, Esc, Tab,
    Up, Down, Left, Right,
    CtrlC, CtrlD, CtrlK, CtrlJ, CtrlR, CtrlU,
    F(u8),
}
```

### `transport.rs` (~250 lines)

Thin RPC client. Speaks the Tier 2.1 protocol. Default stdio (spawns Python child). Optional `--connect=unix://...` or `--connect=ws://...`.

```rust
pub enum Transport {
    Stdio(StdioTransport),
    Unix(UnixTransport),
    WebSocket(WsTransport),
}

impl Transport {
    pub async fn initialize(&mut self) -> Result<ServerCapabilities> {
        let resp = self.call("initialize", json!({
            "client_name": "autocode-tui-min",
            "client_version": env!("CARGO_PKG_VERSION"),
            "protocol_version": "2.0",
            "capabilities": {
                "supports_approval_response": true,
                "supports_streaming_deltas": true,
            },
        })).await?;
        self.send_notification("initialized", json!({})).await?;
        Ok(serde_json::from_value(resp)?)
    }

    pub async fn call(&mut self, method: &str, params: Value) -> Result<Value> { ... }
    pub async fn send_notification(&mut self, method: &str, params: Value) -> Result<()> { ... }
    pub async fn recv(&mut self) -> Option<RpcMsg> { ... }
}
```

### `verbs.rs` — keep verbatim from current code

This is the one piece worth keeping unchanged. 187 verbs, `random()` function, no other complexity. `~200 lines`.

### `theme.rs` (~50 lines)

```rust
pub struct Theme {
    pub accent: Color,        // amber #cc7832
    pub primary: Color,       // bright text
    pub dim: Color,           // dim gray
    pub success: Color,       // green
    pub error: Color,         // red
    pub warning: Color,       // yellow
}

impl Theme {
    pub fn default() -> Self { /* claude-code amber */ }
    pub fn light() -> Self { /* light terminal background */ }
    pub fn dark() -> Self { /* dark terminal background */ }
}
```

---

## Performance budget

Hard targets:

| Metric | Current rtui | Target | How |
|---|---|---|---|
| Cold start to first frame | ~250 ms | < 80 ms | No `lazy_static`, no `tokio::full` features, prune deps |
| Resident memory at idle | ~85 MB | < 30 MB | Drop heavy crates (`portable-pty`, `shell-words` if not needed) |
| Frame time during streaming | ~8-12 ms | < 3 ms | Cache rendered Lines, redraw only on event |
| Redraw rate during streaming | ~60 Hz | 30 Hz | Lower poll rate; visually identical |
| Cells changed per frame during streaming | unknown | < 10 | Buffer diff verifies; benchmark in CI |
| Total binary size | ~2.2 MB | < 1.5 MB | `strip = true`, `lto = "fat"`, `codegen-units = 1` |
| LOC | ~7500 | < 1500 | Architectural rewrite |

### Cargo.toml for size

```toml
[package]
name = "autocode-tui-min"
version = "0.1.0"
edition = "2024"

[dependencies]
ratatui = { version = "0.29", default-features = false, features = ["crossterm"] }
crossterm = { version = "0.28", features = ["event-stream"] }
tokio = { version = "1", features = ["rt-multi-thread", "io-util", "process", "macros", "sync"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
anyhow = "1"
# NO portable-pty (use tokio::process::Command directly)
# NO tracing-subscriber (use eprintln! to stderr or a 50-line custom logger)

[profile.release]
opt-level = "z"          # optimize for size
lto = "fat"
codegen-units = 1
strip = true
panic = "abort"
```

---

## Migration plan

### Step 1: build `rtui-min` alongside `rtui`

Don't delete the old TUI. Add the new one as `rtui-min/` at the repo root. Both build, both can be installed:

```bash
cd autocode/rtui && cargo build --release        # old, ~2.2 MB
cd autocode/rtui-min && cargo build --release    # new, target < 1.5 MB
```

User selects via `AUTOCODE_TUI_BACKEND=min` env var.

### Step 2: ship behind opt-in flag

Document `AUTOCODE_TUI_BACKEND=min` in README. Encourage early adopters to try it. Collect feedback.

### Step 3: parity sweep

Two weeks of bug reports. Fix what's missing. Don't add features that aren't in the old TUI yet — Tier 6 is a rewrite, not a feature push.

### Step 4: flip default

After parity is reached and old TUI shows no advantage:
- Change default to `min`
- Old TUI accessible via `AUTOCODE_TUI_BACKEND=legacy`

### Step 5: deprecate old

After 2 minor versions on `min` as default with no regressions, delete `rtui/` and rename `rtui-min/` to `rtui/`.

---

## What `rtui-min` deliberately does NOT have

To stay under 1500 LOC, the rewrite drops these features (some can come back later):

- **No mouse support** — keyboard-only. (Can add later as ~100 LOC.)
- **No multiple themes from config file** — three hard-coded: default, light, dark. (Can add later.)
- **No `--altscreen` flag** — inline mode only. (Most users prefer it; if needed, ~30 LOC.)
- **No editor launch (`Ctrl+E`)** — drop until someone asks. (~150 LOC saved.)
- **No clipboard support** — terminal-native paste only. (~80 LOC saved.)
- **No PTY subprocess spawning** — uses plain `tokio::process::Command`. The complex PTY handling in current rtui is for the backend, which doesn't need full PTY semantics. (~400 LOC saved.)
- **No detail surfaces beyond Tasks/Plan/Diff** — Grep/Restore/CommandCenter dropped. (Can re-add as plugins later.)

The Pareto principle: 80% of the value at 20% of the LOC.

---

## Acceptance tests

```rust
// tests/render_snapshots.rs

#[test]
fn idle_input_renders_correctly() {
    let app = App::new(Theme::default());
    let backend = TestBackend::new(80, 20);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| ui::render(&app, f)).unwrap();

    let buffer = terminal.backend().buffer();
    insta::assert_snapshot!(buffer_to_string(buffer));
}

#[test]
fn streaming_shows_rotating_verb() {
    let mut app = App::new(Theme::default());
    app.mode = Mode::Streaming {
        spinner_verb: "Pondering",
        since: Instant::now(),
    };
    let backend = TestBackend::new(80, 20);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| ui::render(&app, f)).unwrap();

    let s = buffer_to_string(terminal.backend().buffer());
    assert!(s.contains("Pondering"));
    assert!(s.contains("…"));
}

#[test]
fn approval_overlay_blocks_input() {
    let mut app = App::new(Theme::default());
    app.mode = Mode::Approval {
        tool: "run_command".into(),
        args: json!({"command": "rm -rf /"}),
        request_id: 42,
        options: vec!["Yes", "No"],
        cursor: 1,
    };
    // typing into composer should NOT change composer in Approval mode
    let result = app.handle_input(InputEvent::Char('a'));
    assert!(result.is_none());
    assert_eq!(app.composer.len(), 0);
}

#[test]
fn render_perf_cells_changed_under_10_during_streaming_delta() {
    let mut app = make_streaming_app();
    let mut backend = TestBackend::new(80, 20);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| ui::render(&app, f)).unwrap();
    let buf_before = terminal.backend().buffer().clone();

    // Apply small streaming delta
    app.on_item_delta("item-1".into(), "x".into());

    terminal.draw(|f| ui::render(&app, f)).unwrap();
    let buf_after = terminal.backend().buffer();

    let cells_changed = count_diff_cells(&buf_before, buf_after);
    assert!(cells_changed < 10, "Expected < 10 cells changed, got {}", cells_changed);
}
```

---

## Why this is achievable

OpenCode shipped its TUI in Bubble Tea (Go) at roughly comparable size. Codex's TUI in `codex-rs/tui/` is larger but it's also got more features (multi-thread, transcript overlay, plugin marketplace UI). Hermes Agent's React-Ink TUI is ~3000 LOC with markdown rendering and virtualized history. None of these projects spent 7500 LOC on the TUI alone.

The current rtui's size is a local maximum from organic growth, not an architectural requirement. A clean rewrite in 1500 LOC is achievable because:

1. The protocol (Tier 2.1) absorbs the per-event-type complexity
2. Caching `Lines<'static>` per history entry eliminates the partial-rendering hacks
3. One `Mode` enum replaces the 9-stage × 9-detail-surface combinatorial tree
4. `terminal.insert_before` for completed turns means live area shrinks dramatically

---

## Risks

| Risk | Mitigation |
|---|---|
| Rewrite takes longer than 3 weeks | Step 1-2 ship in week 1; user sees option early. Slippage acceptable on parity sweep. |
| Users prefer old TUI | Keep both. Default doesn't flip until parity reached + telemetry shows usage shift. |
| Performance numbers don't materialize | Run benchmark in CI gating merge. If targets miss, treat as bug not as ship-blocker. |
| Some weird corner case (e.g., utf-16 surrogates in composer) breaks | TestBackend snapshot tests catch most. Property-based tests (`proptest`) for input handling. |
| App Server protocol (Tier 2.1) isn't ready | Rewrite waits. Don't do Tier 6 before Tier 2.1. |

---

## Counterargument: don't rewrite, refactor

A reasonable alternative: keep the current `rtui/`, but delete half of it. Specifically:

- Replace `view.rs`'s 9 × 9 match arms with one widget-per-mode pattern: ~−2000 LOC
- Collapse 44 RPC structs to 3 primitives via Tier 2.1: ~−500 LOC
- Cache `Lines<'static>` per entry: ~−400 LOC of streaming buffer hacks

Total reduction: ~−2900 LOC, ending at ~4600 LOC. Less than the rewrite target of 1500, but no risk of behavioral regression.

**Pick rewrite if:** the team is comfortable with the rewrite, wants the binary-size and startup-time wins, and wants to retire the legacy TUI for good.

**Pick refactor if:** stability matters more than size, and the team prefers incremental improvement to a clean break.

Both are correct. The roadmap lists rewrite because OpenCode/Codex/Hermes all chose rewrites at similar sizes and reported the gains were worth it. But refactor is a defensible choice.

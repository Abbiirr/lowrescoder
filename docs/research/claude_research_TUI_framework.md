# Go Bubble Tea is the best stack for a Claude Code competitor

**Go with Charm's Bubble Tea framework is the clear winner** for building an inline TUI coding agent that meets all stated constraints. It offers the rare combination of inline-mode rendering, concurrent streaming architecture, single-binary distribution, cross-platform Windows/Linux support, and a proven track record powering real AI coding tools — all without JavaScript or Rust. Python Textual is a strong second choice if you can tolerate its Windows inline-mode gap and distribution overhead. C++ FTXUI is the dark horse for maximum performance at higher development cost.

This recommendation is grounded in how the existing competitors actually work: Claude Code, Codex CLI (original), and Gemini CLI all use React + Ink (JavaScript) — the very thing you're avoiding. Codex CLI rewrote to Rust + Ratatui for performance. The Go-based OpenCode already proves Bubble Tea works for this exact use case.

---

## How the competitors actually build their TUIs

Understanding what you're up against clarifies the design space. **Claude Code uses TypeScript + React + Ink** with Yoga (Meta's Flexbox engine) for layout. Its founding engineer Boris Cherny described Ink as "amazing but sort of hacky and janky," comparing cross-terminal ANSI compatibility to "building for Internet Explorer 6 versus Opera." Ink redraws the entire terminal on state changes — fast on Ghostty, problematic on slower emulators.

**Codex CLI started with the same Ink stack, then rewrote entirely to Rust + Ratatui.** The migration, announced June 2025, was motivated by zero-dependency installation (eliminating the Node v22+ requirement), native sandboxing, and rendering performance. The Rust version uses Ratatui's inline viewport mode with immediate-mode double-buffered rendering, achieving sub-millisecond frame times. As of early 2026, the Rust version (v0.97.0) is the default. **Gemini CLI** also uses React + Ink. **Aider** takes the simplest path — Python prompt_toolkit for input plus Rich for formatted output, in a basic REPL style without a full-screen TUI.

The tool most architecturally relevant to your project is **OpenCode**, a Go-based AI coding agent built entirely on Bubble Tea + Lip Gloss. It demonstrates that the Charm ecosystem can power a production coding agent with streaming, session management, LSP integration, and vim-like editing.

---

## Go Bubble Tea delivers the best balance of every requirement

Bubble Tea implements **The Elm Architecture** (Model-Update-View), where the entire UI state lives in a single model struct, messages drive state transitions through `Update()`, and `View()` renders the full screen as a string. This sounds expensive but works brilliantly: the renderer maintains a framerate-limited loop that diffs consecutive string outputs and emits only changed ANSI sequences — no flicker, no redundant draws.

**Streaming LLM output while keeping input responsive** is architecturally natural. User keystrokes arrive as `tea.KeyMsg` through a dedicated stdin-reading goroutine. LLM tokens arrive as custom messages via `tea.Cmd` goroutines or thread-safe `p.Send()` calls from external goroutines. Both feed into a single message channel, processed sequentially in `Update()` (which should be fast — just state mutations), then rendered at the next frame tick. You never block input while streaming. Charm's own **mods** tool (an AI CLI chat app) proves this pattern works, using a state machine (`startState → requestState → responseState → doneState`) with a viewport for glamour-rendered Markdown output.

The **fixed input bar + scrollable output** layout composes cleanly:

```go
func (m model) View() string {
    header := renderStatusBar(m)
    inputBar := m.textInput.View()
    m.viewport.Height = m.termHeight - lipgloss.Height(header) - lipgloss.Height(inputBar)
    return lipgloss.JoinVertical(lipgloss.Top, header, m.viewport.View(), inputBar)
}
```

Terminal resize events arrive as `tea.WindowSizeMsg`, triggering recalculation of the viewport dimensions. The viewport component handles scrolling, `GotoBottom()` for auto-scroll during streaming, and keyboard navigation. Bubbletea ships with a `examples/chat` demonstrating exactly this pattern.

**Command autocomplete** uses the textinput bubble's built-in `SetSuggestions()` and `ShowSuggestions` API for ghost-text completion. For a full dropdown with arrow-key navigation (slash commands), compose a custom overlay using the `list` bubble — the Inngest team documented this exact pattern in their CLI. Multi-stage permission prompts work as a simple state machine in your model, switching between `stageInput`, `stageConfirmPermission`, and `stageExecuting` states that each render different UI. Charm's **Huh** forms library provides ready-made confirmation prompts.

**Windows support** works on Windows 10+ with Windows Terminal. A flickering regression in v0.26.0 was fixed in PR #1132 by switching from line-erasing to overwriting. The main limitation is that Windows lacks `SIGWINCH` for resize events — the framework uses polling as a workaround. Cross-compilation is trivial: `GOOS=windows GOARCH=amd64 go build` produces a Windows binary from any platform, yielding a **single ~10-15MB binary with zero external dependencies**.

---

## Python Textual solves Rich's problems but has critical gaps

Textual directly addresses the parallel rendering limitations you hit with Rich. Where Rich writes sequentially to stdout and blocks interleaved input, **Textual runs each widget in its own asyncio task** with a full event loop, message-passing system, and compositor that can update individual screen regions — even single characters — without redrawing everything. The `Workers` API (`@work` decorator) launches background tasks that safely update the UI via `call_from_thread()`.

Will McGugan has personally optimized Textual's **Markdown streaming specifically for LLM output**. The key insight: only the last block of the Markdown document is re-parsed when new tokens arrive, avoiding O(n) re-rendering. When tokens arrive faster than they can display, they're buffered and concatenated. "The display is only ever a few milliseconds behind the data itself." His **Toad** application — a universal front-end for AI coding agents — proves Textual can power exactly the kind of tool you're building, with streaming Markdown, fuzzy file search, slash commands, and session management.

The component library maps perfectly to your needs: `Input` widget with `Suggester` for autocomplete, `RichLog` with `auto_scroll` for streaming output, `ModalScreen` for permission prompts, CSS `dock: bottom` for fixed input bars, and a built-in `CommandPalette` (Ctrl+P) with fuzzy search.

However, three limitations are significant:

- **Inline mode does not work on Windows.** This is documented explicitly. Toad runs on "Linux and macOS" — Windows isn't mentioned. For a cross-platform coding agent, this is a serious gap.
- **Startup time is ~100-300ms** versus ~5-10ms for a Go binary. For a CLI tool invoked repeatedly, this lag is perceptible.
- **Distribution requires Python** (or a 50-180MB PyInstaller bundle). The `uv tool install` workflow mitigates this for developers, but it's still more friction than downloading a single binary.

If your user base is primarily Linux/macOS developers who already have Python, Textual is excellent. If Windows is a hard requirement with inline mode, Textual cannot deliver today.

---

## The C/C++ and alternative language landscape

**FTXUI** is the standout C++ option — a modern, zero-dependency C++17 library with a React-inspired functional API. Its three-module architecture (screen, dom, component) provides declarative layouts (`vbox`, `hbox`, `flexbox`), pre-built interactive components (Input, Menu, Dropdown, Modal), and diff-based rendering. It fully supports Windows, Linux, macOS, and even WebAssembly. Actively maintained by ArthurSonzogni with regular releases through v6.1.9. The development effort is **3-5x higher than Go** due to C++ build complexity, memory management, and cross-platform toolchain setup — but the performance ceiling is the highest of any option.

**notcurses** offers raw rendering power with thread-safe z-ordered planes, 24-bit color, and multimedia support, but comes with a complex C API, questionable Windows support (requires MSYS2 UCRT64), and maintenance concerns (a two-year development gap from late 2022 to October 2024). **ncurses + PDCurses** is the classic approach — battle-tested but dated, requiring two separate libraries for cross-platform support and offering no high-level layout system.

**Zig's libvaxis** is production-ready (used by Ghostty) with cross-platform support including Windows, but Zig itself is pre-1.0 (v0.15.x), meaning language-level breaking changes remain possible. **Nim's illwill** provides basic double-buffered rendering with non-blocking input but has no widget ecosystem and a small community.

A critical insight from the performance research: **no formal benchmarks exist comparing TUI framework rendering speeds** because the bottleneck is always the terminal emulator's rendering, not the framework's diff calculation. Textual achieves 60fps in Python. Ratatui claims sub-millisecond frame times. For streaming ~50-100 LLM tokens per second, any modern framework is trivially fast enough. The real performance differentiators are **startup time** (compiled languages win) and **memory footprint** (Rust/C++ at ~5-10MB, Go at ~10-15MB, Python at ~35-50MB).

---

## Go tview has great widgets but a fatal flaw

Go's tview deserves mention for its **significantly richer built-in widget set** — 15+ components including InputField with native autocomplete dropdown, TextView implementing `io.Writer` for thread-safe streaming, Flex/Grid layouts, DropDown, Modal, TreeView, and Form. The streaming pattern is elegantly simple: `fmt.Fprint(textView, chunk)` from any goroutine, since TextView is thread-safe. The Flex layout trivially creates fixed-height input bars with proportional scroll areas.

**However, tview cannot do inline mode.** It exclusively uses the alternate screen buffer (full-screen takeover). The Bubble Tea creator explicitly noted this as the reason they built their own framework. For an inline TUI coding agent that renders within the existing terminal session — the way Claude Code works — **tview is architecturally unsuitable**. If you're willing to accept full-screen mode (which many users prefer for focused coding sessions), tview's superior widgets and simpler streaming API make it genuinely compelling.

---

## Recommended architecture for a Bubble Tea coding agent

Based on all the research, here is the concrete architecture that satisfies every stated requirement:

**Model structure** — a root model composing child bubble components:

- `viewport.Model` for scrollable AI output with auto-scroll and Glamour-rendered Markdown
- `textinput.Model` for the fixed input bar with `SetSuggestions()` for slash-command autocomplete
- A custom overlay list for arrow-key navigable command menus
- `spinner.Model` for generation indicators
- A `stage` enum for multi-stage flows (input → streaming → permission → executing)
- An `[]Message` slice for conversation history

**Streaming pattern** — external goroutine with thread-safe message injection:

```go
go func() {
    stream := anthropicClient.Stream(ctx, prompt)
    for token := range stream.Tokens() {
        p.Send(tokenMsg(token))
    }
    p.Send(streamDoneMsg{})
}()
```

**Flicker-free rendering** — Bubble Tea's default renderer overwrites previous frame content line-by-line using `EraseLineRight`, avoiding the blank-frame flicker that clearing causes. For inline mode (rendering within terminal scrollback rather than alternate screen buffer), omit `tea.WithAltScreen()`.

**Windows compatibility** — target Windows Terminal (default on Windows 11, available on 10). Use polling-based resize detection since Windows lacks `SIGWINCH`. Test with `GOOS=windows go build` cross-compilation. The v0.26+ flicker fix ensures clean rendering.

**Distribution** — single static binary per platform via `go build`. Typical size **~10-15MB** (strippable to ~7MB with `-ldflags="-s -w"`). Zero runtime dependencies. Cross-compile for all targets from a single CI machine.

---

## Final verdict and framework ranking

Given the hard constraints (no JavaScript, no Rust, cross-platform Windows + Linux), here is the definitive ranking:

| Rank  | Framework      | Language | Best for                             | Key tradeoff                                  |
| ----- | -------------- | -------- | ------------------------------------ | --------------------------------------------- |
| **1** | **Bubble Tea** | Go       | All-around winner                    | Requires manual layout composition            |
| **2** | **Textual**    | Python   | Fastest development, richest widgets | No Windows inline mode, distribution friction |
| **3** | **FTXUI**      | C++      | Maximum native performance           | 3-5x development effort                       |
| **4** | **tview**      | Go       | Best widgets/autocomplete            | No inline mode (full-screen only)             |
| **5** | **libvaxis**   | Zig      | Bleeding-edge performance            | Pre-1.0 language, small ecosystem             |

**Go Bubble Tea is the recommendation.** It uniquely satisfies every hard constraint: inline mode rendering, concurrent streaming without blocking input, cross-platform including Windows, single-binary distribution, proven in production AI coding tools (OpenCode, mods), and a rich ecosystem (Bubbles components, Lip Gloss styling, Glamour Markdown, Huh forms). The Elm Architecture enforces clean unidirectional data flow that scales well as your agent's UI complexity grows. You'll build the layout manually rather than using tview's declarative Flex — but the tradeoff is inline mode support, which is non-negotiable for matching Claude Code's terminal experience.

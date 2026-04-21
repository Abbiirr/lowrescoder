# TUI Testing Strategy — Definitive Guide

**Scope:** all interactive terminal UI testing in this repo — Rust TUI (`autocode-tui`), Textual fullscreen, any terminal-driven interactive path. This file is the single source of truth for **TUI testing** (not unit tests).

**Unit tests are not in scope for this doc.** They're required but separate; cover them in focused `*_test.rs` / `test_*.py` files. This doc is about proving the interactive terminal surface actually works.

---

## Contents

1. [Four Testing Dimensions](#1-four-testing-dimensions) — the matrix
2. [Rust TUI Binary Resolution](#2-rust-tui-binary-resolution) — how harnesses find the binary
3. [Required Validation Matrix](#3-required-validation-matrix) — the checklist for every TUI change
4. [Command Surface Discoverability](#4-command-surface-discoverability) — slash autocomplete, arrow pickers, palette
5. [Do Not Confuse The Dimensions](#5-do-not-confuse-the-dimensions)
6. [Policies](#6-policies) — VHS rebaseline, review gate, commit discipline
7. [PTY Patterns](#7-pty-patterns) — pty.fork() recipe + escape sequences
8. [Required Test Layers](#8-required-test-layers)
9. [Exit Gates and Reporting](#9-exit-gates-and-reporting)
10. [Sub-harness Pointers](#10-sub-harness-pointers)
11. [Triage — Red Test Workflow](#11-triage--red-test-workflow)
12. [Adding a New Test Scenario](#12-adding-a-new-test-scenario)
13. [Common Pitfalls](#13-common-pitfalls)

---

## 1. Four Testing Dimensions

The repo has four complementary TUI test dimensions. Each answers a different question. Use the right one for the change you made.

| # | Dimension | Question | Entry command | Substrate |
|---|---|---|---|---|
| 1 | **Runtime invariants** (Track 1) | Does the TUI start, accept input, render correctly, not leak debug state? | `make tui-regression` | `autocode/tests/tui-comparison/` |
| 2 | **Design-target ratchet** (Track 4) | Does the live TUI render the layout the mockup bundle specifies? Each scene is `strict=True` xfail that flips to a hard gate when the matching UI feature ships. | `make tui-references` | `autocode/tests/tui-references/` |
| 3 | **Self-vs-self PNG regression** (VHS) | Did today's TUI render pixel-identical to yesterday's committed baseline? | `uv run python autocode/tests/vhs/run_visual_suite.py` | `autocode/tests/vhs/` |
| 4 | **PTY smoke** (live binary + backend) | Does the real binary + real backend path work end-to-end in a real terminal? | `uv run python autocode/tests/pty/<script>.py` | `autocode/tests/pty/` |

### When to use which

- **Runtime regression** (crash / composer / warnings / pickers / queues / spinner) → Track 1
- **Implementing a UI feature that matches a mockup scene** → Track 4 (XPASS is the "done" signal — flip the `xfail` off)
- **Layout / color / palette / alt-screen / scrollback change** → VHS self-regression (commit new baseline or prove no drift)
- **Backend/TUI JSON-RPC contract or startup timeout change** → PTY smoke
- **Any feature the user will touch** → at minimum a PTY smoke plus the Track/VHS dimension matching what changed

### Architecture source of truth

`PLAN.md §1g` documents all four tracks end-to-end. This doc is the operational guide.

---

## 2. Rust TUI Binary Resolution

**Canonical path:** `autocode/rtui/target/release/autocode-tui`

All four dimensions accept `$AUTOCODE_TUI_BIN` as an override. **Current harness state (2026-04-20):**

| Harness | Auto-resolves Rust binary? | Notes |
|---|---|---|
| Track 1 launcher (`tui-comparison/launchers/autocode.py`) | ✅ yes | Resolution order: env → `autocode/rtui/target/release/autocode-tui` → PATH |
| Track 4 (`tui-references/`) | ✅ yes | Defaults to `autocode/rtui/target/release/autocode-tui`; env override still supported |
| VHS (`vhs/run_visual_suite.py`) | ✅ yes | Defaults to `autocode/rtui/target/release/autocode-tui`; env override still supported |
| PTY smokes (`tests/pty/*.py`) | ✅ yes | `pty_smoke_rust_m1.py`, `pty_smoke_rust_comprehensive.py`, and `pty_e2e_real_gateway.py` all resolve the Rust binary path |

**Until Track 4 / VHS are retargeted, always set the env var:**

```bash
export AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui
```

**Target resolution order (every harness should eventually use this):**

1. `$AUTOCODE_TUI_BIN` env override
2. `autocode/rtui/target/release/autocode-tui` (package-relative)
3. `autocode-tui` on PATH

**Build:**

```bash
cd autocode/rtui && cargo build --release
```

**Why this matters:** cross-harness drift investigation is meaningless if different harnesses are running different binaries. If Track 1 passes but VHS shows drift, first check: are they pointing at the same binary? Use `ls -l` on the resolved path.

---

## 3. Required Validation Matrix

Run every item below for every TUI change unless the user explicitly waives it. If you cannot run a check, state the blocker explicitly — do not silently skip.

### 3.0 Visible Surface Rule (recurring Rust-TUI failure mode)

Every modal, picker, palette, banner, and message produced by the TUI must have **visible terminal output** that a user would see. "Reducer state advanced to Stage::Picker" is not sufficient — the captured terminal frame must contain the renderable content the user would interact with.

Apply this rule to:

- every picker (§3.4) — **visible header + list of options + filter indicator + selection marker**, not just a `Picker>` prompt
- every palette (§3.3, §4.2) — **visible command entries + filter state**, not just a `Palette>` prompt
- every modal (§3.11 ask-user, §3.12 approval) — **visible question / options / hotkey hints**
- every banner (§3.1 startup timeout, §3.6 warnings, §3.13 error banner) — **visible dim or error line**

A PTY capture or VHS scene that only shows the prompt label is a failed test even if internal state is correct. Codex Entry 1262 documented four concrete examples of this failure mode on the current Rust tree.

### 3.1 Startup Path

Prove the real entrypoint starts into a usable state.

- binary starts → reaches a usable prompt / header / explicit timeout fallback
- no panic, traceback, or dead start
- no malformed ANSI leaked during boot
- raw mode restored cleanly on crash (`RawModeGuard` Drop covers this)
- **silent-backend path:** when backend never sends `on_status`, the TUI must render a **visible** timeout banner (e.g. "backend unresponsive") — not just a blank screen. Use `tests/pty/silent_backend.py` fixture.

Evidence: PTY transcript via `pty.fork()` + mock backend, plus a second run against `silent_backend.py` showing the timeout banner.

### 3.2 Basic Chat Turn

Prove a normal user turn still works.

- **the user's submitted message is echoed into scrollback** (visible transcript of what they typed, not just the assistant reply)
- assistant output appears in the scrollback/inline region
- turn returns to a usable input state
- no unexpected picker or modal after the turn
- streaming tokens visible during, flushed to scrollback on `on_done`
- a fresh user scrolling back through the terminal must see the full conversation: user turn, assistant turn, user turn, assistant turn — in order

### 3.3 Slash Command Surface (see §4 for the full discoverability spec)

Prove command routing and discovery work. Apply the §3.0 visible-surface rule.

- typing `/` alone must surface the **visibly-rendered** inline autocomplete dropdown — PTY capture must show ≥5 command names (§4.4)
- arrow keys navigate the dropdown; Enter/Tab completes
- Escape closes the dropdown without submitting
- `/help`, `/model`, `/plan`, `/fork`, `/clear`, `/exit` all route correctly when invoked directly
- **Ctrl+K palette must render visible entries and filter state**, not just a `Palette>` prompt. PTY capture must contain at least 3 command names + filter indicator when a filter is typed.

### 3.4 Picker Surface (model / provider / session)

Prove arrow-key pickers open, filter, and select. **Text dumps + "type this alias" are unacceptable** — memory rule, user-affirmed. Apply the §3.0 visible-surface rule.

PTY capture of an open picker must contain:

- a **visible header** (e.g. `Select a model:`)
- the **visible list of options**, not just a `Picker>` prompt
- a **filter state indicator** when any filter is typed (e.g. `[filter: cod|]`)
- a **selection cursor** or inverse-video marker on the focused row

Functional requirements:

- `/model` → opens arrow-navigable picker populated from backend `model.list` RPC (current Rust tree does NOT request this — known gap)
- typing in the picker filters case-insensitively
- `↑` / `↓` navigate visible entries; Enter selects
- first `Escape` clears filter if non-empty; second Escape exits
- filter state resets on re-open
- Same for `/provider`, `/sessions` / `/resume`

### 3.5 Keyboard Interaction

Prove control keys behave correctly.

- **Enter** submits at end of line; in multi-line splits at cursor
- **Alt+Enter** inserts newline
- **Backspace** / **Delete** edit composer; merge lines when at line start
- **↑** / **↓** browse frecency-ranked history in `Stage::Idle`
- **Ctrl+C** state machine (see M8 spec):
  - `Stage::Idle` → sends `cancel` RPC, does NOT quit
  - `Stage::Streaming` (first press) → enters steer mode
  - `Stage::AskUser` (in steer) → cancel steer, back to streaming
  - Triple-press in quick succession → hard quit
- **Ctrl+K** → command palette
- **Ctrl+E** → external editor (EDITOR env var); tempfile round-trip; raw mode restored on return
- **Escape** closes pickers/palette/modals cleanly; never re-enters an unrelated stage

### 3.6 Warning / Error Rendering

Prove backend stderr and runtime errors render with correct severity. Apply the §3.0 visible-surface rule.

- **backend warnings must be visibly rendered** as dim scrollback lines — absence of red is not sufficient; they must actually appear. A warning that is silently dropped is a failure.
- real errors surface with `Error:` banner (red, bold)
- no raw traceback / panic text leaks into the happy path
- mandatory for any backend/TUI notification contract change
- PTY fixture: use `tests/pty/mock_backend.py` with `__WARNING__` trigger to emit a warning mid-chat; capture must contain the warning text on a dim line, not a red banner.

### 3.7 Queue / Streaming / Interrupt Cleanliness

Prove the TUI never leaks internal state into visible output.

- no debug / queue / spinner junk text in chat output
- no duplicate or stuck spinner after turn end
- cancel / steer / followup stay coherent when touched
- bracketed paste inserts text at cursor, doesn't execute control sequences
- sliding-window flush keeps scrollback bounded (10k line cap)

### 3.8 Narrow / Real Terminal Constraints

Prove layout survives real geometry.

- run at least one ~60-column narrow capture
- no catastrophic wrapping, no invisible prompt, no broken status bar
- resize (`SIGWINCH` / PTY resize) redraws without corruption
- scrollback preserved across resize

### 3.9 Inline vs Alt-Screen

- default (inline): no `?1049h` alt-screen enter; prior terminal content preserved above
- `--altscreen`: alt-screen on entry, primary buffer restored on exit
- `ScreenGuard` drop restores terminal on panic for both modes

### 3.10 Changed-Feature Regression

Prove the feature you actually changed works in the live TUI, not just a unit test.

- run the smallest real scenario that exercises the exact path
- assert on visible behavior, not internal state
- include ≥1 regression assertion for the failure mode you fixed

### 3.11 Ask-User Modal (visible surface)

When backend sends `ask_user` RPC, the TUI must render a visible modal that includes:

- the **question text** exactly as provided
- the **options list** (if non-empty) with a selection cursor on the focused row
- the **free-text input field** (if `allow_text=true`) with a visible `?` prompt
- hotkey hints if non-trivial (e.g. `↑/↓ to navigate, Enter to select, Esc to cancel`)

PTY capture of `ask_user` state must contain the question string. A blank capture = test failure.

Trigger: `tests/pty/mock_backend.py` responds to `__ASK_USER__` in the user message with an ask_user request.

### 3.12 Approval Modal (visible surface)

When backend sends an approval request (tool call requiring user consent), the TUI must render a visible modal that includes:

- the **tool name**
- a readable **args snippet** (truncated if long, but visibly present)
- the **hotkey hints**: `[Y] Approve / [N] Deny / [A] Always-allow`

Functional:
- `y` / `Y` / Enter → `approved=true`, `session_approve=false`
- `a` / `A` → `approved=true`, `session_approve=true`
- `n` / `N` / Escape → `approved=false`
- RPC response id correlates with the inbound request id

### 3.13 Error Banner (visible surface)

- `on_error` notification → visible `Error:` banner in red/bold, not silent state flip
- banner persists until next successful turn OR user-initiated clear
- does not obscure the composer

### 3.14 Persistence Paths

Files the TUI writes/reads under `~/.autocode/`:

- `history.json` — frecency-ranked input history; load on startup, write after each `on_done`
  - ☐ malformed file does not crash TUI (fallback to empty history)
  - ☐ concurrent writes don't corrupt (atomic write pattern: tmp + rename)
  - ☐ entries bounded (no unbounded growth)
- `tui.log` — tracing output; never mixed with stdout
  - ☐ file-only sink for `tracing-subscriber`
  - ☐ no log line appears in terminal output
- session files via backend → covered by `session.resume` flow

### 3.15 Shutdown and Exit Paths

Every exit path must leave the terminal in a clean state (raw mode off, cursor visible, alt-screen restored if entered).

| Trigger | Expected | Risk |
|---|---|---|
| `/exit` | clean exit code 0, terminal restored | lose raw mode if Drop missed |
| Triple Ctrl+C | hard quit via Effect::Quit | may not flush PTY child reader |
| Backend EOF | `Event::BackendExit` → Stage::Shutdown → Quit | child process must not orphan |
| SIGTERM from parent | crossterm's signal handling + Drop guards | tests via `kill -TERM <pid>` |
| SIGINT from parent | same as Ctrl+C path | |
| Panic | `RawModeGuard::drop` + `ScreenGuard::drop` restore | MUST restore cursor visibility |

- ☐ Test each exit path leaves `stty -a` showing `echo` and cooked mode
- ☐ No orphan child processes (verify with `pgrep -P <shell_pid>` after exit)
- ☐ Exit code matches expectation (0 for clean, nonzero for error paths)

### 3.16 Backend Failure Modes

Five different failure classes. Each must have explicit handling + visible UI feedback.

| Failure | Fixture | Expected TUI behavior |
|---|---|---|
| Backend never starts | exec nonexistent command | clear startup error, exit nonzero |
| Backend starts but silent | `tests/pty/silent_backend.py` | timeout banner within 15s (§3.1) |
| Backend crashes mid-chat | `tests/pty/dead_backend.py` or stream then exit | `Event::BackendExit` → visible error + Shutdown |
| Backend sends malformed JSON | inject non-JSON line | warn in log, continue (do not panic) |
| Backend sends 1MB+ line | stream large tool-call result | LinesCodec / BufReader delivers intact (§M1 spike) |
| Gateway auth failure | invalid LITELLM_MASTER_KEY | `on_error` with auth message visible |

- ☐ At least two of the above tested in PTY harness per TUI change

### 3.17 Performance Budget

From M10 perf gates. Any TUI change must not regress these:

| Metric | Target | How to measure |
|---|---|---|
| First-token render latency | < 50 ms (current ~5 ms) | timestamp between `on_token` RPC in and render |
| Keystroke-to-render | < 16 ms (current < 1 ms) | keypress timestamp to visible update |
| Idle CPU | < 1% (current ~0%) | `top -p <pid>` during idle for 30s |
| Memory RSS | < 50 MB (current ~15 MB) | `ps -o rss` during active session |
| Startup time (`--version`) | < 200 ms (current 2 ms) | `time autocode-tui --version` |
| Binary size | < 10 MB (current 2.4 MB) | `ls -lh` on release binary |

- ☐ If the change touches the hot path, measure before/after
- ☐ Otherwise assert targets still met via M10 artifact

### 3.18 Terminal Compatibility

Known-good terminals (from M10 matrix): xterm-256color, kitty, alacritty, gnome-terminal, tmux, Ghostty.

- ☐ No `TERM=dumb` crash (graceful degrade)
- ☐ Color output on 256-color terminals; mono-safe fallback on `TERM=vt100`
- ☐ Unicode characters (braille spinner, arrows) render on UTF-8 terminals
- ☐ Status bar characters don't leak escape codes as literal text

### 3.19 Long-Session Behavior

- ☐ Scrollback bounded — `VecDeque<StyledLine>` cap at 10,000 lines (see `state/model.rs`)
- ☐ Over-cap lines evicted from front (oldest first)
- ☐ Memory stable over 100+ turns (no unbounded growth)
- ☐ History file size bounded
- ☐ Spinner state reset correctly on each turn

### 3.20 Logging Boundary (CRITICAL)

Violating this corrupts the JSON-RPC protocol — stdout is the RPC channel.

- ☐ `grep -rn "println!" autocode/rtui/src/` returns zero non-test hits
- ☐ `grep -rn "eprintln!" autocode/rtui/src/` — any occurrence must be justified (pre-crash only, never normal path)
- ☐ `tracing-subscriber` configured with file-only sink — not stdout
- ☐ PTY artifact contains clean JSON-RPC stream on stdout; log spew goes to file
- ☐ Startup message `tracing::info!("autocode-tui starting")` appears in `~/.autocode/tui.log`, NOT stdout

### 3.21 Followup Queue + Markdown

- ☐ Enter while streaming queues the message (does not send immediately)
- ☐ Queued messages drain on `on_done` — one per turn in FIFO order
- ☐ Queue visible to user (banner or count), not invisible
- ☐ Inline markdown renders: `` `code` `` (bold+contrast), `**bold**`, `*italic*`, `[link](url)`
- ☐ Block markdown (headers, lists) NOT expected in M9 scope — document if needed

### 3.22 Cost / Token Counter (status bar)

- ☐ `on_cost_update` notification updates `state.status.cost`; visible in status bar
- ☐ `on_done` updates `tokens_in` / `tokens_out`; visible as `N↑M↓`
- ☐ Cost string format preserved from backend (e.g. `$0.0042`)
- ☐ Accumulates across turns, does not reset each turn

---

## 4. Command Surface Discoverability

**Goal:** parity with Claude Code / OpenCode. Typing `/` must reveal, not hide.

### 4.1 Inline slash autocomplete dropdown (user-visible requirement)

When the user types `/` at the start of the composer with no other content:

- an inline dropdown appears directly above the composer listing **all available slash commands**
- each entry: `<command-name>  <one-line description>`
- typing more characters filters the list case-insensitively (substring match on name)
- `↑` / `↓` move the selection cursor
- **Enter** or **Tab** completes the selected command into the composer
- `Esc` closes the dropdown without submitting; composer keeps whatever was typed
- closing the dropdown does not execute

This is the single most-asked-for discoverability feature and is what distinguishes the TUI from a bare REPL.

### 4.2 Ctrl+K command palette

Ctrl+K from any state opens a full-screen overlay palette with the same filter/navigate/select affordance. This is the power-user shortcut. The palette and inline dropdown share entry data (same command registry).

### 4.3 Arrow-key pickers for options

Slash commands that produce option lists (`/model`, `/provider`, `/sessions`, etc.) **must** open an arrow-key picker modal — never a text dump the user has to manually re-type.

This is a user-set rule (memory `feedback_arrow_key_pickers.md`): text-dump + manual alias typing is the exact Claude-Code-parity anti-pattern to avoid.

### 4.4 Tests required for §4

- **Track 1 predicate:** `slash_dropdown_opens_on_slash` — hard predicate; fails CI if typing `/` doesn't surface the dropdown
- **Track 4 scene:** `command_autocomplete_dropdown` — scene expects ≥5 command names visible, one marked focused (inverse video or `▶` marker). xfail until feature lands; XPASS is DoD.
- **VHS scene:** `slash_autocomplete_open.png` — baseline capture after `>` + `/`
- **PTY smoke (`pty_slash_discoverability.py`):**
  ```python
  send(fd, b"/")
  raw = read_until(fd, quiet=0.5, maxwait=1.5)
  text = _collapse_spaces(strip_ansi(raw))
  for cmd in ("/help", "/plan", "/model", "/fork", "/clear", "/exit"):
      assert cmd in text, f"dropdown missing {cmd}"
  send(fd, b"\x1b[B\x1b[B\r")   # ↓ ↓ Enter
  # assert composer now contains the selected command
  ```

### 4.5 Picker tests required (§3.4)

Every option list gets parallel coverage:

- unit test for the reducer logic (filter narrowing, cursor clamping, two-stroke Escape)
- Track 1 predicate `picker_filter_accepts_input` per picker kind
- PTY scenario: `/model` → type `cod` → assert visible list contains `coding` only

---

## 5. Do Not Confuse The Dimensions

A fresh agent landing on a red test must identify which dimension the failure belongs to before "fixing" it.

| Signal | Meaning | Action |
|---|---|---|
| Track 1 hard predicate failed | Actual runtime regression | Fix the TUI code |
| Track 4 `xfail` | Expected until matching UI feature ships | **Do not remove the decorator** unless you shipped the feature |
| Track 4 unexpected XPASS | Feature landed — flip `xfail` off and commit | Celebrate then commit |
| VHS diff above tolerance | Either intentional layout change or real visual regression | **Never** auto-`--update`; ask user (§6.1) |
| PTY smoke failed | Backend contract change, gateway issue, or real runtime bug | Check gateway health, check backend stderr; do not assume PTY harness bug first |

---

## 6. Policies

### 6.1 VHS baseline is user-gated

When `run_visual_suite.py` reports drift above tolerance (default 1%):

- **never** invoke `--update` automatically, even if all scenes drift by a similar amount
- surface the drift in the next user-facing report: mismatch ratios per scene + diff image paths
- ask the user: "intentional UI evolution (rebaseline) or real regression (investigate)?"
- if authorized, commit updated reference PNGs in a dedicated commit

Rationale: drift can be either (a) intentional UI evolution → rebaseline is correct or (b) a real regression → needs investigation. Only the product owner has that context.

### 6.2 Review gate — no review ask without PTY + unit evidence

Before posting "please review" / "APPROVE requested" on any TUI work:

1. Focused unit/reducer tests covering the changed logic must be green
2. A live PTY artifact under `autocode/docs/qa/test-results/` must demonstrate the feature in a real PTY

If either is missing, post a progress update framed as "not asking for review yet" instead. This matches the repo's review discipline (memory `feedback_codex_review_gate.md`).

### 6.3 Commit discipline

- Agents never commit. User commits.
- Every TUI change stores a fresh artifact under `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<label>.md` before the change is considered done.
- Stale artifacts from a different tree state are not evidence.

### 6.4 Cross-harness binary consistency

All four dimensions must exercise the same binary. If you suspect a harness divergence, `ls -l` the resolved path in each. See §2.

### 6.5 Predicate-drift maintenance

Track 1 and Track 4 predicates were authored against the Go TUI's rendered output. When the Rust TUI renders the same feature differently (different prompt shape, different marker characters, different ordering), the predicate must be updated to match the Rust output — **not** the Rust output bent to match the stale predicate.

Process for fixing predicate drift:

1. Capture a fresh Rust PTY frame showing the correct behavior
2. Update the predicate assertion to match the Rust frame
3. Keep the test red only if the Rust behavior is genuinely broken
4. Document the predicate update in the commit message

**Do not** silently loosen predicates to make red tests green — loose predicates are how real regressions slip through.

---

## 7. PTY Patterns

Unit tests are not enough. Use `pty.fork()` against the real installed binary for every TUI change.

### 7.1 Spawn

```python
import pty, os, fcntl, termios, struct, signal

COLS, ROWS = 160, 50
master_fd, slave_fd = pty.openpty()
fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
fcntl.ioctl(slave_fd,  termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
pid = os.fork()
if pid == 0:
    os.setsid(); fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
    for fd in (0, 1, 2): os.dup2(slave_fd, fd)
    os.close(master_fd); os.close(slave_fd)
    env = {**os.environ, "TERM": "xterm-256color",
           "COLUMNS": str(COLS), "LINES": str(ROWS),
           "AUTOCODE_PYTHON_CMD": MOCK_BACKEND}
    os.execve(RUST_TUI, [RUST_TUI], env)
```

### 7.2 Drain output with a quiet window

Fixed timeouts miss incremental renders. Use a quiet-window loop:

```python
def read_until(fd, *, quiet=1.5, maxwait=15.0, stop_on=None):
    buf, deadline, last = b"", time.monotonic()+maxwait, time.monotonic()
    while time.monotonic() < deadline:
        r, _, _ = select.select([fd], [], [], 0.3)
        if r:
            chunk = os.read(fd, 8192)
            if not chunk: break
            buf += chunk; last = time.monotonic()
            if stop_on and stop_on.encode() in buf: break
        elif time.monotonic() - last >= quiet:
            break
    return buf
```

### 7.3 Keystrokes

| Key | Bytes |
|---|---|
| Enter | `b"\r"` |
| Escape | `b"\x1b"` |
| Backspace | `b"\x7f"` |
| Tab | `b"\t"` |
| Ctrl+C | `b"\x03"` |
| Ctrl+D | `b"\x04"` |
| Ctrl+E | `b"\x05"` |
| Ctrl+K | `b"\x0b"` |
| ↑ ↓ → ← | `b"\x1b[A"` `b"\x1b[B"` `b"\x1b[C"` `b"\x1b[D"` |
| Alt+Enter | `b"\x1b\r"` |
| Bracketed paste | `b"\x1b[200~" + text + b"\x1b[201~"` |

### 7.4 Strip ANSI for assertions

```python
ANSI = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
text = ANSI.sub("", raw.decode("utf-8", errors="replace"))
# pyte renders adjacent cells with spaces — collapse for substring checks
text_nospace = re.sub(r"\s+", "", text)
```

### 7.5 Renderer-owned evidence

Never accept `eprintln!` / stderr as proof of render correctness. Require a renderer-owned substring that only the ratatui view path could produce.

- ✅ `"tools | openrouter | suggest"` — status bar Line composed by `render_status_bar`
- ❌ `"[M1]"` — leftover stderr debug

### 7.6 Ctrl+C for clean exit does NOT work post-M8

Per M8 spec, `Stage::Idle + Ctrl+C` sends `cancel` RPC, it does **not** quit. For smoke tests that need a clean exit, use `/exit\r` instead.

---

## 8. Required Test Layers

For every TUI change, cover all four:

1. **Focused reducer/unit tests** for the changed logic (Rust `cargo test` or Python `pytest`)
2. **Live PTY validation** against the real binary (§7) — not a mock test
3. **Visual snapshot regression** (§6.1) when the change touches layout, color, picker, palette, alt-screen, or scrollback. Requires either (a) green diff vs committed references, or (b) explicit user-approved `--update` with baseline commit
4. **Stored artifact** under `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<label>.md`

If any layer is missing, call it out explicitly in the report.

---

## 9. Exit Gates and Reporting

### 9.1 Exit gates (do NOT mark TUI work complete if any are true)

- No PTY / real-terminal evidence was produced
- Changed feature was only tested indirectly
- Startup, basic chat, picker/palette, or warning/error behavior was not checked
- Artifact is stale or from a different tree state
- Docs overstate what is implemented
- Change touches visual surface and no VHS diff or user-authorized baseline update is in the review
- Arrow-key pickers got replaced with text dumps (hard rule — §3.4)

### 9.2 Minimal reporting template

Copy this into the comms entry / review request:

```
- Startup + silent-backend timeout banner: passed
- Basic chat turn (user message echoed to scrollback): passed
- Slash dropdown on `/` (visible entries): passed
- Ctrl+K palette (visible entries + filter): passed
- Picker surface (visible header + list + filter + cursor): passed
- Ask-user modal (visible question + options): passed
- Approval modal (visible tool + args + hotkeys): passed
- Error banner (visible red): passed
- Keyboard interaction (incl. Ctrl+C M8 state machine): passed
- Warning rendering (visible dim line): passed
- Queue/stream cleanliness: passed
- Narrow terminal check: passed
- Inline vs alt-screen: passed
- Changed-feature regression: passed
- Artifact: autocode/docs/qa/test-results/<file>.md
```

If any item is not run, state it explicitly and why.

### 9.3 Artifact contents

Each stored TUI artifact should say:

- entrypoint + binary path used
- terminal size (cols × rows)
- manual or scripted
- exact commands / keystrokes sent
- expected vs observed per check
- pass / fail per §3 checklist item

---

## 10. Sub-harness Pointers

Each dimension has its own tree with implementation detail. Read those when you need to add a scenario or debug internals. Read this doc for the strategy.

| Dimension | README | Key files |
|---|---|---|
| Track 1 | `autocode/tests/tui-comparison/README.md` | `launchers/autocode.py`, `predicates.py`, `tests/test_substrate.py` |
| Track 4 | `autocode/tests/tui-references/README.md` | `test_reference_scenes.py`, `extract_scenes.py`, `manifest.yaml` |
| VHS | `autocode/tests/vhs/README.md` | `run_visual_suite.py`, `scenarios.py`, `capture.py`, `differ.py`, `reference/*.png` |
| PTY smoke | `autocode/tests/pty/README.md` | `pty_smoke_rust_m1.py`, `pty_smoke_rust_comprehensive.py`, `mock_backend.py`, `silent_backend.py`, `dead_backend.py` |

**Retarget note:** `autocode/tests/pty/pty_e2e_real_gateway.py` now resolves the Rust binary and is valid Stage 0A evidence again.

**Canonical entry commands:**

```bash
# Track 1 runtime invariants
make tui-regression

# Track 4 design-target ratchet
make tui-references

# VHS self-regression (diff vs committed baselines)
AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui \
  uv run python autocode/tests/vhs/run_visual_suite.py

# PTY smoke (M1 scaffold evidence)
python3 autocode/tests/pty/pty_smoke_rust_m1.py

# PTY smoke (broader: streaming, /plan, Ctrl+C, /fork, /exit)
python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py
```

---

## 11. Triage — Red Test Workflow

When a test fails, follow this order. Jumping to "fix the code" before triaging creates false positives and hides real bugs.

### 11.1 Identify the dimension

See §5. A Track 4 xfail that stays xfail is **not** a failure. A Track 1 hard-predicate fail IS. A VHS diff needs human judgment.

### 11.2 Is the harness itself stale?

Before assuming the TUI is broken:

- ☐ Is the harness resolving the same Rust binary as the other harnesses? (§2 table)
- ☐ Are the test predicates from the Go-era? (§6.5 — check `predicates.py` for stale markers)
- ☐ Is the artifact from a previous tree state?
- ☐ Is the mock backend the right variant (mock / silent / dead)?

### 11.3 Reproduce with a minimal PTY

```bash
AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui \
  AUTOCODE_PYTHON_CMD=autocode/tests/pty/mock_backend.py \
  autocode/rtui/target/release/autocode-tui
```

Watch `~/.autocode/tui.log` in another pane. Real errors surface there, not on stdout (§3.20).

### 11.4 Classify the failure

| Symptom | Likely cause | Action |
|---|---|---|
| Blank modal/picker capture, state advanced | Renderer missing visible-surface code (§3.0) | Add render code; do not adjust test |
| Predicate rejects current Rust output | Stale Go-era predicate (§6.5) | Update predicate to Rust frame |
| Cargo gates green, PTY red | Runtime regression OR harness stale (§11.2) | Reproduce manually |
| PTY smoke passes, VHS drifts | Layout change vs baselines | §6.1 — surface drift, ask user |
| Fatal `Error: failed to enable raw mode` | Non-TTY environment | Not a bug; use `pty.fork()` |
| `ModuleNotFoundError: autocode.inline` | Dead Python test imports | Delete/rewrite the test file |

### 11.5 Commit evidence before claiming fixed

- Store pre-fix artifact under `autocode/docs/qa/test-results/<ts>-pre-fix-<label>.md`
- Store post-fix artifact
- Diff the two in your review note

---

## 12. Adding a New Test Scenario

When adding coverage for a new UI behavior, plumb through **all four dimensions** the scenario touches:

### 12.1 Checklist

| Dimension | File | What to add |
|---|---|---|
| Track 1 | `autocode/tests/tui-comparison/scenarios/<name>.py` | `Scenario` dataclass with `steps`, `name`, `drain_maxwait_s`, `graceful_exit=False` |
| Track 1 predicate | `autocode/tests/tui-comparison/predicates.py` | New `_pred_<name>()` + registry entry; use hard predicate (not soft) if the scenario is user-facing |
| Track 4 | `autocode/tests/tui-references/test_reference_scenes.py` | `@pytest.mark.xfail(strict=True)` test function; scene predicate in `extract_scenes.py` |
| VHS | `autocode/tests/vhs/scenarios.py` | Add `Scenario` with steps; reference PNG captured via `run_visual_suite.py --update` (user-gated) |
| PTY smoke | `autocode/tests/pty/<new_script>.py` or extend `pty_smoke_rust_comprehensive.py` | `send()` + `read_until()` + assertion |

### 12.2 Naming convention

- Scenario id: `snake_case_short` (e.g. `slash_autocomplete_open`)
- VHS reference PNG: `<scenario-id>.png` under `autocode/tests/vhs/reference/`
- Track 1 predicate: `_pred_<scenario_id>`
- PTY artifact stored: `<YYYYMMDD-HHMMSS>-<scenario-id>.md`

### 12.3 Hard vs soft predicate

- **Hard** = fails CI if the capture doesn't match. Use for user-facing invariants.
- **Soft** = logged, doesn't gate. Use for style-only gaps that are tracked but not blocking.

If you can't decide, start hard. Easier to loosen than tighten.

---

## 13. Common Pitfalls

Collection of ways TUI tests go wrong in this codebase. All have been hit in previous reviews.

### 13.1 "State exists therefore it renders"

The #1 Rust-TUI failure mode. `Stage::Picker` is set ≠ picker is visible to user. Always capture the terminal frame and assert on **rendered text**, not state. See §3.0.

### 13.2 Pyte cell-by-cell spacing

When reading pyte-rendered output, adjacent characters appear space-separated in the stripped text. "hello" becomes `"h e l l o"`. Collapse spaces for substring checks:

```python
text_nospace = re.sub(r"\s+", "", text)
assert "hello" in text_nospace   # not `in text`
```

### 13.3 Fixed timeouts miss incremental renders

`time.sleep(2)` then `os.read()` misses tokens that arrive right before the sleep ends. Use a quiet-window loop (§7.2).

### 13.4 `\x03` (Ctrl+C) doesn't quit post-M8

`Stage::Idle + Ctrl+C` sends a cancel RPC, it does not quit. Use `/exit\r` for clean exit in PTY scripts. See §7.6.

### 13.5 Mock backend stderr ≠ renderer-owned evidence

`"[M1] on_status received"` in capture is debug stderr leak, not proof of render. Assert on renderer-owned strings like status-bar text. See §7.5.

### 13.6 Binary resolution mismatch across harnesses

VHS used one binary, Track 1 used another → "drift" that's actually harness divergence. `ls -l` the resolved path in each before panicking. See §2.

### 13.7 Header date out of sync

`docs/tests/` or status doc headers dated "2026-04-10" while CLAUDE.md says "2026-04-20" breeds confusion. Update the header date every time you edit a source-of-truth doc.

### 13.8 Retroactive checklist

Filling the verification checklist from memory at the end of the session is how the 21-issue Codex inventory happened. Fill it as you go; paths to artifacts must exist before you check the box.

### 13.9 Claiming "all tests passed"

Unit tests + cargo gates ≠ full TUI tested. The user can always reproduce a "looks blank" bug that the unit suite missed. §3 (visible surface) is mandatory.

### 13.10 Silent failures above the agent's terminal

When agents run in a non-TTY shell, the Rust TUI emits `Error: failed to enable raw mode` on stderr and exits. That's not a bug — it's correct. Don't flag it as a regression. Use PTY-backed scripts for agent-side testing.

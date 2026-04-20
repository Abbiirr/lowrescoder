# TUI Testing Checklist — Enforced Template

**Purpose:** This is the per-review checklist that MUST be filled in for any TUI change before claiming the work is done. It is intentionally verbose and evidence-demanding. "All tests passed" without filled-in artifact paths is not acceptable.

**Template source:** copy this file as an artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-tui-verification.md` per change, fill it in, store it, link it from your comms entry.

**Strategy reference:** [`tui-testing-strategy.md`](tui-testing-strategy.md) defines the rules. This file enforces them.

**Known failure modes (reference):** [`/bugs/codex-tui-issue-inventory.md`](../../bugs/codex-tui-issue-inventory.md) — Codex's 2026-04-20 inventory plus same-day aggressive bug-hunt addendum. If your verification didn't look for these specific patterns, you missed them.

---

## Sign-off header (fill first)

- **Change scope:** (one sentence — what changed in the TUI)
- **Changed files:** (paths)
- **Agent / Reviewer:** (name)
- **Date:** (YYYY-MM-DD)
- **Binary built:** `autocode/rtui/target/release/autocode-tui` — `ls -lh` output: `<size + mtime>`
- **Mock backend used:** `autocode/tests/pty/mock_backend.py` (or specify alternative)
- **Artifact dir:** `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-*`

---

## Section 1 — Baseline Gates (REQUIRED before any other section)

All four cargo gates must be green. Stale build output is not evidence. Rebuild.

| Check | Command | Result | Evidence path |
|---|---|---|---|
| fmt | `cargo fmt --manifest-path autocode/rtui/Cargo.toml -- --check` | ☐ PASS / ☐ FAIL | N/A (stdout) |
| clippy | `cargo clippy --manifest-path autocode/rtui/Cargo.toml -- -D warnings` | ☐ PASS / ☐ FAIL | N/A (stdout) |
| test | `cargo test --manifest-path autocode/rtui/Cargo.toml` | ☐ PASS / ☐ FAIL | count: ___ tests |
| build | `cargo build --release --manifest-path autocode/rtui/Cargo.toml` | ☐ PASS / ☐ FAIL | size: ___ MB |

If any gate fails, **stop and fix**. Do not proceed.

---

## Section 2 — Visible Surface Rule (§3.0 in strategy)

For every modal, picker, palette, banner: the captured terminal frame must contain the renderable content, not just a prompt label. This is the single most-common Rust-TUI failure pattern (Codex Inventory §2, §3, §4, §14, §15).

### 2.1 Slash autocomplete dropdown (maps to Inventory §1)

- ☐ Typing `/` alone surfaces an inline dropdown listing ≥5 slash commands
- ☐ Dropdown includes at minimum: `/help`, `/plan`, `/model`, `/fork`, `/clear`, `/exit`
- ☐ Typing more characters filters the list (case-insensitive substring)
- ☐ `↑` / `↓` move the selection cursor — cursor is **visible** in captured output
- ☐ **Enter** completes the selected command into the composer
- ☐ **Tab** completes the selected command into the composer
- ☐ Escape closes without submitting; composer keeps what was typed
- **Evidence PTY artifact:** `_________________________`
- **VHS scene captured:** `slash_autocomplete_open.png` ☐ yes / ☐ no

### 2.2 Ctrl+K palette (maps to Inventory §2)

- ☐ Ctrl+K captured frame shows ≥3 command entries, **not** just `Palette>` prompt
- ☐ Typing filter text narrows the visible entries (captured, not just state)
- ☐ Filter state indicator visible in capture (e.g. `[filter: x]`)
- ☐ Arrow navigation cursor visible
- ☐ Enter dispatches selected command; state returns to Idle
- **Evidence PTY artifact:** `_________________________`

### 2.3 Picker surface — model / provider / session (maps to Inventory §3, §9, §12)

For each of `/model`, `/provider`, `/sessions`:

- ☐ Captured frame contains visible header (e.g. `Select a model:`)
- ☐ Captured frame contains visible list of options, not just `Picker>`
- ☐ Typing filter shows `[filter: <text>]` indicator in capture
- ☐ Selection cursor (inverse video or `▶`) visible on focused row
- ☐ Backend `model.list` / `provider.list` RPC actually sent and response used (not hardcoded client-side list)
- ☐ First Escape clears filter; second Escape exits picker
- ☐ Session picker: selection honors the FILTERED visible list, not the unfiltered backing array (Inventory §12 latent bug)
- **Evidence PTY artifact per picker:** model=`___`  provider=`___`  session=`___`

### 2.4 Ask-user modal (maps to Inventory §4, §5)

- ☐ Question text visible in captured frame, exactly as provided by backend
- ☐ Options list visible with selection cursor
- ☐ Free-text `?` prompt visible when `allow_text=true`
- ☐ Typing into free-text input inserts characters (Inventory §5 bug — char insertion was missing)
- ☐ Backspace edits free-text
- ☐ Enter submits; Esc cancels
- ☐ Response RPC id correlates with inbound request id
- **Evidence PTY artifact:** `_________________________`

### 2.5 Approval modal (maps to Inventory §4)

- ☐ Tool name visible in captured frame
- ☐ Args snippet visible (truncated if long, but visibly present)
- ☐ Hotkey hints visible: `[Y] Approve / [N] Deny / [A] Always-allow`
- ☐ `y` / `Y` / Enter → `approved=true, session_approve=false`
- ☐ `a` / `A` → `approved=true, session_approve=true`
- ☐ `n` / `N` / Escape → `approved=false`
- ☐ RPC response id correlates with inbound request id
- **Evidence PTY artifact:** `_________________________`

### 2.6 Warning + error banners (maps to Inventory §14)

- ☐ Backend `WARNING: ...` stderr emission → visible dim scrollback line (not silently dropped)
- ☐ Backend `on_error` → visible `Error:` banner in red/bold
- ☐ No raw traceback leaks into happy path
- ☐ PTY fixture `mock_backend.py __WARNING__` trigger exercises this path
- **Evidence PTY artifact:** `_________________________`

### 2.7 Silent-backend timeout banner (maps to Inventory §15)

- ☐ Spawning TUI against `silent_backend.py` (never sends `on_status`) produces a visible timeout banner within 15s
- ☐ Banner text is readable (e.g. "Backend not connected" / "backend unresponsive")
- ☐ TUI does NOT show a blank dead start
- **Evidence PTY artifact:** `_________________________`

---

## Section 3 — Functional Flows

### 3.1 Basic chat turn + user echo (maps to Inventory §13)

- ☐ User submits `hello` — user's own message echoes into scrollback (visible, not silent-sent)
- ☐ Assistant streaming tokens appear during the turn
- ☐ `on_done` flushes completed message to scrollback
- ☐ Turn returns to usable input state (composer cleared, cursor visible)
- ☐ Scrolling the terminal back shows: user turn → assistant turn (both visible, in order)
- **Evidence PTY artifact:** `_________________________`

### 3.2 Ctrl+C M8 state machine (§3.5 in strategy)

- ☐ `Stage::Idle` + Ctrl+C → sends `cancel` RPC, process does NOT exit
- ☐ `Stage::Streaming` + first Ctrl+C → enters steer mode; steer prompt visible
- ☐ Steer + Enter → sends `steer` RPC; returns to streaming or idle
- ☐ Steer + Escape → cancels steer without sending
- ☐ 3× Ctrl+C in rapid succession → hard quit
- **Evidence PTY artifact:** `_________________________`

### 3.3 Composer keys

- ☐ Enter on last/only line submits
- ☐ Alt+Enter inserts newline at cursor
- ☐ Backspace edits; merges lines when at line start
- ☐ Arrow keys move cursor within composer when composer has focus
- ☐ ↑ / ↓ in empty Idle composer browse frecency history
- ☐ Bracketed paste inserts text at cursor without executing control codes
- ☐ History persists to `~/.autocode/history.json` across runs
- **Evidence PTY artifact:** `_________________________`

### 3.4 Editor launch (Ctrl+E)

- ☐ Ctrl+E launches `$EDITOR` with composer text as tempfile contents
- ☐ Raw mode disabled cleanly during editor session
- ☐ Tempfile contents on save become new composer content after editor exit
- ☐ Raw mode re-enabled on return; no terminal corruption
- ☐ Missing `$EDITOR` shows clear error banner, does not crash
- **Evidence PTY artifact:** `_________________________`

### 3.5 Slash command routing (maps to Inventory §7, §8, §10)

- ☐ `/help` produces usable output (not just a static text dump, or at minimum is consistent with palette inventory — Inventory §8)
- ☐ Unknown slash command → visible error or suggestion (not silent fallthrough — Inventory §7)
- ☐ Command inventory is consistent across: slash router, `/help` output, `Ctrl+K` palette (Inventory §10)
- ☐ `/sessions` and `/resume` actually transition into a visible session picker (Inventory §6)
- **Evidence PTY artifact:** `_________________________`

### 3.6 Task panel (maps to Inventory §11)

- ☐ `on_tasks` notifications render a visible task panel (not just a `⏳ N bg` counter)
- ☐ Each task entry shows status icon + name
- ☐ Subagent delegation visible
- **Evidence PTY artifact:** `_________________________`

### 3.7 Queue / streaming / interrupt cleanliness (§3.7 in strategy)

- ☐ No debug / queue text leaks into chat output
- ☐ No duplicate or stuck spinner after turn ends
- ☐ Cancel / steer / followup stay coherent
- ☐ Scrollback bounded at 10k lines (verify via unit test; cite it)
- **Unit test name cited:** `_________________________`

### 3.8 Followup queue + markdown (§3.21 in strategy)

- ☐ Enter while streaming queues the message (not sent immediately)
- ☐ Queued messages drain FIFO on each `on_done`
- ☐ Queue visibility (banner or count) surfaced to user
- ☐ Inline markdown: `` `code` ``, `**bold**`, `*italic*`, `[text](url)` render with styling
- **Evidence PTY artifact:** `_________________________`

### 3.9 Cost / token status bar (§3.22 in strategy)

- ☐ `on_cost_update` → status bar cost visible
- ☐ `on_done` → `N↑M↓` token counts visible
- ☐ Format preserved from backend; accumulates across turns
- **Evidence PTY artifact:** `_________________________`

---

## Section 4 — Layout & Terminal

### 4.1 Narrow terminal (§3.8 in strategy)

- ☐ Run at ~60-column terminal — no catastrophic wrapping
- ☐ Status bar not corrupted
- ☐ Composer prompt still visible
- ☐ Resize via TIOCSWINSZ redraws correctly
- **Evidence PTY artifact:** `_________________________`

### 4.2 Inline vs alt-screen (§3.9 in strategy)

- ☐ Default (inline): no `?1049h` emitted; prior terminal content preserved above
- ☐ `--altscreen`: alt-screen entered on startup, primary buffer restored on `/exit`
- ☐ Panic path: `ScreenGuard::drop` restores terminal (test via panic-induced process)
- **Evidence PTY artifact:** `_________________________`

### 4.3 Persistence files (§3.14 in strategy)

- ☐ `~/.autocode/history.json` exists after a turn; corrupted file does not crash
- ☐ `~/.autocode/tui.log` contains startup INFO line; nothing of this leaks to terminal stdout
- ☐ Atomic-write pattern used (tmp + rename) — no partial writes on crash
- ☐ History entries bounded (no unbounded growth after 100+ turns)
- **Evidence log path + size:** `_________________________`

### 4.4 Shutdown / exit paths (§3.15 in strategy)

- ☐ `/exit` → exit 0, raw mode off, cursor visible (verify `stty -a` after)
- ☐ Triple Ctrl+C → hard quit; no orphaned child
- ☐ Backend EOF (`dead_backend.py`) → visible error + clean shutdown
- ☐ SIGTERM from parent → clean shutdown, raw mode restored
- ☐ Panic → `RawModeGuard` + `ScreenGuard` restore terminal (inject a test panic)
- ☐ `pgrep -P <pid>` after exit shows 0 orphan children
- **Evidence PTY artifact:** `_________________________`

### 4.5 Backend failure modes (§3.16 in strategy)

Tick each that applies to the changed surface; mark N/A with reason otherwise.

- ☐ Backend never starts → clear startup error, nonzero exit
- ☐ Backend silent (`silent_backend.py`) → timeout banner in 15s
- ☐ Backend crashes mid-chat (`dead_backend.py`) → visible error, clean shutdown
- ☐ Malformed JSON from backend → warn in log, continue (no panic)
- ☐ 1 MB+ RPC line → delivered intact (LinesCodec / BufReader safety)
- ☐ Gateway auth failure → `on_error` with auth message visible
- **Evidence PTY artifact(s):** `_________________________`

### 4.6 Performance budget (§3.17 in strategy)

Only required if change touches hot path (render / event loop / reducer). Otherwise cite the M10 artifact.

- ☐ First-token render latency < 50ms
- ☐ Keystroke-to-render < 16ms
- ☐ Idle CPU < 1%
- ☐ Memory RSS < 50MB
- ☐ Startup (`--version`) < 200ms
- ☐ Binary size < 10MB
- **Measurement artifact or M10 citation:** `_________________________`

### 4.7 Terminal compatibility (§3.18 in strategy)

- ☐ `TERM=dumb` → graceful degrade, no crash
- ☐ `TERM=vt100` → mono-safe fallback
- ☐ UTF-8 terminal → braille spinner + arrows render
- ☐ Status bar chars don't leak literal escape codes

### 4.8 Long-session stability (§3.19 in strategy)

- ☐ Scrollback eviction at 10k lines verified (unit test name: `______________`)
- ☐ 100+ turn run memory stable (RSS delta < 5MB)
- ☐ Spinner state resets per turn
- ☐ No file-descriptor leaks (`ls /proc/<pid>/fd/` growth bounded)

### 4.9 Logging boundary (§3.20 in strategy) — CRITICAL

- ☐ `grep -rn "println!" autocode/rtui/src/` returns **zero non-test lines**
- ☐ Any `eprintln!` occurrences are for pre-crash paths only — each one justified
- ☐ `tracing-subscriber` sinks to file only
- ☐ PTY capture stdout contains valid JSON-RPC; no log spew interleaved
- **Evidence (grep output):** `_________________________`

---

## Section 5 — Harness Hygiene (REQUIRED)

These are verifying the TEST HARNESS, not the TUI itself. Stale harnesses produce false greens.

### 5.1 Harness binary resolution (§2 + Inventory §17, §18, §20)

- ☐ Track 1 launcher (`autocode/tests/tui-comparison/launchers/autocode.py`) resolves Rust binary without env var — `grep -A5 "def find_binary" autocode/tests/tui-comparison/launchers/autocode.py` shows Rust path in priority order
- ☐ Track 4 (`autocode/tests/tui-references/test_reference_scenes.py`) either resolves Rust auto OR fails fast with clear guidance if env var unset (Inventory §18)
- ☐ VHS (`autocode/tests/vhs/run_visual_suite.py`) either resolves Rust auto OR fails fast (Inventory §17)
- ☐ `pty_e2e_real_gateway.py` retargeted to Rust binary OR deleted (Inventory §20)

### 5.2 Harness README accuracy (Inventory §16)

- ☐ `autocode/tests/pty/README.md` does NOT reference deleted Go-era harnesses
- ☐ No `go build` instructions remain
- ☐ Script inventory matches `ls autocode/tests/pty/*.py`

### 5.3 "Comprehensive" coverage matches the name (Inventory §19)

- ☐ `pty_smoke_rust_comprehensive.py` docstring accurately describes scenarios implemented (S1-S2 currently, despite claiming S1-S6)
- ☐ Artifact filename matches actual coverage (currently writes `*-rust-m1-pty-smoke.md` — should be renamed)

### 5.4 Predicate-drift (§6.5 in strategy, Inventory §21)

- ☐ No Track 1 predicate asserts against Go-era markers when the Rust frontend renders them differently
- ☐ `basic_turn_returns_to_usable_input` updated to accept Rust `> ` bare prompt shape
- **Reviewed predicate file:** `autocode/tests/tui-comparison/predicates.py`

---

## Section 6 — Four-Dimension Matrix (§1 in strategy)

Every TUI change must exercise all four dimensions that apply to the changed surface. If the change doesn't touch the surface for a dimension, mark N/A with reason.

| Dimension | Command | Result | Evidence path | N/A reason (if skipped) |
|---|---|---|---|---|
| Track 1 runtime invariants | `make tui-regression` | ☐ PASS / ☐ FAIL / ☐ N/A | `_______` | `_______` |
| Track 4 design-target ratchet | `make tui-references` | ☐ PASS / ☐ FAIL / ☐ N/A | `_______` | `_______` |
| VHS self-regression | `AUTOCODE_TUI_BIN=... uv run python autocode/tests/vhs/run_visual_suite.py` | ☐ PASS / ☐ drift (user-gated — §6.1) / ☐ N/A | `_______` | `_______` |
| PTY smoke | `python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py` | ☐ PASS / ☐ FAIL / ☐ N/A | `_______` | `_______` |

---

## Section 7 — Known-Bug Regression Sweep

Codex Inventory §1-21. For each, confirm the change did NOT reintroduce, and preferably closed it.

| # | Bug | Closed? | Evidence |
|---|---|---|---|
| 1 | Slash autocomplete missing | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 2 | Ctrl+K palette invisible | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 3 | Picker UI invisible | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 4 | Ask-user / approval invisible | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 5 | Free-text ask-user cannot type | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 6 | `/sessions` / `/resume` no visible browser | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 7 | Unknown slash silent fallthrough | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 8 | `/help` only static dump | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 9 | Model/provider pickers hardcoded | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 10 | Command inventory inconsistent | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 11 | Task panel not rendered | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 12 | Session picker filtered-selection bug | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 13 | User chat messages not echoed | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 14 | Backend warnings not surfaced | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 15 | Silent-backend timeout banner missing | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 16 | PTY README stale | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 17 | VHS defaults to Go-era paths | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 18 | Track 4 file uses Go path | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 19 | Comprehensive smoke overclaims | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 20 | `pty_e2e_real_gateway.py` stale | ☐ still open / ☐ closed / ☐ n/a | `_______` |
| 21 | Track 1 predicate drift | ☐ still open / ☐ closed / ☐ n/a | `_______` |

---

## Section 8 — Final Sign-Off

- ☐ Every item in sections 1-7 has a concrete ☐PASS, ☐FAIL, ☐N/A + reason, or ☐closed/open + evidence
- ☐ No section was skipped. "Didn't apply" counts as N/A with a specific reason, not blank
- ☐ Every evidence path points to a real file in `autocode/docs/qa/test-results/` or the regression output tree — not `<TODO>` or `<TBD>`
- ☐ The agent posting the review request checked §2 + §3 specifically with PTY captures — NOT just cargo unit tests
- ☐ Codex Inventory bugs §1-21 have been deliberately examined (Section 7)
- ☐ Staged files listed: ________________________
- ☐ Comms entry posted: Entry # ________________________

**Final verdict:** ☐ READY FOR REVIEW / ☐ NEEDS MORE WORK

**If NEEDS_WORK, the open items are:**

1. 
2. 
3. 

---

## How to use this checklist

1. **Copy** this file to `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-tui-verification.md` at the start of your TUI work
2. **Fill it in as you go** — evidence path must exist before you can check the box
3. **Do not** use this as a "retroactive checklist" — filling it in at the end from memory is the anti-pattern that led to Codex's 21-issue inventory in the first place
4. **Post the filled-in file** as your review artifact in `AGENTS_CONVERSATION.MD`
5. **An unchecked box, or a box without an evidence path, is treated as FAIL** by reviewers

## Anti-patterns

| Don't | Do |
|---|---|
| "cargo test green, all tests pass" | Fill the actual Section 2 visible-surface checklist with PTY captures |
| "Skipped §3.5 because /help isn't what I changed" | Mark N/A with that reason — still required to record |
| "Ran make tui-regression, no issues" | Attach the regression output artifact path |
| "VHS drifted but similar to last time" | Surface the drift; ask user per §6.1 — do not auto-rebaseline |
| "Will add tests later" | If the item is in §2, and you can't check it now, the change is not ready to merge |

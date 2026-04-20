# Codex TUI Issue Inventory

Date: 2026-04-20
Source: mirrored from `autocode/docs/qa/test-results/20260420-102627-codex-tui-issue-inventory.md`
Scope: Initial issue inventory before the rest of the full four-dimension TUI matrix finishes.
Basis:
- user-provided screenshot and UX expectation
- live Rust TUI source inspection
- TUI harness/doc inspection
- baseline Rust gates run in this session

## Baseline checks already run

| Check | Result |
|---|---|
| `cargo fmt -- --check` | PASS |
| `cargo clippy -- -D warnings` | PASS |
| `cargo test` | PASS |
| `cargo build --release` | PASS |

These baseline results mean the Rust TUI compiles and its unit tests are green. They do **not** mean the TUI UX or test harness state is correct.

## Confirmed product issues

### 1. Slash-command autocomplete/discoverability is missing

Severity: High

Expected:
- typing `/` should open a visible command list
- the list should be navigable with arrow keys
- `Tab` and/or `Enter` should complete or execute the selected command

Observed / evidence:
- the user screenshot shows the composer with just `/` inserted and no command UI
- [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:23) only treats slash input specially **after Enter**, by checking `trimmed.starts_with('/')`
- there is no slash-suggestion state machine in the composer path
- there is no `Tab` handling in the Rust composer path at all
- the only selectable command UI is the separate palette opened by `Ctrl+K` in [reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:148)

Impact:
- slash commands are effectively hidden unless the user already knows the exact command name
- this is below the expected terminal-agent UX bar

### 2. The `Ctrl+K` palette is largely invisible and its filter is nonfunctional

Severity: High

Evidence:
- `Ctrl+K` does create palette state with entries in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:148)
- the renderer never draws palette entries or the palette filter; it only changes the composer prompt to `Palette> ` in [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:135)
- `handle_palette_key()` stores filter text, but Enter and arrow navigation still operate on the full unfiltered `palette.entries` vector in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:253)
- a live PTY probe in this session showed only `Palette>` after `Ctrl+K`, with no rendered entries

Impact:
- even the fallback command browser is not a real visible picker
- typed palette filtering has no trustworthy UX because the filter is not rendered and is not applied to selection logic

### 3. Picker UI is mostly invisible in live captures

Severity: High

Evidence:
- targeted Track 1 run for `model-picker` failed its hard picker predicate and wrote:
  - [autocode.txt](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-102953/model-picker/autocode.txt:1)
  - [predicates.json](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-102953/model-picker/predicates.json:1)
- the captured screen shows only the status bar and `Picker>` prompt, with no header, no options, and no visible filter text
- the renderer never draws picker entries or filter state; it only swaps the prompt to `Picker> ` in [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:134)

Impact:
- `/model` and `/provider` are effectively blind pickers
- users cannot see available options or what their typed filter is doing

### 4. Ask-user and approval surfaces are mostly invisible

Severity: High

Evidence:
- targeted Track 1 run for `ask-user-prompt` failed its hard modal predicate and wrote:
  - [autocode.txt](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103014/ask-user-prompt/autocode.txt:1)
  - [predicates.json](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103014/ask-user-prompt/predicates.json:1)
- the captured screen shows no question text, no options, and no keyboard hint
- the renderer does not draw `state.approval` or `state.ask_user` payloads at all; it only changes the prompt to `[Y/N/A] ` or `? ` in [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:132)

Impact:
- approval and ask-user flows are not usable because the user cannot see the content they are meant to answer

### 5. Free-text ask-user / steer input cannot actually be typed

Severity: High

Evidence:
- ask-user state stores `question`, `options`, `allow_text`, and `free_text` in [autocode/rtui/src/state/model.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/model.rs:92)
- `handle_ask_user_key()` only handles Enter, Esc, Up, and Down in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:896)
- there is no character insertion or backspace handling for `ask.free_text`

Impact:
- steer-mode and any free-text `ask_user` flow cannot work correctly even if the backend requests them

### 6. `/sessions` and `/resume` do not open any visible session browser

Severity: High

Evidence:
- `/sessions` and `/resume` only send `session.list` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:370)
- the response handler only stores `state.session_list = Some(...)` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:645)
- no code path transitions into `PickerKind::Session`; that branch exists but is unreachable from the current slash/palette flows
- a live PTY probe in this session showed no visible session browser after `/sessions`

Impact:
- `/sessions` appears to do nothing visible
- `/resume` has no usable interactive flow

### 7. Unknown slash commands fail silently

Severity: Medium

Evidence:
- the slash router falls through to `_ => {}` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:416)
- there is no error banner, help suggestion, or "unknown command" feedback

Impact:
- typoed or partially typed slash commands look like dead input instead of recoverable mistakes

### 8. `/help` is only a static text dump, not a usable command browser

Severity: Medium

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:412) pushes a single scrollback line:
  - `Available commands: /clear /exit /fork /compact /plan /sessions /resume /model /provider /help`
- no selection model, descriptions, grouping, filtering, or completion is attached to the slash path

Impact:
- `/help` is not a real substitute for inline slash discoverability
- it also duplicates part of the `Ctrl+K` palette instead of unifying command discovery

### 9. Model and provider pickers are hardcoded client-side

Severity: Medium

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:390) hardcodes model entries to `tools`, `coding`, `fast`
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:401) hardcodes provider entries to `openrouter`, `anthropic`, `openai`

Impact:
- picker contents can drift from real backend/provider state
- this blocks trustworthy command/picker UX for fresh sessions and different configs

### 10. Command inventories are inconsistent across slash help, palette, and router

Severity: Medium

Evidence:
- the router handles `/sessions` and `/resume` together in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:370)
- `/help` lists `/resume` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:413)
- the `Ctrl+K` palette entries do **not** include `/resume` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:152)

Impact:
- users get different command availability depending on which discovery surface they try
- this makes the already-weak command discoverability story more confusing

### 11. Task and subagent updates are stored but not rendered as a real panel

Severity: Medium

Evidence:
- the app state stores `tasks` and `subagents` in [autocode/rtui/src/state/model.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/model.rs:126)
- `on_tasks` updates both collections and background-task count in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:596)
- the renderer only shows `⏳ N bg` in the status bar and does not render a task panel in [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:52)

Impact:
- background work is only visible as a count, not as actionable or inspectable state
- this underdelivers on the claimed “task panel” surface

### 12. Session-picker filtering would select the wrong session even if the picker were wired up

Severity: Medium

Evidence:
- picker selection computes a filtered `visible` list in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:726)
- for `PickerKind::Session`, the code ignores that filtered `visible` selection and uses `sessions.get(picker.cursor)` instead in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:777)

Impact:
- if a session picker becomes reachable later, filtered selection can target the wrong underlying session
- this is a latent logic bug behind the current missing-UI bug

### 13. User chat messages are not echoed into scrollback

Severity: Medium

Evidence:
- the targeted `first-prompt-text` capture shows only the assistant response, not the user message:
  - [autocode.txt](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103354/first-prompt-text/autocode.txt:1)
  - [predicates.json](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103354/first-prompt-text/predicates.json:1)
- sending chat in [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:63) emits RPC but does not append the user message to scrollback
- reducer-side scrollback writes are response-oriented (`on_token`, `on_done`) rather than user-message-oriented

Impact:
- the visible transcript is incomplete
- users cannot easily verify what was actually sent from the TUI itself

### 14. Deliberate backend warnings are not surfaced as warning lines

Severity: High

Evidence:
- the mock backend’s warning trigger prints `WARNING: deliberate mid-session warning from mock backend` to stderr in [autocode/tests/pty/mock_backend.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/mock_backend.py:148)
- the targeted `error-state` capture does **not** show that warning line; it only shows the normal token stream `Warning emitted.`:
  - [autocode.txt](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103412/error-state/autocode.txt:1)
  - [predicates.json](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103412/error-state/predicates.json:1)

Impact:
- backend warning detail is effectively dropped
- the real warning-rendering path is not doing the job the harness expects

### 15. Silent-backend startup fallback does not surface a usable timeout banner

Severity: High

Evidence:
- the targeted `orphaned-startup` Track 1 capture is effectively blank:
  - [autocode.txt](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103644/orphaned-startup/autocode.txt:1)
  - [predicates.json](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/tui-comparison/regression/20260420-103644/orphaned-startup/predicates.json:1)
- the hard predicate `startup_timeout_fires_when_backend_absent` fails with `no startup-timeout/\`Backend not connected\` text in frame`

Impact:
- if the backend never announces readiness, the user can end up with a blank dead start instead of a recoverable timeout state
- this violates the testing strategy’s startup-path requirement

## Confirmed test-harness and discoverability issues

### 16. PTY README is stale after the Rust cutover

Severity: High

Evidence:
- [autocode/tests/pty/README.md](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/README.md:48) still inventories deleted Go-era harnesses
- [autocode/tests/pty/README.md](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/README.md:80) still says stubs are selected when spawning the Go TUI
- [autocode/tests/pty/README.md](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/README.md:124) still tells builders to compile `autocode/build/autocode-tui` with `go build`

Impact:
- fresh sessions are pointed at scripts and binary paths that no longer define the product

### 17. VHS runner still defaults to Go-era binary paths

Severity: High

Evidence:
- [autocode/tests/vhs/run_visual_suite.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/vhs/run_visual_suite.py:48) documents `_resolve_go_tui()`
- [autocode/tests/vhs/run_visual_suite.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/vhs/run_visual_suite.py:52) still prefers `autocode/build/autocode-tui`
- [autocode/tests/vhs/run_visual_suite.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/vhs/run_visual_suite.py:61) still falls back to `autocode/cmd/autocode-tui/autocode-tui`

Impact:
- visual regression runs need manual env override to hit the real Rust frontend
- the default contract is wrong for the current product state

### 18. Track 4 live test file still uses Go-path assumptions

Severity: Medium

Evidence:
- [autocode/tests/tui-references/test_reference_scenes.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/tui-references/test_reference_scenes.py:28) still says the environment requires the Go TUI binary
- [autocode/tests/tui-references/test_reference_scenes.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/tui-references/test_reference_scenes.py:45) still points `_BIN_PATH` at `autocode/build/autocode-tui`
- [autocode/tests/tui-references/test_reference_scenes.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/tui-references/test_reference_scenes.py:114) still tells the user to run `go build`

Impact:
- Track 4 is harder than it should be to run correctly against the Rust frontend
- the product’s own design-target ratchet is still narrating the old binary contract

### 19. “Comprehensive” PTY smoke overclaims its actual coverage

Severity: Medium

Evidence:
- [autocode/tests/pty/pty_smoke_rust_comprehensive.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/pty_smoke_rust_comprehensive.py:2) claims S1-S6 coverage
- [autocode/tests/pty/pty_smoke_rust_comprehensive.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/pty_smoke_rust_comprehensive.py:152) only implements S1 and S2 in `run_smoke()`
- [autocode/tests/pty/pty_smoke_rust_comprehensive.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/pty_smoke_rust_comprehensive.py:222) still writes the artifact as `*-rust-m1-pty-smoke.md`

Impact:
- the script is useful, but its name/docs can mislead reviewers about what PTY coverage is actually proven

### 20. `pty_e2e_real_gateway.py` is still wired to the deleted Go binary contract

Severity: High

Evidence:
- the script hardcodes `../../build/autocode-tui` into `GO_TUI` in [autocode/tests/pty/pty_e2e_real_gateway.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/pty_e2e_real_gateway.py:29)
- it does not honor `$AUTOCODE_TUI_BIN`
- this session’s stored artifact confirms it actually ran against `/autocode/build/autocode-tui`, not the Rust binary:
  - [20260420-043851-pty-e2e-real-gateway.md](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/test-results/20260420-043851-pty-e2e-real-gateway.md:1)

Impact:
- the current “real gateway” PTY smoke is not a valid Rust-frontend verification step
- the PTY dimension is partially stale until this harness is retargeted or replaced

### 21. Track 1 `basic_turn_returns_to_usable_input` is stale against the Rust prompt shape

Severity: Medium

Evidence:
- `_pred_composer_present()` explicitly accepts the Rust TUI’s bare trailing `>` prompt in [autocode/tests/tui-comparison/predicates.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/tui-comparison/predicates.py:135)
- `_pred_basic_turn_returns_to_usable_input()` still uses the older marker set and does not include that fallback in [autocode/tests/tui-comparison/predicates.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/tui-comparison/predicates.py:197)
- both the `first-prompt-text` and `error-state` captures visibly end with `>`, yet that predicate still reports failure

Impact:
- at least one current Track 1 failure is a harness mismatch, not a pure runtime break
- reviewers need to read the artifact text directly instead of trusting the high-level fail count

## Aggressive bug-hunt addendum (2026-04-20)

The items below were confirmed after switching from “matrix compliance” mode to direct PTY bug hunting using the guidance in:

- [docs/tui-testing/tui-testing-strategy.md](/home/bs01763/projects/ai/lowrescoder/docs/tui-testing/tui-testing-strategy.md:1)
- [docs/tui-testing/tui_testing_checklist.md](/home/bs01763/projects/ai/lowrescoder/docs/tui-testing/tui_testing_checklist.md:1)

These are additional live/runtime or source-level issues beyond the original 21-item inventory above.

### 22. `ask_user` is protocol-incompatible with the current backend and mock harness

Severity: Critical

Evidence:
- the Python backend server still emits `on_ask_user` in [autocode/src/autocode/backend/server.py](/home/bs01763/projects/ai/lowrescoder/autocode/src/autocode/backend/server.py:537)
- the PTY mock backend also emits `on_ask_user` in [autocode/tests/pty/mock_backend.py](/home/bs01763/projects/ai/lowrescoder/autocode/tests/pty/mock_backend.py:53)
- the Rust reducer only handles `ask_user` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:682)

Impact:
- the Rust TUI and the Python backend disagree on the RPC method name for the same feature
- current ask-user scenarios can fail before rendering because the request is never recognized

### 23. Rapid triple `Ctrl+C` does not hard-quit; it just sends repeated `cancel` RPCs from idle

Severity: High

Evidence:
- the reducer has no press-counter or timing window; `Stage::Idle` always sends `cancel` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:105)
- ad hoc PTY probe against the Rust binary logged three consecutive `cancel` RPCs after three quick `Ctrl+C` presses:
  - `{"id": 2, "method": "cancel"}`
  - `{"id": 3, "method": "cancel"}`
  - `{"id": 4, "method": "cancel"}`
- the process remained alive after those three presses

Impact:
- the M8 “rapid hard-quit” behavior from the TUI testing docs/checklist is not implemented
- panic-recovery and emergency-exit expectations are weaker than the docs claim

### 24. Inline mode clears existing terminal content instead of preserving it above the app

Severity: High

Evidence:
- the Rust entrypoint calls `terminal.clear()` before it even branches on `--altscreen` in [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:84)
- a direct PTY probe that printed `PRELUDE` immediately before `exec autocode-tui` rendered the TUI boot frame without any surviving `PRELUDE` content

Impact:
- default inline mode does not preserve prior terminal content as the docs require
- the current startup behavior is closer to “clear-screen fullscreen” than “inline terminal app”

### 25. The editor round-trip forces alternate screen even when the app started in inline mode

Severity: High

Evidence:
- editor launch always executes `LeaveAlternateScreen` before opening `$EDITOR` in [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:185)
- editor return always executes `EnterAlternateScreen` on resume in [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:205)
- that code path does not check whether `--altscreen` was actually active

Impact:
- using `Ctrl+E` in default inline mode can silently switch the app into alt-screen semantics on return
- this breaks the expected “inline by default” model and can make terminal restoration behavior confusing

### 26. History persistence is non-atomic and unbounded

Severity: Medium

Evidence:
- history is written directly via `fs::File::create(&path)` in [autocode/rtui/src/ui/history.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/history.rs:18)
- there is no temp-file + rename path, and no length cap before serialization in [autocode/rtui/src/ui/history.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/history.rs:12)

Impact:
- interrupted writes can truncate or corrupt `~/.autocode/history.json`
- long-running usage can grow the history file without any retention bound

### 27. Live `Ctrl+K` palette filtering is not just invisible; pressing Enter after filtering still does not open the filtered command

Severity: High

Evidence:
- direct PTY probe showed this exact visible sequence:
  - after `Ctrl+K`: prompt changed to `Palette>`
  - after typing `m`: prompt still just `Palette>` with no filter text or entries
  - after `Enter`: prompt returned to plain `>` instead of opening `/model`’s picker
- this matches the reducer logic: typed filter chars are stored, but `Enter` still indexes the unfiltered palette entry list in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:263)

Impact:
- the palette is not merely missing visuals; it is functionally misleading
- a user can type a filter that appears to do nothing and still dispatch the wrong command

## Extended bug-hunt addendum (2026-04-20, follow-up source audit)

The items below were confirmed after a deeper static pass across `autocode/rtui/src/` focused on axes the original 27-item inventory did not emphasize: **UTF-8 safety**, **ID-space / RPC correlation integrity**, **modal concurrency**, **resource bounds**, and **renderer-reachability**.

All references are line-pinned against the tree as of 2026-04-20.

### 28. UTF-8 backspace/delete panics the TUI

Severity: Critical

Evidence:
- character insertion advances cursor by `c.len_utf8()` in [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:140)
- Backspace uses `state.composer_text.remove(state.composer_cursor - 1)` in [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:94) — `String::remove` takes a byte index and panics if it isn't a char boundary
- Delete has the same shape in [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:102)
- Left/Right arrow in [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:108) and [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:115) move cursor ±1 byte, landing mid-codepoint

Repro: type `é`, press Backspace → panic at `remove(1)` because byte 1 is the second byte of `é`.

Impact:
- any non-ASCII character (accented Latin, emoji, CJK, RTL) crashes the TUI on the very next keystroke
- this is a hard dead-end for any user who doesn't type pure ASCII
- this must be treated as blocking for any locale that uses non-ASCII input

### 29. Renderer panics on non-char-boundary composer cursor

Severity: Critical

Evidence:
- [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:144) slices `text[..cursor_pos.min(text.len())]`
- [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:145) slices `text[cursor_pos.min(text.len())..]`
- both panic if `cursor_pos` is not at a UTF-8 char boundary

Repro: type `é` (cursor=2), press Left (cursor=1), next render panics on `text[..1]`.

Impact:
- companion to §28 — even navigation over a multi-byte character triggers a render panic
- any ratatui backend assertion that sees this panic will take down the TUI

### 30. History up-arrow is stuck on the most recent entry

Severity: High

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:213): `let idx = state.history_cursor.map_or(0, |c| c.saturating_sub(1));`
- first Up → None → 0 → show `history[0]`
- second Up → Some(0) → `0.saturating_sub(1)` → 0 → show `history[0]` again
- history is sorted newest-first by the frecency sort in [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:51), so Up should increment to reach older entries

Impact:
- users can only ever recall the single most-recent prompt
- history browse is functionally broken for any N > 1

### 31. Frecency sort is dominated by timestamp; `use_count` is effectively ignored

Severity: Medium

Evidence:
- [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:52): `score = last_used_ms * 0.7 + use_count * 0.3`
- `last_used_ms` is a Unix epoch in milliseconds (~1.7×10¹²); `use_count` is a small integer
- the product gap (~10⁹ orders of magnitude) means `use_count` is never the tiebreaker

Impact:
- the "frecency" claim in user-facing docs is inaccurate; in practice it is pure LRU
- frequently-used prompts never float above merely-recent ones

### 32. Slash commands have no visible echo in scrollback

Severity: Medium

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:311) dispatches `/plan`, `/fork`, `/compact`, `/sessions`, `/model`, `/provider` etc. with no `scrollback.push_back`
- only `/help` writes a scrollback line in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:413)

Impact:
- toggling plan mode or forking session leaves no record in the chat transcript
- companion to §13 (user-message echo) — the transcript is missing command events

### 33. `/plan` mode change is only visible as a status-bar tag

Severity: Medium

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:326) toggles `state.plan_mode`
- [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:58) renders `[PLAN]` only in the status bar; no scrollback note, no composer-prompt change

Impact:
- easy for the user to lose track of whether plan mode is on
- closely tied to §32 — both stem from missing scrollback echo

### 34. `on_tool_call` overwrites the previous tool call; parallel tools vanish from UI

Severity: High

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:581) assigns `state.current_tool = Some(...)` unconditionally
- state field is `current_tool: Option<ToolCallInfo>` in [autocode/rtui/src/state/model.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/model.rs:125)

Impact:
- a backend that streams two tool calls concurrently (e.g. `read` and `grep` in flight) loses the first from the UI
- tool args and result are also never rendered for the surviving tool (see §39)

### 35. `on_thinking` accumulates `stream_buf` with no flush / overflow path

Severity: High

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:517) appends to `stream_buf` and rebuilds `stream_lines`, but skips the 20-line overflow drain that `on_token` performs in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:502)
- only `on_done` flushes `stream_lines` to scrollback

Impact:
- a long thinking block that never reaches `on_done` (e.g. cancelled request) leaves text pinned in `stream_lines` forever, rendered dim
- couples badly with §60 — idle ticks do not re-render, so stuck dim content persists visibly

### 36. Tokens received during Approval or AskUser are silently absorbed

Severity: Medium

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:499) only promotes `stage` when `Stage::Idle`
- in `Stage::Approval` or `Stage::AskUser`, incoming tokens still append to `stream_buf` but stage stays modal; the dim render path is not triggered because the stage check gates the transition, not the append

Impact:
- assistant output streamed concurrently with an approval arrives invisibly; only appears retroactively if stage ever returns to `Streaming`

### 37. `followup_queue` is invisible and unbounded

Severity: High

Evidence:
- field `followup_queue: VecDeque<String>` in [autocode/rtui/src/state/model.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/model.rs:119)
- drained one-per-`on_done` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:554)
- no reader in [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:1)
- no cap on push sites

Impact:
- the testing strategy §3.21 requires queue visibility; current state is invisible + unbounded
- both UX and resource bug

### 38. `Ctrl+L` bypasses the `/clear` dispatcher

Severity: Low

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:194) clears only `scrollback`, `stream_buf`, `stream_lines`
- `/clear` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:317) does the same three things via a parallel code path

Impact:
- latent divergence risk when `/clear` grows semantics (error banner, tool info, tasks, followup queue); only one surface gets updated
- neither path currently clears `error_banner`, `current_tool`, `tasks`, or `followup_queue`

### 39. `ToolCallInfo.args` and `.result` are stored but never rendered

Severity: Medium

Evidence:
- fields `args` and `result` in [autocode/rtui/src/state/model.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/model.rs:51)
- [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:116) renders `name + status` only

Impact:
- tool-call UI is strictly less informative than the state supports
- same family as §2 / §3 / §4 / §11 in the original inventory — the renderer lags the reducer

### 40. Session-list response has no rendering path

Severity: High

Evidence:
- response handler stores `state.session_list = Some(...)` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:645)
- [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:1) never reads `session_list`

Impact:
- reinforces §6 — even if `/sessions` were wired into `PickerKind::Session`, the returned data has no render path today
- double-invisible: unreachable state and unreachable UI

### 41. `/compact` response is silently dropped

Severity: Medium

Evidence:
- `/compact` sends `method: "command"` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:356)
- `handle_response` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:624) only matches `session.fork` and `session.list`; the `command` response falls through `_ => {}`

Impact:
- user runs `/compact`, sees no confirmation
- same shape as §7 (unknown slash) but on the response side

### 42. Second `approval` inbound overwrites the pending one with no queue

Severity: High

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:672) sets `state.approval = Some(...)` unconditionally
- same shape for `ask_user` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:687)

Impact:
- back-to-back approval requests drop the first silently
- the backend hangs indefinitely waiting for a response to the correlation id that will never be answered

### 43. Approval / ask-user response IDs share space with TUI-assigned IDs

Severity: Medium

Evidence:
- inbound request id stored at [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:673) via `msg.id.unwrap_or(0)`
- TUI's `next_request_id` starts at 1 and increments in [autocode/rtui/src/state/model.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/model.rs:169)
- no ID-space separation

Impact:
- a backend inbound request with id=5 is correlation-ambiguous with a TUI-originated request id=5
- `pending_requests` and inbound-request maps overlap; future additions can mis-route responses

### 44. Multiple stale pending requests collapse into a single banner

Severity: Medium

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:451) only sets `error_banner` when it is `None` — the first stale id wins
- subsequent stale ids are removed from `pending_requests` without banner updates

Impact:
- if three requests stall together, the user sees a timeout for only one
- the other two are invisibly dropped; no log cue on the user-facing path

### 45. PTY writer leaks outbound queue after a write error

Severity: Medium

Evidence:
- [autocode/rtui/src/rpc/bus.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/rpc/bus.rs:63) breaks the writer loop on write error
- `rpc_tx` in [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:98) remains alive; `UnboundedSender::send` continues to succeed
- no back-pressure path to the reducer, no visible error

Impact:
- when the backend pipe breaks, every subsequent `Effect::SendRpc` succeeds into a dead queue
- memory grows; user has no signal that their input is not reaching the backend

### 46. Editor launch crashes for any `$EDITOR` value with arguments

Severity: High

Evidence:
- [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:193): `Command::new(&editor).arg(&tmp_path)`
- `editor` is read verbatim from `$EDITOR`; `EDITOR="code --wait"` tries to exec a binary literally named `code --wait` and fails with ENOENT

Impact:
- anyone with `EDITOR="vim -p"`, `EDITOR="code --wait"`, `EDITOR="emacsclient -t"`, etc. cannot use `Ctrl+E`
- no user-visible error beyond a generic banner

### 47. Editor tempfile uses a predictable world-readable path

Severity: Medium

Evidence:
- [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:187): `format!("/tmp/autocode-editor-{}.md", std::process::id())`
- written with default umask (typically 0644); not cleaned up on crash

Impact:
- on a shared host, another user can read the user's draft prompt during the editor session
- symlink-collision potential if an attacker pre-places `/tmp/autocode-editor-<predicted-pid>.md` as a symlink

### 48. Editor round-trip competes with the main render loop

Severity: Medium

Evidence:
- [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:182) spawns the editor inside `tokio::task::spawn_blocking`, disabling raw mode
- the main `tokio::select!` loop continues pulling from `event_rx`, and the tick task continues firing `Event::Tick` every 100 ms
- each Tick while `Stage::Streaming` emits `Effect::Render` per [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:457)

Impact:
- during an in-flight turn, opening `$EDITOR` paints the TUI frame on top of the editor UI at 10 Hz
- keystrokes typed while the editor is foregrounded may be interpreted by the shell/terminal rather than the editor depending on timing

### 49. RPC reader has no line-length cap

Severity: High

Evidence:
- [autocode/rtui/src/rpc/bus.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/rpc/bus.rs:14) uses `BufReader::new(reader).read_line(&mut line)` with no `.take(n)` limit

Impact:
- a backend that emits a single line of 1 GB causes unbounded memory growth before the trailing `\n`
- the "1 MB+ line" requirement in §3.16 of the testing strategy is hoped for, not enforced
- a buggy or hostile backend can OOM the TUI

### 50. `Event::BackendExit` always reports code 0 regardless of actual exit status

Severity: Medium

Evidence:
- [autocode/rtui/src/rpc/bus.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/rpc/bus.rs:21): `event_tx.send(Event::BackendExit(0))` hardcoded
- `ChildGuard::try_wait` exists in [autocode/rtui/src/backend/process.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/backend/process.rs:31) but is not consulted by the reader

Impact:
- a backend that crashed with SIGSEGV is indistinguishable from clean EOF in the reducer
- user-facing error text cannot differentiate "backend crashed" from "backend exited normally"

### 51. Inline-mode editor return unconditionally enters alternate screen (extension of §25)

Severity: High

Evidence:
- [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:185): `LeaveAlternateScreen` called with no `if altscreen` guard
- [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:205): `EnterAlternateScreen` called with no `if altscreen` guard

Impact:
- confirms §25 via precise line references; the bug is on both the leave and the re-enter branch
- inline default silently flips to alt-screen semantics after the first `Ctrl+E`

### 52. `Stage::EditorLaunch` is never actually entered

Severity: Low

Evidence:
- no assignment to `Stage::EditorLaunch` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:1)
- the prompt mapping in [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:136) has a case for it that is unreachable dead code
- `Ctrl+E` in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:200) sets an `error_banner` but does not change `state.stage`

Impact:
- composer prompt stays `> ` during editor sessions; the intended `Editor... ` prompt never shows
- user cannot tell from the prompt that the TUI is mid-editor

### 53. Status-bar session-id truncation panics on non-ASCII IDs

Severity: Low (backend currently emits ASCII)

Evidence:
- [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:36): `let short = &sid[..sid.len().min(8)];` — byte slice

Impact:
- latent crash if backend ever returns a UTF-8 session identifier and byte 8 is not a char boundary

### 54. Palette filter accepts any `KeyCode::Char(c)` including control chars

Severity: Low

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:294) pushes `c` unconditionally
- picker variant in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:836) gates on `is_ascii_alphanumeric() || is_ascii_punctuation() || ' '`

Impact:
- palette filter can accumulate tab, control, or non-printing chars silently
- inconsistency between the two input surfaces is a refactor hazard

### 55. Palette Enter indexes the unfiltered entry list (precise line for §27)

Severity: High

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:267): `palette.entries.get(palette.cursor)` uses the backing vec
- cursor bound in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:287) is the unfiltered `entries.len()`

Impact:
- confirms §27 with the exact line references
- typed palette filter is decorative; selection dispatches against the backing list

### 56. History dedupe uses strict `==` and never caps the history size

Severity: Medium (strengthens §26)

Evidence:
- dedupe in [autocode/rtui/src/ui/composer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/composer.rs:37) compares `h.text == state.composer_text` — no trimming or normalization
- [autocode/rtui/src/ui/history.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/ui/history.rs:12) serializes the entire Vec on every turn with no cap

Impact:
- `" hi "` and `"hi"` are different history entries; trivial whitespace variants multiply the file
- no retention bound; power users can accumulate a multi-MB `history.json` that is rewritten every turn

### 57. Resize event is not clamped; tiny geometry hides the composer

Severity: Low

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:62) applies `(w, h)` unchanged
- layout is `[Length(1), Min(1), Length(2)]` in [autocode/rtui/src/render/view.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/render/view.rs:14); at height < 3 the middle `Min(1)` becomes 0 and content disappears

Impact:
- on very small terminals the composer and content area are not visible; TUI looks dead
- no minimum-size banner telling the user to enlarge

### 58. `tui.log` is append-only with no rotation or size cap

Severity: Low

Evidence:
- [autocode/rtui/src/main.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/main.rs:50): `OpenOptions::new().create(true).append(true).open(&log_path)`
- no rotation, no size check anywhere

Impact:
- long-lived installs accumulate GBs on disk
- `tracing::debug!` logs include `on_status` and other payloads — privacy + disk-usage risk

### 59. Tick only emits `Render` when `Stage::Streaming`

Severity: Low

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:457) gates the final Render push on `Stage::Streaming`
- the stale-request banner path in [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:451) only pushes Render when the banner was previously `None`

Impact:
- a stale-request banner set at t=30s during idle only appears visibly when the next keypress or RPC event triggers a render
- small correctness gap; can delay error visibility arbitrarily in idle sessions

### 60. Mouse events are silently dropped

Severity: Low

Evidence:
- [autocode/rtui/src/state/reducer.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/state/reducer.rs:36) maps only `Key` and `Resize`; everything else returns `None`
- no mouse-wheel binding to scrollback scroll

Impact:
- users who try to scroll with a mouse wheel discover scrolling does not work
- minor, but repeatedly raised by users of other terminal chat UIs

## New bug-finding strategies (2026-04-20 addendum)

These sweeps would have caught several of §28-§60 and are not currently represented in the TUI testing checklist or strategy doc. Treat each as a candidate addition to `docs/tui-testing/tui_testing_checklist.md`.

### S1. Reducer fuzz with arbitrary event sequences

Feed the pure reducer random `Event` streams (`Key`, `RpcNotification`, `Resize`, `Tick`, `Paste`) and assert invariants after every step:

- `composer_cursor <= composer_text.len()`
- `composer_text.is_char_boundary(composer_cursor)` ← would have caught §28 / §29
- `scrollback.len() <= 10_000`
- all `pending_requests` entries younger than `STALE_REQUEST_TIMEOUT + tick_grace`
- `next_request_id` strictly monotonic
- `state.picker.is_some() == matches!(state.stage, Stage::Picker(_))`
- `state.palette.is_some() == (state.stage == Stage::Palette)`

`proptest` or `arbitrary` crate; the reducer is pure, no I/O, cheap to run.

### S2. UTF-8 torture suite for composer + renderer

Pair input and render. Input set: basic ASCII, Latin-1 accents (`é`, `ñ`), CJK (`漢`, `日`), 4-byte emoji (`😀`, `🇺🇸`), ZWJ sequences (`👨‍👩‍👧`), RTL (Hebrew / Arabic), combining diacritics (`a` + `̀`), BiDi strings.

For each: insert → Left/Right nav → Backspace/Delete → render. Catches §28 / §29 / §53.

### S3. Render-panic smoke (pair S1 with ratatui `TestBackend`)

After every fuzz step in S1, call `Terminal::draw()` with `TestBackend::new(cols, rows)`. If draw panics, the reducer produced a state the renderer can't handle. Catches §29 and any future renderer that assumes invariants the reducer doesn't enforce.

### S4. ID-space audit

Static grep + runtime assertion that inbound-request ids and TUI-assigned ids do not overlap. Either pre-declare separate spaces (TUI uses positive, backend-inbound uses `INBOUND_BASE + n`) or track both in a single map with a tag. Catches §43.

### S5. ANSI-injection resistance for backend payloads

Send `on_token`, `on_thinking`, and error payloads containing: `\x1b[2J` (clear screen), `\x1b]0;foo\x07` (OSC set title), DCS, APC, raw BEL `\x07`, SI/SO. Assert the TUI renders them as literal text or strips them — never executes. Currently zero coverage.

### S6. Malformed-frame / giant-frame harness

Extend `autocode/tests/pty/mock_backend.py` with triggers:

- `__GIANT__` writes 1 GB of `x` without a trailing newline → catches §49
- `__INVALID_UTF8__` writes `\xff\xfe` then a valid line → catches lossy-decode assumptions
- `__WRONG_VERSION__` writes a frame with `"jsonrpc": "1.0"` → exercises codec reject path in [autocode/rtui/src/rpc/codec.rs](/home/bs01763/projects/ai/lowrescoder/autocode/rtui/src/rpc/codec.rs:12)

### S7. Modal-concurrency chaos

Scenarios:

- two `approval` inbounds 50 ms apart
- `approval` then `ask_user` 50 ms apart
- `ask_user` while `Picker` is open
- `approval` while `Palette` is open

Assert that the second modal either queues visibly or is rejected with an explicit backend error. Catches §42 and prevents future parallel-state regressions.

### S8. Mouse / unknown-crossterm-event smoke

Send `MouseEvent::ScrollUp` / `ScrollDown` to the key reader. Assert either it scrolls scrollback or it is explicitly documented as ignored. Catches §60 and documents the contract.

### S9. Editor-launch cross-environment matrix

Test `Ctrl+E` with `$EDITOR` values: `vim`, `nano`, `vim -p`, `code --wait`, `"ed with spaces"`, unset, `/nonexistent/bin/editor`. Assert graceful banner for each failure mode. Catches §46.

### S10. Long-session soak with resource-delta assertions

Script-backend run with 10 000 short turns. Measure:

- RSS delta (should be bounded)
- fd count via `ls /proc/<pid>/fd/ | wc -l` (should be stable)
- `~/.autocode/history.json` size (should be capped)
- `~/.autocode/tui.log` size (should be rotated or capped)

Catches §56 and §58.

### S11. Grep-based static-analysis pass

Cheap lints to add to CI or pre-commit:

- `String::remove\s*\(` not paired with `is_char_boundary` → §28 class
- `&\w+\[[^\]]*\.\.[^\]]*\]` on `String` / `&str` where the index comes from a `cursor` field → §29 / §53 class
- every `Option<...>` field on `AppState` must have a documented overwrite policy (ongoing vs. queued) → §34 / §42 class
- `eprintln!` / `println!` outside tests (already §3.20 in strategy — make it a clippy lint)

### S12. Renderer-reachability audit

Static check that every field on `AppState` has at least one read site in `autocode/rtui/src/render/view.rs`. A stored-but-unread field is a smell. Would have surfaced §37, §39, §40 (and §11 from the original inventory is one instance of this class).

Run as a `cargo test` that enumerates `AppState` fields via macro-derived metadata, or as a grep guard in CI.

## Not currently an issue in the live tree

These were previously raised in comms but are not current blockers in the code I inspected today:

- `autocode chat` default entrypoint now resolves the Rust binary via `_find_tui_binary()` and launches it directly:
  - [autocode/src/autocode/cli.py](/home/bs01763/projects/ai/lowrescoder/autocode/src/autocode/cli.py:212)
  - [autocode/src/autocode/cli.py](/home/bs01763/projects/ai/lowrescoder/autocode/src/autocode/cli.py:247)
- the old Python `--inline` fallback path is not in the current `chat()` signature anymore

## Remaining live verification work

Live runs completed so far in this session:

1. `cargo fmt -- --check`
2. `cargo clippy -- -D warnings`
3. `cargo test`
4. `cargo build --release`
5. `pty_smoke_rust_m1.py`
6. targeted Track 1 `model-picker`
7. targeted Track 1 `ask-user-prompt`
8. targeted Track 1 `startup`
9. targeted Track 1 `first-prompt-text`
10. targeted Track 1 `error-state`
11. targeted Track 1 `orphaned-startup`
12. targeted Track 1 `spinner-cadence`
13. Track 1 substrate/unit tests
14. Track 4 extractor + unit tests + live xfail scene set
15. VHS visual suite
16. `pty_smoke_rust_comprehensive.py`
17. attempted real-gateway PTY smoke via `pty_e2e_real_gateway.py`
18. direct manual Rust-binary real-backend PTY probe

Still worth running if we continue the full matrix:

1. full `make tui-regression` as a single top-level command, after deciding whether to preserve or fix the currently confirmed failures
2. a valid Rust-binary real-gateway PTY smoke harness, because the current `pty_e2e_real_gateway.py` is stale
3. deeper manual or scripted command-surface probes (`Ctrl+K`, `/sessions`, `/resume`, approval, ask-user`) if we want more evidence artifacts beyond the current issue inventory

## Current conclusion

The Rust TUI is buildable and test-green at the unit level, but it still has clear product-level and verification-surface issues.

The most important product issue from the user perspective is:

**slash commands do not behave like a modern selectable/autocomplete command surface.**

Right now the closest thing to that UX is `Ctrl+K`, not `/`.

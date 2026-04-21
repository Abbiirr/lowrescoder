# Stabilization + Claude-Code-Class Feature Parity Plan

> Owner: reviewers (Claude / Codex).
> Created: 2026-04-20.
> **Status: APPROVED** — user approved 2026-04-20 (Entry 1266). Stage 0A–4 cleared to execute. §14 Qs 1+2 locked: hand-maintained Markdown schema; one-release compat-shim window.
> Canonical companion docs: `PLAN.md` §1f/§1g/§1h, `EXECUTION_CHECKLIST.md`, `bugs/codex-tui-issue-inventory.md`, `docs/tui-testing/tui-testing-strategy.md`, `docs/tui-testing/tui_testing_checklist.md`.

## 0. Why this plan exists

`current_directives.md` and `EXECUTION_CHECKLIST.md` report **§1h Rust TUI Migration COMPLETE** as of 2026-04-19. The Rust binary is the sole interactive frontend, cargo gates are green, performance targets are met, and M11 cutover has shipped.

That is only the *engineering-gate* view of "done." The **product-gate** view, produced by direct source audit and live PTY probing on 2026-04-20 and captured in `bugs/codex-tui-issue-inventory.md`, is very different:

- **60 concrete defects** across visibility, UTF-8 safety, RPC correlation, modal concurrency, editor lifecycle, resource bounds, and renderer-reachability.
- **2 critical crashers** (Inventory §28, §29) that panic the TUI on the next keystroke after any non-ASCII input.
- **Protocol drift** between the Rust reducer and the Python backend (`ask_user` vs `on_ask_user`, `approval` vs `on_tool_request`, `on_tasks` vs `on_task_state`) — documented as Inventory §22 but broader than one method name.
- **Command-discovery surface is vestigial**: `/` opens nothing, `Ctrl+K` palette is visually empty and dispatches the unfiltered list on Enter, `/sessions` silently drops its own response.
- **Documentation ahead of reality**: root `README.md` still promises queued input / autocomplete / approvals as shipping defaults, while `autocode/rtui/README.md` still describes itself as only "M1 complete — scaffold + PTY launch + minimal RPC echo."

The Rust TUI is a working scaffold with several interaction-path mismatches, not a working replacement for the documented product. This plan replaces "patch 60 bugs one by one" with a structured sequence: **freeze the contract and harness first, harden the engine second, rebuild the visible UI surface third, restore modal/transcript correctness fourth, then layer inspection/polish work after the core interaction paths are green.** The cross-product parity surface (Claude Code / Codex / OpenCode / Pi / Goose) rides on top of that stack, not alongside it. The broader parity backlog is explicitly post-stabilization work, not part of the critical path for Stages 0-4.

## 1. Non-goals

- **Do not copy individual leaked-source behaviors.** Use only public docs, public repos, and published contracts.
- **Do not chase every P2 feature.** This plan gets to "Claude/Codex/OpenCode-class daily driver" — not feature-superset.
- **Do not grow the frontend.** Every new capability lands in the backend first; the TUI renders what the backend declares.
- **Do not keep compatibility shims forever.** Stage 0 adds dual-name RPC acceptance as a *transition* for one release window; Stage 4 removes them.
- **Do not merge parity features that regress the inventory.** The `tui_testing_checklist.md` §6.5 sweeps and §7 regression table are the ship gate.
- **Do not treat the follow-on feature backlog as execution approval.** Sections 9-11 are planning inventory only; builders should stay on Stages 0-4 unless the user explicitly expands scope.

## 2. Guiding principles

1. **Backend-canonical, TUI-thin.** Command inventory, permission policy, session state, plan/todo state, subagent orchestration, MCP registry, and instruction loading live in the Python backend. The Rust TUI asks the backend "what exists?" and renders.
2. **One versioned RPC schema.** All inbound/outbound names, types, and IDs are declared in a single versioned schema file. Both sides generate types from it and validate in CI.
3. **Crash-proofing before feature-chasing.** Unicode safety, RPC frame bounds, editor lifecycle, and modal queueing ship before any P0 feature work begins.
4. **Visible-surface rule wins every time.** If state is stored but not rendered, it doesn't exist. (`docs/tui-testing/tui-testing-strategy.md` §3.0.)
5. **Inventory-driven acceptance.** A stage is "done" when its bug-mapping rows (Section 13) flip to `closed` with evidence, the stage's §S-sweeps (Section 14) pass, and the relevant `tui_testing_checklist.md` Section 6.5 rows are green.
6. **Deliberate obsolescence.** Every compatibility shim added in Stage 0 is tagged with the commit that adds it; Stage 4 has a dedicated pass that removes every tagged shim.
7. **Week labels are sequencing hints, not promises.** Treat Weeks 1-5 as minimum serial order for planning, not guaranteed calendar duration.

## 3. Architecture target (end state)

```
┌──────────────────────────────┐       ┌──────────────────────────────┐
│ Rust TUI (autocode/rtui)     │◄─────►│ Python backend               │
│  - text-buffer core          │ JSON- │  - command registry          │
│  - command-registry renderer │ RPC   │  - permission policy         │
│  - modal stack               │ over  │  - session / checkpoint      │
│  - picker/palette/overlay    │ PTY   │  - plan / todo / task        │
│  - transcript panels         │       │  - subagent orchestrator     │
│  - inspection panels         │       │  - MCP / hooks / skills      │
│  - never owns feature state  │       │  - search / web / git        │
└──────────────────────────────┘       └──────────────────────────────┘
             ▲                                         ▲
             │                                         │
             └── Verification layer (CI + harnesses) ──┘
                 Track 1 · Track 4 · VHS · PTY · §S1-S12 sweeps
```

**TUI owns:** input, rendering, text editing, local scrollback, visual modes, keybinding interpretation, rendering of backend-declared state.

**Backend owns:** everything else — including what the TUI *can* do via the command registry.

**RPC schema owns:** the contract between them.

## 4. Stage 0 — Protocol freeze + harness retarget (WEEK 1)

Goal: make the TUI/backend contract single-source-of-truth; unblock every downstream stage without forcing optional registry/bootstrap expansion ahead of critical bug recovery.

Stage 0 is intentionally split:

- **Stage 0A** is mandatory and is the only part that must land before Stage 1/2 work begins.
- **Stage 0B** is optional and should only ship if Stage 2 still needs a richer backend-owned bootstrap/registry surface than dedicated endpoint calls can provide.

### 4.1 Stage 0A — schema, fixtures, aliases, harness hygiene

1. `docs/reference/rpc-schema-v1.md` — versioned schema file declaring every inbound notification, outbound notification, request/response pair, and all field types. Uses the protocol language already implied by `autocode/rtui/src/rpc/protocol.rs` but treats it as authoritative.
2. `autocode/src/autocode/backend/schema.py` — generated/hand-maintained Pydantic models matching §4.1.1. Both the backend server and the mock backend import from here.
3. `autocode/rtui/src/rpc/schema.rs` — matching serde structs, one-to-one with §4.1.1.
4. **Schema-owned fixture corpus + conformance test** (runs in CI for both sides): decode every published fixture from `autocode/tests/pty/fixtures/rpc-schema-v1/` in both Python and Rust and assert round-trip equality. `mock_backend.py` may consume these fixtures, but it is not the source of truth.
5. **RPC-name audit before shims land**: grep every `method:` site in `autocode/rtui/src/rpc/`, `autocode/src/autocode/backend/server.py`, and the PTY/mock harnesses; enumerate the full old/new method-name map in `rpc-schema-v1.md` before implementing any alias shim. The three pairs already identified (`ask_user` / `on_ask_user`, `approval` / `on_tool_request`, `on_tasks` / `on_task_state`) are the minimum known set, not the assumed complete set.
6. **Compatibility alias layer** in the Rust reducer: accept every audited dual-name pair from §4.1.5 during the transition window. Alias code tagged `// STAGE0_COMPAT_SHIM` so Stage 4 can strip it.
7. **Dedicated endpoint declarations for Stage 2 data sources**: Stage 0A schema explicitly declares the backend-owned inventory endpoints Stage 2 may call directly (`command.list`, `model.list`, `provider.list`, `session.list`, and any equivalent canonical names chosen in the schema) so Stage 2 does not depend on Stage 0B to be unblocked.
8. **Protocol/harness-facing doc sync pass**: update root `README.md`, `autocode/rtui/README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/session-onramp.md`, and PTY/VHS/Track-1/Track-4 harness READMEs to reflect the stabilized protocol/harness contract. Close Inventory §16/§17/§18/§19/§20 and the known Track 1 predicate-drift/docsync gap.

### 4.2 Stage 0B — backend registry/bootstrap (only if still needed after 0A)

If Stage 2 can remain correct by calling dedicated backend endpoints (`model.list`, `provider.list`, `session.list`, command registry endpoint, etc.), do that and skip `capabilities.get`. Only add a richer bootstrap snapshot if the UI still needs one coherent readiness payload.

1. **Bootstrap/registry RPC** `capabilities.get` — backend returns:
   - command inventory (name, description, hotkey, category, required permission)
   - picker inventories (model list, provider list, session list)
   - current plan mode, current session, current model, current provider
   - feature flags (mcp_enabled, hooks_enabled, skills_enabled, web_enabled, etc.)
   - loaded instruction sources (global AGENTS.md, project CLAUDE.md, local overrides)
   - permission mode (auto / per-tool / strict)
2. **Bootstrap-ready contract** documented in the schema: the app is considered ready when the agreed readiness signal arrives (`on_status`, `capabilities.get`, or a narrower equivalent). Stage 3 timeout handling must key off this standardized readiness contract rather than a single method name.
3. **Explicit Stage 0B decision memo** stored with the Stage 0A artifact: "ship 0B because X" or "skip 0B because endpoints Y/Z/W already cover Stage 2." Do not leave the 0B decision implicit.

### 4.3 Bugs closed by Stage 0A / 0B

- **Stage 0A** closes Inventory §16, §17, §18, §19, §20, §21, §22 and removes protocol/harness drift as a blocker for live bug work.
- **Stage 0B** closes Inventory §9 and any remaining inventory/bootstrap ownership questions if a shared bootstrap snapshot is actually introduced.
- Together they lay the foundation for §1, §2, §6, §7, §8, §10, §11, §34, §37, §40, §41 to close cleanly in Stage 2 / 3.

### 4.4 Verification gate

- CI: schema conformance test green on both sides against the schema-owned fixture corpus.
- CI: grep guard — every method name in `autocode/rtui/src/rpc/` appears in the schema doc.
- PTY: if Stage 0B ships, `capabilities.get` round-trip verified against mock backend; otherwise verify the dedicated Stage-2-facing endpoints directly.
- Doc: `tui_testing_checklist.md` Section 5 green (harness hygiene).

## 5. Stage 1 — TUI engine hardening (WEEK 2)

Goal: crash-proof the input/render core and terminal lifecycle.

### 5.1 Deliverables

1. **Shared text-buffer abstraction** `autocode/rtui/src/ui/textbuf.rs`:
   - Unicode-scalar-indexed cursor (not byte-indexed).
   - `insert(c)`, `delete_left()`, `delete_right()`, `move_left()`, `move_right()`, `move_word_left()`, `move_word_right()`, `home()`, `end()`, `clear()`.
   - `as_str()` returns the underlying `&str`; `char_boundary_cursor_byte()` returns the rendering cursor's *byte* index for `&str[..x]` slicing.
   - Used by composer, ask-user free-text, palette filter, picker filter. Single-implementation, single test matrix.
2. **UTF-8 torture test suite** per `tui_testing_checklist.md` §S2.
3. **Renderer boundary-safety**: replace `text[..cursor_pos.min(text.len())]` in `autocode/rtui/src/render/view.rs:144-145` with `textbuf`-aware slicing.
4. **Status-bar session-id truncation** (§53): use `str::ceil_char_boundary` or char-count slicing instead of byte slicing.
5. **Editor lifecycle rewrite** `autocode/rtui/src/main.rs:182-208`:
   - Parse `$EDITOR` with `shell_words` (or equivalent) to support `vim -p`, `code --wait`.
   - Use `tempfile::Builder` for secure, mode-0600 temp file in `$XDG_RUNTIME_DIR` (fallback `std::env::temp_dir()`).
   - Conditional alt-screen: only `LeaveAlternateScreen` / `EnterAlternateScreen` if the app is in altscreen mode.
   - Suspend the render loop (move to `Stage::EditorLaunch`) for the full editor lifetime; resume only on editor exit.
   - Unlink tempfile on success, panic, and Ctrl+C.
6. **RPC hardening**:
   - Cap `BufReader::read_line` via `.take(MAX_FRAME_BYTES)` (default 8 MiB, overrideable via `AUTOCODE_MAX_FRAME_BYTES`). Emit `Event::RpcFrameTooLarge` on overflow.
   - `Event::RpcFrameTooLarge` is terminal for the current backend session: banner the user, stop processing the corrupted/oversized stream, and require reconnect/restart rather than trying to continue on an unknown frame boundary.
   - Propagate writer errors from `bus.rs:63-66` to the reducer as `Event::BackendWriteFailed`; banner the user.
   - Preserve real exit status: `Event::BackendExit(status: ExitStatus)`; map to banner "backend crashed (code N)" vs clean exit.
7. **Inline terminal preservation**: remove the unconditional `terminal.clear()` at `autocode/rtui/src/main.rs:84`. In inline mode, the prior terminal content must survive startup (Inventory §24).
8. **Resize clamping**: minimum cols/rows in the reducer's `Resize` handler; below threshold, render a "Terminal too small (Nx M, needs W×H)" placeholder instead of collapsing the composer (§57).
9. **Tick-driven render**: Tick must emit `Render` whenever any of `error_banner`, `current_tool`, `stream_lines`, or stage is transitioning — not only during `Stage::Streaming` (§59).
10. **Mouse events**: handle `MouseEvent::ScrollUp` / `ScrollDown` → scroll scrollback; any other mouse event → document as ignored (§60).
11. **History**: atomic `rename(2)` write, size cap (default 5000 entries), whitespace-normalized dedupe key, fixed Up/Down traversal (§26, §30, §31, §56).
12. **`tui.log` rotation**: max 10 MiB primary + 3 rotated (§58).

### 5.2 Bugs closed by Stage 1

§24, §25, §26, §28, §29, §30, §31, §45, §46, §47, §48, §49, §50, §51, §52, §53, §56, §57, §58, §59, §60.

### 5.3 Verification gate

- `tui_testing_checklist.md` §6.5 S1, S2, S3, S6, S9, S10, S11 green.
- `cargo test` adds: `textbuf` property tests (proptest), editor-env matrix unit tests, RPC-frame-overflow unit test, resize-clamp unit test.
- Live PTY smoke with UTF-8 payload (`é`, `👨‍👩‍👧`, `日本語`, Hebrew) — no panic.
- `tui_testing_checklist.md` Section 7 rows for §28-§31 and §45-§60 flip to `closed` with evidence paths.

## 6. Stage 2 — Command registry + visible UI (WEEK 3)

Goal: make every command/picker/palette actually visible and dispatchable.

### 6.1 Deliverables

1. **Slash dropdown overlay** that opens on `/`:
   - Sources commands from the backend-owned command registry established in Stage 0A (direct endpoint or `capabilities.get`, whichever Stage 0 settled on).
   - Filters case-insensitively as the user types.
   - Arrow keys move a visible cursor; Enter / Tab complete the selected command into the composer; Escape closes.
   - Renders description + hotkey per entry.
2. **Ctrl+K palette rewrite**: same rendering as the slash overlay but modal (full list always visible, filter string shown as `[filter: xxx]`). Enter operates on the FILTERED list (`Inventory §55`). Palette filter rejects control chars (§54).
3. **Picker overlay** (`/model`, `/provider`, `/sessions`):
   - Reads inventory from backend-owned sources (not hardcoded), using direct endpoints unless Stage 0B intentionally introduced a bootstrap snapshot.
   - Visible header ("Select a model:"), visible option list with descriptions, visible filter state, visible cursor.
   - Selection operates on filtered visible list for all variants (fixes `Inventory §12` latent bug globally).
   - First Escape clears filter; second Escape exits.
4. **`/sessions` / `/resume` wiring**: on the backend session-list response, transition into `PickerKind::Session`; render rows with timestamp/title; Enter dispatches `session.resume` / `session.fork`.
5. **`/help` unification**: `/help` opens the same command overlay, pre-filtered to "all". Removes the static text-dump path (§8) and keeps the command inventory consistent across `/`, `Ctrl+K`, `/help`, and the welcome screen (§10).
6. **Unknown slash command** → visible scrollback line "Unknown command: `/foo` — try `/help`" (§7).
7. **`/compact` visible completion banner** — response handler appends a "Compacted N turns → M tokens" scrollback line (§41).
8. **Backend-owned command execution**: `/plan` calls backend `plan.set_mode`, the response drives a scrollback echo and a status-bar change. Plan-mode is no longer a local boolean flip (§33). `plan.set_mode` and its response shape must be declared in the Stage 0A schema before Stage 2 starts.
9. **Slash-command echo**: every slash dispatch writes a `/command` line into scrollback (§32).

### 6.2 Bugs closed by Stage 2

§1, §2, §3, §6, §7, §8, §10, §12, §27, §33, §40, §41, §54, §55.

### 6.3 Verification gate

- VHS scene set: `slash_autocomplete_open.png`, `palette_filtered.png`, `picker_model.png`, `picker_session.png`, `help_overlay.png`.
- Track 1 picker / palette predicates flip to PASS without xfail.
- `tui_testing_checklist.md` §2.1-§2.3, §3.5 green.

## 7. Stage 3 — Modal correctness, transcript integrity, and inspection surfaces (WEEK 4)

Goal: restore correct modal/transcript behavior first, then add the lower-priority inspection surfaces that depend on that state already being reliable.

### 7.1 Stage 3A — modal + transcript correctness (critical path)

1. **Modal stack** replacing `state.approval: Option<_>` / `state.ask_user: Option<_>`:
   - `state.modal_queue: VecDeque<ModalRequest>`.
   - `state.active_modal` is the head.
   - Queue semantics are explicit FIFO.
   - Inbound approval/ask-user push to the queue; the renderer always shows the head. `(Inventory §42, §43)`
   - RPC correlation IDs use an explicit `InboundId` wrapper so backend-issued and TUI-assigned IDs can never collide (§43).
   - Approval is only actionable until the backend signals the corresponding tool/request has already started. If the start signal wins the race, the queued approval becomes stale, the deny action must not pretend it prevented execution, and the UI surfaces that state explicitly.
2. **Approval modal rendering**:
   - Tool name, args snippet (truncated if > 80 chars, inspectable on `Space`), hotkey hints `[Y] [N] [A]`, `[I]nspect args` key.
3. **Ask-user modal rendering**:
   - Question text (verbatim), option list with cursor, free-text input via the Stage-1 `textbuf` when `allow_text == true`. Backspace/Delete/Left/Right all work (§5).
4. **Steer mode** (Ctrl+C during streaming): same free-text input path. Triple Ctrl+C within 2s hard-quits (§23).
5. **User-message echo**: every outbound `chat` writes the user text into scrollback immediately (§13).
6. **Warning banner**: backend stderr `WARNING:` lines appear as dim scrollback lines (§14).
7. **Silent-backend timeout**: no bootstrap-ready signal within 15s by default (`on_status`, `capabilities.get`, or whatever Stage 0 standardized) → visible banner "Backend not responding" (§15). The default is intentionally conservative for local startup jitter and should be overrideable via `AUTOCODE_BACKEND_READY_TIMEOUT_SECS`.
8. **Thinking flush**: `on_thinking` runs the same 20-line overflow drain as `on_token`; on stage-change or `on_done`, stream_lines always flush to scrollback (§35, §36).
9. **`Ctrl+L` dispatch unification**: both `Ctrl+L` and `/clear` call the same clear handler, which clears scrollback, stream_buf, stream_lines, error_banner, current_tool, followup_queue (§38).
10. **Stale-request banner**: maintain a stack of stale ids; banner shows "N requests timed out" when multiple pile up (§44).

### 7.2 Stage 3B — inspection panels + queue visibility (non-blocking after 3A)

1. **Task panel**: render `state.tasks` / `state.subagents` as a collapsible panel (default collapsed → `⏳ N bg` counter; expand on `Ctrl+T`). Shows task name, status, parent chain (§11).
2. **Tool-call panel**: render `ToolCallInfo.args` and `ToolCallInfo.result` when the current tool completes. Store concurrent calls as `state.active_tools: Vec<ToolCallInfo>` instead of a single `Option` (§34, §39).
3. **Followup queue visibility**: bounded (default 32 entries) with a banner `Queued: N` in the status bar; Ctrl+Q opens a scrollable queue view (§37).

### 7.3 Bugs closed by Stage 3A / 3B

- **Stage 3A** closes §4, §5, §13, §14, §15, §23, §32, §35, §36, §38, §42, §43, §44.
- **Stage 3B** closes §11, §34, §37, §39.

### 7.4 Verification gate

- **Stage 3A gate:** PTY smoke covers ask-user round-trip with free-text input, approval queue with 3 back-to-back requests, mid-streaming steer, silent-backend timeout, and warning/transcript visibility. `tui_testing_checklist.md` §2.4, §2.5, §2.6, §3.1, §3.2, §3.6 green. §S7 modal-concurrency sweep green.
- **Stage 3B gate:** PTY smoke adds task-panel expansion, tool-call inspection, and followup queue visibility. `tui_testing_checklist.md` §2.7 and any queue/panel-specific rows green.

## 8. Stage 4 — Persistence, polish, shim removal (WEEK 5)

Goal: close the long tail and strip Stage 0 transition shims.

### 8.1 Deliverables

1. Remove every `// STAGE0_COMPAT_SHIM` line — backend and mock backend emit only the new names.
2. Long-session soak (§S10): 10k-turn run against `mock_backend.py`; assert history, tui.log, RSS, fd count bounded.
   - `~/.autocode/history.json` stays within the configured entry cap.
   - `~/.autocode/tui.log*` rotates correctly (max primary + configured rotated files).
   - RSS delta stays bounded across the soak run.
   - open file-descriptor count stays bounded.
3. Welcome screen (optional, low-priority): renders from the stabilized backend-owned registry/bootstrap source on startup — no hardcoded banner text.
4. `autocode doctor` coverage for optional deps (already partially exists; lock it as Stage-4 gate).
5. Final pass over the inventory: every row closed or explicitly marked "accepted latent" with a named tracking issue.

### 8.2 Bugs closed by Stage 4

Any residual; Inventory §21 (Track 1 predicate drift) cleared by harness updates.

### 8.3 Verification gate

- `tui_testing_checklist.md` every section green against mock backend.
- `autocode/docs/qa/test-results/<date>-stabilization-verification.md` posted as artifact.

## 9. Deferred follow-on feature backlog (post-stabilization; separate execution approval)

Priority source: user's feature matrix, cross-referenced with Claude Code official docs, Codex TUI docs, OpenCode repo, Pi SDK docs, Goose repo.

Sections 9-11 are deliberately **not** part of stabilization execution approval. They are here so the post-stabilization backlog is visible, but builders should not start them during Stages 0-4 unless the user explicitly widens scope after Stage 3A is green.

### 9.1 Backend tools

| Tool | Contract | TUI rendering |
|---|---|---|
| `file.glob` | ripgrep-backed file pattern match; returns `[{path, size, mtime}]`, capped 10k | Tool-call panel: path list, truncation notice |
| `file.grep` | ripgrep-backed content search; returns `[{path, line, context}]`, capped 500 | Tool-call panel with jumpable anchors |
| `todo.read` / `todo.write` | Backend-owned todo store per session; persistent | Dedicated `Ctrl+T todo` panel, separate from task panel |
| `plan.start` / `plan.finish` / `plan.add` | Plan mode state machine in the backend | Status-bar `[PLAN]` + scrollback `/plan` echo + tasks visible |
| `checkpoint.create` / `checkpoint.list` / `checkpoint.restore` | Wraps existing `CheckpointStore`; exposes `/undo`, `/redo`, `/diff` | `/diff` opens a pager-style diff overlay; `/undo` / `/redo` show scrollback confirmation |
| `session.list` / `session.resume` / `session.fork` / `session.export` | Already partially in backend; complete wiring | Session picker (Stage 2); `/export` writes Markdown to a user-chosen path |
| `instruction.list` / `instruction.reload` | Returns loaded AGENTS.md / CLAUDE.md hierarchy | `Ctrl+I` panel shows "loaded instruction sources" |

### 9.2 TUI surfaces

- `@file` mention picker (Codex/OpenCode): `@` in composer opens a fuzzy file picker backed by `file.glob`; Enter inserts the path.
- `!shell` inline (Codex/OpenCode): `!cmd` in composer prefix dispatches to backend `shell.exec` with per-session approval cache.
- `/model`, `/provider`, `/sessions` pickers — already built in Stage 2.
- `/compact`, `/fork`, `/clear`, `/exit` — already routed.
- `/undo`, `/redo`, `/diff`, `/export` — new in P0.
- Non-interactive mode: `autocode chat --non-interactive --prompt "..."` path with strict JSON output; required for benchmark reliability.

### 9.3 Permission system

Tiered policy replacing `requires_approval: bool`:

- Per-tool default: `auto` / `ask_once` / `ask_session` / `deny`.
- Per-path policy for filesystem tools.
- Per-host policy for network tools (web_fetch, MCP).
- Session-scope memory: "allow for session" / "allow this path only" / "allow this host only".
- Surfaces through the approval modal (Stage 3) + `/permissions` command.

### 9.4 Instruction hierarchy

Precedence (highest wins for conflicting rules):

1. Project-local (`./CLAUDE.md`, `./AGENTS.md`)
2. Project-user-private (`./.local/CLAUDE.md`, gitignored)
3. User-global (`~/.autocode/CLAUDE.md`)

Exposed via `instruction.list`. Loaded sources visible in the `Ctrl+I` panel. Manual `/compact` produces a durable summary — auto-compaction tiers are P1.

### 9.5 Follow-on backlog acceptance gates

- `/undo`, `/redo`, `/diff` — PTY round-trip against a sample git edit.
- `@file` — fuzzy-match picker renders in under 50ms on a 10k-file repo.
- `!shell` — runs `echo hi`, asks for approval, caches session approval.
- Non-interactive: `autocode chat --prompt "2+2" --non-interactive --json` returns a valid JSON envelope.
- Permission system: `/permissions deny Bash` blocks every subsequent shell tool call until `/permissions auto Bash`.
- Instruction loading: a stray `CLAUDE.md` one level up in the tree is NOT loaded by default (strict project-root scoping).

## 10. P1 features (deferred follow-on backlog)

| Feature | Source | Approach |
|---|---|---|
| `web.search` / `web.fetch` | Claude Code, Codex | Backend tool; per-host allowlist in permissions |
| `edit.multi` (atomic multi-file) | Claude Code | Backend tool; single apply-or-rollback via `CheckpointStore` |
| `agent.spawn` as a first-class tool | Claude Code, Goose | Already exists as Subagent; re-expose as a tool-call in the same transcript |
| Parallel subagents | Goose | Scheduler in backend; TUI renders a concurrent-agent strip above scrollback |
| Hooks | Claude Code | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse` event pubsub; user-configurable via `~/.autocode/hooks.yaml` |
| MCP | Claude Code, OpenCode, Goose | Backend registers MCP servers; tools are exposed through the same command registry |
| Skills | Claude Code | Skill directory auto-loads from `~/.autocode/skills/` and `./skills/` |
| Custom slash commands | Claude Code, OpenCode | User-defined commands in `~/.autocode/commands/*.md` — auto-register into the command registry |
| `/review` | Codex | Opens a structured diff + review prompt against current session |
| `/commit` | Claude Code | Invokes backend `git.commit` with a summary from the session transcript |
| `/cost` | Claude Code | Reads `on_cost_update` stream; status-bar `$X.XX` |
| Worktree isolation | Claude Code | Backend `git.worktree_add` per session; opt-in |
| Memory / compaction tiers | Claude Code | Three-level: micro (per-turn), auto (per-N-turns), full (explicit) |

### 10.1 P1 acceptance gates

- MCP server registration round-trip (mock MCP stub).
- Parallel subagents: two delegated tasks run concurrently without race-corrupting the task panel.
- Hooks fire for all four lifecycle events; failure in a hook does not break the main loop.
- `/commit` produces a git commit that passes any configured pre-commit hook.

## 11. P2 features (deferred follow-on backlog)

- Notebook editing (`.ipynb`).
- Theme system (Codex/OpenCode parity).
- Markdown transcript export (already partially in P0 via `session.export`).
- Recipes/workflow YAML (Goose).
- Progressive reasoning-budget controls (Forge-style).

Defer until P1 acceptance gates are green. Revisit after user feedback.

## 12. Cross-cutting: verification & CI

Stages 0-4 enforce:

- **§S1-§S12 adversarial sweeps** per `docs/tui-testing/tui_testing_checklist.md` §6.5.
- **§3.0 visible-surface rule** per `docs/tui-testing/tui-testing-strategy.md`.
- **Inventory §1-§60 regression sweep** per `docs/tui-testing/tui_testing_checklist.md` §7.
- **Schema conformance CI** (Stage 0+).
- **Protocol drift alarm**: a `make proto-check` target grepping every `method:` site against the schema file.
- **Per-stage regression cascade**: after each stage gate turns green, rerun the earlier-stage sweeps it builds on (`§S1-§S12` + Section 7 rows relevant to prior stages) so later work cannot silently re-break stabilized behavior.

P0-P2 features add:

- Fixture corpus under `autocode/tests/pty/fixtures/` for `@file`, `!shell`, `/undo`, hooks, MCP stubs.
- Non-interactive mode golden JSON transcripts.

No stage ships without the `tui_testing_checklist.md` §6.5 sweeps that apply to its deliverables flipped to green.

Operational cadence: because agents do not commit, the intended workflow is **one user commit per green stage gate**. Each stage should leave the tree independently committable so the user can checkpoint and, if needed, revert at stage granularity.

## 13. Bug-to-stage mapping (Inventory §1-§60)

| Inventory # | Short label | Stage | Closing mechanism |
|---|---|---|---|
| 1 | Slash autocomplete missing | Stage 2 | Slash dropdown overlay from registry |
| 2 | Ctrl+K palette invisible | Stage 2 | Palette rewrite |
| 3 | Picker UI invisible | Stage 2 | Picker overlay |
| 4 | Ask-user / approval invisible | Stage 3 | Modal rendering |
| 5 | Free-text ask-user cannot type | Stage 3 | `textbuf` + ask-user input path |
| 6 | `/sessions` no visible browser | Stage 2 | Session picker wiring |
| 7 | Unknown slash silent fallthrough | Stage 2 | Scrollback error line |
| 8 | `/help` static dump | Stage 2 | Unified help overlay |
| 9 | Model/provider pickers hardcoded | Stage 0A | Schema-declared `model.list` / `provider.list` / `session.list` endpoints (or their canonical renamed equivalents) drive Stage 2 pickers directly; Stage 0B bootstrap snapshot is optional sugar, not the only path |
| 10 | Command inventory inconsistent | Stage 2 | Registry as single source |
| 11 | Task panel not rendered | Stage 3 | Task panel |
| 12 | Session picker filtered-selection | Stage 2 | Filtered-list selection global fix |
| 13 | User messages not echoed | Stage 3 | Composer echoes on send |
| 14 | Warnings not surfaced | Stage 3 | Dim scrollback banner |
| 15 | Silent-backend timeout | Stage 3 | 15s bootstrap timeout banner |
| 16-20 | Harness/doc drift | Stage 0 + Stage 4 | Harness retarget + doc sync |
| 21 | Predicate drift | Stage 0A | Harness/doc sync + predicate rewrite against the stabilized Rust-visible contract |
| 22 | `ask_user` protocol mismatch | Stage 0 | Schema + alias shim |
| 23 | Triple Ctrl+C no hard-quit | Stage 3 | Press-counter in steer path |
| 24 | Inline clears terminal | Stage 1 | Remove `terminal.clear()` |
| 25 | Editor altscreen forced | Stage 1 | Conditional altscreen |
| 26 | History non-atomic + unbounded | Stage 1 | Atomic write + cap |
| 27 | Palette Enter dispatches unfiltered | Stage 2 | Palette rewrite |
| 28 | **UTF-8 Backspace panic** | Stage 1 | `textbuf` |
| 29 | **Renderer UTF-8 panic** | Stage 1 | `textbuf` boundary slicing |
| 30 | History Up stuck | Stage 1 | Correct traversal |
| 31 | Frecency sort broken | Stage 1 | Logarithmic scoring |
| 32 | Slash commands not echoed | Stage 3 | Scrollback echo |
| 33 | `/plan` only status-bar tag | Stage 2 | Backend-owned plan state |
| 34 | Parallel tools overwritten | Stage 3 | `active_tools: Vec<_>` |
| 35 | `on_thinking` no flush | Stage 3 | Unified overflow drain |
| 36 | Tokens absorbed during modal | Stage 3 | Modal stack + stage rule |
| 37 | `followup_queue` invisible | Stage 3 | Queue banner + Ctrl+Q view |
| 38 | Ctrl+L bypasses `/clear` | Stage 3 | Unified clear handler |
| 39 | ToolCall args/result unrendered | Stage 3 | Tool-call panel |
| 40 | `session_list` no render path | Stage 2 | Session picker |
| 41 | `/compact` response dropped | Stage 2 | Scrollback banner on response |
| 42 | Second approval overwrites | Stage 3 | Modal queue |
| 43 | Approval ID-space collision | Stage 3 | `InboundId` wrapper |
| 44 | Stale-request banner collapse | Stage 1 / Stage 3 | Stale-id stack |
| 45 | PTY writer leaks | Stage 1 | Writer failure → reducer |
| 46 | `$EDITOR` with args crashes | Stage 1 | `shell_words` parse |
| 47 | Editor tempfile predictable | Stage 1 | `tempfile` with 0600 |
| 48 | Editor competes with render | Stage 1 | Suspend render loop |
| 49 | RPC no line cap | Stage 1 | `.take(MAX_FRAME_BYTES)` |
| 50 | BackendExit hardcoded 0 | Stage 1 | Real `ExitStatus` |
| 51 | Editor unconditional altscreen | Stage 1 | Conditional altscreen |
| 52 | `Stage::EditorLaunch` unreached | Stage 1 | Set in Ctrl+E handler |
| 53 | Session-id slice panic | Stage 1 | `ceil_char_boundary` |
| 54 | Palette filter control chars | Stage 2 | Char class guard |
| 55 | Palette Enter unfiltered | Stage 2 | Selection on filtered list |
| 56 | History dedupe strict-`==` | Stage 1 | Normalized key + cap |
| 57 | Resize unclamped | Stage 1 | Min-size placeholder |
| 58 | `tui.log` no rotation | Stage 1 | Rotating file appender |
| 59 | Tick only renders Streaming | Stage 1 | Dirty-bit driven tick |
| 60 | Mouse events dropped | Stage 1 | Scroll-wheel mapping |

## 14. Decisions and open questions

### 14.1 Decided (locked 2026-04-20 by user)

1. **Schema source format — LOCKED**: **hand-maintained Markdown** with fenced code-blocks in `docs/reference/rpc-schema-v1.md`. Zero toolchain cost, single source both sides read. Revisit at Stage 4 only if drift recurs.
2. **Compat-shim release window — LOCKED**: **one release**. Removal is gated on "backend + mock backend + every known external consumer" being on the new names. Every shim carries a `// STAGE0_COMPAT_SHIM` tag; Stage 4 strips every tagged line.

### 14.2 Still open (non-blocking for Stage 0A kickoff)

3. **Non-interactive mode JSON envelope**: define early (Stage 0 schema) or at post-stabilization backlog time? Claude opinion: define early if benchmark harnesses need it soon; otherwise keep it out of Stage 0A and revisit once Stage 3A is green.
4. **Worktree isolation as P0 vs P1**: user's matrix says P2; Codex-class UX would argue P1. Claude opinion: backlog question only, not a Stage 0A blocker.
5. **MCP as P1 vs P0**: the Claude Code product leans heavily on MCP. Claude opinion: backlog question only, not a Stage 0A blocker; adding MCP too early will dominate schema work.

## 15. Directly actionable next steps

1. **Approve or reject the narrowed Stage 0A / Stage 1 / Stage 2 / Stage 3A path** — this is the critical-path execution decision.
2. **Appoint a builder** for Stage 0A (OpenCode suggested per the §1h pattern).
3. **Lock a Stage 0A artifact date** so `EXECUTION_CHECKLIST.md` can move to "Stabilization Sprint, Stage 0A active."
4. **Update `current_directives.md`** to reflect that §1h COMPLETE was an engineering gate, not a product gate.
5. **Treat Sections 9-11 as deferred backlog** until Stage 3A is green or the user explicitly widens scope.

Only Questions 1-2 in Section 14 affect Stage 0A kickoff. Questions 3-5 can remain open while stabilization starts. The first required artifact should be `docs/reference/rpc-schema-v1.md` plus the schema-owned fixture corpus in `autocode/tests/pty/fixtures/rpc-schema-v1/`.

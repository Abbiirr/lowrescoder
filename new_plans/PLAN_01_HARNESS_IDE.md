# PLAN_01 — The "AI Harness Capable IDE" Brief

> Plan 1 of 3. This is the substrate for PLAN_03 (the full Codex/Cursor IDE). It specifies the **IDE surface that exposes IDE features to agents as token-efficient tools**, fronted by a **Codex-CLI-style REPL** that the operator sees. The operator does not see agents, tool calls, JSON-RPC, or model reasoning — only user-meaningful state (file, region, operation, progress, result). Agents are invisible machinery behind the REPL.

**Companion plans in this set**
- `PLAN_01_HARNESS_IDE.md` (this file) — the agent-facing IDE surface + REPL UI.
- `PLAN_02_VIDEO_AGENT.md` — separate product; an agentic general-purpose video editor.
- `PLAN_03_FULL_CODEX_IDE.md` — the consumer-facing IDE that embeds PLAN_01 as its agent panel and diff-hunk surface.

**Existing corpus in `new_plans/` that this plan composes with**
- `01-trust-domains.md` — the five-trust-domain model (planner proposes, compiler authorizes). PLAN_01 is the *policy + render domain* of an IDE.
- `01-phase-plan.md` — phased build pattern. PLAN_01 follows the same shape.
- `00-adversarial-validation.md` — the security layer we inherit (instruction/data separation, deny-by-default egress, audit log).
- `autocode-station-requirements.md` — the editor + collaboration + approval requirements that PLAN_01's REPL must satisfy (Accept/Reject/Ask-why hunks, maker/checker, audit log).
- `market-research-agent-cockpit (1).md` — Codex app / Claude Code desktop / T3 Code / Conductor / Vibe Kanban teardowns that fix the design vocabulary.

The brief is structured as: thesis → design language → tool surface → permission model → session/lifecycle → UI specification → agent-bridge → phase plan → open questions. Each section ends with a short "**How this inherits from existing corpus**" callout so the plan composes rather than duplicates.

---

## 0. Thesis — what this is, what it isn't

### 0.1 What it is

An **IDE whose operator-facing UI is a Codex-CLI-style REPL** and whose **back-end exposes every IDE feature as a typed, token-efficient MCP tool** that any harness (Claude Code, Codex CLI, OpenCode, Aider, custom agents) can call. The harness is the agent runtime; the IDE is the agent's *control plane* and *tool surface*.

- The user types `edit auth/session.ts so the token is rotated on every refresh` into a REPL.
- Behind the scenes, the agent invokes `edit_file`, `read_range`, `lsp_definition`, `lsp_references`, `diagnostics`, `run_command`, `git_checkpoint`, etc. — all MCP tools served by the IDE.
- The REPL shows user-meaningful state: `Edited auth/session.ts:42–57`, `Found 4 references`, `Linting... 0 errors`, `Checkpoint #3 saved`.
- The user never sees JSON-RPC, tool_use_ids, raw diffs unless they ask, or model chain-of-thought.

### 0.2 What it isn't

- It is **not** a wrapper around an existing CLI (no `codex exec` pumping). It is a control plane and a tool bus; the agent runtime is pluggable.
- It is **not** a full desktop IDE with a file tree, tabs, terminal panel, and a debug view. That is PLAN_03. PLAN_01 is the *agent-facing substrate* PLAN_03 embeds.
- It is **not** a chat product. The REPL is a working surface; the chat is a *narrow band of the working surface*.
- It is **not** an agent-cockpit dashboard (T3/Conductor-style "run N agents in parallel, pick a winner"). Cockpits orchestrate agents; PLAN_01 *is* an agent's environment.

### 0.3 The three design constraints (in priority order)

1. **The user sees UI, not agents.** Every tool result renders as user-meaningful state. No raw JSON. No tool IDs as primary state. No model reasoning. *(AutoCode Station §3.2's "agent edits as first-class pending hunks" is the precedent.)*
2. **Token efficiency is a load-bearing requirement.** Every tool is designed to return the *minimum* bytes that preserve the agent's ability to act. LSP replaces content reads; symbol references replace grep-and-parse; structured diffs replace full-file rewrites.
3. **The 5-trust-domain model applies.** The agent (planning domain) sees only the symbolic surface; the compiler (policy + render domain) authorizes every side effect; the analysis domain (LSP/lint/typecheck workers) sees raw files but cannot act; the artifact domain is the git repo. *(From `01-trust-domains.md`.)*

### 0.4 How this inherits from existing corpus

**From `01-trust-domains.md`:** PLAN_01 is the **policy + render domain** in IDE clothing. The MCP tool surface is the narrow interface between the *privileged* LLM (the agent) and the *non-LLM* policy compiler that authorizes tool calls. Instruction/data separation is enforced at the prompt and at the tool surface: the agent never receives raw file bytes when a structural query would do, and OCR/transcript content carried into the agent is always labelled untrusted.

**From `autocode-station-requirements.md` §3.2:** the "pending hunk anchored at its target line, labelled with its source" requirement is the unit of agent edit in PLAN_01. The `accept`/`reject`/`ask_why` verbs are MCP tool calls; the UI shows hunks. The status bar reflects pending vs staged counts.

**From `market-research-agent-cockpit (1).md` §4:** Codex's design language — collapsed single-line rows, hairline borders, color reserved for status — is the visual grammar. The Codex TUI shell (composer, slash commands, keybindings) is the operator's mental model.

---

## 1. Design language — what the REPL looks like

### 1.1 The reference: Codex CLI's TUI

The Codex CLI is the operator UI to clone. Source: [openai/codex](https://github.com/openai/codex) (Rust 96.3%); TUI shell documented at [developers.openai.com/codex/cli/features](https://developers.openai.com/codex/cli/features) and [slash-commands](https://developers.openai.com/codex/cli/slash-commands).

Key UI conventions, verified from docs:

- **Composer at the bottom, reserved space**; toasts go top-right; approval cards never overlapped.
- **Agent activity renders as collapsed single-line rows**: `Edited 3 files`, `Ran pytest`, `Read src/foo.py`. Expand on demand to reveal the structured payload.
- **Slash commands** with autocomplete and queueing: `/model`, `/plan`, `/permissions`, `/diff`, `/review`, `/mcp`, `/skills`, `/init`, `/status`, `/usage`, `/statusline`, etc.
- **Keybindings** (the operator's muscle memory): `Tab` queues follow-up input; `Enter` sends; `Up`/`Down` navigates draft history; `Ctrl+R` searches prompt history; `Ctrl+L` clears; `Ctrl+O` copies last assistant output; `Ctrl+G` opens `$VISUAL`/`$EDITOR`; `@` opens fuzzy file search in composer; `!cmd` runs shell inline; `Double-Esc` edits the previous user message.
- **Plan mode vs exec mode** — `/plan` switches; the plan-mode UI shows the proposed step list as a numbered list with accept/reject per step.
- **Modes are visible state** in the top bar: current model, approval policy, working directory, context budget, thread ID.

### 1.2 The PLAN_01 REPL's deviations from Codex CLI

| Aspect | Codex CLI | PLAN_01 |
|---|---|---|
| Underlying runtime | `codex` agent loop in Rust | Pluggable: Codex CLI, Claude Code, OpenCode, custom |
| Connection | Single-process | MCP stdio (local) or Streamable HTTP (remote) over `app-server`-style WebSocket |
| Tool surface | Codex-internal tools | MCP tools served by the IDE (this plan's contribution) |
| Persistence | `codex resume` session picker | Same shape (`{ts}_{cwd_hash}.jsonl`) plus per-tool-call hashes for replay |
| Approval model | `untrusted`/`on-request`/`never` + permission profiles | Same, plus a `policy` scope that writes to the audit log (AutoCode Station §5) |
| Renderer | ratatui / crossterm | ratatui (Rust) for the TUI; Tauri or Electron if a GUI client is desired |

The REPL is the same surface the user already knows; the only difference is the *backend* the agent calls into.

### 1.3 Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ● model: claude-opus-4-7  │  ⊕ policy: workspace  │  /home/user/proj  │ 73% │  ← status bar
├──────────────────────────────────────────────────────┬───────────────────────┤
│                                                      │  REVIEW (right rail)  │
│   ▸ Read src/auth/session.ts                         │                       │
│   ▸ LSP definition at session.ts:42                  │   ⟳ Pending hunks (2)  │
│     → src/auth/store.ts:88                          │   ─ src/auth/sess…    │
│   ▸ Edit src/auth/session.ts:42–57                  │     + token = rotate  │
│   ▸ Read src/auth/store.ts:88–110                   │     − token = keep    │
│   ▸ Edit src/auth/store.ts:88–97                    │     [Accept][Reject]  │
│   ▸ Run cargo test --workspace                      │   ─ src/auth/stor…    │
│     ✓ 142 passed; 0 failed                          │     [Accept][Reject]  │
│   ▸ Checkpoint #3 saved                             │                       │
│                                                      │   ⟳ Audit log          │
│                                                      │   • 14:32 edit accept  │
│                                                      │   • 14:33 cargo test   │
├──────────────────────────────────────────────────────┴───────────────────────┤
│ ▌ edit auth/session.ts so the token is rotated on every refresh  ▌  [Send]  │  ← composer
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Left (wide conversation column)**: collapsed one-line rows for every tool call. Expand on demand; never show JSON.
- **Right (review rail)**: pending hunks, audit log, approval cards. Quiet until there's something to act on.
- **Bottom (composer)**: reserved; never overlapped by tool rows or approval cards.
- **Top (status bar)**: model, policy, cwd, context window, thread id, current mode (plan/exec).

### 1.4 How this inherits from existing corpus

**From `market-research-agent-cockpit (1).md` §4 (Codex design language):** "paper-white surfaces, hairline borders, almost no chrome; a slim plain-text sidebar; a wide centered conversation column where agent activity renders as collapsed single-line rows … color reserved for status dots and diff +/−. Information density comes from typography and spacing, not boxes." This plan adopts that grammar verbatim.

**From `autocode-station-requirements.md` §3:** the right-rail review pane is the AutoCode Station "review rail" pattern; the pending-hunk UX is the AutoCode Station "pending hunk anchored at its target line" requirement, surfaced in the REPL.

---

## 2. Tool surface — the IDE as an MCP server

This is the heart of the plan. The IDE exposes a typed MCP server whose tools are the agent's vocabulary. Every tool is designed for token efficiency: it returns the minimum bytes that preserve the agent's ability to act.

### 2.1 The principle

**The agent never reads a whole file when a structural query would do.** Every "I want to know X about the code" question has a tool that returns a compact, structured answer. The agent reasons over structure, not over bytes.

The set below is the agent's vocabulary. Every name is canonical, every schema is JSON-Schema validated, every result is a typed MCP `content` array (`text`, `diff`, `diagnostic`, `symbol`, `command_result`, `image`, `resource_link`).

### 2.2 The tool registry (v1)

#### 2.2.1 File system — read/edit with surgical precision

| Tool | Purpose | Token-efficiency principle |
|---|---|---|
| `read_range` | Read `file_path` from `offset` (line) for `limit` lines. | Returns lines with `line_no: content` format; caps at N lines; returns a `PARTIAL` notice when truncated. |
| `read_symbol` | Read the body of a named symbol (`function`, `class`, `method`, `interface`) by LSP `documentSymbol` + slice. | Returns only the symbol's source range — never the file. |
| `list_files` | Glob a workspace subtree. | Caps at 100 results with truncation flag; respects `.gitignore`; `head_limit` parameter. |
| `stat_file` | Size, mtime, hash, language, line count. | One round trip; no content. |
| `edit_file` | Surgical edit: `old_string` → `new_string`. Requires read-before-edit. Optional `replace_all`. | Returns the resulting unified diff as a typed `diff` content block. |
| `write_file` | Create or overwrite. | Returns the file's hash; emits a `diff` content block if the file existed. |
| `move_path` / `delete_path` | Tree operations. | Requires read-before-delete for safety; logs to audit. |

**`edit_file` schema** (canonical, used in permission rules and hook matchers):

```jsonc
{
  "name": "edit_file",
  "inputSchema": {
    "type": "object",
    "required": ["file_path", "old_string", "new_string"],
    "properties": {
      "file_path":   { "type": "string" },
      "old_string":  { "type": "string", "description": "Exact substring to match; must be unique unless replace_all." },
      "new_string":  { "type": "string" },
      "replace_all": { "type": "boolean", "default": false }
    }
  }
}
```

The harness enforces three checks the agent cannot bypass: (1) the file was read in this session and not changed since, (2) `old_string` exists, (3) `old_string` is unique unless `replace_all: true`. Rejections return explainable violations — never silent failures.

#### 2.2.2 Search — ripgrep-shaped, content-bounded

| Tool | Purpose | Modes |
|---|---|---|
| `grep` | ripgrep-backed regex. | `files_with_matches` (default), `content` (lines with `file:line:col`), `count`. `glob`/`type`/`multiline` filters. `.gitignore`-aware. |
| `list_files` | Glob. | Capped at 100. |
| `semantic_search` | Embedding-indexed natural-language search over the workspace. | Returns top-K with file:line:col anchors and a relevance score. |

**The token-efficiency rule:** `grep` defaults to `files_with_matches`; the agent only requests `content` when it needs the lines. `head_limit` caps the result set. The agent never receives whole files as a search result.

#### 2.2.3 LSP — structural queries replace content reads

| Tool | Wraps | Returns |
|---|---|---|
| `lsp_definition` | `textDocument/definition` | `Location[]` (file + range). |
| `lsp_references` | `textDocument/references` | `Location[]` (with line content preview, max 1 line each). |
| `lsp_hover` | `textDocument/hover` | Annotated type + 1-paragraph doc. |
| `lsp_symbols` | `textDocument/documentSymbol` | Hierarchical tree of the file's symbols. |
| `lsp_workspace_symbols` | `workspace/symbol` | Server-indexed search across the workspace. |
| `lsp_rename` | `textDocument/rename` | `WorkspaceEdit` (the server does the rename; the IDE applies it). |
| `lsp_code_action` | `textDocument/codeAction` | `CodeAction[]` (refactor, quick-fix, source action). |
| `lsp_format` | `textDocument/formatting` / `rangeFormatting` | `TextEdit[]` applied as a `diff` content block. |
| `lsp_diagnostics` | `textDocument/publishDiagnostics` snapshot | `Diagnostic[]` (severity, message, range, code, source). Pushed automatically after `didChange`. |
| `lsp_completion` | `textDocument/completion` | `CompletionItem[]` (label, kind, detail, optional `documentation`). |
| `lsp_implementation` | `textDocument/implementation` | `Location[]` for interface → concrete. |
| `lsp_type_definition` | `textDocument/typeDefinition` | `Location[]` for expressions. |
| `lsp_inlay_hints` | `textDocument/inlayHint` | Per-line annotation hints. |
| `lsp_call_hierarchy` | `prepareCallHierarchy` + `incomingCalls`/`outgoingCalls` | Hierarchical call graph. |

**The token-savings pattern:**

| Want | Bad pattern | LSP-backed pattern |
|---|---|---|
| Find a symbol's definition | Read whole file | `lsp_definition` → 1 location |
| All references to a function | Read whole file | `lsp_references` → locations list |
| Type of an expression | Read whole file | `lsp_hover` → annotated type |
| Rename a symbol across the codebase | Read every file, find matches, write every file | `lsp_rename` → server returns `WorkspaceEdit`; the IDE applies it |
| Refactor (extract function, inline) | Manual edits in many files | `lsp_code_action` → `WorkspaceEdit` with safe edits |
| What diagnostics exist | Run compiler, parse output | Server pushes `lsp_diagnostics` automatically after every edit |

#### 2.2.4 Lint / typecheck — feedback signals

| Tool | Purpose |
|---|---|
| `run_linter` | Run a project-configured linter (eslint, ruff, clippy, etc.) over a path or workspace. |
| `run_typecheck` | Run the project's typechecker (tsc, mypy, cargo check, etc.). |
| `lint_diagnostics` | Return a snapshot of current diagnostics (LSP + lint + typecheck merged). |

**Pattern:** after every `edit_file`, the IDE runs a fast feedback loop (typecheck on the changed file, then lint) and surfaces diagnostics as a `lint_diagnostics` push. This is exactly Claude Code's `LSP` tool behavior: "after each file edit, it automatically reports type errors and warnings so Claude can fix issues without a separate build step." *(From [code.claude.com/docs/en/tools-reference](https://code.claude.com/docs/en/tools-reference).)*

#### 2.2.5 Run / shell — sandboxed, approved, audited

| Tool | Purpose |
|---|---|
| `run_command` | Run a shell command in the thread's mode (local/worktree/cloud). |
| `background_process` | Start a long-running process (dev server, watcher). Stream output. |
| `tail_output` | Get the last N lines of a background process. |

**The approval card** (UI, per AutoCode Station §5.1) shows: exact command, why (agent's stated reason), scope (cwd, filesystem read/write, network allowed/blocked, secrets available/unavailable), origin (agent / `AGENTS.md` / `package.json` / user), policy rule matched, risk class, repeat-vs-new. Actions: `Approve once` / `Approve test commands for this task` / `Deny with note`. Approval cards are never overlapped by composer, terminal, or toasts.

#### 2.2.6 Git — checkpoint, review, ship

| Tool | Purpose |
|---|---|
| `git_status` | Current branch, dirty files, ahead/behind. |
| `git_diff` | `git diff` (staged / unstaged / untracked); supports `path` and `commit_range`. |
| `git_log` | Last N commits, optional path filter. |
| `git_blame` | Per-line author + commit. |
| `git_checkpoint` | Stash-or-`git notes`-based snapshot with a name. The operator's "rewind" button. |
| `git_restore_checkpoint` | Restore a named checkpoint. |
| `git_commit` | Stage + commit (with the agent's proposed message); operator approves. |
| `git_push` | Push; operator approves. |
| `open_pr` | Open a PR via host (GitHub/GitLab/Bitbucket OAuth). |
| `git_review` | "Review my working tree" — same shape as Codex's `/review`. |

`git_checkpoint` is the operator's safety net. Every accepted edit auto-checkpoints (configurable: every N edits, or on a schedule). The REPL footer shows the most recent checkpoint; the right rail lists checkpoint history with one-click restore.

#### 2.2.7 Browser / Playwright — for web tasks

| Tool | Purpose |
|---|---|
| `browser_navigate` | Open a URL. |
| `browser_snapshot` | Capture the accessibility tree (not a screenshot) — token-efficient by an order of magnitude. |
| `browser_click` / `browser_type` / `browser_press` | Interact with the page. |
| `browser_console` | Get console messages. |
| `browser_network` | Get network log. |
| `browser_screenshot` | Take a screenshot when the agent needs to see pixels (e.g. visual diffs). |

**All browser-derived content is labelled untrusted** in the agent's context, per instruction/data separation (`01-trust-domains.md` §1 data-flow rule 1: "Raw media flows only into Analysis. Never into Planning."). The agent's prompt structure carries the snapshot as a `role: "evidence"` block, never as `role: "user"`.

#### 2.2.8 Session / introspection

| Tool | Purpose |
|---|---|
| `list_threads` | Enumerate the operator's threads. |
| `switch_thread` | Switch the active thread (the operator's context). |
| `get_diff` | Return the working diff (this thread's pending + staged + committed). |
| `get_status` | Model, policy, cwd, context budget, mode, pending hunks count. |
| `request_user_input` | Pause and ask the operator a multiple-choice question (mirror of Claude Code's `AskUserQuestion`). |

### 2.3 Tool result shape (MCP content blocks)

Every tool returns an MCP `content: [...]` array. Typed blocks:

- `text` — narrative, terminal output, search hits as `file:line: content`.
- `diff` — unified diff (header, hunk header, +/- lines). The UI renders this as a hunk in the review rail.
- `diagnostic` — `Diagnostic` (severity, message, range, code, source). The UI renders this as a gutter marker + problems panel.
- `symbol` — `DocumentSymbol` (name, kind, range, children). The UI renders this as an outline.
- `command_result` — `exit_code`, `stdout`, `stderr`, `duration_ms`, `truncated`. The UI renders this as a collapsible row.
- `image` — base64 PNG/JPEG with dimensions. The UI renders this as a thumbnail.
- `resource_link` — `uri` + `name` + `mimeType` pointing at an MCP `Resource` for lazy follow-up.

This typed-content pattern is the same one MCP itself uses (`modelcontextprotocol.io/docs/learn/architecture`). The benefit: the UI can render each kind appropriately without parsing prose.

### 2.4 Tool registry wiring (MCP server lifecycle)

The IDE boots a single MCP server (stdio by default, Streamable HTTP if remote) on `mcp://ide`. At startup:

1. `initialize` → server returns capabilities (`tools`, `resources`, `prompts`).
2. `notifications/initialized` → server is ready.
3. The agent calls `tools/list` → IDE returns the full tool registry (section 2.2) with one canonical schema per tool.
4. The agent calls `tools/call` → IDE validates, executes under policy, returns typed content.
5. Server pushes `notifications/tools/list_changed` if extensions are installed/removed.

The agent never calls anything outside this registry. The IDE is the agent's *entire* tool universe for code work; other MCP servers (linter wrappers, database tools, design tools) plug in via the same lifecycle.

### 2.5 How this inherits from existing corpus

**From Claude Code's `tools-reference`:** the tool names (`Read`, `Edit`, `Write`, `Grep`, `Glob`, `Bash`, `LSP`, `WebFetch`, `WebSearch`, `Monitor`, `Skill`, `Agent`, `AskUserQuestion`, `TaskCreate`) are the canonical vocabulary an agent expects. PLAN_01's tool registry mirrors these names where the semantics match, and extends with IDE-native verbs (`lsp_*`, `lint_diagnostics`, `git_checkpoint`, `run_linter`).

**From MCP architecture:** the IDE is a *server*; the harness is a *host*; the connection is JSON-RPC 2.0. This is the same pattern Codex CLI already supports: "Codex can itself run as an MCP server." *(Verified from [developers.openai.com/codex/cli/features](https://developers.openai.com/codex/cli/features).)*

**From `autocode-station-requirements.md` §3.2:** "Each agent edit appears as a pending hunk anchored at its target line, labelled with its source." PLAN_01's `edit_file` tool returns a `diff` content block; the UI renders that as a hunk. Accept/Reject/Ask-why are tool calls (`apply_hunk` / `discard_hunk` / `request_clarification`); the UI shows them as buttons.

---

## 3. Permission model — the agent's blast radius

The plan adopts Codex CLI's new `permissions.<name>` profile system (verified from [developers.openai.com/codex/permissions](https://developers.openai.com/codex/permissions)) plus Claude Code's `permission_mode` spectrum, plus the AutoCode Station `policy` scope that writes to the audit log.

### 3.1 Sandbox modes (Codex-compatible)

| Mode | Filesystem | Network | Shell | Default? |
|---|---|---|---|---|
| `read-only` | Read in workspace | Blocked | Blocked except approved | No |
| `workspace-write` | Read + write in workspace, `:tmpdir` | Approved domains | Approved commands | **Yes** |
| `danger-full-access` | Full | Full | Full | No — explicit step-up |

**Linux enforcement:** `bubblewrap` (`bwrap`) on PATH, with a bundled helper fallback for unprivileged user-namespace creation. Layer `landlock`/`seccomp` if available. The Codex docs say "platform-native" and reference bwrap + user namespaces; landlock/seccomp details were not directly verified in this research pass and should be confirmed before commit. *(Open question §9.)*

### 3.2 Approval policy (Codex-compatible)

`approval_policy` values:
- `untrusted` — ask before running commands not in the trusted set.
- `on-request` — work inside the sandbox by default; ask to cross the boundary. **Default.**
- `never` — don't stop for approval prompts.

`approvals_reviewer`:
- `user` — prompts surface to the operator (default).
- `auto_review` — eligible prompts go to a reviewer agent.

### 3.3 Approval scopes (PLAN_01 extension)

| Scope | Lifts for | Persists until |
|---|---|---|
| `once` | The next single action | That action completes |
| `session` | Any matching action | Session ends or mode changes |
| `project` | Any matching action | Project-level config change or revoke |
| **`policy`** | Any matching action | Rule revoked by operator — **written to audit log** |

The `policy` scope is PLAN_01's differentiator. It turns approvals into org-level rules that are immutable, attributed, and exportable — exactly what AutoCode Station §5 calls for.

### 3.4 The approval card

Per AutoCode Station §5.1, every approval request shows full risk framing before any action runs:

- **What will run** (exact command).
- **Why** (agent's stated reason, free-text).
- **Scope** (cwd, filesystem read/write, network allowed/blocked, secrets available/unavailable).
- **Origin** (agent request / `AGENTS.md` / `package.json` / user).
- **Policy** rule matched (the YAML/JSON rule the engine matched).
- **Risk class** (`low` / `medium` / `high` / `critical`).
- **Repeat** (is this the first time, or Nth?).

Actions:
- `Approve once` (default).
- `Approve test commands for this task` (scoped to `*test*` / `cargo test` / `pytest` / `npm test`).
- `Deny with note` (note goes back to the agent as structured feedback).

Avoid "approve for session" or "approve forever" unless session is precisely defined (per AutoCode Station §5.1).

### 3.5 Audit log

Every approval, denial, override, delegation, edit, and command is written to an immutable, attributed JSONL log. Schema:

```jsonc
{
  "ts": "2026-06-21T14:32:11.482Z",
  "thread_id": "th_7f9f9a2e",
  "actor": "operator:bs01763",
  "action": "edit_accept" | "edit_reject" | "command_approve" | "command_deny" | "checkpoint_restore" | "mode_change" | ...,
  "target": { "kind": "file" | "command" | "checkpoint" | "policy", "ref": "src/auth/session.ts" },
  "policy_matched": "permissions.workspace.tools.edit_file",
  "decision": "allow" | "deny",
  "note": "free-text, optional",
  "hash_in":  "sha256:...",
  "hash_out": "sha256:..."
}
```

The log is append-only, content-addressed (each line carries the hash of the previous), and exportable. *(Per AutoCode Station §5.3 + §7 P3.)*

### 3.6 Maker / checker

Per AutoCode Station §4.4: the person who authored/ran a task should not be the sole approver of high-risk actions on it. The REPL surfaces the required checker in the approval card: `awaiting Maya`. Permissions gate the *governed actions* (approve command, approve commit/merge), not mere viewing or commenting.

### 3.7 How this inherits from existing corpus

**From `00-adversarial-validation.md`:** every recommendation in the table at §"Net adoption decision" applies. The proposer/compiler split is core; the audit log is core; the permission profile system is the codification.

**From `autocode-station-requirements.md` §5:** the approval card's risk-framing fields, the maker/checker separation, and the override-with-explicit-audit pattern are carried forward verbatim.

**From Codex's `permissions` page:** the `:read-only`/`:workspace`/`:danger-full-access` profile names, the network `domains` rule, the `allowed_permission_profiles` enterprise lockdown, and the warning that *Permission profiles do not compose with the older sandbox settings* — PLAN_01 picks one model (profiles) and commits.

---

## 4. Session and lifecycle — the resume model

### 4.1 The session record

A session is a content-addressed, append-only JSONL stream persisted to `$IDE_HOME/sessions/{thread_id}.jsonl`. Each line is a typed event:

```jsonc
{ "ts": "...", "kind": "user_prompt" | "tool_call" | "tool_result" | "approval" | "denial" | "checkpoint" | "mode_change" | "compact" }
```

- `tool_call` carries the canonical tool name, the validated arguments, and a `hash_in` (the content hash of the arguments).
- `tool_result` carries the typed MCP `content` array and a `hash_out`.
- `approval` / `denial` carry the actor, the policy rule matched, the decision, and the note.
- `checkpoint` carries the git ref (`refs/notes/ide-checkpoint/N`) and the operator-friendly name.
- `compact` carries a summary of the trimmed tail and the new starting offset.

### 4.2 Resumption

`ide resume` opens a picker of recent sessions (Codex pattern). `ide resume <thread_id> "<prompt>"` targets a specific run. Non-interactive: `ide exec resume --last "..."`. `--cd` overrides cwd; `--add-dir` exposes additional writable roots. *(Verbatim from [developers.openai.com/codex/cli/features](https://developers.openai.com/codex/cli/features).)*

### 4.3 Compaction

When the context window approaches the budget, the IDE triggers a compaction:

1. Snapshot the current session tail.
2. Summarize the trimmed portion (LLM call, but the summary is itself content-addressed and replayable).
3. Emit a `compact` event with the summary hash.
4. The agent continues from the summary + tail.

The summary is *not* a black box — it's a typed `summary` content block in the next tool call, so the agent can verify it.

### 4.4 Subagents (parallel + forked + background)

The agent's `Agent` tool (Claude Code semantics) spawns a subagent with its own context window. The subagent sees a *subset* of the parent's tools (filtered by the parent's policy), runs in a sub-thread, and returns a single text result. The parent never sees the subagent's intermediate tool calls unless it explicitly asks.

- **Parallel subagents** run concurrently (e.g., "research X and Y in parallel").
- **Forked subagents** inherit the full parent conversation.
- **Background subagents** don't show prompts; auto-deny on missing permission.

This is the Claude Code `Agent` semantics verbatim, exposed to the agent via `request_subagent`. *(From [code.claude.com/docs/en/tools-reference](https://code.claude.com/docs/en/tools-reference).)*

### 4.5 How this inherits from existing corpus

**From Codex's `codex resume` design:** session IDs, picker, `--last`, `--all` are the operator's mental model. PLAN_01 keeps it.

**From Claude Code's subagent system:** `maxTurns`, `tools`/`disallowedTools` filtering, the single-text-result return contract. PLAN_01 keeps it.

**From the 5-domain model:** the session record is the audit log; the audit log is the artifact domain. Every event is content-addressed, every event is replayable.

---

## 5. UI specification — what the operator sees

The UI is the *only* place the agent's work becomes visible. The design rule from §0.3: **the operator sees UI, not agents.** This section specifies that contract.

### 5.1 The REPL's input surface (composer)

- Multiline composer with `Enter` to send, `Tab` to queue (Codex convention), `Up`/`Down` for history, `Ctrl+R` for fuzzy history search, `Ctrl+G` to open `$VISUAL`/`$EDITOR` for the prompt.
- `@` opens a fuzzy file search (powered by `list_files` + `lsp_workspace_symbols`); the picked file is attached as `@file:path` in the composer.
- `!cmd` runs shell inline (sandboxed, approved, audited — same approval flow as `run_command`).
- `#` opens slash command autocomplete (see §5.4).
- Drag-drop image support: dropped images attach as `@image:hash` in the composer (Claude Code / Codex behavior).

### 5.2 The REPL's output surface (rows + review rail)

Every tool result becomes a *row* with a one-line summary and an expand affordance:

| Tool result kind | Row summary | Expand reveals |
|---|---|---|
| `read_range` / `read_symbol` | `Viewed src/foo.ts:100–149` | The line content with line numbers. |
| `edit_file` | `Edited src/foo.ts:42–57` | The unified diff; offers Accept / Reject / Ask-why. |
| `write_file` | `Wrote src/foo.ts (3.2 KB)` | The file's full content; offers Accept / Reject. |
| `grep` (files_with_matches) | `Found 12 files matching /TokenStore/` | The file list. |
| `grep` (content) | `Found 4 references to TokenStore` | The matched lines with `file:line: content`. |
| `lsp_definition` | `Found definition at src/auth/store.ts:88` | The file + range + first line of the definition. |
| `lsp_references` | `Found 7 references to TokenStore` | The locations with line content preview. |
| `lsp_diagnostics` | `3 errors, 2 warnings in src/auth/session.ts` | The diagnostics list with severity, message, range, code. |
| `run_command` | `Ran cargo test --workspace (4.2s, 0 failed)` | The command, exit code, stdout, stderr (truncated). |
| `git_checkpoint` | `Checkpoint #3 saved` | The git ref + the operator-friendly name. |
| `git_restore_checkpoint` | `Restored to Checkpoint #2` | The git ref + a diff of the restore. |
| `git_commit` | `Committed abc1234` | The commit message + the diff stats. |
| `git_push` | `Pushed to origin/main` | The remote URL + ref. |
| `open_pr` | `Opened PR #142` | The PR URL + body. |
| `browser_navigate` | `Opened https://…` | The accessibility-tree snapshot. |
| `request_user_input` | `Asked: which auth backend?` | The question + the options. |

The **right rail (review pane)** holds pending hunks, the audit log, and approval cards. It is *quiet* until there's something to act on. Reserved space; never overlapped by composer, terminal, or toasts.

### 5.3 The status bar

Always visible. Carries:
- Model (`claude-opus-4-7`).
- Policy (`workspace` / `read-only` / `danger-full-access`).
- Working directory (`/home/user/proj`).
- Thread ID (`th_7f9f9a2e`).
- Context window usage (`73% / 200k`).
- Mode (`plan` / `exec`).
- Pending hunks count (`2 pending`).

### 5.4 Slash command set (Codex-parity)

PLAN_01 mirrors Codex's slash command list (verified from [slash-commands](https://developers.openai.com/codex/cli/slash-commands)):

```
/permissions   /ide          /keymap        /vim
/sandbox-add-read-dir          /agent
/apps          /plugins      /hooks         /clear
/archive       /delete       /compact       /copy
/diff          /exit         /experimental  /approve
/memories      /skills       /import        /feedback
/init          /logout       /mcp           /mention
/model         /fast         /plan          /goal
/personality   /ps           /stop          /fork
/side          /btw          /raw           /resume
/new           /quit         /review        /status
/usage         /debug-config /statusline    /title
/theme
```

PLAN_01-specific additions:
- `/tool <name>` — show the schema for a tool.
- `/policy` — show the current permission profile.
- `/checkpoint` — list / save / restore checkpoints.
- `/hunks` — list pending hunks.
- `/audit` — view the audit log for this thread (tail or filter).
- `/ide` — show which IDE backend is connected (e.g. `zed-fork v0.x`, `code-oss v1.92`).

### 5.5 Plan mode vs exec mode

- **`/plan`** switches to plan mode. The agent emits a numbered step list. The operator accepts/rejects steps *before* any side effect. Switching from `exec` → `plan` halts the current run and asks the agent to summarize state.
- **`/exec`** (or default) runs side effects. Each step is a tool call, rendered as a collapsed row.
- **Mid-task queueing:** "When a task is already running, you can type a slash command and press Tab to queue it for the next turn. Codex parses queued slash commands when they run." *(Verbatim from [slash-commands](https://developers.openai.com/codex/cli/slash-commands).)*
- **Disabled states:** `/archive`, `/delete`, `/import`, `/plan` are disabled during running tasks or in side conversations.

### 5.6 The agent edit lifecycle (pending hunk UX)

This is AutoCode Station §3.2 in REPL form. Agent edits never silently mutate the buffer.

1. Agent calls `edit_file(file, old, new)`.
2. The IDE's policy compiler:
   - Validates the schema.
   - Checks read-before-edit.
   - Checks uniqueness (or `replace_all: true`).
   - Generates the unified diff.
   - Records the proposed hunk in a **pending-hunk registry** keyed by `(file, range)`.
3. The REPL renders the row `Edited src/auth/session.ts:42–57` (collapsed) and adds the hunk to the right-rail pending-hunks list.
4. The status bar updates: `1 pending approval`.
5. The operator's options:
   - **Accept** (`⌘↵` or click) → applies the hunk to the working buffer; emits a `tool_result` (the diff) and a `hunk_apply` audit event; `git_checkpoint` is auto-called (configurable).
   - **Reject** → discards the hunk; emits a `hunk_discard` audit event; the agent is notified.
   - **Ask why** → sends a `request_clarification` tool call to the agent; the agent's reply appears in the conversation column.

Multiple pending hunks in the same file are independently acceptable / rejectable. Manual edits and agent edits coexist in the same buffer; both flow through the same review path (per AutoCode Station §3.3's `Ctrl+I` inline-edit requirement).

### 5.7 The approval card UX

When the agent calls a tool that requires approval (`run_command` outside the trusted set, `git_push`, `open_pr`, a `bwrap`-restricted network call):

1. The tool call *pauses*. The right rail surfaces an approval card.
2. The card shows: exact command, why, scope, origin, policy matched, risk class, repeat count.
3. The composer remains visible; the terminal is reserved; toasts are top-right. **The card is never overlapped.**
4. The operator's buttons: `Approve once` / `Approve test commands for this task` / `Deny with note`.
5. The decision emits an `approval` or `denial` event in the audit log; the tool call continues or is rejected with a structured feedback message to the agent.

### 5.8 How this inherits from existing corpus

**From `autocode-station-requirements.md` §3:** the file tree, tabs, code/diff toggle, agent side panel, and agent-edits-as-pending-hunks are the AutoCode Station Editor's vocabulary. PLAN_01 collapses that vocabulary into the REPL: the right rail is the side panel, the row expand affordance is the diff toggle, the slash command `/diff` is the unified-diff view.

**From `autocode-station-requirements.md` §5:** the approval card, the merge gate (per-task checklist: tests, lint, comments resolved, maker/checker, dirty-worktree conflict), the override-with-explicit-audit, and the reserved-space rule.

**From `market-research-agent-cockpit (1).md` §4:** the Codex design language — collapsed single-line rows, paper-white surfaces, hairline borders, color reserved for status, information density from typography — adopted verbatim.

---

## 6. Agent bridge — connecting the harness to the IDE

PLAN_01's distinctive move: the IDE is the **MCP server**, and the harness is the **MCP host**. This is the seam the Codex `app-server` pattern opens up.

### 6.1 The transport

- **Local:** MCP over stdio. The IDE spawns the harness as a child process; the harness treats the IDE as one of its MCP servers; bidirectional JSON-RPC 2.0.
- **Remote:** MCP over Streamable HTTP with bearer-token auth (the canonical MCP transport for remote). Tokens are passed as `Authorization: Bearer …`; remote tokens are only accepted over `wss://` or local `ws://`.
- **Connection strings:** the IDE writes `mcp.json` with the server's `command` (local) or `url` + `headers` (remote). The harness reads the same file.

This is the same pattern Codex CLI already documents: "Configure STDIO or streaming HTTP servers in `~/.codex/config.toml`. Manage via `codex mcp` CLI. Codex can itself run as an MCP server." *(Verbatim from [developers.openai.com/codex/cli/features](https://developers.openai.com/codex/cli/features).)*

### 6.2 The auth modes

- **Local stdio:** no auth (process is the auth boundary).
- **Local WS (loopback):** `capability-token` mode with a file-backed token (`--ws-token-file`) or a hashed token (`--ws-token-sha256`). Token is passed as `Authorization: Bearer …`. *(Verbatim from [developers.openai.com/codex/cli/features](https://developers.openai.com/codex/cli/features).)*
- **Remote WS:** `signed-bearer-token` mode (HMAC) with `--ws-shared-secret-file` and optional `--ws-issuer` / `--ws-audience` / `--ws-max-clock-skew-seconds`. Remote tokens are only accepted over `wss://` or local `ws://`.

### 6.3 Multi-harness

A single IDE can connect to multiple harnesses concurrently:

- Claude Code (subprocess, stdio).
- Codex CLI (subprocess, stdio or WS).
- OpenCode (subprocess, stdio).
- Custom agent (over Streamable HTTP).

Each harness sees the IDE as a single MCP server with the full tool registry. The IDE multiplexes tool calls by `clientId` from the MCP `initialize` handshake.

### 6.4 The lifecycle handshake

```jsonc
// harness → IDE
{
  "jsonrpc": "2.0", "id": 1, "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": { "elicitation": {}, "sampling": {} },
    "clientInfo": { "name": "claude-code", "version": "2.1.142" }
  }
}

// IDE → harness
{
  "jsonrpc": "2.0", "id": 1, "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": { "tools": { "listChanged": true } },
    "serverInfo": { "name": "ide-harness-mcp", "version": "0.1.0" }
  }
}

// harness → IDE
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

Then `tools/list` returns the full registry, `tools/call` invokes a tool, and the IDE returns typed content. The agent reasons over structure; the UI renders each type appropriately.

### 6.5 How this inherits from existing corpus

**From Codex's `app-server` mode:** the local WS / capability-token / signed-bearer-token pattern is the precedent. PLAN_01 copies it.

**From MCP architecture:** the host/server/client split, the JSON-RPC 2.0 wire format, the typed content blocks, the `notifications/tools/list_changed` pattern, the `sampling`/`elicitation` client-side capabilities — all from [modelcontextprotocol.io/docs/learn/architecture](https://modelcontextprotocol.io/docs/learn/architecture).

---

## 7. Phase plan — build order, exit criteria, effort

The sequencing rule from `01-phase-plan.md` applies: **build the trust boundary first (hardest to retrofit), the compiler second (determines whether the system stays safe), and delay the external-model path until redaction + approval + audit work.** PLAN_01's twist: the *trust boundary* is the MCP server's policy compiler; the *compiler* is the policy engine itself; the *external-model path* is multi-harness support.

### Phase 0 — MCP core + REPL shell (no agent)

**Goal:** prove the typed tool bus + REPL render path before any intelligence.

- Stand up the MCP server in Rust (using `mcp-rs` or the official SDK) with a minimal tool set: `read_range`, `edit_file`, `list_files`, `grep`, `run_command`, `git_status`, `git_diff`.
- Stand up the REPL in Rust + ratatui: composer, slash command set, collapsed-row output, right-rail pending hunks, status bar.
- Wire a stub agent (deterministic, scripted) so the REPL's render path is exercised end-to-end.
- Implement the policy compiler: schema validation, read-before-edit, uniqueness check, `replace_all` opt-in.

**Build:** MCP server, REPL, policy compiler. **Use:** ratatui, MCP Rust SDK, ripgrep.
**Exit:** a stub agent can `edit_file` a sample file; the REPL shows the hunk; the operator accepts; the file is patched.
**Effort:** ~1–2 weekends.

### Phase 1 — Tool registry expansion (LSP, lint, git)

**Goal:** ship the full §2 tool registry.

- Wire LSP: `lsp_definition`, `lsp_references`, `lsp_hover`, `lsp_symbols`, `lsp_workspace_symbols`, `lsp_rename`, `lsp_code_action`, `lsp_format`, `lsp_diagnostics`, `lsp_completion`, `lsp_implementation`, `lsp_type_definition`, `lsp_inlay_hints`, `lsp_call_hierarchy`.
- Wire lint + typecheck: `run_linter`, `run_typecheck`, `lint_diagnostics` (post-edit feedback loop).
- Wire git: `git_status`, `git_diff`, `git_log`, `git_blame`, `git_checkpoint`, `git_restore_checkpoint`, `git_commit`, `git_push`, `open_pr`, `git_review`.
- Wire browser: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_console`, `browser_network`, `browser_screenshot`.

**Build:** tool registry, LSP bridge, git plumbing, Playwright bridge.
**Use:** tower-lsp (or a thin client to any LSP server — rust-analyzer, pyright, tsserver, gopls), Playwright.
**Exit:** an agent can perform a full rename via `lsp_rename`, run a typecheck and react to diagnostics, checkpoint and restore.
**Effort:** ~2–3 weekends.

### Phase 2 — Harness bridge + multi-harness

**Goal:** the REPL works with Claude Code, Codex CLI, and OpenCode.

- Implement the transport: stdio + Streamable HTTP.
- Implement the auth modes: capability-token, signed-bearer-token.
- Implement the multi-harness multiplexer.
- Hand-test the full agent loop on each harness.

**Build:** transport, auth, multiplexer.
**Exit:** the same operator session can be driven by Claude Code and Codex CLI interchangeably.
**Effort:** ~1 weekend.

### Phase 3 — Permission profile + approval card + audit log  ← **MVP endpoint**

**Goal:** the system is safe to use on a real codebase.

- Implement the permission profile system (Codex-compatible): `permissions.<name>.filesystem`, `permissions.<name>.network.domains`, `permissions.<name>.tools.<tool>`, `allowed_permission_profiles`.
- Implement the approval card UX (per AutoCode Station §5.1).
- Implement the audit log (JSONL, content-addressed, append-only).
- Implement the `policy` scope (rules that persist across sessions, written to audit).
- Implement sandbox enforcement on Linux: bwrap + user namespaces; layer landlock/seccomp if available.

**Build:** permission engine, approval card, audit log, sandbox.
**Exit:** an agent can run a 30-minute multi-file refactor under the `workspace` profile; every tool call is approved or auto-approved per policy; the audit log is complete and exportable.
**Effort:** ~1–2 weekends.

> **At the end of Phase 3 you have a working harness IDE.** The REPL exposes a typed tool surface to any MCP-compatible agent; the operator's UI is the Codex-style REPL; the audit log is real; the sandbox is enforced. For an individual developer on their own code, this is a reasonable place to live and iterate.

### Phase 4 — Plan mode + checkpointing + maker/checker

**Goal:** the operator can review before any side effect.

- Implement `/plan` mode with per-step accept/reject.
- Implement auto-checkpointing (configurable cadence: per edit, per N edits, on demand).
- Implement maker/checker: high-risk actions require a separate checker identity; the REPL surfaces `awaiting Maya`.
- Implement the override-with-explicit-audit path.

**Build:** plan mode, checkpoint manager, maker/checker policy.
**Exit:** an agent can propose a 5-step refactor; the operator reviews and edits the plan; the executed plan is the operator's plan; the audit log attributes every step to its approver.
**Effort:** ~1–2 weekends.

### Phase 5 — Subagents + background + browser

**Goal:** the harness can run parallel research and long-running tasks.

- Implement `request_subagent` with `tools`/`disallowedTools` filtering.
- Implement `background_process` + `tail_output` for dev servers, watchers, CI.
- Implement browser tools with the untrusted-content labeling (per `01-trust-domains.md`).

**Build:** subagent manager, process manager, browser bridge.
**Exit:** the operator can ask "research these 5 docs in parallel"; the REPL renders 5 subagent rows; the operator can pin one and discard the rest.
**Effort:** ~1–2 weekends.

### Phase 6 — Hardening + CI + provenance  ← **hardened endpoint**

**Goal:** the deployable, auditable version (the `00-adversarial-validation.md` review's 16–24 week target, mostly here).

- Rootless containers for the LSP/lint/typecheck workers (no `/dev/input`, no docker-socket, no general network).
- SBOM + signed builds + SLSA-ish provenance (only if regulated code is in scope).
- Headless mode: `ide --headless` exposes the MCP server over Streamable HTTP for CI.
- The lightweight incident checklist; retention reaper; log hygiene.
- Telemetry hooks (operator-visible only).

**Build:** isolation, provenance, headless mode.
**Exit:** the same agent + tool surface runs in a CI pipeline; isolation is verified by the security test suite.
**Effort:** weeks, not weekends.

### Phase summary

| Endpoint | Phases | Effort | What you get |
|---|---|---|---|
| **MVP** | 0–3 | ~5–8 weekends | REPL + typed tool surface + Claude/Codex harness support + permission profile + audit log |
| **+ plan + checkpoint + maker/checker** | 4–5 | +2–4 weekends | Plan-then-execute review, git checkpointing, regulated-team approval flow |
| **Hardened** | 6 | weeks | Isolation, provenance, CI mode |

### What changes the plan (decision triggers)

- LSP latency > 200ms p95 → drop to a per-language allowlist; warm-start servers on idle.
- REPL render > 16ms p99 → drop expand affordance, replace with `R` to view full payload in a pager.
- Audit log size > 100MB/thread → compact old `tool_result` content blocks to hashes; keep the audit log's content-addressing.
- An MCP server's tool list > 200 tools → split into multiple servers (e.g., `ide-core`, `ide-lang-rust`, `ide-test`).
- A harness's tool-call rate > 50/sec → add a back-pressure channel; the agent waits on a per-tool semaphore.
- A new tool's schema is unstable → pin a `schema_version` in the tool registry; refuse calls with mismatched versions.

---

## 8. Open questions — what to decide before build

**Q1 — Which harness to target first?**
Claude Code (most agent-feature-complete, has `LSP` tool, has `Agent` subagent) or Codex CLI (the design target for the REPL, has its own MCP server mode)? Recommendation: Claude Code for v1 because its `LSP` tool gives us a precedent for the `lsp_*` tool semantics, and its permission modes are well-documented. Codex CLI in Phase 2.

**Q2 — MCP server in Rust or TypeScript?**
Rust gives us a single binary (like `codex-rs`); TypeScript reuses the rich MCP-TS SDK. Recommendation: Rust, mirroring `codex-rs`. The binary embeds the REPL (ratatui) and the MCP server; one process.

**Q3 — Is the IDE's tool surface a single MCP server or many?**
A single server with the full registry is simpler (one `mcp.json` entry). Many servers (e.g., `ide-core`, `ide-lsp`, `ide-git`, `ide-browser`) allow per-server permission policies and per-server lifecycles. Recommendation: a single server for v1; split in v2 if the registry grows past 100 tools or if a per-server policy becomes a requirement.

**Q4 — Should the REPL be a separate process from the MCP server?**
Yes. The REPL is a client of the MCP server (over local stdio or WS). This matches the Codex `app-server` pattern and lets the REPL be a thin TUI that doesn't need to be co-located with the agent.

**Q5 — Linux sandbox: bwrap only, or bwrap + landlock + seccomp?**
The current Codex sandboxing docs reference bwrap + user namespaces only. Landlock/seccomp is referenced in older codex-cli JS implementation. Recommendation: bwrap first (the documented path), layer landlock/seccomp in Phase 6 hardening if available on the target kernel.

**Q6 — Permission profile compatibility with Codex's `permissions.<name>`?**
Should PLAN_01's profile files be readable by Codex CLI and vice versa? Recommendation: yes — adopt the Codex schema verbatim, so an operator can move between the harness IDE and Codex CLI without rewriting policy. Document any extensions in a separate `ide.*` namespace.

**Q7 — Local-only or remote-capable?**
Remote (over Streamable HTTP) is essential for the auto-mode, CI, and headless use cases. Recommendation: local stdio by default, Streamable HTTP in Phase 2 (multi-harness).

**Q8 — Do we ship a GUI client (Tauri/Electron) or stay TUI?**
TUI is faster to build and matches the Codex reference. A GUI client is the path to a Codex-app-like experience. Recommendation: TUI for v1; Tauri/Electron in v2 (PLAN_03) when the editor surface is the primary focus.

---

## 9. Composition with the rest of the corpus

PLAN_01 is the agent-facing substrate. Here's how it composes with what already exists and what the other plans in this set specify.

### 9.1 vs ClipMind (`README.md` + `01-trust-domains.md` + `01-phase-plan.md`)

| Aspect | ClipMind | PLAN_01 |
|---|---|---|
| Trust domain | 5-domain (capture, artifact, analysis, planning, policy+render) | 3 domains: agent (planning), IDE MCP server (policy+render), LSP/lint workers (analysis) — capture + artifact don't apply to a code IDE |
| Agent role | Proposer; emits typed Change Requests | Same role; emits typed tool calls (the "Change Request" is the MCP `tools/call`) |
| Compiler | Non-LLM validator + render DAG generator | Non-LLM schema validator + tool executor |
| Approval model | Per-edit human approval | Codex permission profile + approval card + audit log |
| Render | FFmpeg + Remotion | Patch the file (no separate render step) |
| Adversarial surface | Footage contains a terminal with attacker instructions | Code contains an attacker-influenced comment / string / dependency |

The 5-domain model is *the same shape* in PLAN_01, just mapped onto a code IDE: the **agent is the planning domain**, the **IDE MCP server is the policy + render domain**, the **LSP/lint/typecheck workers are the analysis domain**. Capture and artifact don't apply (the user's "captured content" is the codebase on disk, which is already the artifact domain).

### 9.2 vs AutoCode Station (`autocode-station-requirements.md`)

AutoCode Station is a **cockpit** — a control plane that wraps existing coding-agent CLIs. PLAN_01 is an **agent's environment** — the tool surface the agent calls into. They compose: AutoCode Station is the operator's UI for orchestrating *N agents*; each agent runs against a PLAN_01-style IDE. The Editor view's requirements (file tree, tabs, code/diff, agent side panel, agent edits as pending hunks, `Ctrl+I` inline edit) are PLAN_01's REPL features.

### 9.3 vs PLAN_02 (Video agent)

PLAN_02 is a separate product (general-purpose agentic video editor). PLAN_01 is the *pattern* PLAN_02's "IDE" front-end can use: a chat-with-video REPL where the tool surface is video-edit tools (cut, trim, zoom, caption, color) and the renderer is FFmpeg/Remotion. The two plans share the same architectural pattern (REPL + typed tool surface + audit log) but ship different tool registries and different render backends.

### 9.4 vs PLAN_03 (Full Codex/Cursor IDE)

PLAN_01 is the **agent half** of PLAN_03. PLAN_03 takes PLAN_01's REPL, the typed tool surface, and the audit log, and embeds them in a full desktop IDE (file tree, tabs, terminal panel, debug view, browser panel, etc.) — the consumer-facing product. PLAN_01 is what the agent sees; PLAN_03 is what the operator sees, with PLAN_01 behind it.

---

## 10. Sources

Verified (canonical, fetched in this research pass):

- [OpenAI Codex GitHub repo](https://github.com/openai/codex) — Rust 96.3%, install, `codex-rs/`.
- [Codex CLI features](https://developers.openai.com/codex/cli/features) — TUI shell, keybindings, slash commands, MCP, app-server, resume.
- [Codex CLI slash-commands](https://developers.openai.com/codex/cli/slash-commands) — full command list, queueing, disabled states.
- [Codex sandboxing concepts](https://developers.openai.com/codex/concepts/sandboxing) — modes, Linux bwrap, fallback helper.
- [Codex permissions](https://developers.openai.com/codex/permissions) — permission profiles, `:read-only`/`:workspace`/`:danger-full-access`, network domains.
- [Codex App overview](https://developers.openai.com/codex/app) — sidebar / active thread / review pane layout.
- [Codex App features](https://developers.openai.com/codex/app/features) — full Codex app feature inventory.
- [Claude Code overview](https://code.claude.com/docs/en/overview) — install, surfaces, capabilities.
- [Claude Code tools reference](https://code.claude.com/docs/en/tools-reference) — full tool list, schemas, subagent semantics, hook events.
- [Cursor docs root](https://cursor.com/docs) — agent area, rules, skills, MCP, sandboxing, worktrees.
- [Cursor agent overview](https://cursor.com/docs/agent/overview) — agent tools list, `Cmd+I`, checkpoints.
- [MCP architecture](https://modelcontextprotocol.io/docs/learn/architecture) — JSON-RPC, primitives, lifecycle, tool discovery, notifications.
- [MCP introduction](https://modelcontextprotocol.io/introduction) — high-level framing.
- [LSP index](https://microsoft.github.io/language-server-protocol/) — method names; spec 3.18.

In-repo (existing corpus in `new_plans/`):

- `README.md` — ClipMind thesis and document map.
- `01-trust-domains.md` — 5-domain model and data-flow rules.
- `01-phase-plan.md` — phased build with MVP/hardened endpoints.
- `00-adversarial-validation.md` — adversarial review validation; net adoption table.
- `autocode-station-requirements.md` — Editor + collaboration + approval requirements; maker/checker; audit log.
- `market-research-agent-cockpit (1).md` — Codex app / Claude Code desktop / T3 Code / Conductor / Vibe Kanban teardowns.

---

*End of brief. This is the substrate PLAN_03 embeds. Ready to be paired with PLAN_02 and PLAN_03.*

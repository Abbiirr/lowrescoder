# PLAN_03 — Full Codex + Cursor IDE (Technical Brief)

**Status:** research brief · Plan 3 of 3
**Goal of the plan:** an end-user desktop IDE — **not a wrapper around an existing CLI** — that ships every meaningful feature of the OpenAI Codex app *and* every meaningful feature of Cursor, plus the full traditional IDE surface, with the trust-domain / maker-checker discipline from `01-trust-domains.md` and the IDE-tool surface from PLAN_01 baked in from day one.

This brief is the **research substrate** for PLAN_03. It inventories the surface area we have to cover, sketches the architecture decisions, and calls out what AutoCode Station already addresses (so we don't re-design) and what diverges.

---

## 0. Where this plan sits

| Plan | What it is | Relationship to this plan |
|---|---|---|
| **PLAN_01 — Harness IDE** | The IDE surface that exposes tools to agents (codex-cli style UI). | This plan **embeds** PLAN_01's tool surface as the "agent panel + diff hunks" inside the full IDE. |
| **PLAN_02 — Video agent** | A separate product. | Out of scope here. |
| **PLAN_03 — Full Codex/Cursor IDE** (this plan) | A complete coding IDE — file editing, terminal, debug, git, browser — with AI everywhere. | The consumer-facing product; PLAN_01 is the agent half; AutoCode Station's `Editor` view (§3 of autocode-station-requirements.md) is the **minimum-viable prototype** of this plan's editor. |

AutoCode Station's editor requirements (file tree, tabs, code/diff toggle, agent side panel, agent edits as first-class pending hunks with Accept / Reject / Ask-why, inline AI edit `Ctrl+I` routed through the same review gate) are **carried forward** into this plan. The difference: AutoCode Station treats the Editor as one of eight views in a cockpit; PLAN_03 makes the Editor the *primary surface* with everything else attached to it.

---

## 1. Codex app — every feature (inventory + how it's built)

Reference: [developers.openai.com/codex/app](https://developers.openai.com/codex/app), [codex/app/features](https://developers.openai.com/codex/app/features). The Codex app is the most ambitious reference IDE of mid-2026 and sets the bar for what a "full coding IDE with AI" means.

### 1.1 Core work surfaces

| Feature | What it does | How it's built (inferred) |
|---|---|---|
| **Projects** | Choose a project folder that Codex works in; sidebar lists projects. | Workspace selector mapping a directory to a thread root; persisted in app config (`codex.json`); one project = one local checkout + one sandbox scope. |
| **Threads** | Run multiple project threads side-by-side; switch fast. | Each thread is a conversation context with independent message history, tool state, and terminal. Persisted to disk as JSONL or SQLite; resumable across sessions. |
| **Local / Worktree / Cloud modes** | Three execution modes per thread. | An environment adapter picks: local shell on the user's machine, a `git worktree` checkout for isolation, or a remote environment (cloud VM, dev container, SSH). Threads declare their mode at creation; switching mid-thread is allowed but creates a new thread. |

### 1.2 Code workflow

| Feature | What it does | How it's built |
|---|---|---|
| **In-app diff pane** | Inspect code changes the agent made. | Unified/split diff renderer fed by `git diff` or by `apply_patch` outputs. Diff is also exposed as `@`-style context the agent can re-read. |
| **Stage/revert chunks or files** | Partial staging of agent edits. | `git add -p`-style hunk UI; each hunk has Accept/Reject; per-file stage/revert; status bar reflects pending vs staged counts. |
| **Inline comments on diffs (the agent addresses them)** | Human leaves a comment on a line; agent fixes. | Diff is a commentable surface (file + line range anchor); comments round-trip into the agent's prompt as structured tool inputs. |
| **Commit, push, create PR in-app** | Ship work without leaving the app. | git plumbing + the host's API (GitHub/GitLab/Bitbucket via OAuth). PR body generated from thread history + diff; supports Linear/Jira ticket refs. |

### 1.3 Terminal & actions

| Feature | What it does | How it's built |
|---|---|---|
| **Integrated terminal per thread** | `⌘J` toggles a terminal scoped to the thread's mode (local/worktree/cloud). | PTY (xterm.js or platform native) with cwd bound to the thread root. |
| **Agent-readable terminal output** | Agent can `cat` the running dev server's output and react to it. | Terminal stream is structured-parsed into events (exit codes, file changes, URL opens) and offered as a tool the agent calls; raw scrollback remains accessible. |
| **Actions** | Reusable command buttons per project (`pnpm test`, `pnpm lint`). | Named command/script definitions in project config (`.codex/actions.toml` or similar); invokable from UI or by the agent. |
| **Cmd+K command palette / Ctrl+L clears terminal** | Standard IDE ergonomic. | Command palette over registered actions; Ctrl+L sends the conventional clear sequence to the PTY. |

### 1.4 Automations

| Feature | What it does | How it's built |
|---|---|---|
| **Scheduled / recurring tasks** | "Every weekday at 9am, run X in a worktree." | Cron-like scheduler (system cron / launchd / Task Scheduler) that re-invokes a thread prompt on intervals. |
| **Thread automations** | Wake the *same* thread on a schedule for ongoing checks. | Heartbeat loop — re-prompt the same thread id with new context (e.g., latest CI failures). |

### 1.5 Safety & sandbox

| Feature | What it does | How it's built |
|---|---|---|
| **Approval scopes** | "Approve once" vs "for session" gates on shell commands. | Per-command policy with explicit scope (`once`, `thread`, `session`); recorded in an audit log. |
| **Sandbox controls** | Limit filesystem and network per command. | OS-level sandbox profiles: macOS sandbox-exec, Linux Landlock + seccomp, Windows AppContainer. |
| **Native Windows sandbox** | No WSL required. | PowerShell under a Windows Job Object + restricted token. |
| **Optional automatic approval-review policy** | A static rule that auto-approves low-risk commands. | YAML/JSON rule engine matched against command shape (regex on command + cwd + env). |

### 1.6 Extensibility

| Feature | What it does | How it's built |
|---|---|---|
| **Skills** | Reusable instruction+script bundles shared across app/CLI/IDE. | Packaged prompt fragments + scripts, versioned, distributed as a directory or git submodule; the Skills discovery loader walks `$CODEX_HOME/skills/` and per-project `.codex/skills/`. |
| **MCP config** | Model Context Protocol servers registry. | Reads the same `mcp.json` as the CLI/IDE; servers launch as child processes; tools surface to the agent. |
| **Plugins** | Add UI surfaces and tools. | Plugin loader that registers commands, panels, and providers. |

### 1.7 Input modalities

| Feature | What it does | How it's built |
|---|---|---|
| **Voice dictation (^M)** | Hold Ctrl+M while composer is visible; transcribed text is editable before send. | OS-level audio capture + STT (Whisper or platform STT). |
| **Drag-drop image input** | Drop a screenshot into the composer. | File drop handler uploads/stores image and references it in conversation context. |
| **Screenshots ("Appshots")** | Send the frontmost Mac/Windows app window to Codex. | Captures the active window via OS APIs (CGWindowList on macOS, PrintWindow on Windows) + accessibility text extraction. |
| **Computer use** | Codex clicks/types in native apps for GUI testing. | Mouse/keyboard driver (Quartz on macOS, SendInput on Windows) + screen-grab loop; gated by approvals and excluded in EEA/UK/CH. |

### 1.8 Surfaces

| Feature | What it does | How it's built |
|---|---|---|
| **Floating pop-out always-on-top thread window** | Detach a thread to a second monitor. | OS window with `alwaysOnTop` flag; shares thread state via local IPC. |
| **In-app browser** | Preview dev servers and public pages. | Embedded webview (WebKit/WebView2/WebKitGTK); supports localhost and public origins; no auth/extensions. |
| **Element comments** | Click a DOM element, leave a comment; the agent fixes. | DOM-overlay + comment thread keyed by CSS selector + XPath. |
| **Agent browser-use** | Agent drives the in-app browser (login flows, clicks, scrapes). | CDP (Chrome DevTools Protocol) automation over the in-app browser. |
| **Artifact previews (PDF / sheets / decks)** | Inline renderers for generated Office/PDF outputs. | Embedded renderers (PDF.js, SheetJS, pptxjs). |
| **Task sidebar (plan / sources / summary)** | Right rail showing plan, sources cited, artifacts, summary. | Per-thread structured state surfaced alongside the chat column. |

### 1.9 Models, memory, integrations

| Feature | What it does |
|---|---|
| **Built-in web search** | Default-on retrieval tool; results cached; can be disabled. |
| **Image generation (gpt-image-2)** | In-thread image gen/edit. |
| **Chats** | Project-less ephemeral threads. |
| **Memories** | Persistent user/team knowledge the agent recalls across threads. Stored as Markdown in `$CODEX_HOME/memories/` or vector-indexed. |
| **IDE-extension sync / Auto Context** | Threads and active-file context mirrored across app and IDE extension via local IPC + cloud sync. |
| **Integrations (GitHub, Slack, Linear)** | Connectors that link PRs, messages, tickets to threads. |
| **Chrome extension** | Companion granting the agent controlled access to authenticated web sessions. |
| **Notifications + prevent-sleep** | Native OS notifications and power-management flag for long-running automations. |

> **PLAN_03 implication:** Every Codex-app feature listed above is in scope. The ones AutoCode Station partially covers: agent edit hunks (Accept/Reject/Ask-why), terminal (per-thread, agent-readable), diff pane with inline comments, git worktree per task, approval scopes, sandbox controls, in-app browser with comments. The ones PLAN_03 must add from scratch: floating pop-out, voice, drag-drop image, screenshots, computer use, artifact previews, task sidebar (plan/sources/summary), web search/image generation in-thread, Memories, IDE-extension sync, prevent-sleep, project-less Chats.

---

## 2. Cursor — every feature (inventory + how it's built)

Reference: [Cursor Docs](https://cursor.com/docs), [Agent overview](https://cursor.com/docs/agent/overview), [Agent plan-mode](https://cursor.com/docs/agent/plan-mode), [Zed Inline Assistant](https://zed.dev/docs/ai/inline-assistant) (architecture comparable to Cursor's Cmd-K). Cursor is a VS Code fork with AI as the central metaphor; PLAN_03 inherits much of the UX vocabulary.

### 2.1 Completion and inline editing

| Feature | What it does | How it's built |
|---|---|---|
| **Tab completion (single-line)** | Cursor suggests the next token/line as you type. Accept with Tab. | Local small model (<50ms) for the easy case; upgraded to a frontier model when context is richer; edits are *ghost text* rendered as an inline overlay until accepted. |
| **Tab multi-line** | Same but predicts several lines. | Same model pipeline with a larger completion budget; the diff is shown as a multi-line insertion. |
| **Cursor prediction** | Cursor jumps to the next likely edit point after accepting. | Combines completion with a heuristic cursor-movement model; "smart" cursor jumps are shown as a soft suggestion. |
| **Cmd-K inline edit** | Select code, press Cmd-K, type "add error handling," get a diff applied in place. | Selection + prompt → model → proposed edit → diff/accept flow. Equivalent to Zed's Inline Assistant ([zed.dev/docs/ai/inline-assistant](https://zed.dev/docs/ai/inline-assistant)) and the **same pattern as AutoCode Station's Ctrl+I inline edit (§3.3 of autocode-station-requirements.md)**. |

### 2.2 Conversational interfaces

| Feature | What it does | How it's built |
|---|---|---|
| **⌘L chat** | Side panel chat scoped to current file or selection. | Chat panel with file/selection auto-attached as context. |
| **⌘I composer** | New composer window for multi-step / multi-file work. | Same chat surface but with a larger context window and tool access. |
| **Agent Mode** | Autonomous multi-step agent with tools. | Loop: understand → plan → execute → verify. Tools: semantic search, file/folder search, web search, read files (with image support), edit files, shell commands, browser control, image gen, clarifying questions ([Cursor Agent overview](https://cursor.com/docs/agent/overview)). |
| **Plan Mode** | Agent produces a plan first; user reviews/edits before execution. | Same loop but the first iteration only emits a structured plan and stops; user can edit the plan or hit go. |
| **Background agents** | Long-running agents that don't block the foreground. | Separate worker processes or remote container per background task; results streamed back. |
| **Subagents** | A lead agent delegates to subagents. | Hierarchical agent loop with a separate context per subagent. |

### 2.3 Context system

| Feature | What it does |
|---|---|
| **Codebase indexing** | Embeddings + semantic search over the workspace. |
| **@-symbols** | `@file`, `@folder`, `@codebase`, `@git`, `@docs`, `@web`, `@db` — explicit context injection. |
| **Privacy mode** | Disable telemetry; data does not leave the device for training. |
| **.cursorrules** | Project-level natural-language rules the agent obeys. Equivalent to `CLAUDE.md` / `AGENTS.md` (auto-loaded into system prompt). |
| **Memories** | Cross-session persistent knowledge. |

### 2.4 Review and ship

| Feature | What it does |
|---|---|
| **Apply / Diff / Reject** | Standard inline-edit review flow. |
| **Multi-model routing** | Same UI lets the user pick Claude, GPT-5, Gemini, Grok, Cursor's own Composer models, etc. PLAN_03 should match. |
| **Bugbot** | Automatic PR review that comments on likely bugs. LLM runs against the diff. |
| **Migrations** | One-shot bulk code transforms (e.g., "upgrade all `axios.get` calls to `fetch`"). |
| **PR review (Cursor Review)** | A separate inbox/page for PRs with AI-generated reviews and merge queue. |

### 2.5 UX plumbing

| Feature | What it does |
|---|---|
| **Image input** | Paste/drop an image into chat. |
| **Voice** | Speech-to-text into composer. |
| **Terminal** | Integrated terminal (same as VS Code / Codex app). |
| **Debug integration** | Standard VS Code debug UI (DAP). |
| **Run & test** | Tasks panel and test runner. |
| **Project structure awareness** | Tree-sitter parsed AST exposed to the model. |
| **Cursor CLI + ACP** | Headless agent that speaks ACP for embedding into other tools. |

> **PLAN_03 implication:** Tab completion is the single feature Cursor owns most strongly — its UX is the reason people leave VS Code. **PLAN_03 must ship a competitive Tab.** Codebase indexing is the second must-have. Everything else in §2 has prior art (AutoCode Station, Codex app) we can carry forward.

---

## 3. Zed — the OSS reference

Reference: [Zed docs](https://zed.dev/docs), [Zed Agent](https://zed.dev/docs/ai/zed-agent), [Inline Assistant](https://zed.dev/docs/ai/inline-assistant). Zed is the cleanest architectural reference because it's GPU-native Rust, open source, and was built by the team that made Tree-sitter and Atom.

### 3.1 Core architecture

| Layer | What it is |
|---|---|
| **GPU-rendered UI** | `gpui` — Zed's GPU-accelerated UI framework (wgpu). 120fps on commodity hardware; no DOM, no Skia. |
| **Tree-sitter native** | Every buffer is parsed incrementally by Tree-sitter; syntax highlighting, code-folding, outline, and selection ranges all come from the CST. |
| **LSP-native** | Language servers run as out-of-process children speaking LSP over stdio. Zed implements the LSP client itself; LSIF/Indexorama for precomputed indices. |
| **Multi-buffer** | A single editor surface can host multiple selections across multiple files ("edit these 12 occurrences at once"). |
| **Agent Client Protocol (ACP)** | Open protocol for embedding external coding agents in the editor. ACP differs from MCP: ACP is **editor ↔ agent** (the agent wants to read files, request edits, render UI), MCP is **agent ↔ tool** (the agent calls a tool). Zed ships native + ACP-integrated + terminal-thread agent modes. |

### 3.2 AI surface

| Feature | What it does |
|---|---|
| **Inline Assistant (`ctrl-enter|ctrl-enter`)** | Transform a selection in place. Supports `@-mentions`, parallel generations across multiple models (`inline_alternatives`), and prefilled prompt keybindings. |
| **Edit Prediction** | Automatic suggestions while typing — Zed's equivalent of Cursor Tab. |
| **Agent Panel** | Conversational agent with thread persistence. |
| **Terminal Threads** | Run an agent CLI/TUI inside a Zed terminal pane. |
| **Skills, Instructions, Tools, Profiles, MCP** | All configurable per-agent. |
| **Tool Permissions** | Per-tool allow/deny. |
| **Privacy controls** | Opt-in training data; provider selection. |
| **LLM Providers** | Hosted, API, subscription (Claude/ChatGPT), gateway, local. |

### 3.3 Collaboration & remote

| Feature | What it does |
|---|---|
| **CRDT-based collab** | Real-time multi-cursor editing over CRDTs; channels for shared chat; contacts + private calls. |
| **Remote projects** | Open a folder over SSH; same UX as local. |
| **Dev containers** | Work inside a containerized environment. |

### 3.4 Extension system

Zed extensions cover **language**, **debugger** (DAP), **theme**, **icon theme**, **snippets**, **MCP server**, and **agent server** (ACP) — i.e. the extension surface mirrors the protocols the editor already speaks natively.

> **PLAN_03 implication:** Zed is the proof that a **native Rust + GPU** editor can match Electron's UX and beat it on latency. We should weigh Zed's approach seriously against a Code-OSS fork. The argument for Zed-style: smaller memory, faster, no DOM, AI integration is first-class. The argument against: 5–10× the engineering effort; extensions ecosystem is thin; fewer shipping IDEs have proved this path.

---

## 4. Traditional IDE features that AI IDEs still need

A coding IDE without these is a toy. List adapted from VS Code + JetBrains.

### 4.1 File & project

- File tree (worktree-scoped, git status badges)
- Multi-tab editor with dirty indicators
- Breadcrumbs (path › file › symbol)
- Outline view (symbols from tree-sitter / LSP)
- Multi-root workspaces
- Recently opened / quick open (`Cmd+P`)
- File watcher (chokidar / fsevents / inotify / ReadDirectoryChangesW)

### 4.2 Editing

- Syntax highlighting (tree-sitter / TextMate grammars)
- Multi-cursor / column select
- Split view / multi-buffer
- Minimap
- Soft wrap / word wrap / whitespace rendering
- Indent guides / bracket matching / auto-close
- Code folding / folding ranges
- Snippet support + user snippets
- Vim/Helix modal editing modes (Zed pattern)
- Command palette

### 4.3 Language intelligence (LSP)

- Completion (resolve, snippets, inline)
- Hover docs / parameter hints / signature help
- Go to definition / declaration / type definition / implementation
- Find references / document symbols / workspace symbols
- Rename (prepare-rename + rename)
- Code actions / quick fixes / refactor (extract method, move, change signature)
- Diagnostics (publish + pull)
- Inlay hints
- Semantic tokens
- Call hierarchy / type hierarchy
- Peek definition
- Format document / format selection / organize imports
- Linked editing (rename in sync, e.g. HTML tag pair)

### 4.4 Search & navigation

- Find in file (regex, case, whole-word)
- Find in files (ripgrep-style)
- Replace (in-file and across files)
- Go to line / go to symbol / go to file
- Breadcrumb navigation

### 4.5 Source control

- Source Control panel (git)
- Diff gutter (added/modified/deleted indicators)
- Branch / remote management
- Stash / tag / blame
- Inline PR comments (Carried from Codex app: comments round-trip to the agent)

### 4.6 Debug (DAP)

- Breakpoints (line, conditional, logpoint, function)
- Step over / into / out / run to cursor
- Watch expressions / hover-evaluate
- Call stack / scopes / variables
- Debug console
- Run configurations (`launch.json`)
- Multi-target / compound launches

### 4.7 Run & tasks

- Tasks (`tasks.json`)
- Problem matchers
- Test runner integration (per-language test APIs)
- Output panel / per-task output channels

### 4.8 Terminal

- Integrated terminal panel (PTY)
- Multiple terminals / split terminals
- Shell detection (bash / zsh / fish / pwsh)
- Terminal links (file:line detection)
- Persistent shell history

### 4.9 Window & workbench

- Sidebar (left/right)
- Panel (bottom — terminal, output, problems, debug console)
- Status bar (path, language, Ln/Col, encoding, EOL)
- Notification toasts (top-right, never overlapping approvals per AutoCode Station §5.1)
- Zen / focus mode
- Zoom (per-window or per-editor)

### 4.10 Configurability

- Settings (GUI + JSON)
- Keybindings (rebindable, vim/helix modes)
- Color themes (light/dark/auto)
- Icon themes
- Profiles (synced across machines)

### 4.11 Extensibility

- Extension marketplace / registry
- Extension API: commands, views, panels, webviews, language models (chat participant + tool APIs), MCP server providers, notebook renderers, task providers, debug providers, walkthroughs
- Built-in extension sandboxing (extension host process)

---

## 5. AI-IDE specific features

### 5.1 Conversational

- **Chat panel** (project, file, or selection scope)
- **Inline edit** (Cmd-K / Ctrl-I)
- **Composer / multi-file edit** (`⌘I` in Cursor)
- **Agent Mode** (autonomous multi-step with tools)
- **Plan Mode** (review-before-execute)
- **Background agent** (long-running, don't block)
- **Subagents** (hierarchical delegation)
- **Multi-agent A/B race** (run same task on two models, pick winner — AutoCode Station §Compare)

### 5.2 Code-touching

- **Suggested edits (review flow)** — the heart of the trust model: every edit is a pending hunk with Accept / Reject / Ask-why
- **@-symbol context injection** (`@file`, `@folder`, `@codebase`, `@git`, `@docs`, `@web`, `@db`, `@thread`)
- **Slash commands for AI**: `/edit`, `/test`, `/explain`, `/review`, `/commit`, `/refactor`, `/doc`, `/agent`, `/init`, `/fix`, `/simplify`, `/security-review`
- **AI diagnostics explanation** ("explain this error")
- **AI refactor / AI test generation / AI doc generation**
- **AI commit message / AI PR description / AI PR review (Bugbot-style)**
- **AI code review on push / on PR open**

### 5.3 Model & cost

- **Model selector** (Claude, GPT, Gemini, Grok, Kimi, etc.)
- **BYOK** (bring your own key) for any provider
- **Provider-agnostic** for those that ship a local server (Ollama, LM Studio, vLLM)
- **Cost tracking** (per-thread and per-session)
- **Context window indicator** (tokens used / limit)
- **Token usage breakdown** (by tool, by file, by model call)
- **Rate-limit awareness** (per provider)

### 5.4 Trust/safety (carried from `01-trust-domains.md`)

- **Per-tool permission scopes** (allow / ask / deny)
- **Approval card with full risk framing** (AutoCode Station §5.1: what runs, why, scope, origin, policy, risk class, repeat)
- **Maker/checker separation** (author ≠ approver)
- **Audit log** (every approval, denial, override, delegation)
- **Diff-first** (show diff before commit; never commit without a diff state)
- **Sandbox controls** (filesystem + network) per thread/mode
- **Checkpoints / time-travel** (Claude Code's `/rewind`; Cursor's checkpoints)
- **Disable training / privacy mode** (provider-agnostic)

### 5.5 Distribution & sync

- **Memories** (cross-session)
- **Skills** (cross-project)
- **MCP servers** (registry)
- **Settings sync** (across machines, opt-in)
- **Cloud sync** of thread history (opt-in; can be self-hosted)
- **IDE-extension sync** with the app (Codex-app pattern)

---

## 6. Architecture decisions to make

### 6.1 Shell / runtime

| Option | Pros | Cons |
|---|---|---|
| **Electron** (Code-OSS fork) | Mature; huge extension ecosystem; proven at Cursor scale; web tech is hireable. | RAM hungry (~400MB+ idle); Chromium drift; bundle size; not Linux-loved. |
| **Tauri 2** | Tiny binaries (~10MB); Rust backend; webview reuses OS; Linux-friendly. | Webview inconsistency (WebKitGTK quirks); less mature extension story; debugging the webview is harder than Electron DevTools. |
| **Native Rust + wgpu (Zed)** | Fastest path to 120fps; lowest memory; AI-native integration is cleanest. | 5–10× engineering effort; extension ecosystem thin; multi-platform shipping is harder; only one team (Zed) has proven this at scale. |
| **Flutter desktop** | Single codebase; native rendering; good for non-editor surfaces. | Code editor performance is hard; rich text rendering is non-trivial; tree-sitter integration is custom work. |

**Recommendation:** Start with a **Code-OSS fork** (Electron + Monaco) for v1 to ship the feature surface and trust-domain UX quickly. Plan a Zed-style native port for v3 if the market validates. Avoid Tauri unless the team has Tauri experience — the LSP/DAP/MCP/PTY plumbing is hard enough without webview quirks.

### 6.2 Editor core

- **Code-OSS fork**: VS Code's editor (Monaco) is battle-tested. Forking means we inherit LSP/DAP/extensions market and can focus on AI/UX.
- **Zed fork**: smaller, faster, but rebuild every VS Code feature from scratch.
- **Build from scratch**: not on the table.

**Recommendation:** Fork Code-OSS. Replace Monaco's file tree, tabs, diff, and AI surfaces with our own; keep Monaco's text buffer. This is what Cursor did.

### 6.3 Cross-platform targets

| Platform | Must-have for v1? |
|---|---|
| **macOS** (Apple Silicon + Intel) | Yes — primary dev platform, matches Codex-app and Cursor. |
| **Windows** | Yes — required for parity with Codex/Cursor. |
| **Linux** (x86_64) | **Yes — differentiator per market-research §S7 + AutoCode Station** (Linux primary). This is the one thing Cursor does poorly and Codex app refuses to do. AppImage + .deb + .rpm + Flatpak. |

A flatpak/Snap for Linux is the safest distribution story; an AppImage for "just run it" UX.

### 6.4 Backend / agent execution model

| Option | What it is | When to use |
|---|---|---|
| **Local agent loop** | The IDE process spawns an in-process agent. | Best latency, simplest auth, BYOK is straightforward. The Codex-app and Cursor default. |
| **Remote agent (cloud thread)** | Agent runs on a server; IDE is a thin client. | Long-running tasks; team sharing; phone/web access. The Codex cloud-thread model. |
| **Hybrid** | Local for fast interactions (Tab, Cmd-K, small edits); remote for background agents and cross-device. | The right answer for PLAN_03. |

**Recommendation:** Hybrid. Local-first for interactive AI; cloud as opt-in for automations and background agents. This matches AutoCode Station's local-first thesis.

### 6.5 Multi-model routing

PLAN_03 should ship first-class multi-model from day one. Routing model:

- **User picks default model per project** (stored in `.llm/config.json`).
- **Per-call override** at the prompt site (slash command or composer header).
- **Routing rules** (`/route slow` → Opus, `/route fast` → Haiku).
- **BYOK for any provider** + a hosted convenience tier.
- **A/B race mode** (AutoCode Station §Compare) for the same task on two models side-by-side.

### 6.6 MCP support

Mandatory. MCP is the de-facto standard for tools. We must:

- Read the same `mcp.json` as Codex CLI / Claude Code.
- Expose MCP servers to both the in-process agent and external agents over ACP.
- Provide an MCP registry UI (settings panel).
- Allow per-project MCP scopes.

### 6.7 Extension API

Cursor's approach (custom extension API + open VS Code extensions) is the sweet spot. PLAN_03 should:

- Accept unmodified VS Code extensions where possible (so the marketplace is reachable).
- Expose new extension points for AI: chat participants, tools, slash commands, language model providers, MCP server providers, agent server (ACP) providers.
- Avoid the "we reimplemented everything badly" trap — don't fork Monaco's extension API; extend it.

### 6.8 Storage

- Local SQLite for thread history + memories + skill cache.
- Local file system for skills/MCP servers (shared with CLI).
- Content-addressable store for artifacts (carried over from `01-trust-domains.md` §Artifact domain).

---

## 7. Reference apps

The IDE landscape, grouped by lineage.

### 7.1 VS Code lineage

- **VS Code** (Microsoft) — the reference; Electron + Monaco + extension host + LSP/DAP clients. Architecture: [code.visualstudio.com/docs](https://code.visualstudio.com/docs); repo: [github.com/microsoft/vscode](https://github.com/microsoft/vscode).
- **Cursor** (Anysphere) — VS Code fork; AI-first; $2B ARR (Mar 2026).
- **Windsurf** (Codeium) — VS Code fork; Cascade agent.
- **Trae** (ByteDance) — VS Code fork; AI agent IDE.
- **PearAI** — VS Code fork; opinionated AI features.
- **Project IDX** (Google) — web-based VS Code fork; AI-first.
- **CodeSandbox / StackBlitz** — web IDEs; WebContainers.

### 7.2 Native lineage

- **Zed** — Rust + wgpu + tree-sitter + LSP/ACP. Open source. [zed.dev](https://zed.dev).
- **JetBrains Fleet** — distributed IDE architecture; uses the IntelliJ code-processing engine; reimagined UI. Public Preview. [jetbrains.com/fleet](https://www.jetbrains.com/fleet/).
- **Xcode** (Apple) — macOS/iOS only; not relevant.

### 7.3 Cloud-native

- **GitHub Codespaces** — VS Code in the cloud; dev container per project.
- **Cloud9** (AWS) — browser IDE; older.
- **Replit** — browser IDE; multi-language; agent features.

### 7.4 Agent-first IDEs

- **Cody** (Sourcegraph) — VS Code + JetBrains extension; codebase-aware chat.
- **Continue** — open source; VS Code + JetBrains extension.
- **Tabnine** — completion-first; LSP-aware.
- **Aider** — terminal-based agent; git-native; multi-model.
- **Claude Code** — Anthropic's CLI agent; not an IDE but a tool an IDE embeds.
- **Codex CLI** — OpenAI's CLI agent.
- **OpenCode** — open source terminal agent.

### 7.5 Cockpits (carry-overs from PLAN_02 / AutoCode Station)

- Codex app, Claude Code desktop, T3 Code, Conductor, Vibe Kanban, Crystal, Claude Squad, opcode, Happy/Omnara, Sculptor. See [market-research-agent-cockpit (1).md](market-research-agent-cockpit%20(1).md) §6 for the full table.

---

## 8. Differentiators for this new IDE

If PLAN_03 is "another Cursor," nobody will switch. The differentiators should be drawn from the gaps already identified in `01-trust-domains.md`, AutoCode Station, and the market research.

### 8.1 Linux-first (proven gap)

- Codebase app: Linux is waitlist-only.
- Conductor: Apple Silicon Mac only.
- Cursor: ships a Linux build but it's an afterthought.

PLAN_03 ships Linux as a **first-class target** (parity with macOS/Windows from day one, not "later"). AppImage + Flatpak + .deb/.rpm; Wayland tested; inotify-tuned file watching.

### 8.2 Trust-domain architecture from the start (home turf)

Cursor and Codex app have ad-hoc permission systems. PLAN_03 has the trust-domain architecture from PLAN_01 / `01-trust-domains.md` baked in:

- **Five trust domains** with explicit interfaces (Capture / Artifact / Analysis / Planning / Policy+Render).
- **Dual-LLM / CaMeL pattern**: the planner is quarantined; only the deterministic policy compiler authorizes execution.
- **Maker-checker separation** for regulated teams (the AutoCode Station §5 thesis).
- **Immutable audit log** of every agent action, approval, denial, override, and delegation.
- **Egress deny-by-default** for any external model call; explicit redacted approval required.

This is the most defensible differentiator for a regulated-team audience. Cursor cannot copy it without re-architecting.

### 8.3 End-to-end reproducibility

Every AI action is a **typed, versioned, replayable artifact**:

- Every agent edit is a hunk with source, rationale, and a hash of the prompt that produced it.
- Every thread is replayable from its prompt log + tool log + git state.
- Every commit is attributable to a thread + agent + model + prompt + version.
- The audit log is the source of truth — it must be possible to reconstruct *exactly* what the agent saw, did, and was told.

### 8.4 Local-first, cloud optional

- Default: everything local. Thread history, skills, memories, MCP servers — all on disk in standard formats (JSONL, SQLite, Markdown).
- Cloud features (Codex-app-style cloud threads, team sync) are **opt-in** and **never required** for the core product.
- This is the opposite of Codex-app's positioning (ChatGPT-account-centric, cloud-tied).

### 8.5 Multi-model, multi-harness, multi-agent A/B

- First-class support for every provider (Claude, GPT, Gemini, Grok, Kimi, Cursor's Composer models).
- ACP for embedding third-party agents (Claude Code, Codex CLI, OpenCode).
- A/B race mode in the composer (run same task on two models, diff the results, pick the winner).
- BYOK plus an optional hosted convenience tier.

### 8.6 Plan-First development as a UI primitive

The Plan Mode that Cursor introduced should be PLAN_03's **default**. Every non-trivial task lands as:

1. **Spec** — what the user wants, in natural language.
2. **Plan** — agent's structured plan, editable by the user.
3. **Approval gate** — what permissions the plan needs; what's high-risk.
4. **Execution** — with checkpoints and rollback.
5. **Review** — diff + audit log.
6. **Ship** — commit / push / PR with audit-traceable attribution.

This makes the IDE inherently *reviewable* in a way no current product is.

### 8.7 Real, full, traditional IDE

Most "AI IDEs" ship a stripped-down editor. PLAN_03 ships the **whole §4 surface** as table stakes — debugger, refactor, test runner, profiles, full LSP/DAP, etc. AI is the agent in the room, not a thin wrapper around a textarea.

### 8.8 Open core, governed tier

- OSS core (editor + agent + multi-model + MCP).
- Paid tier: team admin (SSO, audit log export, compliance reports, on-prem deployment).
- Self-hostable cloud threads.

---

## 9. Where AutoCode Station covers parts of this (no re-design needed)

The following are already specified in `autocode-station-requirements.md` and should be **carried forward** into PLAN_03 without modification:

| Surface | AutoCode Station § | What PLAN_03 inherits |
|---|---|---|
| **Agent-edit pending hunks** (Accept/Reject/Ask-why) | §3.2 | The core of the editor — same review flow. |
| **`Ctrl+I` inline AI edit routed through review gate** | §3.3 | Same inline-edit UX. |
| **Per-file Code/Diff toggle** | §3.1 | Same diff surface. |
| **Activity-rail IA (Inbox default)** | §2 | Same left rail; the Editor view *is* PLAN_03's full window, but the IA vocabulary carries. |
| **Command approval card with full risk framing** | §5.1 | The same approval card pattern is PLAN_03's primary approval surface. |
| **Merge gate with checklist + override** | §5.2 | Same merge gate before commit/PR. |
| **Maker/checker separation** | §4.4 / §5 | Same approval authority separation. |
| **Immutable attributed audit log** | §5.3 / P3 | Same audit log, persisted locally and (optionally) synced. |
| **Browser QA Studio** | P2 | Same in-app browser with comments; PLAN_03 ships it from day one. |
| **Harness capability matrix** | §6 | Same per-provider model of installed/auth/capability flags. |
| **Compare (multi-agent runs)** | P2 | Same side-by-side diff + cherry-pick workflow. |
| **Narrow mode (mobile)** | §6 | Same remote-approval-only narrow UI. |

---

## 10. Where this plan diverges from AutoCode Station

| Axis | AutoCode Station | PLAN_03 |
|---|---|---|
| **What it is** | A cockpit wrapper around existing agent CLIs. | A full IDE with a built-in agent. |
| **Editor** | Minimal native IDE for review of agent edits. | The full IDE *is* the product; review is one of many modes. |
| **Harness** | External CLIs (Claude Code, Codex CLI). | The agent runs *inside* the IDE; external agents connect over ACP. |
| **Distribution** | Web-first (`npx`); desktop later. | Desktop-first (Linux/macOS/Windows); web a remote-client option. |
| **Audience** | Operator running multiple harnesses. | End-user writing code. |
| **Trust model** | Maker/checker for approval. | Same maker/checker + trust-domain architecture from `01-trust-domains.md`. |

---

## 11. Open architectural questions to settle before build

These are the calls a v1 plan has to make. Mark with the recommendation.

1. **Electron vs Zed-style native?** *Recommend: Code-OSS fork (Electron + Monaco) for v1; revisit in v3.*
2. **Tab completion model — local-only, or local + cloud fallback?** *Recommend: local small model for the easy case (Cursor pattern), cloud for hard cases.*
3. **First-party agent or ACP only?** *Recommend: first-party agent + ACP for third-party (Claude Code, Codex CLI).*
4. **Memory store format — SQLite, JSONL, Markdown?** *Recommend: SQLite for index, Markdown for memories (LLM-readable).*
5. **Audit log format?** *Recommend: signed JSONL (append-only, content-addressed).*
6. **Linux distribution — AppImage, Flatpak, .deb/.rpm?** *Recommend: AppImage + Flatpak as primary, .deb/.rpm for power users.*
7. **Cloud threads — own infra or partner with Anthropic/OpenAI?** *Recommend: ACP speaks to the official providers' cloud threads; build local-first.*
8. **Pricing model — fully OSS, OSS core + paid team, or freemium?** *Recommend: OSS core + paid team/governed tier (AutoCode Station §S2 thesis).*

---

## 12. Sources

### Codex app & OpenAI
- [developers.openai.com/codex/app](https://developers.openai.com/codex/app)
- [developers.openai.com/codex/app/features](https://developers.openai.com/codex/app/features)

### Cursor
- [cursor.com/docs](https://cursor.com/docs)
- [cursor.com/docs/agent/overview](https://cursor.com/docs/agent/overview)
- [cursor.com/docs/agent/plan-mode](https://cursor.com/docs/agent/plan-mode)

### Claude Code & Anthropic
- [code.claude.com/docs/en/overview](https://code.claude.com/docs/en/overview)
- [anthropic.com/news/enabling-claude-code-to-work-more-autonomously](https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously)

### Zed
- [zed.dev/docs](https://zed.dev/docs)
- [zed.dev/docs/ai/zed-agent](https://zed.dev/docs/ai/zed-agent)
- [zed.dev/docs/ai/inline-assistant](https://zed.dev/docs/ai/inline-assistant)
- [github.com/zed-industries/zed](https://github.com/zed-industries/zed)

### VS Code & Microsoft protocols
- [code.visualstudio.com/docs](https://code.visualstudio.com/docs)
- [github.com/microsoft/vscode](https://github.com/microsoft/vscode)
- [microsoft.github.io/language-server-protocol](https://microsoft.github.io/language-server-protocol/)
- [microsoft.github.io/debug-adapter-protocol](https://microsoft.github.io/debug-adapter-protocol/)

### JetBrains Fleet
- [jetbrains.com/fleet](https://www.jetbrains.com/fleet/)

### Internal plans (carried over)
- `01-trust-domains.md` — five trust domains, dual-LLM pattern, audit log
- `01-phase-plan.md` — phased build model for the harness agent (applicable shape)
- `autocode-station-requirements.md` — editor surface and approval model
- `market-research-agent-cockpit (1).md` — category, gaps, competitive matrix

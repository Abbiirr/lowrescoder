# Backend Features Inventory

> Current-state backend inventory.
> Last updated: 2026-04-29.
> Scope: Python backend, agent runtime, session stores, JSON-RPC hosts, slash-command runtime, and backend-facing tool surfaces.

This file is an implementation inventory, not a roadmap. Roadmap and tranche execution details remain in `docs/plan/backend-feature-improvement-plan.md` and `docs/plan/backend-feature-improvement-todo.md`.

## Implemented Backend Features

### Runtime And Hosting

- Backend application host: `autocode.backend.server.BackendServer`.
- Host-independent service helpers: `autocode/src/autocode/backend/services.py`.
- JSON-RPC method dispatch separated from the host: `autocode/src/autocode/backend/dispatcher.py`.
- Transport abstraction and concrete host adapters: `autocode/src/autocode/backend/transport.py`, `stdio_host.py`, and `tcp_host.py`.
- Runnable backend modes: `autocode serve --transport stdio` and `autocode serve --transport tcp --host 127.0.0.1 --port 8765`.
- Frontend-compatible attach mode through the TCP JSON-RPC host.
- Startup status emission, response framing, request dispatch, graceful shutdown, and transport conformance coverage.

### Chat Turn Execution

- Chat-turn orchestration extracted to `autocode/src/autocode/backend/chat.py`.
- Chat lifecycle events include request acknowledgement, status updates, streamed output, thinking output, tool-call activity, cost updates, visible warnings/errors, and completion.
- Active turn cancellation cancels the agent loop and propagates cancellation to subagents.
- Steering can cancel an active run and persist the steer message into the current session.
- Provider/model/config state is owned by the backend and projected through RPC and slash commands.

### Provider And Thinking Support

- Layer 4 provider path supports OpenRouter/OpenAI-compatible gateway and Ollama-style local providers.
- Thinking toggle controls provider request behavior, not just frontend display, where the provider supports it.
- Streaming thinking events are emitted through `on_thinking`.
- Shared streaming think-tag parser lives in `autocode/src/autocode/layer4/thinking_parser.py`.
- OpenRouter reasoning metadata and `<think>` tag fallback are handled; Ollama tag output is parsed in streaming order.
- Token and usage data are recorded through provider usage metadata where available.

### Layer Routing And Context

- Layer 1/2 deterministic and search surfaces feed the agent context.
- Layer 3 local constrained generation remains opt-in through the `layer3` optional extra and simple-edit routing; core installs fall back to Layer 4.
- Layer 4 provider calls remain the default general-purpose path.
- Context assembly includes search results under budget.
- Context priority and per-section budget enforcement are implemented.
- Ranked repo-map context is generated from Layer 2 for explicit prompt-context use and the `/repomap` command while first-turn bootstrap keeps repo-map generation deferred.
- Repo-map generation uses token-budget markdown output, dependency fan-in ranking, persistent file metadata cache invalidated by mtime+sha256, and Python+Go symbol extraction.
- Subprocess LSP adapter framework is implemented in `autocode/src/autocode/layer2/lsp_client.py` with stdio JSON-RPC framing, initialize capability negotiation, lazy start, bounded restart-on-crash, graceful shutdown, idle reap, and a nine-operation client surface for future language adapters.
- LSP adapter registry substrate is implemented in `autocode/src/autocode/layer2/lsp_servers/` with file-extension adapter resolution and non-spawning doctor readiness checks.
- Java LSP adapter support is registered for `.java` files via `jdtls`, including deterministic workspace setup, build-file discovery for `pom.xml`/Gradle roots, Java runtime readiness metadata, and project-local fixture coverage for the nine-operation client surface.
- JavaScript and TypeScript LSP adapter support is registered through `typescript-language-server`, with explicit routing for `.js`/`.jsx`/`.mjs` and `.ts`/`.tsx`/`.d.ts`, project config discovery, TypeScript type-diagnostic metadata, peer-dependency doctor metadata, and project-local fixture coverage.
- C, Kotlin, and Python subprocess LSP adapters are registered for `.c`/`.h`, `.kt`/`.kts`, and `.py`/`.pyi`, with `clangd`, `kotlin-language-server`, and `pylsp` readiness metadata respectively. Kotlin uses an extended request timeout, Python keeps Jedi-backed `lsp_*` tools reachable as fallback for one release, and all fixtures stay project-local.
- Go and Rust subprocess LSP adapters are registered for `.go` and `.rs`, with `gopls` plus Go 1.16+ readiness metadata, `rust-analyzer` plus rustup component metadata, `go.mod` / `Cargo.toml` discovery, Rust cold-cache timeout extension, and project-local fixture coverage for the nine-operation client surface.
- Post-edit auto-verify is implemented in `autocode/src/autocode/agent/auto_verify.py` and wired into `AgentLoop` after successful filesystem-mutating tools. It runs LSP diagnostics for edited files with registered adapters, skips unsupported or disabled languages, feeds formatted diagnostics back into the tool result, respects `/verify on|off|status`, surfaces persistent failures without automatic rollback, and halts retry guidance when the cost limit has been crossed.
- Iteration-zero bootstrap can include bounded cached Layer 1 symbol previews for active working-set files only.
- Tool-result truncation is adaptive and preserves high-signal code, error, traceback, and list structure under per-tool budgets.

### Tool Runtime

- Core file/system tools: `read_file`, `write_file`, `edit_file`, `list_files`, `search_text`, `run_command`, and `apply_patch`.
- Git tools: `git_status`, `git_diff`, and `git_log`.
- Web/tool discovery surfaces: `web_fetch` and `tool_search`.
- Layer 1/2 code-intelligence tools: `find_references`, `find_definition`, `get_type_info`, `list_symbols`, `search_code`, `semantic_search`, plus Jedi-backed `lsp_goto_definition`, `lsp_find_references`, `lsp_get_type`, and `lsp_symbols`; a broader subprocess LSP client substrate now exists for upcoming multi-language adapters.
- Task tools: `create_task`, `update_task`, `list_tasks`, and `add_task_dependency`.
- Todo tools: `todo_write` and `todo_read`.
- Search convenience tools: `glob_files` and `grep_content`.
- Subagent tools: `spawn_subagent`, `check_subagent`, `cancel_subagent`, and `list_subagents`.
- Tool-result cache tools: `list_tool_results`, `clear_tool_result`, and compatibility `clear_tool_results`.
- `ask_user` tool supports backend-driven explicit user questions.

### Safety, Approval, And Hooks

- Approval manager covers approval decisions and hard-block rules.
- Dangerous shell commands are blocked before execution.
- Dangerous write paths/content are blocked for write/edit/apply-patch paths before handlers execute.
- Interruptible tool cancellation is supported; non-interruptible in-flight tools can finish before cancellation propagates.
- PreToolUse and PostToolUse hooks are wired.
- Background subagents auto-deny approval-requiring tools.
- Sandbox policy primitives exist in `autocode/src/autocode/agent/sandbox.py`.
- Git-aware post-edit staging stages successful FS-mutating tool outputs with `git add` only and surfaces deterministic user-owned commit-message proposals; forbidden git operations are blocked at the wrapper layer.
- Legacy multi-edit and write/edit safety paths use local file-copy snapshots instead of git commits/resets; product code has source-scan coverage preventing forbidden git subprocess operations.

### Sessions, Messages, And Checkpoints

- SQLite-backed sessions persist messages and tool-call rows.
- Session create/list/resume/fork are available over backend RPC.
- Session resume supports prefix matching and ambiguity errors.
- Checkpoints preserve task DAG state plus bounded recent message history and assistant tool-call rows.
- Checkpoint restore rehydrates messages/tool calls and task state.
- Per-tool-call atomic checkpoints: before FS-mutating tool calls (write_file, edit_file, apply_patch), files are snapshotted to `~/.autocode/snapshots/<session_id>/<tool_call_id>/` and a `pre_tool` checkpoint is saved with `parent_tool_call_id`, `tool_call_idx`, and `kind` fields.
- `/rollback` slash command lists per-tool checkpoints, previews specific checkpoints by ID or `--last`, and restores file snapshots only via explicit `/rollback restore <id>`.
- Retention enforcement drops oldest per-tool checkpoints beyond N=50 per session.
- `/undo` restores the most recent checkpoint through the command runtime.
- Session teardown consolidates deterministic learnings before LLM-based memory enrichment.

### Tasks, Plans, Subagents, And Loops

- Task lifecycle supports `pending -> in_progress -> completed` and rejects stale backward transitions through generic updates.
- Backend emits task/subagent projections through `on_task_state`.
- Plan mode state is persisted in the backend and can be queried/set over RPC.
- Plan artifact export/sync bridges markdown checkboxes with task status.
- Subagent manager supports spawn, status/result lookup, listing, cancellation, max-concurrency controls, timeouts, and status summaries.
- Recurring `/loop` jobs are implemented in the slash-command runtime.

### Memory And Episode Retention

- Project memory store supports learned memories and listing.
- Session consolidation can persist durable learnings through `MemoryStore.save()`.
- Memory extraction is robust to malformed bracketed preambles before valid JSON arrays.
- Episode retention creates deterministic non-LLM summary events before old episodes are pruned.
- Summary recursion is capped so summary rows do not recursively dominate retained history.

### Cost And Token Accounting

- `CostDashboard` tracks per-session input/output/cached-token usage and estimated cost.
- OpenRouter cached prompt token metadata is captured where provider usage exposes it.
- `/cost` and `/cost --detail` display real session usage from the dashboard rather than message-character heuristics.
- Optional `agent.cost_limit_usd` emits a single warn-and-continue notification on threshold crossing.
- Provider/model aggregation and cache-savings estimates are available in detailed cost output.

### Slash Commands And Backend RPC Surface

- Backend-owned slash-command catalog is exposed through `command.list`.
- Current command runtime includes session, model/provider, mode, TUI mode, compaction, shell, copy, freeze, thinking, clear, loop, index, repomap, tasks, plan, research, build, review, memory, checkpoint, rollback, undo, diff, cost, and export commands.
- Frontend-facing RPC methods include `chat`, `cancel`, `command`, `command.list`, `session.new`, `session.list`, `session.resume`, `session.fork`, `model.list`, `provider.list`, `task.list`, `subagent.list`, `subagent.cancel`, `plan.status`, `plan.set`, `plan.export`, `plan.sync`, `config.get`, `config.set`, `memory.list`, `checkpoint.list`, `checkpoint.restore`, `steer`, and `shutdown`.
- Backend notifications include status, warning, token, thinking, done, tool-call, task-state, cost-update, error, and chat-ack events.
- Backend-originated frontend requests include tool approval and ask-user flows.

### Testing And Verification Surfaces

- Unit coverage exists for backend server/services, backend chat, transport conformance, commands, cost dashboard, checkpoint restore, MCP server behavior, token accounting, doctor, and edge cases.
- Transport conformance tests exercise both stdio and TCP host paths for core backend surfaces.
- PTY smoke tests cover real TUI/backend behavior, thinking split, slash surfaces, restore interaction, tool output budgets, and real gateway canaries.
- Stored release artifacts record the current green release gate, including Python unit, benchmark harness, Rust TUI, Track 1/4, PTY smoke, and real-gateway canary results.

## Expected Backend Features Not Fully Implemented

- Capability/version negotiation between frontend and backend is not explicit.
- Reconnect/reattach semantics for remote or dropped TCP clients are not explicit.
- TCP host is local and simple; it is not a hardened multi-client remote service.
- Transport security/authentication is not defined for remote attachment.
- Backend application boundaries are still broad: `BackendServer` remains the coordinating host for many services even though dispatcher/services/transports are now split out.
- Slash-command UX semantics remain backend-led; a fully swappable UI still needs a stricter command/picker contract.
- Full LSP parity with external agents is not present yet; the subprocess client exposes the broader nine-operation surface and all eight planned language adapters are registered, but frontend/tool consumption of that broader subprocess LSP surface is still pending.
- Sandbox mode switching is not exposed as a first-class `/sandbox <mode>` command.
- Subagent permission enforcement and scheduler fairness are intentionally deferred beyond the completed backend tranche.
- Cross-session memory promotion is deferred beyond v1.
- Hard-abort cost limits are not implemented; the current behavior is warn-and-continue.
- Tool-call execution memoization is not implemented; current tool-result cache is prompt-pressure relief, not execution reuse.
- Layer 3 broadening is intentionally not implemented; the path remains optional-extra and simple-edit scoped.
- Metrics beyond cost/token accounting are not consolidated into an operational dashboard.
- Auto-verify currently feeds diagnostics back through the agent/tool-result path; dedicated frontend validation drawer events remain planned in `docs/features/validation-output.md`.

## Planned Or Deferred Backend Features

- L3 broadening only after optional-extra activation criteria, route tests, and integration tests are defined.
- Tool-call execution memoization with safe invalidation for file-reading and environment-sensitive tools.
- Citation surfacing for code/search context and generated answers.
- Provider failover and retry policy beyond current warning/retry behavior.
- Streaming back-pressure and cancellation cleanup across every provider/tool edge case.
- Plan artifact versioning and richer task/plan synchronization.
- Subagent permission scoping, scheduler fairness, and deeper delegation policy controls.
- Telemetry hooks for skill trigger accuracy, hook success, retry counts, compaction behavior, and provider latency.
- Config validation UX improvements around layered configuration and one-shot runtime overrides.
- Long-form supervision UX for extended loops, subagent swarms, and recovery flows.
- Tool/front-end consumption of the new subprocess LSP client surface.
- `/sandbox <mode>` slash command and command-scoped allow/deny policy controls.
- External-client JSONL transcript/export schema with replay support.

## Feature Contract Cross-References

The following feature-contract files provide typed-shape specifications that cross-reference this inventory. They are descriptive of intent and planned shapes, not frozen implementations.

| Contract | File | Key typed models |
|---|---|---|
| Agent Events | `agent-events.md` | `AgentEvent` discriminated union + `BaseEvent` |
| Session Lifecycle | `session-lifecycle.md` | `SessionInfo`, session state machine |
| Transcript | `transcript.md` | `TranscriptMessage`, rendering rules |
| Composer | `composer.md` | `ChatParams`, `preservedDraft` semantics |
| Queue | `queue.md` | `QueueItem` + `QueueItemState` |
| Commands | `commands.md` | `CommandDefinition`, same-registry rule |
| Permissions | `permissions.md` | `PermissionMode` + `RiskFacts` |
| Protected Paths | `protected-paths.md` | Protected-path matcher, rail escalation |
| Diff Review | `diff-review.md` | `FileDiff` + `DiffHunk` + `DiffLine` |
| Checkpoints and Restore | `checkpoints-restore.md` | `Checkpoint`, `PerToolCheckpoint` |
| Recovery | `recovery.md` | `RecoveryState` (with `preservedDraft`) |
| Validation Output | `validation-output.md` | `CommandStream` |
| Subagents and Tasks | `subagents-tasks.md` | `TaskEntry` + `SubagentEntry` |
| Search, File, Symbol | `search-file-symbol.md` | `FileReference` + `SymbolEntry` |
| TUI Rendering | `tui-rendering.md` | Full-screen render contract |
| Terminal Compatibility | `terminal-compat.md` | Compatibility requirements |

Index: `_index.md` cross-links all 16 contracts plus this file and `features_behavior.md`.

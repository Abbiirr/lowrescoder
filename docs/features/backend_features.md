# Backend Features Inventory

> Current-state backend inventory.
> Last updated: 2026-05-01.
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
- Headless NDJSON mode: `autocode exec [PROMPT] --json` emits Tier 4.4-compatible NDJSON event stream to stdout. Event schema in `autocode/src/autocode/backend/headless_schema.py` with typed Pydantic models, `protocol_version: "0.2.0-harness"` stamp on every event, `item.kind` constrained to {agent_message, tool_execution, plan_update, approval}, `usage` block always present on `turn_completed` with zero-defaulted cache/reasoning fields. Structured tool events (`tool_call_started`, `tool_call_completed`, `tool_call_failed`) provide first-class tool-execution evidence with tool name, family, call ID, timestamps, duration, args shape/hash, result bytes/hash, and error type. Stdout-only-NDJSON rule enforced; logs/warnings go to stderr. Tool requests emit visible `approval` items; headless JSON denies tool approvals by default unless launched with `--auto-approve`.
- Headless runner: `autocode/src/autocode/backend/headless_runner.py` implements ChatHost protocol subset, reuses `backend/chat.py::run_chat_turn()`, emits NDJSON events without importing or spawning the Rust TUI.
- `--output-schema PATH` flag for typed JSON output via direct `generate_json()`; this validates provider JSON output and does not run full agent context/tool execution.
- `autocode generate-schema --out DIR` emits JSON Schema files for all event types plus a meta schema documenting valid/reserved item kinds.

### Chat Turn Execution

- Chat-turn orchestration extracted to `autocode/src/autocode/backend/chat.py`.
- Chat lifecycle events include request acknowledgement, status updates, streamed output, thinking output, tool-call activity, cost updates, visible warnings/errors, and completion.
- Active turn cancellation cancels the agent loop and propagates cancellation to subagents.
- Steering can cancel an active run and persist the steer message into the current session.
- Provider/model/config state is owned by the backend and projected through RPC and slash commands.

### Provider And Thinking Support

- Layer 4 provider path supports OpenRouter/OpenAI-compatible gateway and Ollama-style local providers.
- P2 prompt-cache breakpoint injection is implemented for explicit-cache OpenRouter models (`anthropic/*` and `google/gemini-*`): the stable system prompt prefix is split from dynamic runtime context with `CACHE_BOUNDARY_MARKER`, `cache_control: {"type": "ephemeral", "ttl": "1h"}` is attached only to the stable block, OpenRouter→Anthropic requests include `anthropic-beta: prompt-caching-2024-07-31`, provider `cache_control` rejection falls back to non-cached requests, and `AUTOCODE_DISABLE_PROMPT_CACHE=true` disables injection.
- Prompt-cache usage capture records cached input tokens, cache creation tokens, and reasoning tokens from OpenAI/OpenRouter-compatible usage metadata. Deterministic cassette fixtures cover cache-write and cache-read shapes; live prompt-cache integration is opt-in because cache behavior is provider-side and token-spending.
- Prompt-cache workspace isolation caveat: provider caches are treated as workspace/session scoped, not organization-global. Silent TTL expiry appears as a later cache-write event and is tracked through cache creation token metrics rather than assumed from wall-clock state.
- Layer 4.5 cost-aware router: `autocode/src/autocode/layer4_5/router.py` deterministically selects provider/model by request class, configured tier map, model rate table, confidence, and `billable_input_cost_factor` cache-multiplier hook. Selections include non-empty explanations and estimated cost deltas; backend/headless hosts apply the selection before Layer 4 provider creation.
- Architect/editor model split: optional `agent.architect_model` overrides planning/research/review mode model selection, optional `agent.editor_model` overrides build mode model selection, and both take precedence over Layer 4.5 auto-routing while preserving the routed provider/tier explanation.
- Prompt-cache keepalive: `autocode/src/autocode/agent/prompt_cache_keepalive.py` provides provider-gated Anthropic/Claude keepalive ticks for the stable prompt prefix, configurable through `agent.cache.keepalive_enabled` and `agent.cache.keepalive_interval_seconds`, with cache-read usage recorded into `CostDashboard`.
- Routing config: `routing.default_tier_map`, `routing.low_confidence_tier`, `routing.fallback_tier`, and `routing.model_rates` are available in config. Without configured rates, routing preserves the current provider/model for all tiers.
- Cost dashboard routing-tier breakdown: `CostDashboard.by_routing_tier()` groups recorded usage and cost by selected routing tier when callers provide `routing_tier`.
- `autocode telemetry drift --last 7d` groups local drift detections by tool, drift kind, and severity.
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
- Nested `AGENTS.md` project-memory loading can collect parent-to-child `AGENTS.md` files from a repo root to the active working directory, preserving broad-to-specific order so deeper rules appear later and can override parent guidance. `/agents reload` hot-loads that nested memory into the command context.
- Ranked repo-map context is generated from Layer 2 for explicit prompt-context use and the `/repomap` command while first-turn bootstrap keeps repo-map generation deferred.
- Repo-map generation uses token-budget markdown output, dependency fan-in ranking, persistent file metadata cache invalidated by mtime+sha256, and Python+Go symbol extraction.
- Subprocess LSP adapter framework is implemented in `autocode/src/autocode/layer2/lsp_client.py` with stdio JSON-RPC framing, initialize capability negotiation, lazy start, bounded restart-on-crash, graceful shutdown, idle reap, and a nine-operation client surface for future language adapters.
- LSP adapter registry substrate is implemented in `autocode/src/autocode/layer2/lsp_servers/` with file-extension adapter resolution and non-spawning doctor readiness checks.
- Java LSP adapter support is registered for `.java` files via `jdtls`, including deterministic workspace setup, build-file discovery for `pom.xml`/Gradle roots, Java runtime readiness metadata, and project-local fixture coverage for the nine-operation client surface.
- JavaScript and TypeScript LSP adapter support is registered through `typescript-language-server`, with explicit routing for `.js`/`.jsx`/`.mjs` and `.ts`/`.tsx`/`.d.ts`, project config discovery, TypeScript type-diagnostic metadata, peer-dependency doctor metadata, and project-local fixture coverage.
- C, Kotlin, and Python subprocess LSP adapters are registered for `.c`/`.h`, `.kt`/`.kts`, and `.py`/`.pyi`, with `clangd`, `kotlin-language-server`, and `pylsp` readiness metadata respectively. Kotlin uses an extended request timeout, Python keeps Jedi-backed `lsp_*` tools reachable as fallback for one release, and all fixtures stay project-local.
- Go and Rust subprocess LSP adapters are registered for `.go` and `.rs`, with `gopls` plus Go 1.16+ readiness metadata, `rust-analyzer` plus rustup component metadata, `go.mod` / `Cargo.toml` discovery, Rust cold-cache timeout extension, and project-local fixture coverage for the nine-operation client surface.
- Post-edit auto-verify is implemented in `autocode/src/autocode/agent/auto_verify.py` and wired into `AgentLoop` after successful filesystem-mutating tools. It runs LSP diagnostics for edited files with registered adapters, skips unsupported or disabled languages, feeds formatted diagnostics back into the tool result, respects `/verify on|off|status`, surfaces persistent failures without automatic rollback, and halts retry guidance when the cost limit has been crossed.
- P3a drift detectors live in `autocode/src/autocode/agent/drift.py`: schema drift detects structural changes in repeated tool outputs, context staleness warns on old MemoryFS topic reads, and same-turn tool consistency detects deterministic tools returning conflicting results. Detectors are registered through the internal hook dispatcher when `agent.drift.*.enabled` is true, inject drift warnings before the next model turn, and emit `tool_drift_detected` telemetry.
- Iteration-zero bootstrap can include bounded cached Layer 1 symbol previews for active working-set files only.
- Tool-result truncation is adaptive and preserves high-signal code, error, traceback, and list structure under per-tool budgets.

### Tool Runtime

- Core file/system tools: `read_file`, `write_file`, `edit_file`, `list_files`, `search_text`, `run_command`, and `apply_patch`.
- Git tools: `git_status`, `git_diff`, and `git_log`.
- Web/tool discovery surfaces: `web_fetch` and `tool_search`.
- Layer 1/2 code-intelligence tools: `find_references`, `find_definition`, `get_type_info`, `list_symbols`, `search_code`, `semantic_search`, plus Jedi-backed `lsp_goto_definition`, `lsp_find_references`, `lsp_get_type`, and `lsp_symbols`; a broader subprocess LSP client substrate now exists for upcoming multi-language adapters.
- Task tools: `create_task`, `update_task`, `list_tasks`, and `add_task_dependency`.
- Todo tools: `todo_write` and `todo_read`.
- Recipe/workflow YAML packaging: `autocode/src/autocode/agent/recipes.py` validates and discovers bundled, global (`~/.autocode/recipes/*.yaml`), and project-local (`.autocode/recipes/*.yaml`) recipes; `/recipe list|run <name>` can create task steps and dispatch prompt/subagent-style steps through the shared loop.
- Search convenience tools: `glob_files` and `grep_content`.
- Subagent tools: `spawn_subagent`, `check_subagent`, `cancel_subagent`, and `list_subagents`.
- Tool-result cache tools: `list_tool_results`, `clear_tool_result`, and compatibility `clear_tool_results`.
- Durable memory tools: `memory_read_topic`, `memory_write_topic`, `memory_grep_logs`, and `memory_index_show` operate on the P3 file-system memory root and are registered in the default tool registry.
- Scratch store for large tool output: `autocode/src/autocode/agent/scratch.py` offloads large or always-offloaded tool results to `.autocode/scratch/<thread-id>/<turn-id>/<NNN>-<tool>.md`, returns compact stubs with summary + first 5 lines, writes `manifest.json`, keeps the last 10 turn directories, honors `SCRATCH_NEVER_FOR` / `SCRATCH_ALWAYS_FOR`, and supports `AUTOCODE_DISABLE_SCRATCH=true` to inline all outputs.
- `ask_user` tool supports backend-driven explicit user questions.

### Safety, Approval, And Hooks

- Approval manager covers approval decisions and hard-block rules.
- Dangerous shell commands are blocked before execution.
- Dangerous write paths/content are blocked for write/edit/apply-patch paths before handlers execute.
- Interruptible tool cancellation is supported; non-interruptible in-flight tools can finish before cancellation propagates.
- PreToolUse and PostToolUse hooks are wired.
- Internal backend hook dispatcher is wired through `autocode/src/autocode/agent/hooks.py` and factory-created `AgentLoop` instances. It provides ordered exception-isolated lifecycle dispatch for `pre_turn`, `post_turn`, token callbacks, pre-tool calls, synchronous post-tool result augmentation, asynchronous post-tool result augmentation, and tool errors. Current internal adapters cover scratch offload, git-aware staging, per-tool checkpoints, and post-edit auto-verify.
- Background subagents auto-deny approval-requiring tools.
- Sandbox policy primitives exist in `autocode/src/autocode/agent/sandbox.py`.
- Git-aware post-edit staging stages successful FS-mutating tool outputs with `git add` only and surfaces deterministic user-owned commit-message proposals; forbidden git operations are blocked at the wrapper layer.
- Legacy multi-edit and write/edit safety paths use local file-copy snapshots instead of git commits/resets; product code has source-scan coverage preventing forbidden git subprocess operations.

### Sessions, Messages, And Checkpoints

- SQLite-backed sessions persist messages and tool-call rows.
- Session create/list/resume/fork are available over backend RPC.
- Session resume supports prefix matching and ambiguity errors.
- Session forks persist `parent_session_id`, copy bounded message/tool-call snapshots, expose `/fork [session_id]` and `/tree`, and provide a deterministic rollout replay payload from stored message/tool-call order.
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
- Subagent spawn tools can optionally allocate an isolated git worktree and include a read-only diff-to-`apply_patch` merge-back plan. Integration remains user/reviewer-owned; no commits, pushes, merges, pulls, resets, or checkouts are performed by the merge-back helper.
- Recurring `/loop` jobs are implemented in the slash-command runtime.
- Watch mode state and marker parsing support `# AUTOCODE: <instruction>` file-save directives through `autocode/src/autocode/agent/watch.py` and `/watch on|off|status`.

### Memory And Episode Retention

- P3 file-system memory is implemented in `autocode/src/autocode/session/memory_fs.py` as a three-layer durable store under `~/.autocode/projects/<git-root-sha256-prefix>/`: bounded `MEMORY.md` index, topic files under `memory/<topic>.md`, and append-only daily logs under `logs/YYYY/MM/YYYY-MM-DD.md`.
- The durable memory index is capped at 200 lines with pointer lines capped near 150 chars; topic files include YAML-style frontmatter (`topic`, `type`, `created`, `updated`, `size_lines`, `summary`) and warn above the 1000-line soft cap.
- Backend and headless runtime paths use `MemoryFS` by default for learned memory context and consolidation writes. `AUTOCODE_USE_LEGACY_MEMORY=true` keeps the legacy SQLite `MemoryStore` path available for rollback.
- Legacy `memory.list` RPC payloads read from `MemoryFS.get_memories()` when MemoryFS is active, avoiding stale SQLite-only reads.
- `scripts/migrate_memory_to_fs.py` and `autocode.session.memory_migration` migrate legacy SQLite `memories` rows into grouped MemoryFS topics and rename the old table to `memories_archive_<date>` without dropping data.
- Session Notes are implemented in `autocode/src/autocode/session/session_notes.py` with 10k-token activation, 5k-token update interval, minimum 3 tool calls between updates, bounded note length, a write-only updater contract (`write_file` allowlist), and Path A compaction integration in `ContextEngine.auto_compact()`.
- Compaction telemetry emits `compaction_event` with `path`, `tokens_before`, `tokens_after`, and `duration_ms` when Path A or Path B compaction runs.
- Legacy SQLite memory extraction remains available behind rollback and is robust to malformed bracketed preambles before valid JSON arrays.
- Episode retention creates deterministic non-LLM summary events before old episodes are pruned.
- Summary recursion is capped so summary rows do not recursively dominate retained history.

### Cost And Token Accounting

- `CostDashboard` tracks per-session input/output/cached-token usage and estimated cost.
- OpenRouter cached prompt token metadata is captured where provider usage exposes it.
- `TokenTracker` tracks cache reads, cache writes, reasoning tokens, per-provider cache totals, and an effective billable input multiplier using 0.10x cache-read and 1.25x cache-write factors.
- Session token usage persists in SQLite and is hydrated on session resume, so `/cost` and `/cost --detail` can survive backend restarts.
- Rust TUI cost updates include cached input token counts and render a `⚡N% cached` status-bar indicator when cache reads are present.
- `/cost` and `/cost --detail` display real session usage from the dashboard rather than message-character heuristics.
- Optional `agent.cost_limit_usd` emits a single warn-and-continue notification on threshold crossing.
- Provider/model aggregation and cache-savings estimates are available in detailed cost output.

### Local Telemetry

- P1a local-only telemetry is implemented in `autocode/src/autocode/telemetry/`.
- `TelemetryStore` writes append-only daily JSONL files under `~/.autocode/telemetry/events-YYYY-MM-DD.jsonl` using a bounded non-blocking queue and daemon writer thread.
- `TelemetryAggregator` reads local JSONL files, filters by kind/session/date window, summarizes by event kind and session, and exports JSONL or CSV.
- `autocode telemetry summary --last 7d|30d|all`, `events --kind ... --session ...`, `session <session_id>`, `export --since YYYY-MM-DD --format jsonl|csv`, and `purge` are available through the CLI.
- `AUTOCODE_TELEMETRY_DISABLED=true` disables emission; `autocode telemetry purge` deletes the local store.
- Agent-loop telemetry covers `session_start`, `turn_start`, `turn_completed`, `turn_interrupted`, `llm_call_completed`, `tool_call_started`, `tool_call_completed`, `tool_call_failed`, approval decisions, shell permission escalation, and P3 compaction events.
- P2 cache telemetry emits `cache_breakpoint_applied` when a stable prefix breakpoint is present and populates `llm_call_completed` with cached input, cache creation, and reasoning token fields.
- P2a scratch telemetry emits `tool_output_offloaded` with `tool_name`, `result_bytes`, and `scratch_path` whenever a tool result is replaced by a scratch stub.
- Backend session transition telemetry covers initial thread start, new-session thread start, session resume, session fork, and session shutdown.
- Reserved event kinds for later phases are declared in the catalog but not emitted until the owning feature lands.

### Slash Commands And Backend RPC Surface

- Backend-owned slash-command catalog is exposed through `command.list`.
- Current command runtime includes session, model/provider, mode, TUI mode, compaction, shell, copy, freeze, thinking, clear, loop, index, repomap, tasks, plan, research, build, review, architect/editor model overrides, nested AGENTS reload, fork/tree, recipe list/run, watch mode, marketplace list/info/install stubs, memory, checkpoint, rollback, undo, diff, cost, and export commands.
- Frontend-facing RPC methods include `chat`, `cancel`, `command`, `command.list`, `session.new`, `session.list`, `session.resume`, `session.fork`, `model.list`, `provider.list`, `task.list`, `subagent.list`, `subagent.cancel`, `plan.status`, `plan.set`, `plan.export`, `plan.sync`, `config.get`, `config.set`, `memory.list`, `checkpoint.list`, `checkpoint.restore`, `steer`, and `shutdown`.
- Backend notifications include status, warning, token, thinking, done, tool-call, task-state, cost-update, error, and chat-ack events.
- Backend-originated frontend requests include tool approval and ask-user flows.
- Static marketplace registry pointer: `autocode/src/autocode/external/registry.py` reads `docs/marketplace/registry.json` without remote fetch, and `/marketplace list|info|install` surfaces bundled/pre-vetted entries with local-only install guidance.

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
- Metrics beyond cost/token accounting and local telemetry summaries are not consolidated into an operational dashboard.
- Auto-verify currently feeds diagnostics back through the agent/tool-result path; dedicated frontend validation drawer events remain planned in `docs/features/validation-output.md`.

## Planned Or Deferred Backend Features

- L3 broadening only after optional-extra activation criteria, route tests, and integration tests are defined.
- Tool-call execution memoization with safe invalidation for file-reading and environment-sensitive tools.
- Citation surfacing for code/search context and generated answers.
- Provider failover and retry policy beyond current warning/retry behavior.
- Streaming back-pressure and cancellation cleanup across every provider/tool edge case.
- Plan artifact versioning and richer task/plan synchronization.
- Subagent permission scoping, scheduler fairness, and deeper delegation policy controls.
- Additional telemetry hooks for skill trigger accuracy, hook success, retry counts, compaction behavior, drift events, eval signals, and provider latency.
- Config validation UX improvements around layered configuration and one-shot runtime overrides.
- Long-form supervision UX for extended loops, subagent swarms, and recovery flows.
- Tool/front-end consumption of the new subprocess LSP client surface.
- `/sandbox <mode>` slash command and command-scoped allow/deny policy controls.

### AI Verification Harness (P1 Narrow Substrate)

- YAML scenario loader: `benchmarks/ai_verification/scenario_yaml.py` converts human-friendly YAML scenario definitions (with `expected_outcomes` extension) to existing `ScenarioSpec` objects.
- NDJSON runner: `benchmarks/ai_verification/ndjson_runner.py` spawns `autocode exec "<prompt>" --json --auto-approve` against a sandbox, captures NDJSON stdout, and parses events via `headless_schema.validate_event()`. Returns `RunResult` with event list, tool call count, and token usage.
- NDJSON grader: `benchmarks/ai_verification/ndjson_grader.py` applies `must_have` / `must_not_have` predicates over the NDJSON event stream. Supports event-type, kind=, and field-presence predicates.
- 7 hand-graded YAML scenarios in `benchmarks/ai_verification/scenarios/`: simple edit, tool output shape, session persistence, cost routing, headless NDJSON protocol invariant, prompt-cache hit ratio, and large tool-output offload.
- Upgraded `run_scenario.py._run_autocode()` to use the NDJSON runner instead of the previous `--non-interactive` placeholder, enabling structured tool-call/token accounting from C6.G5 NDJSON output.
- `ScenarioSpec.expected_outcomes` field added for `must_have` / `must_not_have` NDJSON grader predicates, backward-compatible (defaults to empty lists).
- `RunMeta.status` records the final scenario verdict independently from the agent process `exit_status`, so artifacts distinguish transport/process failures from deterministic scenario failures.

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

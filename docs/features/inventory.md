# AutoCode Feature Inventory

Last refreshed: **2026-04-30** (UTC offset Asia/Dhaka).

This is a point-in-time inventory of implemented runtime features across the repo, based on source files and feature docs.

## 1) Product Surface

### 1.1 CLI / Launcher

- `autocode` (default launcher): starts Rust TUI by default.
- `autocode --mode inline|altscreen`: terminal mode hint for Rust TUI.
- `autocode --attach HOST:PORT`: attach Rust TUI to backend TCP host.
- `autocode chat --tui`: fallback Textual TUI.
- `autocode chat --legacy`: fallback legacy Rich mode (no full agent loop).
- `autocode ask`: one-shot ask prompt.
- `autocode edit`: placeholder command surface (not yet implemented).
- `autocode config`: show/check/set/path for config.
- `autocode serve --transport stdio|tcp --host --port`: run backend server host.
- `autocode mcp-serve`: read-only MCP server.
- `autocode exec --json` and `autocode exec --output-schema`: headless execution modes.
- `autocode generate-schema`: emit NDJSON schemas for headless protocol.
- `autocode team`: team management/list/create.
- `autocode rename`: symbol rename preview/apply.
- `autocode version`, `doctor`, `setup`.

### 1.2 Frontend

- **Canonical frontend:** Rust TUI (`autocode/rtui`), inline + alt-screen modes.
- **Secondary frontends (supported fallback paths):**
  - Textual TUI (`autocode/src/autocode/tui/*`).
  - Rich REPL (`chat --legacy`).
- Rust TUI capabilities:
  - streaming transcript and status bar
  - fixed composer with multiline + paste handling
  - slash autocomplete
  - command palette and command picker surfaces
  - model/provider/session/task/subagent pickers
  - approval and ask-user modals
  - task/subagent side panel + recovery states
  - queue and detail surfaces

## 2) Backend Runtime

- JSON-RPC application split by transport (`stdio`, `tcp`) and dispatcher/services.
- Chat orchestration with lifecycle events and cancellation.
- Provider/model-aware `think` request handling and streaming think-token handling.
- Request routing across Layer 1 / Layer 2 / Layer 3 (opt-in) / Layer 4.
- Cost-aware Layer 4.5 routing (`RequestType` + tier + model-rate table).
- Headless execution:
  - NDJSON stream with protocol versioned events.
  - typed schema output generation.

## 3) Intelligence Layers and Code Intelligence

### 3.1 Layer 1

- Tree-sitter parser cache and file AST analysis.
- Symbol extraction (functions/classes/methods/imports/vars).
- Deterministic deterministic routing path for fast symbol-level queries.

### 3.2 Layer 2

- Code chunking and embedding search flow.
- BM25 + vector + RRF hybrid search.
- Repository map generation with ranked symbol graph.
- Retrieval index persistence/invalidation and rule loading.
- Query tools for search/definitions/references/symbol/type info via L1 + LSP-backed paths.

### 3.3 Layer 3

- Constrained-generation path exists via `llama-cpp-python` + outlines adapter scaffolding.
- Optional/extra-based and not the default path in core flow.

### 3.4 Layer 4

- LLM provider abstraction with Ollama/OpenRouter-compatible paths.
- Tool calling, structured output (`generate_json`), streaming generation.
- OpenRouter reasoning metadata plus `<think>` stream parsing in compatible flows.

## 4) Agent Runtime

- Main agent loop with:
  - tool calling and tool-result flow
  - turn iteration limits and cancellation
  - middleware hooks (`PreToolUse`, `PostToolUse`, error/retry controls)
  - context packing/budgeting and adaptive truncation
  - auto-verify integrations after file edits
  - steering/cancellation signal propagation.
- Tool-shim fallback parsing for models that return inline tool-call formats.
- Auto-verify flow runs post-edit diagnostics for supported language tooling.

## 5) Tools

Total tool surface is implemented via registry composition:

- Core tool registry (`autocode/src/autocode/agent/tools.py`)  
- Task tools (`autocode/src/autocode/agent/task_tools.py`)  
- Subagent tools (`autocode/src/autocode/agent/subagent_tools.py`)  

Tool families:

- Filesystem/read-write: `read_file`, `write_file`, `edit_file`, `list_files`, `search_text`, `apply_patch`.
- Git: `git_status`, `git_diff`, `git_log`.
- Execution/systems: `run_command`, shell enablement + blocking policy.
- Discovery/search: `web_fetch`, `glob_files`, `grep_content`, `find_references`, `find_definition`, `get_type_info`, `list_symbols`, `search_code`, `semantic_search`.
- LSP family: `lsp_goto_definition`, `lsp_find_references`, `lsp_get_type`, `lsp_symbols`.
- Session/project helpers: `todo_read`, `todo_write`.
- Collaboration/orchestration: `spawn_subagent`, `check_subagent`, `cancel_subagent`, `list_subagents`, `create_task`, `update_task`, `list_tasks`, `add_task_dependency`.
- Cache tools: `list_tool_results`, `clear_tool_result`, `clear_tool_results`.
- User interaction: `ask_user`.
- Tool discovery: `tool_search`.

## 6) Sessions, Memory, Persistence

- SQLite session store for messages/tool calls/sessions.
- Session resume/list/fork and prefix matching resume.
- Message and tool-call compaction workflows.
- Memory store + learned-memory projection persistence.
- Episode store and blob store (content-addressed).
- Training event recorder and JSONL export scaffolding.
- Checkpointing:
  - session checkpoints
  - per-tool pre-tool checkpoints with file snapshots
  - checkpoint restore + rollback + undo integration.

## 7) Permissions, Safety, and Governance

- Permission modes: read-only / suggest / auto / autonomous.
- Approval decisions for risked tools and policy evaluation.
- Dangerous-command and dangerous-write/path/content blocking.
- Protected-path behavior with escalation path.
- Approval UX integration and shell enablement toggles.
- Subagent policy guardrails for auto-deny approval-requiring actions.

## 8) Cost, Config, Telemetry

- Cost dashboard and token accounting with per-session metrics.
- `/cost` and `/cost --detail` projection.
- Usage accounting includes cache token and reasoning/token fields.
- Config model (`AutoCodeConfig`) with validation and check command.
- Structured logs, session log rotation/sessions dirs, and event capture.

## 9) Checkpoints, Recovery, Diff, and Git

- `/checkpoint`, `/undo`, `/rollback`, and `/diff` command runtime.
- Git-aware post-edit staging (`git add`) and restricted forbidden git operations.
- Diff review payload path from tool results and git-backed comparisons.
- Recoverable/undoable edit workflow integrated with session history.

## 10) External/Interop Surfaces

- MCP read-only server:
  - exposed read-only tools
  - stdio transport
  - audit logging and allowlist validation.
- External adapters for benchmark/eval interoperability.

## 11) Benchmarks and Quality Gates

- Benchmark matrix and scenario framework (`benchmarks/*`).
- Calculator + bugfix + CLI scenario support.
- Evidence-oriented tracks:
  - unit/integration tests
  - benchmark tests
  - Rust TUI tests
  - PTY smoke
  - VHS visual regressions
  - transport conformance suites
  - TUI reference matrix and diff/rule checks.
- AI verification harness (HFIX):
  - Headless protocol `0.2.0-harness` with structured `tool_call_started/completed/failed` events providing first-class tool-execution evidence.
  - Typed trajectory assertions (`must_use_tools`, `must_not_use_tools`, `in_order_tools`, `any_order_tools`, `must_use_tool_families`, `min/max_tool_calls`).
  - Typed artifact assertions (`must_change_files`, `must_not_change_files`, `require_non_empty_diff`, `forbid_noop_pass`, `must_contain_text`, `must_remove_text`).
  - Typed turn assertions (`min_turns`, `max_turns`, `no_regression_after_pass`, `require_final_turn_grading`).
  - Per-run artifacts: `turns.json`, `tool_calls.jsonl`, `trajectory_report.json`, `run_summary.json`, `grading_report.json`.
  - Infrastructure classification: empty turns, 429/rate-limit, timeouts, sandbox failures classified as `INFRA_FAIL` distinct from `FAIL`/`PASS`/`PARTIAL`.
  - Subprocess-isolated benchmark lane workers with process-group timeout kill.
  - Structured transient retry classification via `failure_evidence.transient_class`.
  - Canaries: `refactor-noop-guard.yaml`, `multi-turn-regression.yaml`, `tool-trajectory-git.yaml`, `ask-user-scripted.yaml` (gateway-deferred), `semantic-search-required.yaml`, `spawn-subagent-required.yaml`.
  - `summarize_runs.py` report CLI scanning run dirs for verdict counts, infra reasons, tool coverage, assertion failures, missing artifacts, and slowest runs.

## 12) Slash Commands (Backend-Owned Registry)

Registered commands in `autocode/src/autocode/app/commands.py`:

- `exit`, `new`, `sessions`, `resume`
- `help`, `model`, `provider`, `mode`, `tui`, `compact`, `init`, `shell`
- `copy`, `freeze`, `thinking`, `verify`, `clear`
- `loop`, `index`, `repomap`, `tasks`, `plan`, `research`
- `build`, `review`, `architect`, `editor`, `agents`
- `fork`, `tree`, `memory`, `checkpoint`, `undo`, `rollback`
- `diff`, `cost`, `export`

## 13) Non-Implemented / Deferred from Current Inventory

- Full `edit` command body.
- Full backend/frontend first-class capability negotiation and reconnect protocol.
- Full remote-host hardening for transport/security beyond local-first design.
- Complete LSP feature parity for all supported adapters (surface exists; consumption breadth is still progressing).
- Hard-abort cost limits and richer long-running control policies.

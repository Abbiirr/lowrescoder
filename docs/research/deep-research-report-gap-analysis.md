# Deep-Research Report → Gap Analysis

Last updated: 2026-04-12 (Phase A + Phase B bundles complete, integration loose ends closed)
Source: `docs/research/deep-research-report.md` (487 lines, Claude research)
Scope: audit current AutoCode capability surface against the report's proposed multi-lane execution model, typed tool surface, memory planes, governance, and sandbox tiers.
Status: **Phase A + Phase B complete (~60%), all integration loose ends closed.** Phase C architectural frontier (multi-lane router, virtual shell, OS sandbox integration, PTC, SQL query tool, container/microVM lanes) is still open.

## TL;DR

Implemented (Phase A + Phase B delta):

Phase A (Lane A typed host APIs):
- Typed T0/T1 core tools (read/write/edit/search/list/run/tool_search)
- **Typed git API** (`git_status`/`git_diff`/`git_log`, read-only, structured) — Phase A Item 1
- **Mandatory caps on `read_file` / `search_text`** (2000 lines / 256 KB / 500 hits / 64 KB) — Phase A Item 2
- **`run_command` shell-escalation detection** (`bash -lc`, `eval`, `$(...)`, backticks — output-prefix annotation) — Phase A Item 3
- **Typed `web_fetch`** with domain allowlist, hard byte cap, binary refusal — Phase A Item 4

Phase B (transactional edits, context ops, LSP, governance):
- **`apply_patch` with dry-run + conflict detection** (`agent/apply_patch.py`, atomic multi-file range edits) — Phase B Item 1
- **Tool-result clearing primitive** (`agent/tool_result_cache.py`, by id / tool / age / all) — Phase B Item 2
  - **Now exposed as `clear_tool_results` meta-tool** in registry (Phase B integration loose end 1)
- **LSP tools via Jedi** (`agent/lsp_tools.py`, `goto_definition`/`find_references`/`get_type_hint`/`list_symbols`) — Phase B Item 3
- **Fail-closed sandbox mode** (`ShellConfig.fail_if_unavailable`, `run_sandboxed` returns code 126 when no bwrap/Seatbelt) — Phase B Item 4
- **Pattern-based permission rules** (`agent/permission_rules.py`, `Bash(npm run test *)` style with deny-first precedence and inline self-tests) — Phase B Item 5
  - **Now enforced at `_handle_run_command`** call site (Phase B integration loose end 2); config via `ShellConfig.permission_rules`

Ambient infrastructure:
- Four-plane memory model + durable-memory consolidation pipeline
- Deferred tool loading + `tool_search` meta-tool
- Policy hooks (stop_gate.sh, pre_tool_guard.sh) + approval modes
- Retrieval contract + semantic search
- Verification gate (BUILD mode)
- Strategy overlays + runtime state
- Inline TUI arrow pickers: `/model`, `/provider`, `/mode`, `/sessions`, `/resume`, `/loop cancel`, `/checkpoint`, `/copy pick`

Missing (all Phase C — large architectural work):
1. **Multi-lane execution router** with tier selection (Lane A→F) — Phase C Item 1
2. **Virtual shell lane (just-bash)** — Phase C Item 2
3. **OS-level sandbox integration first-class** (Seatbelt/Landlock/bwrap beyond B29 fixtures) — Phase C Item 3
4. **Programmatic tool calling (PTC)** — Phase C Item 4
5. **SQL/SQLite query tool** — Phase C Item 5
6. **Container/microVM lanes** (rootless Docker, gVisor, Firecracker) — Phase C Item 6

Also deferred (medium-priority inline TUI UX polish, not research-report scope):
- Bare `/` multi-line command menu (prompt_toolkit architectural limitation)

Landed since last sync (inline TUI pickers, commits `635fd26`, `9f03567`):
- `/loop cancel` arrow picker — DONE
- `/checkpoint` arrow picker — DONE
- `/copy pick` message-selection picker — DONE

## Detailed Status

### A. Typed host APIs (Lane A, T0–T1)

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| `read_file(offset, limit)` with mandatory caps | Highest | **DONE** | `_handle_read_file` auto-caps unbounded reads at 2000 lines / 256 KB with truncation markers (explicit `end_line` bypasses) |
| `write_file` | Highest | DONE | In `CORE_TOOL_NAMES` |
| `edit_file` (range edits) | Highest | DONE | In `CORE_TOOL_NAMES` |
| `list_dir / list_files` | High | DONE | Promoted into `CORE_TOOL_NAMES` 2026-04-11 |
| `glob(patterns, respect_ignore)` | High | PARTIAL | `search_text` + `list_files` cover this; no dedicated `glob` tool yet — low priority |
| Structured `grep` (hits with file/line/column) | Highest | **DONE** | `search_text` now exposes `max_results` param (default 50, hard cap 500, 64 KB byte cap) |
| Semantic search | Medium | DONE | LanceDB + jina-v2-base-code, `semantic_search` alias |
| `tool_search` deferred loading | High | DONE | `CORE_TOOL_NAMES` + deferred tool loading meta-tool |
| **Typed git API** (status/diff/log) | High | **DONE** | `git_status`/`git_diff`/`git_log` in `CORE_TOOL_NAMES`; argv-first, 10s timeout, structured dataclass, 32 KB diff cap |
| Typed git worktree API | Medium | MISSING | Mutation path (commit/rebase/worktree) still goes through `run_command` + approval gate |
| **`apply_patch`** with dry-run + conflict report | Highest | PARTIAL | `edit_file` exists; no dedicated patch API with preflight — **Phase B Item 1** |
| **LSP tools** (definition/references/diagnostics) | High | MISSING | Jedi is Phase 5 planned — **Phase B Item 3** |
| **`web_fetch(url)`** with domain allowlist | High | **DONE** | `agent/web_fetch.py`; suffix+exact allowlist, 64 KB cap, binary refusal, redirect-out-of-allowlist refusal |

### B. Specialized query engines (Lane B, T0–T2)

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| SQL/SQLite query tool | High | MISSING | Report says shell pipelines for data queries are a cost blowup |
| AST / tree-sitter as typed tool | Medium | PARTIAL | Tree-sitter used internally for parsing; not exposed as a query tool |
| Semantic index search | Medium | DONE | `semantic_search` |

### C. Virtual shell (Lane C, T2)

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| just-bash with overlay FS | Medium | MISSING | Report: portable, low-risk shell semantics without host escape |
| Network allowlist in virtual shell | Medium | MISSING | |
| WASM sandbox for JS/Python | Medium | MISSING | |

### D. OS-sandboxed native exec (Lane D, T3)

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| macOS Seatbelt integration | High | MISSING | |
| Linux Landlock integration | High | MISSING | |
| bubblewrap integration | High | PARTIAL | `bwrap` fallback exists only in B29 fixtures |
| Network proxy filtering | High | MISSING | |
| Fail-closed on sandbox unavailable | High | MISSING | Claude Code has `sandbox.failIfUnavailable`; we don't |

### E. Container / microVM (Lane E/F, T4/T5)

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| Rootless Docker + seccomp | High | MISSING | |
| gVisor runsc | Medium | MISSING | |
| Firecracker microVM | Medium | MISSING | |
| Per-sandbox VM (Cloudflare-style) | Medium | MISSING | |

### F. Memory planes (4-plane model)

| Plane | Report Priority | Status | Notes |
|---|---|---|---|
| Plane 0: Immutable system & policy | Required | DONE | Static/dynamic prompt split with caching |
| Plane 1: Project instructions | Required | DONE | `CLAUDE.md`, `AGENT_COMMUNICATION_RULES.md` |
| Plane 2: Session working set | Required | DONE | Bounded active working set (PLAN Sec 0.3) |
| Plane 3: Durable memory (<=200 lines / 25KB) | Required | DONE | `session/consolidation.py` orient/gather/consolidate/prune |
| Plane 4: Tool artifacts cache | Required | **DONE** | L2 CodeIndex cache + explicit `ToolResultCache.clear()` primitive in `agent/tool_result_cache.py` (Phase B Item 2) |

### G. Permission / governance

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| Hard policy layer (managed) | High | PARTIAL | Config + hooks exist; no strict "managed" layer separation |
| Project layer | High | DONE | `CLAUDE.md` + config |
| User layer | High | DONE | `~/.autocode/config.yaml` |
| Deny-first precedence rules | High | **DONE** | `agent/permission_rules.py::evaluate()` — deny-first wins over allow (Phase B Item 5) |
| `Bash(npm run test *)` pattern rules | Medium | **DONE** | `agent/permission_rules.py::parse_rule()` + fnmatch glob semantics (Phase B Item 5) |
| Inline rule unit tests | Medium | **DONE** | `PermissionRule.run_self_tests()` with matches/not_matches (Phase B Item 5) |
| Approval policy decoupled from sandbox | High | DONE | `approval_mode` + `agent/sandbox.py` |
| Policy hooks (pre/post tool) | High | DONE | `stop_gate.sh`, `pre_tool_guard.sh` |
| Fail-closed defaults | High | **DONE** | `ShellConfig.fail_if_unavailable` + `SandboxConfig.fail_if_unavailable` — returncode 126 when no OS sandbox available (Phase B Item 4) |

### H. Context engineering

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| Tool search | High | DONE | Deferred tool loading + `tool_search` |
| **Programmatic tool calling (PTC)** | High | **MISSING** | Phase C — model does not write code that calls tools |
| Compaction | High | DONE | Structured carry-forward memory |
| Tool-result clearing | High | **DONE** | `ToolResultCache.clear(ids|tool|older_than_seconds|all)` in `agent/tool_result_cache.py` (Phase B Item 2) |

### I. Exec contract

| Feature | Report Priority | Status | Notes |
|---|---|---|---|
| `argv[]` first (never shell string default) | Highest | PARTIAL | `run_command` accepts a shell-string command; escalation is annotated, not blocked |
| `bash -lc` treated as risk escalation | Highest | **DONE (visibility)** | `detect_shell_escalation` in `agent/git_tools.py`; compound commands now prefixed with `[shell escalation: …]` in the tool output. Blocking/gating them remains Phase B |
| Mandatory `timeoutMs`, `maxStdoutBytes` | Highest | PARTIAL | `timeout` param exists on the schema; hard byte cap on stdout/stderr TBD |
| Tier hint routing | Highest | MISSING | No multi-lane router — Phase C |

## Proposed Implementation Order (ROI × risk)

### Phase A — Tractable highest-ROI items ✅ **COMPLETE**
1. **Typed git API** — `git_status`, `git_diff`, `git_log` as structured tools — **DONE**
2. **Mandatory caps on `read_file` / `search_text`** — tightened signatures + enforcement — **DONE**
3. **`run_command` hardening** — detect `bash -lc`, annotate as escalation — **DONE**
4. **`web_fetch(url)` tool** with allowlist — **DONE**

### Phase B — Medium-effort ✅ **COMPLETE**
5. **`apply_patch` with dry-run + conflict detection** — `agent/apply_patch.py`, transactional multi-file range edits — **DONE**
6. **Tool-result clearing primitive** — `agent/tool_result_cache.py` with 4 clear modes — **DONE**
7. **LSP tools (Jedi)** — `agent/lsp_tools.py` + `jedi==0.19.2` dep — **DONE**
8. **Fail-closed sandbox mode** — `ShellConfig.fail_if_unavailable` — **DONE**
9. **Pattern-based permission rules** — `agent/permission_rules.py` — **DONE**

### Phase C — Large architectural work (multi-sprint)
10. **Multi-lane execution router** with tier routing
11. **Virtual shell (just-bash)** — Lane C
12. **OS sandbox integration** (Seatbelt/Landlock/bwrap first-class)
13. **Programmatic tool calling (PTC)** — code execution sandbox for PTC
14. **SQL/SQLite query tool**
15. **Container/microVM lanes** (Lane E/F)

## Effort Estimates

| Phase | Scope | Sessions | Blockers |
|---|---|---|---|
| A | Typed git + caps + exec hardening + web_fetch | 1–2 | None |
| B | Patch API + LSP + fail-closed + rule language | 3–5 | LSP blocked on Jedi phase |
| C | Multi-lane router + virtual shell + sandbox tiers + PTC | 8–15 | Architectural; needs design review |

## Risk Notes

- The report explicitly warns about post-leak ecosystem malware distribution via fake Claude Code repos. That pushes Phase C higher than its effort alone would suggest — but only if AutoCode runs untrusted code, which it largely does not today.
- Container/microVM tiers (E/F) are only justified once we're running untrusted agent-suggested dependencies. For the current inside-repo coding-assistant workflow, Lane A/D are sufficient.
- Virtual shell (Lane C) is low-ROI if Lane D (OS sandbox) is properly integrated first.

## Sources

- `deep-research-report.md` — 2026-04-11, 487 lines
- Implementation surface reference: `autocode/src/autocode/agent/tools.py::CORE_TOOL_NAMES`
- Memory planes reference: `autocode/src/autocode/session/consolidation.py`
- Approval modes reference: `autocode/src/autocode/tui/commands.py::_handle_mode`
- Hook scripts reference: `tools/verify/verify.sh`, `autocode/agent/verification.py`

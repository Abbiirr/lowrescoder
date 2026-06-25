# NEW_PLANS_GAPS.md — Plan-by-Plan Gap Analysis

**Date:** 2026-06-22 · **Last updated:** 2026-06-23
**Scope:** All five `lowrescoder/new_plans/PLAN_*.md` briefs against the actual code in `autocode-full/`.
**Method:** Each plan was read in full; the canonical source modules were walked; every gap was anchored to a `file:line` reference and to the plan's own line range.

> **2026-06-23 update.** Several `❌` entries below were stale and are corrected inline (`sense`, G5 distiller, Channel B — now built). A new **§8** folds in everything the original §1–§7 never audited: the Anvil self-maintenance/eval source docs (`harness_copy_teacher/`), the ClipMind security source docs, the autocode-station requirements/mockups, the **empirical test-run status**, and cross-cutting gaps. Full detail and ranked remaining work live in `NEW_PLANS_REST_AUDIT.md`; the actionable checklist is in `NEW_PLANS_REMAINING_TODO.md` (Addendum).

> **Convention used in this document**
> - **IMPLEMENTED** = ships as specified, with file:line refs.
> - **PARTIAL** = ships some of it; what's done vs what's stubbed is enumerated.
> - **MISSING** = no code path, no symbol, no doc.
> - **DEFERRED-DOCUMENTED** = explicitly out-of-scope, with a doc/README that names the deferral.
>
> Closing gates and verification criteria are in `NEW_PLANS_REMAINING_TODO.md`.

---

## 0. Component ↔ plan mapping (verified)

| Plan | Title | Component(s) that implement it |
|---|---|---|
| **PLAN_01** | Harness IDE (agent-facing REPL + MCP tool surface) | `harness-ide/` (root crate) — `Engine`, `mcp/`, `tools/`, `ui/`, `core/` |
| **PLAN_02** | Video Editing Agent | `video-agent/` (Python) |
| **PLAN_03** | Full Codex/Cursor IDE | `harness-ide/crates/station/` (the `autocode-station` crate; embeds the PLAN_01 `Engine`) |
| **PLAN_04** | Teacher Mode (root-cause analyst + ACE playbook) | `autocode/anvil/teacher/` |
| **PLAN_05** | Copycat Mode (structural/outcome/self-distill channels) | `autocode/anvil/` (`registry.py`, `census.py`, `gapdiff.py`, `propose.py`, `cli.py`, `loop.py`) |

The crate split is correct (`harness-ide/Cargo.toml:16-18` declares station as a workspace member; `crates/station/Cargo.toml:13` depends on `harness-ide`). `harness-ide/` is the substrate PLAN_01 specifies; `crates/station/` is the consumer IDE PLAN_03 specifies, and it embeds the same `Engine`.

---

## 1. PLAN_01 — `harness-ide/` (Rust) — Agent-Facing IDE Substrate

**Brief location:** `lowrescoder/new_plans/PLAN_01_HARNESS_IDE.md` (837 lines).
**Status:** ✅ **Phases 0–3 (MVP) shipped; Phase 4–5 partial; Phase 6 hardening absent.**

### 1.1 §1 — REPL design language (`PLAN_01.md:60-117`)

**Verdict: IMPLEMENTED** — the 3-row split, status bar, conversation column, right rail, and composer are all live.

| Spec | Verdict | Evidence |
|---|---|---|
| Status bar (model, policy, cwd, %, mode, thread, pending) | ✅ | `src/ui/statusbar.rs:36-96` |
| Collapsed single-line rows | ✅ | `src/ui/rows.rs:78-125` |
| Right rail (Hunks / Audit / Threads tabs) | ✅ | `src/ui/rail.rs:51-143` |
| Composer with multiline + history | ✅ | `src/ui/composer.rs:70-115` |
| Keybindings: Enter / Alt-Enter / Up / Down / Tab | ✅ | `src/ui/app.rs:302-477` |
| Keybindings: `@` (file-fuzzy), `Ctrl+R` (history), `Ctrl+L` (clear), `Ctrl+G` (`$EDITOR`), `Double-Esc` | ❌ | Not wired in `app.rs:302-477` (only `/` and `!` triggers exist) |
| Plan vs exec mode | ✅ | `core/policy.rs:71-103` denies all non-Read effects under plan |

**Gaps:**
- `Ctrl+R` history search, `Ctrl+L` clear, `Ctrl+G` external editor, `Double-Esc` edit-previous, and `@` file-fuzzy (PLAN_01 §5.1, lines 446-452) are not wired into the composer.
- Slash command set has ~22 of ~50+ Codex commands (PLAN_01 §5.4, lines 491-516). Missing: `/archive /delete /compact /fork /memories /skills /mention /ide /keymap /vim /debug-config /statusline /theme /usage /copy /raw /btw /side /ps /stop /import /feedback /logout /agent /fast /goal /personality /title /apps /plugins /hooks /experimental /approve /sandbox-add-read-dir`. `/init` and `/review` are stubs (`app.rs:692, 701`); `/resume` is a stub (`app.rs:712-714`).

### 1.2 §2 — Tool surface / MCP server (`PLAN_01.md:124-298`)

**Verdict: PARTIAL** — 26 tools shipped; 5 of the expected surface absent.

#### 1.2.1 File system (`PLAN_01.md:136-164`) — IMPLEMENTED

| Tool | Verdict | Evidence |
|---|---|---|
| `read_range` | ✅ | `tools/fs.rs:22-76` (with read-tracker) |
| `read_symbol` | ✅ | `tools/fs.rs:84-176` (regex + brace-balanced; LSP will replace) |
| `list_files` | ✅ | `tools/fs.rs:180-221` (.gitignore-aware, head_limit 100) |
| `stat_file` | ✅ | `tools/fs.rs:232-253` |
| `edit_file` (read-before-edit, uniqueness) | ✅ | `tools/fs.rs:285-452`; `fs.rs:309-315, 318-331` |
| `write_file` | ✅ | `tools/fs.rs:467-521` |
| `move_path` | ✅ | `tools/fs.rs:525-548` |
| `delete_path` (read-before-delete) | ✅ | `tools/fs.rs:550-583` |

#### 1.2.2 Search (`PLAN_01.md:167-172`) — PARTIAL

| Tool | Verdict | Evidence |
|---|---|---|
| `grep` (ripgrep-shaped) | ✅ | `tools/search.rs:13-107` (files_with_matches / content / count) |
| `list_files` | ✅ | re-used |
| `semantic_search` | ❌ | Not in dispatch (`tools/mod.rs:29-80`); zero references in source |

#### 1.2.3 LSP (`PLAN_01.md:175-202`) — PARTIAL (5 of 14)

| Tool | Verdict | Evidence |
|---|---|---|
| `lsp_definition` | ✅ | `tools/lsp.rs:138-194` (real LSP when server on PATH, regex fallback) |
| `lsp_references` | ✅ | `tools/lsp.rs:196-258` |
| `lsp_hover` | 🟡 stub | `tools/lsp.rs:260-279` — returns "type info: <not available in v1 (LSP stub)>" |
| `lsp_symbols` | ✅ | `tools/lsp.rs:281-316` (regex outline) |
| `lsp_diagnostics` | ✅ | `tools/lsp.rs:318-385` |
| `lsp_workspace_symbols` | ❌ | Not registered |
| `lsp_rename` | ❌ | Not registered |
| `lsp_code_action` | ❌ | Not registered |
| `lsp_format` | ❌ | Not registered |
| `lsp_completion` | ❌ | Not registered |
| `lsp_implementation` | ❌ | Not registered |
| `lsp_type_definition` | ❌ | Not registered |
| `lsp_inlay_hints` | ❌ | Not registered |
| `lsp_call_hierarchy` | ❌ | Not registered |

#### 1.2.4 Lint / typecheck (`PLAN_01.md:205-212`) — IMPLEMENTED

| Tool | Verdict | Evidence |
|---|---|---|
| `run_linter` (auto-detect: clippy/eslint/ruff/go vet) | ✅ | `tools/lint.rs:133-135` |
| `run_typecheck` (cargo check/tsc/mypy/go build) | ✅ | `tools/lint.rs:129-131` |
| `lint_diagnostics` (merged) | ✅ | `tools/lint.rs:139-193` |

#### 1.2.5 Run / shell (`PLAN_01.md:215-223`) — IMPLEMENTED + bonus

| Tool | Verdict | Evidence |
|---|---|---|
| `run_command` (approval-gated, sandbox-wrapped, 50KB trunc) | ✅ | `tools/run.rs:24-192` |
| `background_process` (approval-gated, ProcRegistry) | ✅ | `tools/proc.rs:19-73` |
| `tail_output` | ✅ | `tools/proc.rs:75-98` |
| **bonus:** `stop_process` / `list_processes` | ✅ | `tools/proc.rs:100-128` |

#### 1.2.6 Git (`PLAN_01.md:226-239`) — PARTIAL (8 of 10)

| Tool | Verdict | Evidence |
|---|---|---|
| `git_status` | ✅ | `tools/git.rs:30-40` |
| `git_diff` | ✅ | `tools/git.rs:42-61` |
| `git_log` | ✅ | `tools/git.rs:63-78` |
| `git_blame` | ✅ | `tools/git.rs:121-134` |
| `git_checkpoint` (stash + `refs/notes/ide-checkpoint/`) | ✅ | `tools/git.rs:80-119` |
| `git_restore_checkpoint` | ✅ | `tools/git.rs:136-157` |
| `git_commit` (approval-gated) | ✅ | `tools/git.rs:159-203` |
| `git_review` | ✅ | `tools/git.rs:205-215` |
| `git_push` | ❌ | Not registered |
| `open_pr` | ❌ | Not registered |

#### 1.2.7 Browser / Playwright (`PLAN_01.md:242-253`) — PARTIAL (2 of 7)

| Tool | Verdict | Evidence |
|---|---|---|
| `browser_navigate` (HTML→text, UNTRUSTED label) | ✅ | `tools/browser.rs:141-147` (UNTRUSTED at `:135`) |
| `browser_snapshot` (same backend) | ✅ | `tools/browser.rs:145-147` (no accessibility tree) |
| `browser_click` / `browser_type` / `browser_press` | ❌ | Stub `browser_unsupported` at `browser.rs:151-155` ("requires Playwright/CDP backend not configured in v1") |
| `browser_console` | ❌ | Not registered |
| `browser_network` | ❌ | Not registered |
| `browser_screenshot` | ❌ | Not registered |

#### 1.2.8 Session / introspection (`PLAN_01.md:256-263`) — PARTIAL

| Tool | Verdict | Evidence |
|---|---|---|
| `list_threads` | ✅ | `tools/session_tools.rs:75-94` |
| `switch_thread` | ❌ | Not registered |
| `get_diff` | ✅ | `tools/session_tools.rs:33-50` |
| `get_status` | ✅ | `tools/session_tools.rs:12-31` |
| `request_user_input` | 🟡 | `tools/session_tools.rs:96-117` renders question+options; **no TUI card in `app.rs`** — the agent-side stub exists but the UI never pauses on it |

**Bonus session tools:** `apply_hunk` / `discard_hunk` (`session_tools.rs:52-73`); `request_subagent` (`session_tools.rs:119-137`).

#### 1.2.9 Typed MCP content blocks (`PLAN_01.md:266-276`) — IMPLEMENTED

All 7 blocks defined in `core/content.rs:14-74` and serialized to MCP `content` in `mcp/mod.rs:162-233`. Severity enum at `content.rs:76-94`.

#### 1.2.10 MCP server lifecycle (`PLAN_01.md:280-288`) — IMPLEMENTED

`mcp/mod.rs:100-138` — `initialize` returns `protocolVersion: 2025-06-18`, capabilities `{tools:{listChanged:true}, resources, prompts}`; `tools/list` returns the registry; `tools/call` dispatches. `notifications/initialized` accepted at `:133`. Tested in `tests/integration.rs:188-216`.

### 1.3 §3 — Permission model (`PLAN_01.md:300-389`)

**Verdict: PARTIAL** — core discipline shipped, but the `policy` scope and `auto_review` are absent.

| Spec | Verdict | Evidence |
|---|---|---|
| Sandbox modes (ReadOnly / WorkspaceWrite / DangerFullAccess) | ✅ | `core/policy.rs:13-19`; matches Codex names |
| bwrap shim (opt-in via `HARNESS_IDE_SANDBOX=1`) | ✅ | `src/sandbox.rs:46-84`; profile-aware, graceful degradation at `:50-57` |
| Landlock / seccomp layered | ❌ | Not layered (PLAN_01 §3.1, line 312 leaves this as an open question) |
| Approval policy (Untrusted / OnRequest / Never) | ✅ | `core/policy.rs:78-84`; default `OnRequest` at `:91` |
| `approvals_reviewer: auto_review` | ❌ | Only `user` reviewer; no auto_review agent-mode (PLAN_01 §3.2, line 322) |
| Approval scopes (once / session / project / **policy**) | 🟡 | `Profile` switches per-call; **the four scopes are NOT modeled as data** (PLAN_01 §3.3, lines 326-335). `policy` scope is not a first-class type — only ad-hoc `engine.audit(...)` calls in tools like `run.rs:67-77` |
| Approval card risk framing (what / why / scope / origin / policy / risk / repeat / requires_checker) | ✅ | `core/approval.rs:10-28`; rendered at `ui/app.rs:254-284`; risk classifier at `tools/run.rs:216-232` |
| Audit log (sha256-chained, append-only) | ✅ | `core/audit.rs:22-40`; `prev` is sha256 of previous line (`:39`, set at `:105`); append-only via `OpenOptions::append` (`:120-126`) |
| Maker / checker | ✅ | `core/policy.rs:74-75` `required_checker: Option<String>`; `tools/run.rs:45-50` sets it for high/critical; UI refuses self-approval at `app.rs:314-325`. Tested in `tests/integration.rs:263-272` |

### 1.4 §4 — Session and lifecycle (`PLAN_01.md:393-435`)

**Verdict: PARTIAL** — append-only log is there; resumption, compaction, and parallel subagents are not.

| Spec | Verdict | Evidence |
|---|---|---|
| Session record (append-only JSONL) | 🟡 | `core/session.rs:32-43` `SessionLog::append`. **`hash_in`/`hash_out` are NOT added per-event** (the audit log is sha256-chained; the session JSONL is plain) |
| `ide resume` (resumption with picker) | ❌ | CLI has no `--resume <thread_id>`; `/resume` is a stub at `app.rs:712-714` |
| Compaction | ❌ | No `compact` event, no summary snapshot (PLAN_01 §4.3, lines 412-419) |
| Subagents (parallel + forked + background) | 🟡 | `agent/subagent.rs:74-135` `LlmSubagentRunner` is **sequential + read-only**; `request_subagent` at `session_tools.rs:119-137` filters tools at `:29-52`. **Parallel + forked + background subagent modes NOT implemented** (PLAN_01 §4.4, lines 421-428) |

### 1.5 §5 — UI specification (`PLAN_01.md:437-561`)

**Verdict: PARTIAL** — core UX is in place; advanced composter triggers and some slash commands are missing.

| Spec | Verdict | Evidence |
|---|---|---|
| Composer multiline + history + Tab completion | ✅ | `ui/composer.rs:70-115` |
| `@` file-fuzzy, `!cmd` shell, `#` slash, drag-drop image | 🟡 | Only `/` and `!` are wired in `app.rs:444-447`; `@` and `#` and drag-drop are not |
| Output rows (collapsed + expand) | ✅ | `ui/rows.rs:78-125`; one-line summary per tool output |
| Status bar (model, policy, cwd, %, mode, thread, pending) | 🟡 | `ui/statusbar.rs:36-96`; **context % is never updated by the agent** (always 0 — `app.rs:135` initializes `context_pct: 0`) |
| Plan vs exec mode | ✅ | `app.rs:580-594`, `core/policy.rs:71-103` |
| Pending hunk UX (Accept / Reject) | ✅ | `core/hunks.rs` + `engine.rs:50-100`; rail renders at `rail.rs:75-107`; Enter applies, `x` rejects (`app.rs:367-405`) |
| Approval card UX | ✅ | `app.rs:254-284` (yellow `⚠ APPROVE` bar, `[y]/[n]/[c]`) |

### 1.6 §6 — Agent bridge (`PLAN_01.md:563-626`)

**Verdict: PARTIAL** — stdio + HTTP transport work; multi-client multiplex and capability/signed-bearer auth are absent.

| Spec | Verdict | Evidence |
|---|---|---|
| Local stdio transport | ✅ | `mcp/stdio.rs:10-62` |
| Streamable HTTP transport | ✅ | `mcp/http.rs:29-57` (hyper-based, POST `/mcp`) |
| Local `mcp.json` autogeneration | 🟡 | The harness configures `command`/`url` out-of-band |
| Capability-token / signed-bearer-token auth (PLAN_01 §6.2) | 🟡 | HTTP uses bearer (`http.rs:30-38, 80-87`); **no signed-bearer (HMAC) and no capability-token file** |
| Multi-harness (Claude Code + Codex CLI + OpenCode) | 🟡 | Any harness that speaks MCP can connect; **multiplexing by `clientId` is NOT implemented** (single-connection stdio; single-connection HTTP) (PLAN_01 §6.3, lines 588-591) |
| Lifecycle handshake (`initialize` / `notifications/initialized`) | ✅ | `mcp/mod.rs:100-138` |
| Built-in LLM harness (Anthropic + OpenAI providers) | ✅ | `src/llm/{anthropic,openai}.rs`; `agent/mod.rs:82-138` headless exec |

### 1.7 §7 — Phase plan status (`PLAN_01.md:629-744`)

| Phase | Spec | Verdict | Notes |
|---|---|---|---|
| **Phase 0** MCP core + REPL shell + policy compiler | (lines 635-644) | ✅ | Tool set, REPL, stub agent, policy compiler all shipped |
| **Phase 1** Tool registry expansion (LSP, lint, git) | (lines 648-660) | 🟡 | 5 of 14 LSP tools, 8 of 10 git tools, 2 of 7 browser tools |
| **Phase 2** Harness bridge + multi-harness | (lines 662-671) | 🟡 | Transports work; no clientId multiplex; no signed-bearer |
| **Phase 3** Permission profile + approval card + audit log | (lines 673-685) | ✅ | All present; `policy` scope is the soft gap |
| **Phase 4** Plan mode + checkpointing + maker/checker | (lines 688-700) | ✅ | All three shipped |
| **Phase 5** Subagents + background + browser | (lines 702-712) | 🟡 | Subagents sequential read-only; background procs ✅; browser 2 of 7 |
| **Phase 6** Hardening: rootless containers, SBOM, signed builds, headless CI mode, retention reaper, telemetry | (lines 714-726) | ❌ | Headless `serve`/`serve-http` exist as MCP server modes; **no SBOM, no provenance, no rootless worker isolation, no retention reaper, no telemetry** |

### 1.8 Honest assessment

The crate README's claim "every §2–6 feature implemented" (mentioned in the operator's earlier report) is **overstated**. Phases 0–3 (MVP) are real. Phases 4–5 are partial. Phase 6 is absent. The `policy` approval scope (PLAN_01 §3.3, lines 326-335) — listed as "PLAN_01's differentiator" — is not a first-class type. The browser stack is two of seven tools. The LSP surface is 5 of 14. Subagent modes are a fraction of Claude Code's.

---

## 2. PLAN_02 — `video-agent/` (Python) — Video Editing Agent

**Brief location:** `lowrescoder/new_plans/PLAN_02_VIDEO_AGENT.md` (558 lines).
**Status:** ✅ **Core complete; perception backends deferred; UI is CLI-only.**

### 2.1 §2 — Agentic editing patterns / typed CR / JSON EDL (`PLAN_02.md:60-160`)

**Verdict: IMPLEMENTED** — closed op grammar, `extra="forbid"` (no shell/path/command smuggling), discriminated union, JSON-Schema published.

| Spec | Verdict | Evidence |
|---|---|---|
| Typed Change Request (Pydantic) | ✅ | `src/video_agent/schema/change_request.py:1-211` |
| All 12 §2.2 ops (`cut`, `trim`, `crop`, `zoom`, `speed`, `caption`, `callout`, `color`, `transition`, `broll`, `music_duck`, `overlay`) | ✅ | All present; 4 extras (`remove_segments`, `pan`, `normalize_audio`, `chapter`) |
| Discriminated `AnyOp` | ✅ | `change_request.py:172-192` |
| `parse_change_request(payload)` gate | ✅ | `change_request.py:207-210` |
| Published JSON Schema | ✅ | `schema/change_request.schema.json`; `schema/evidence_manifest.schema.json` |
| `jcut` / `lcut` ops (PLAN_02 §5.1, line 233) | ❌ | Not in the op grammar (would each be ~10 lines: pydantic + ffmpeg `adelay` shift) |

### 2.2 §3 — Perception / Evidence Manifest (`PLAN_02.md:103-176`)

**Verdict: PARTIAL** — schema is complete and exhaustive; **only `ffprobe` + `silencedetect` + a hand-rolled ffmpeg-scene-detector are wired**. Heavy backends from §3.2 are not integrated.

| Backend (PLAN_02 §3.2, lines 130-145) | Verdict | Evidence |
|---|---|---|
| Manifest model (all 9 §3.1 fields) | ✅ | `src/video_agent/schema/evidence.py:88-108` |
| ffprobe | ✅ | `src/video_agent/perception/probe.py:10-27, 30-37` (sha256 content_hash) |
| silencedetect | ✅ | `src/video_agent/perception/silences.py:35-53` (CPU-cheap) |
| Scene detection (custom ffmpeg `select=gt(scene,...)`) | ✅ | `src/video_agent/perception/scenes.py:21-44` |
| PySceneDetect | ❌ DEFERRED-DOCUMENTED | `README.md:106-107` ("Honest limits") |
| TransNetV2 | ❌ DEFERRED-DOCUMENTED | same |
| WhisperX / faster-whisper | ❌ DEFERRED-DOCUMENTED | same; `transcript` field is defined but **never populated** |
| pyannote-audio (diarization) | ❌ DEFERRED-DOCUMENTED | same |
| InsightFace (RetinaFace + ArcFace) | ❌ DEFERRED-DOCUMENTED | same; `faces` field is not in the manifest |
| GroundingDINO + SAM2 / YOLOv10 | ❌ DEFERRED-DOCUMENTED | same |
| PaddleOCR | ❌ DEFERRED-DOCUMENTED | same; `on_screen_text` is defined but never populated |
| YAMNet / CREMA / Essentia | ❌ DEFERRED-DOCUMENTED | same; `music` field is defined but never populated |
| PANNs / BEATs | ❌ DEFERRED-DOCUMENTED | same |
| VideoMAE / InternVideo / SlowFast | ❌ DEFERRED-DOCUMENTED | same; `actions` field is not in the manifest |
| Qwen2.5-VL (planner-side) | ❌ DEFERRED-DOCUMENTED | same |

**Bundle rendering** (`src/video_agent/agent/bundle.py:23-46`) only renders populated fields; transcript block is rendered but most sources will have `transcript=[]`.

### 2.3 §4 — Render engine (`PLAN_02.md:178-202`)

**Verdict: PARTIAL (FFmpeg deterministic, Remotion absent).**

| Spec | Verdict | Evidence |
|---|---|---|
| FFmpeg single-source backend | ✅ | `src/video_agent/compiler/ffmpeg_backend.py` |
| `-bitexact`, pinned encoder, strip metadata, frame-identical re-render | ✅ | `ffmpeg_backend.py:283-313` (build), `:160-170` (deterministic `_num`) |
| `format=yuv420p`, timebase `AVTB`, `c:v libx264`, `crf=18` | ✅ | `ffmpeg_backend.py:265-266, 304-305, 310-311` |
| Multi-clip timeline (xfade chain) | ✅ | `src/video_agent/compiler/timeline.py:81-136` (compile), `:139-168` (argv) |
| Remotion dual backend | ❌ | No `remotion/`, no `*.tsx`, no Remotion codegen, no Node.js deps in `pyproject.toml:6-21`; §4.1 defers Remotion to "opt-in progressive enhancement" (this is the documented MVP scope) |
| `broll` render | ❌ parse-only | `ffmpeg_backend.py:55` (`_MULTI_SOURCE_OPS = {"transition", "broll"}`), `:187-191` raises `CompileError`; `timeline.py:83-87` raises `CompileError("op 'broll' needs a stock/asset resolver")` |
| `music_duck` render | ❌ silent no-op | `ffmpeg_backend.py:263` comment: "music_duck/chapter handled elsewhere or as metadata; no-op for the graph." The op is schema-valid but **silently produces nothing** rather than a clean error |

### 2.4 §5 — Proposer/compiler pattern, multi-step plans, named intents (`PLAN_02.md:204-265`)

**Verdict: IMPLEMENTED** for the four sub-areas.

| Spec | Verdict | Evidence |
|---|---|---|
| Proposer/compiler split (propose → validate → render) | ✅ | `src/video_agent/agent/session.py:54-57`; `agent/planner.py` vs `compiler/validate.py` |
| Validation enforces all §5 invariants (bounds, `clip_id` refs, `from`/`to`, sensitivity, no shell/path/command) | ✅ | `compiler/validate.py:60-72`; `CompileError` at `:32-34, 146-149` |
| Multi-step plan with content-addressed artifacts (sha256) | ✅ | `src/video_agent/agent/plan.py:18-24` (canonical), `:27-56` (Step with `cr_hash`), `:59-79` (Plan with `plan_hash`) |
| Replay verifies integrity (recomputes `cr_hash` and compares) | ✅ | `plan.py:37-49`; `Plan.from_dict` integrity check; tested in `cli.py:118-122` |
| Named intent templates | 🟡 | `src/video_agent/templates/intents.py:139-144` registry: `polish_lecture_for_youtube`, `clip_for_shorts`, `quick_caption`, `tighten`, `make_me_a_trailer:111-127`, `clip_highlights_for_shorts` (registered in `templates/__init__.py:20`). **§5.3 lists 6 named intents; 5 implemented; `interview_to_article` and `livestream_vod_to_chapters` are missing** |
| `broll`, `music_duck`, `transition`, `color`, `pan`, `overlay`, `normalize_audio` | ✅ | All 7 in op grammar |
| `jcut` / `lcut` (PLAN_02 §5.1, line 233) | ❌ | Missing from op grammar |
| `chapter` (extra) | ✅ | Implemented as bonus |

### 2.5 §6 — Local vs cloud (`PLAN_02.md:267-301`)

**Verdict: PARTIAL** — hybrid model in place, but the fully-local path is not actually buildable from this repo.

| Spec | Verdict | Evidence |
|---|---|---|
| `HeuristicPlanner` (no network) | ✅ | `src/video_agent/agent/planner.py:41-59` |
| `LLMPlanner` (any OpenAI-compatible callable, schema-gated) | ✅ | `src/video_agent/agent/planner.py:92-131`; `cli.py:27-45` wires `openai` SDK behind `--planner llm` |
| Cloud path requires `OPENAI_API_KEY` | ✅ | Only the live test is skipped (`tests/test_llm_live.py`) |
| Fully-local stack (Qwen2.5-VL/WhisperX/InsightFace/PaddleOCR) | ❌ | No backends wired (see §2.2); the §6.2 fully-local path is not actually buildable |

### 2.6 §7 — UX (`PLAN_02.md:303-353`)

**Verdict: MISSING** — no web/desktop UI, no chat surface, no preview pane, no plan panel, no diff view. The only surface is the CLI.

| Spec | Verdict | Evidence |
|---|---|---|
| Web/desktop chat UI | ❌ | None |
| Preview pane + timeline + diff + accept/reject | ❌ | None |
| Multi-step plan panel | ❌ | The `EditSession` state machine `perceive → propose → validate → render` is the runtime hook a UI would call (`session.py:54-92`), but no UI calls it |
| CLI: `replay` and `diff` (plan-level audit) | ✅ | `cli.py:114-142` (replay), `:145-161` (diff) |

### 2.7 §8 — Differentiation (`PLAN_02.md:357-405`)

| Spec | Verdict | Evidence |
|---|---|---|
| §8.2 #1 Auditable CR history (content-addressed) | ✅ | `agent/plan.py` + `cli.py:114-161` |
| §8.2 #2 Deterministic re-render (frame-identical) | ✅ | `ffmpeg_backend.py:283-313` + `test_render_e2e.py::test_rerender_is_frame_identical` |
| §8.2 #3 Pluggable agent runtime (Planner Protocol) | ✅ | `agent/planner.py:37-131` |
| §8.2 #4 Open CR schema | ✅ | `schema/change_request.schema.json` |
| §8.2 #5 Multi-track audio / ducking | 🟡 | `MusicDuckOp` is **parse-only** (no codegen) |
| §8.2 #6 Local-first / no-egress (default planner) | ✅ | `HeuristicPlanner` is air-gapped |
| §8.2 #7 Multi-step plan UI | 🟡 | Plan object exists; UI is the missing CLI panel |

### 2.8 Test inventory

| File | Tests | Pass/Skip |
|---|---|---|
| `tests/test_schema.py` | 6 | pass |
| `tests/test_evidence.py` | 3 | pass |
| `tests/test_validate.py` | 14 | pass |
| `tests/test_ffmpeg_codegen.py` | 19 | pass (no ffmpeg exec) |
| `tests/test_timeline.py` | 9 | pass |
| `tests/test_templates.py` | 8 | pass |
| `tests/test_highlights.py` | 4 | pass |
| `tests/test_perception.py` | 6 | pass |
| `tests/test_agent.py` | 17 | pass |
| `tests/test_cli.py` | 10 | pass |
| `tests/test_render_e2e.py` | 16 | pass (full ffmpeg exec, frame-identical re-render) |
| `tests/test_llm_live.py` | 1 | **skipped** (no `OPENAI_API_KEY`) |
| **Total** | **113** | **112 passed, 1 skipped** |

---

## 3. PLAN_03 — `harness-ide/crates/station/` (Rust) — Full Codex/Cursor IDE

**Brief location:** `lowrescoder/new_plans/PLAN_03_FULL_CODEX_IDE.md` (654 lines).
**Status:** 🟡 **Working prototype/MVP of a very large spec.** The trust-domain spine + activity rail + editor + agent panel + hunk review are real. ~80% of the traditional IDE surface and ~90% of AI-IDE breadth are missing.

**Source inventory** (13 `.rs` files, ~4,200 LoC):
- `src/main.rs` (L48) — eframe entry, wgpu renderer
- `src/app.rs` (L1399) — Shell: rail, top bar, file tree, central editor, agent panel, status bar
- `src/editor.rs` (L753) — Tabs, code view, Code/Diff toggle, find bar, ⌘I inline bar, outline
- `src/workspace.rs` (L407) — Bridge to `harness_ide::core::Engine` (hunks, audit, policy, approvals)
- `src/palette.rs` (L313) — ⌘K commands + ⌘P quick-open, fuzzy match
- `src/highlight.rs` (L279) — Single-pass syntax highlighter (rs/py/c/js/go/sh)
- `src/harness/{mod,event,autocode,puku}.rs` — Harness trait, event parsers, two adapters
- `src/approver.rs` (L37) — `StationApprover` blocks worker on `mpsc`
- `src/widgets.rs`, `src/theme.rs` — chips, dots, rail items, light/dark palette

**Tests:** 30 inline `#[test]` functions + 24 snapshot baselines under `tests/snapshots/`. Cannot confirm pass count without `cargo test`.

### 3.1 §1 — Codex app features (`PLAN_03.md:28-110`)

| Spec | Verdict | Evidence |
|---|---|---|
| **Projects** | 🟡 | `View::Editor` opened on one root from CLI (`main.rs:27-30`); no project switcher, no persisted project list |
| **Threads** | 🟡 | `harness::Session` (per-harness run) with event stream; no "side-by-side threads" UI |
| **Local/Worktree/Cloud modes** | ❌ | No worktree picker, no remote/SSH mode; only `cwd` passed to harness `spawn` |
| **In-app diff pane** | ✅ | `EditorState::diff_view` (`editor.rs:676-705`) + `diff_layout` colored lines; Review view shows `git_diff` (`app.rs:981-995`) |
| **Stage/revert chunks (Accept/Reject)** | ✅ | Toolbar at `editor.rs:585-610`; ⌘K `AcceptHunk`/`RejectHunk` at `palette.rs:47-48` + `app.rs:431-444` |
| **Inline comments on diffs** | ❌ | Diff is `Label` with select-only; no comment storage |
| **Commit / push / create PR in-app** | ❌ | No git plumbing beyond `git_diff`/`git_status`; no PR API integration |
| **Integrated terminal per thread** | 🟡 | `Run/Output` panel toggled by `⌘J` (`app.rs:208-210, 1165-1224`) runs `run_command`; **not PTY** |
| **Agent-readable terminal output** | 🟡 | `run_command` is dispatched through the engine (`app.rs:256-269`); raw output shown as text, no event-parsed structure |
| **Actions** | ❌ | No `actions.toml`, no named reusable commands |
| **Cmd+K command palette** | ✅ | `palette.rs` entire module; ⌘K wired at `app.rs:215-228`; 12 commands at `palette.rs:37-50` |
| **Scheduled / recurring tasks** | ❌ | `View::Automations` is a placeholder (`app.rs:1226-1233`) |
| **Approval scopes (once/thread/session)** | 🟡 | Approval card has "Approve once" (`app.rs:364`); no "for session" or "for thread" buttons; the scope taxonomy is engine-side |
| **Sandbox controls** | ❌ | No Landlock/seccomp/AppContainer code; no UI control |
| **Native Windows sandbox** | ❌ | — |
| **Skills** | ❌ | — |
| **MCP config (registry UI)** | ❌ | MCP used internally by `harness-ide::core`; no UI for registry |
| **Plugins** | ❌ | — |
| **Voice / drag-drop / screenshots / computer use** | ❌ | — |
| **Floating pop-out thread window** | ❌ | — |
| **In-app browser** | 🟡 | `View::BrowserQa` exists in enum (`app.rs:21`) and rail (`app.rs:725`); routes to `placeholder()` (`app.rs:650`); **no real webview** |
| **Element comments** | ❌ | — |
| **Artifact previews (PDF/Sheets/Deck)** | ❌ | — |
| **Task sidebar (plan/sources/summary)** | 🟡 | Right agent panel is always present (`app.rs:626-631`); shows transcript only; no plan/sources tabs |
| **Web search / image gen / Chats / Memories / IDE-extension sync / prevent-sleep** | ❌ | — |

### 3.2 §2 — Cursor features (`PLAN_03.md:115-170`)

| Spec | Verdict | Evidence |
|---|---|---|
| **Tab completion (single + multi-line)** | ❌ | No completion engine; no ghost text overlay |
| **Cursor prediction** | ❌ | — |
| **Cmd-K inline edit** | ✅ (as `⌘I`) | `editor.rs:342-345` toggles `inline_open`; `:378-413` builds file-scoped instruction routed to harness via `pending_request` → `app.rs:654-656` |
| **⌘L chat** | 🟡 | Agent panel is the chat, but file/selection is not auto-attached |
| **⌘I composer** | ✅ | Composer at `app.rs:824-847` with `⌘↵` send |
| **Agent Mode** | ✅ | `Harness::spawn` runs the agent (`harness/mod.rs:57`) |
| **Plan Mode** | ✅ | `plan_mode` checkbox at `app.rs:791`; passed to `h.spawn(..., plan)` (`app.rs:479`); switches harness to `--permission-mode plan` (`autocode.rs:80-83`, `puku.rs:66-67`) |
| **Background agents** | ❌ | Only one foreground `self.session` |
| **Subagents** | ❌ | — |
| **@symbols / codebase indexing** | 🟡 | `Search` view uses `grep` via engine (`app.rs:903-979`); no `@`-syntax, no embeddings |
| **Privacy mode** | ❌ | — |
| **.cursorrules** | ❌ | — |
| **Memories** | ❌ | — |
| **Apply / Diff / Reject** | ✅ | `editor.rs:585-610` |
| **Multi-model routing** | 🟡 | ComboBox switches between two hardcoded harnesses (`app.rs:782-789`); no Claude/GPT/Gemini enumeration |
| **Bugbot / Migrations / PR review** | ❌ | — |
| **Voice / image paste** | ❌ | — |
| **Debug (DAP)** | ❌ | — |
| **Run & test** | 🟡 | Run panel runs arbitrary commands (`app.rs:1165-1224`); no test-runner UI |
| **Tree-sitter** | 🟡 | Custom single-pass highlighter (`highlight.rs`), not tree-sitter; no AST features (folding, outline from AST) |
| **Cursor CLI / ACP** | ❌ | — |

### 3.3 §3 — Zed features (`PLAN_03.md:176-213`)

| Spec | Verdict | Evidence |
|---|---|---|
| **GPU-rendered UI (wgpu)** | ✅ | `Cargo.toml:18-27` enables `eframe` wgpu + x11/wayland; `main.rs:32-33` sets `Renderer::Wgpu` (NOT `gpui` — uses egui on wgpu) |
| **Tree-sitter native** | ❌ | Hand-rolled highlighter; no `tree-sitter` dep in `Cargo.toml` |
| **LSP-native client** | 🟡 | Symbols from engine's `lsp_symbols` tool (`workspace.rs:234-247`) — engine is the LSP client |
| **Multi-buffer** | ❌ | Single buffer per tab |
| **ACP** | ❌ | — |
| **Inline Assistant** | ✅ | `⌘I` inline bar (`editor.rs:378-413`) |
| **Edit Prediction (Tab)** | ❌ | — |
| **Agent Panel** | ✅ | `agent_panel` at `app.rs:777-848` |
| **Terminal Threads** | ❌ | — |
| **Skills / Instructions / Tools / Profiles** | ❌ | Settings view shows harness info only |
| **Per-tool allow/deny** | 🟡 | Engine enforces (`workspace.rs:62`); UI is the single approval card |
| **CRDT collab / remote / dev containers** | ❌ | — |

### 3.4 §4 — Traditional IDE features (`PLAN_03.md:218-322`)

| Spec | Verdict | Evidence |
|---|---|---|
| **File tree** | ✅ | `EditorState::tree_ui` + `dir_node` (`editor.rs:182-287`); modified badge (`editor.rs:276-281`) |
| **Multi-tab + dirty indicators** | ✅ | `tab_bar` (`editor.rs:507-558`) with `●` dirty prefix |
| **Breadcrumbs** | ❌ | — |
| **Outline view** | ✅ | `editor.rs:203-247` reads `ws.outline()` (engine-side regex scan) |
| **Multi-root workspaces** | ❌ | Single root from CLI arg |
| **Quick open (`⌘P`)** | ✅ | `palette::open_files` (`palette.rs:84-92`); 8000-file cap (`workspace.rs:143`) |
| **File watcher** | ❌ | Uses `std::fs::read_dir` on each draw; no inotify/fsevents |
| **Syntax highlighting** | 🟡 | Hand-rolled single-pass (`highlight.rs`); no semantic tokens, no TextMate grammars, no tree-sitter |
| **Multi-cursor / column select** | ❌ | Single `egui::TextEdit::multiline` |
| **Split view / multi-buffer** | ❌ | — |
| **Minimap** | ❌ | — |
| **Soft wrap** | ❌ | `job.wrap.max_width = f32::INFINITY` (`highlight.rs:93`) |
| **Code folding** | ❌ | — |
| **Snippets** | ❌ | — |
| **Vim/Helix mode** | ❌ | — |
| **Command palette** | ✅ | See §1 |
| **LSP completion / hover / definition / references / rename / code action / format** | 🟡 | Engine exposes tools; station surfaces only the symbol outline. No completion popup, no hover card, no rename UI |
| **Inlay hints / semantic tokens** | ❌ | — |
| **Call hierarchy** | ❌ | — |
| **Find in file** | ✅ | `find_bar` (`editor.rs:415-481`) |
| **Find in files (ripgrep-style)** | ✅ | `Search` view uses engine `grep` (`workspace.rs:252-272`) |
| **Replace (in-file)** | ✅ | "Replace all" in `find_bar` (`editor.rs:465-473`) |
| **Replace (cross-file)** | ❌ | — |
| **Go to line / symbol / file** | ✅ | `scroll_to_line` + `open_at` (`editor.rs:111-114`) |
| **Source Control panel** | 🟡 | `Review` view shows `git_diff`; no `git` operations UI |
| **Diff gutter** | 🟡 | File-tree `●` badge; no per-line gutter markers |
| **Branch / remote / stash / tag / blame** | ❌ | — |
| **Inline PR comments** | ❌ | — |
| **Debug (DAP): breakpoints / step / watch / call stack / launch.json** | ❌ | — |
| **Tasks / problem matchers / test runner** | ❌ | — |
| **Output panel** | ✅ | `Run/Output` panel (`app.rs:1165-1224`) |
| **Integrated terminal (PTY)** | ❌ | Run panel uses `run_command` (subprocess with timeout), not a real PTY |
| **Sidebar (left/right)** | ✅ | Left rail (`app.rs:603-607`), right agent panel (`app.rs:626-631`) |
| **Panel (bottom)** | ✅ | Status bar + run panel (`app.rs:588-600`) |
| **Status bar (path / lang / Ln,Col)** | ✅ | `app.rs:744-775` |
| **Notification toasts** | 🟡 | `note` strings in toolbar (`editor.rs:606-609`); no top-right toast system |
| **Zen / focus mode** | ❌ | — |
| **Zoom** | ❌ | — |
| **Settings (GUI + JSON)** | 🟡 | `Settings` view shows harness matrix + audit log; no editable settings |
| **Keybindings (rebindable)** | ❌ | Hardcoded `⌘K`/`⌘P`/`⌘S`/`⌘F`/`⌘I`/`⌘J`/`⌘↵` |
| **Themes (light/dark)** | ✅ | `theme.rs`; toggle via ⌘K or top-bar button (`app.rs:697-700, 423-430`); persisted |
| **Icon themes** | ❌ | — |
| **Profiles (synced)** | ❌ | — |
| **Extension marketplace** | ❌ | — |

### 3.5 §5 — AI-IDE specific features (`PLAN_03.md:328-378`)

| Spec | Verdict | Evidence |
|---|---|---|
| **Chat panel** | ✅ | `agent_panel` (`app.rs:777-848`) |
| **Inline edit (Cmd-K / Ctrl-I)** | ✅ | `editor.rs:342-413` |
| **Composer (⌘I)** | ✅ | `app.rs:824-847` |
| **Agent Mode** | ✅ | See §2 |
| **Plan Mode** | ✅ | See §2 |
| **Background agent** | ❌ | — |
| **Subagents** | ❌ | — |
| **Multi-agent A/B race** | ✅ | `Compare` view (`app.rs:1098-1163`); `race()` spawns every Ready harness on the same prompt (`app.rs:1060-1096`) |
| **Suggested edits (review flow)** | ✅ | Every save → pending hunk (`editor.rs:169-178` → `ws.stage_write`); Accept/Reject toolbar |
| **@-symbol context injection** | ❌ | — |
| **Slash commands** | ❌ | — |
| **AI diagnostics explanation** | ❌ | — |
| **AI refactor / test gen / doc gen** | ❌ | Harness can do them; no command palette entries |
| **AI commit message / PR description** | ❌ | — |
| **Model selector** | 🟡 | ComboBox between two harnesses (`app.rs:782-789`), not a model list |
| **BYOK** | 🟡 | Inherited from harness binaries (`OPENAI_API_KEY` for puku per `puku.rs:73-76`); no per-provider key UI |
| **Provider-agnostic** | 🟡 | Two adapters shipped; engine has more (`grep`, `lsp_symbols`) |
| **Cost tracking** | ✅ | `HarnessEvent::Cost` → `self.cost_usd`, `self.tokens`; displayed in status bar |
| **Context window indicator** | ❌ | Tokens shown but not against a model limit |
| **Token breakdown by tool/file/model** | ❌ | — |
| **Rate-limit awareness** | ❌ | — |
| **Per-tool permission scopes** | 🟡 | Engine enforces; UI is one binary approval |
| **Approval card with full risk framing** | ✅ | `approval_card` (`app.rs:291-387`): risk chip, WILL RUN, why, scope, origin, policy, maker/checker note, repeat counter, Approve/Deny |
| **Maker/checker separation** | 🟡 | Displayed in approval card (`app.rs:354-361`); logic is engine-side |
| **Audit log** | ✅ | `Workspace::audit_tail` (`workspace.rs:81-99`); displayed in Settings view (`app.rs:1030-1055`) |
| **Diff-first** | ✅ | `Diff` toggle in toolbar (`editor.rs:565-580`) |
| **Sandbox** | 🟡 | Engine-side; no UI control |
| **Checkpoints / time-travel** | ❌ | No `/rewind` or checkpoint list |
| **Privacy mode** | ❌ | — |
| **Memories / Skills / MCP servers (registry UI)** | ❌ | — |
| **Settings sync / cloud sync / IDE-extension sync** | ❌ | — |

### 3.6 §9 — Station-specific carry-overs from AutoCode Station (`PLAN_03.md:573-587`)

| Spec | Verdict | Evidence |
|---|---|---|
| **Pending hunks (Accept/Reject/Ask-why)** | 🟡 | Accept/Reject ✅; **Ask-why MISSING** — no UI affordance for it |
| **⌘I inline edit through review gate** | ✅ | `editor.rs:405-409` builds prompt; routed through `app.rs:654-656` → harness → engine → same hunk registry |
| **Per-file Code/Diff toggle** | ✅ | `ViewMode` enum + toolbar (`editor.rs:19-24, 564-580`) |
| **Activity-rail IA (Inbox default)** | 🟡 | Rail renders all 8 views (`app.rs:716-742`) with Inbox as the first glyph; **default `view` on launch is `View::Editor` (`app.rs:169`), not Inbox** |
| **Command approval card** | ✅ | `app.rs:291-387` |
| **Merge gate with checklist + override** | ❌ | No merge UI; no checklist; no override affordance |
| **Maker/checker separation** | 🟡 | Displayed in approval card; no separate role/identity UX |
| **Immutable attributed audit log** | ✅ | `audit_tail` + display in Settings (`app.rs:1030-1055`) |
| **Browser QA Studio** | ❌ | View enum entry only, no implementation |
| **Harness capability matrix** | ✅ | Settings view shows `HarnessInfo` per adapter (`app.rs:1003-1027`) |
| **Compare (multi-agent runs)** | ✅ | `compare_view` (`app.rs:1098-1163`) |
| **Narrow mode (mobile)** | ❌ | Fixed `1320×860` viewport, no responsive layout |

### 3.7 Honest assessment

**Net verdict:** `crates/station` is a working prototype of the *trust-domain spine* and the *activity-rail + editor + agent-panel* shell, but it is missing ~80% of PLAN_03's traditional IDE surface (LSP, debug, tree-sitter, PTY, real multi-cursor, marketplace) and ~90% of the AI-IDE breadth (background agents, subagents, memories, skills, MCP UI, voice, screenshots, computer use). It is best described as: **a faithful, end-to-end prototype of PLAN_03 §9 (the carry-overs from AutoCode Station) with credible inroads into §1 (approval card, hunk flow, harness adapters) and §2 (composer, plan mode, A/B compare), and a near-empty surface for §3 (Zed/ACP), §4 (traditional IDE), and most of §5 (model selection, cost controls, memories, sync).**

---

## 4. PLAN_04 — `autocode/anvil/teacher/` (Python) — Teacher Mode

**Brief location:** `lowrescoder/new_plans/PLAN_04_TEACHER_MODE.md` (618 lines).
**Status:** ✅ **MVP endpoints (Phases 1–3) implemented; advanced phases 4–7 absent.**

### 4.1 §1 — Teaching-packet schema (`PLAN_04.md:78-127`)

**Verdict: IMPLEMENTED** — all 9 normative fields present.

| Field | Verdict | Evidence |
|---|---|---|
| `packet_id, trajectory_id, verdict, root_cause, score_breakdown, revision, harness_fix, playbook_delta, provenance` | ✅ | `src/autocode/anvil/teacher/schemas.py:352-398` |
| `Verdict` (diff_applies/build/tests/lint/types/label/oracle_strength) | ✅ | `schemas.py:155-187` |
| `RootCause` (Python `category` ↔ JSON `"class"`) | ✅ | `schemas.py:265-284` |
| `ScoreBreakdown` (5 executable sub-scores + style_judge) | ✅ | `schemas.py:287-310` |
| `HarnessFix` (target/kind/sketch) | ✅ | `schemas.py:313-330` |
| `Provenance` | ✅ | `schemas.py:333-348` |

### 4.2 §2 — Signal hierarchy (`PLAN_04.md:141-185`)

**Verdict: IMPLEMENTED.**

| Spec | Verdict | Evidence |
|---|---|---|
| Strict order: diff_applies → build → tests → lint → types; style_judge LLM-only | ✅ | `src/autocode/anvil/teacher/signal.py:40-49` |
| `executable_gate()` (hard gate) | ✅ | `signal.py:52-66` |
| `primary_signal_is_decisive()` (sets `oracle_strength`) | ✅ | `signal.py:69-75` |
| Label rule (`error → fail → partial → success`) | ✅ | `verifier.py:106-129` (`compute_label`) |

### 4.3 §3 — Root-cause taxonomy + cluster ranking (`PLAN_04.md:188-234`)

**Verdict: IMPLEMENTED.**

| Spec | Verdict | Evidence |
|---|---|---|
| All 10 taxonomy values (plus NONE sentinel) | ✅ | `taxonomy.py:17-32` |
| `FAILURE_TABLE` (layer, symptom, fix_tier, component_kind) | ✅ | `taxonomy.py:46-77` |
| `cluster_rank` ×3 multiplier on `tool.missing_capability` | ✅ | `taxonomy.py:88-98` |
| `rank_clusters` | ✅ | `taxonomy.py:101-118` |

### 4.4 §4 — ACE wiring (`PLAN_04.md:239-313`)

**Verdict: IMPLEMENTED.**

| Role | Verdict | Evidence |
|---|---|---|
| **Generator** = the autocode runtime emitting `Trajectory` | ✅ | `recorder.py:100-176` |
| **Reflector** = `reflect()` (deterministic baseline + optional LLM enrichment) | ✅ | `src/autocode/anvil/teacher/reflector.py:212-293`; `build_reflection_prompt` at `:185-209` |
| **Curator** = `PlaybookStore.append_delta()` (append-only) | ✅ | `playbook.py:97-109` |
| **Pruner** = `PlaybookStore.prune()` (merges deltas into Master Rules, never deletes the JSONL) | ✅ | `playbook.py:159-201` |
| Per-language storage (`.autocode/playbook/{lang}.md`, `{lang}.deltas.jsonl`, `_meta.json`) | ✅ | `playbook.py:75-82` |
| Append-only discipline documented | ✅ | `playbook.py:18-21` |

### 4.5 §5 — Online vs offline paths (`PLAN_04.md:317-385`)

**Verdict: IMPLEMENTED.**

| Spec | Verdict | Evidence |
|---|---|---|
| Online: `playbook_delta` (no contract, reversible) | ✅ | `loop.py:162-166` |
| Offline: `harness_fix` (prediction contract, patch bundle) | ✅ | `loop.py:170-173` and `_emit_harness_fix_bundle` (`loop.py:188-251`); writes `prediction_contract.json` + `bundle.json` + `decision.md` + `teaching_packet.json` |

### 4.6 §6 — Manual MVP CLI (`PLAN_04.md:389-424`)

**Verdict: PARTIAL.**

| Spec | Verdict | Evidence |
|---|---|---|
| `anvil teacher run / playbook show / playbook rules / playbook prune / verify` | ✅ | `src/autocode/anvil/teacher/cli.py:66-225` |
| `sense` command (PLAN_04 §6, line 393) | ✅ **(now built — prior ❌ stale)** | `teacher/cli.py:159` exports `sense` — clusters the last-N failed trajectories and prints the ranked list |
| Operator-gated, manual-first | ✅ | `cli.py:9-11` |

### 4.7 §7 — Phase 1-7 measurement substrate (`PLAN_04.md:427-527`)

| Substrate | Verdict | Evidence |
|---|---|---|
| **G2 Trajectory recorder** (autocode NDJSON + puku stream-json) | ✅ | `recorder.py:100, 193`; layer/action mappings at `:39-67` |
| **G3 Verifier** (diff applies → build → tests → lint → types; pytest parser; baseline-failure regression detection) | ✅ | `verifier.py:149-231`; regression detection at `:201-203` |
| **G4 Corpus builder / `eval_report.json`** (per-bundle) | 🟡 | Per-bundle `eval_report.json` written at `gate.py:84-91`. **No `corpus_builder` module that aggregates teaching packets into a Phase-7 eval flywheel**. `signal.py:71-74` mentions "the eval corpus" but no code materializes it |
| **G5 Distiller → layered evidence corpus** (PLAN_04 §7 Phase 3, line 462) | ✅ **(now built — prior ❌ stale)** | `teacher/distill.py` (456 LOC) builds a Layer 0–3 per-cluster drill-down corpus; `anvil teacher sense` drives it; 18 tests (`test_anvil_teacher_distill.py`). *Caveat:* this is the per-cluster distiller; the held-out **eval corpus** (G4) is still absent (see below) |
| **Prediction-contract scorer + edge-cost guards** (PLAN_04 §7 Phase 3, line 466) | 🟡 **(refined — worse than first stated)** | Contract written (`propose.py`, `loop.py`); scored at `gate.py` → `prediction_score.json`. The three edge-cost guards **are now computed** (`teacher/cost.py` `measure`/`compare`/`EdgeCostVerdict`, 15 tests) — but **not enforced in the live flow**: the CLI gate call `gate(_bundle_dir(...))` at `cli.py:282` **never passes `edge_cost_verdict`**, so every gated bundle records `edge_cost_measured: False` (`gate.py:115`) and defaults `no_regression` to True; and `promote.py:42` gates only on `score["met"]`, never on `no_regression` (recorded at `:58` but unused — the module docstring `:3-4` claims "no edge-cost regression," so the code enforces less than it documents). **The guard exists but cannot block a promotion today.** |

### 4.8 Honest assessment

The teacher's online path is fully wired and the manual MVP is built (`sense` + G5 distiller now ship — the two ❌s above were stale). The remaining gaps are narrower but load-bearing: (1) **G4 held-out eval corpus** is still absent — no `corpus build`, no train/held-out split, no measured noise band (`grep` finds none under `autocode/anvil/`), yet 5 bundles were already gated/promoted on single test runs; (2) the **edge-cost guard is built but inert** — computed in `cost.py` but never wired into the live `gate` call and never enforced by `promote` (see the refined row above). So PLAN_04 Phase 2 is real, but the Phase-1 "do not proceed past this gate" measurement substrate it is supposed to rest on does not actually exist. See §8.1 for the full self-maintenance/eval picture.

---

## 5. PLAN_05 — `autocode/anvil/` (Python) — Copycat Mode

**Brief location:** `lowrescoder/new_plans/PLAN_05_COPYCAT_MODE.md` (558 lines).
**Status:** 🟡 **Channel A complete & exercised; Channel B eval-branch now built (prior "absent" stale); Channel B weights-trainer absent; Channel C-cheap wired (teacher emits), Channel C-weights absent.**

### 5.1 §1 — Authorization registry (`PLAN_05.md:88-141`)

**Verdict: IMPLEMENTED.**

| Spec | Verdict | Evidence |
|---|---|---|
| `anvil/copycat/registry.yaml` | ✅ | Exists (2 targets: `puku-cli` + `codex`) |
| Loader/validator (`load_registry`) | ✅ | `src/autocode/anvil/registry.py:141-161` |
| `VALID_CHANNELS = {structural, outcome, self_distill, deny}` | ✅ | `registry.py:22` |
| `VALID_SCOPES = {deny, structure_only, outcomes, weights}` | ✅ | `registry.py:25` |
| `assert_channel_allowed` / `assert_reuse_scope` (with `weights` requires `tos_check`) | ✅ | `registry.py:72-82, 84-103` |

### 5.2 §2 — Channel A: structural imitation (`PLAN_05.md:145-184`)

**Verdict: IMPLEMENTED.**

| Spec | Verdict | Evidence |
|---|---|---|
| Component census (Capability / Census dataclasses, `parse_help_text`) | ✅ | `src/autocode/anvil/census.py:166-217` |
| Census collectors for puku + codex (with snapshot fallback) | ✅ | `targets.py:112-143, 88-97` |
| Gap diff (`gap_diff()` → `GapReport` with present/gaps/ignored) | ✅ | `src/autocode/anvil/gapdiff.py:198-246` |
| Clean-room capability proposal (5 files: `prediction_contract.yaml`, `manifest_delta.yaml`, `proposal.md`, `decision.md`, `bundle.json`) | ✅ | `src/autocode/anvil/propose.py:229-295` |
| 7 curated clean-room proposals | ✅ | `propose.py:52-187` (all `status: implemented`) |
| Live censuses on disk | ✅ | `anvil/copycat/census/puku-cli.yaml`, `codex.yaml` |
| Hard rule: structural imitation produces *new* components evaluated on the oracle, never vendored code | ✅ | `propose.py` enforces; docstring consistent with PLAN_05 §2.5 (line 170) |

### 5.3 §3 — Channel B: outcome distillation (`PLAN_05.md:188-237`)

**Verdict: PARTIAL (eval branch now built — prior "ABSENT" stale; weights-trainer absent).**

The eval-oracle branch was built after the original audit:

- `copycat/outcome.py` (408 LOC) drives an authorized target and captures verified diffs; `copycat/distill.py` (154 LOC) renders the verified-outcome corpus into a training dataset; both are CLI-wired (`cli.py:199-267`, `outcome`/`distill` commands) and covered by `test_anvil_copycat_channel_b.py` (22 tests, green).
- The distill (weights) branch is correctly **ToS-gated**: `reuse_scope: weights` requires a recorded `tos_check`, enforced in `registry.py:84-104`. *Caveat:* no `tos-check` CLI command exists to record one, so the `weights` scope is safe-by-default but **un-runnable and untested**.
- `"self_distill"` remains the teacher's Channel C bundle (`loop.py:217,241,263`), distinct from Channel B.

| Branch | Verdict | Evidence |
|---|---|---|
| Eval-oracle branch (`reuse_scope: outcomes`) | ✅ **(now built)** | `copycat/outcome.py` + `copycat/distill.py` + `outcome`/`distill` CLI; 22 tests |
| Distillation **trainer** branch (`reuse_scope: weights`) | ❌ | Dataset render exists; the actual QLoRA/SOD trainer (`copycat/weights.py`) is absent, and no `tos-check` command exists to unlock the gate |

### 5.4 §4 — Channel C: self-distillation (`PLAN_05.md:241-287`)

**Verdict: PARTIAL (harness cheap branch wired; weights branch absent).**

| Branch | Verdict | Evidence |
|---|---|---|
| **Harness cheap branch** (Channel C-cheap) | ✅ | `loop.py:188-251` (`_emit_harness_fix_bundle`) drafts a `self_distill` channel bundle on `--emit-harness-fix`, including a `prediction_contract.json` and the standard patch-bundle layout. `decision.md` explicitly states `Channel: self_distill (PLAN_05 Channel C)` at `loop.py:263` |
| **Weights branch** | ❌ | No code captures model weights from any target |

The teacher's own trajectory (autocode run against itself) is the implicit "harness cheap" target — there is no separate weight-distillation worker.

### 5.5 §5 — Build order (`PLAN_05.md:301-316`)

**Verdict: DEFERRED-DOCUMENTED.** README at `anvil/README.md:39-59` documents "5 features already copied from puku-cli" and states "0 clean-room-suitable gaps remaining" (line 51-52). This matches the §5 ordering: Channel A is exhausted; Channel C-cheap emitted zero bundles (no `pb_*` was created via `anvil teacher run --emit-harness-fix` — `created_by` is `anvil-copycat` for all 5 bundles). **No code enforces the order.**

### 5.6 §6 — Manual MVP CLI (`PLAN_05.md:326-365`)

**Verdict: IMPLEMENTED.**

| Spec | Verdict | Evidence |
|---|---|---|
| `copycat registry` | ✅ | `cli.py:80-92` |
| `copycat census <target>` | ✅ | `cli.py:95-114` |
| `copycat gap-diff <target>` (with `--json`) | ✅ | `cli.py:117-158` |
| `copycat propose <target> <cap>` | ✅ | `cli.py:161-186` |
| `anvil gate <bundle_id>` | ✅ | `cli.py:193-210` |
| `anvil promote <bundle_id>` | ✅ | `cli.py:213-231` |
| Every command registry-gated via `_enforce_or_exit` | ✅ | `cli.py:64-70` |
| Operator-gated, manual-first | ✅ | `cli.py:9-11` |

### 5.7 Patch bundles promoted

`anvil/patch_bundles/` contains 5 directories (`pb_001` … `pb_005`):

| Bundle | Capability | Target | Channel | Status |
|---|---|---|---|---|
| pb_001 | flag:permission-mode | puku-cli | structural | **promoted** (`bundle.json:9` `status:promoted`, `promoted_on: 2026-06-21T16:55:39`) |
| pb_002 | flag:append-system-prompt | puku-cli | structural | gated_pass |
| pb_003 | flag:add-dir | puku-cli | structural | gated_pass |
| pb_004 | flag:output-format | puku-cli | structural | gated_pass |
| pb_005 | flag:cd | codex | structural | gated_pass |

`audit_log.jsonl` records the pb_001 promotion with `met: true, no_regression: true, operator: "operator"`. `prediction_score.json`: `met: true, no_regression: true, returncode: 0`. `eval_report.json`: `16 passed in 0.57s`.

### 5.8 Honest assessment

**Channel A is exercised** — 7 proposals, 5 promoted (1 fully, 4 gated_pass). Updated picture: **Channel B's eval branch is now built** (`copycat/outcome.py` + `copycat/distill.py`, 22 tests) — the original "B absent" is stale; only the **weights trainer** (`copycat/weights.py`) and the `tos-check` recording command remain absent. Channel C-cheap lives in the teacher (`loop.py:_emit_harness_fix_bundle`), not as a standalone copycat worker. The model is frozen; the ToS gate is real but cannot be satisfied (no command records a check). *Note the bundles in §5.7 were gated/promoted with edge-cost unenforced (see §4.7 refined row) and no held-out corpus — the promotions are optimistic.*

---

## 6. Cross-cutting gaps (none of the five plans addresses alone)

| Gap | Touches | Plan sections |
|---|---|---|
| **Env-broken test harness** (~79 autocode failures, 3 harness-tester failures, all env / split artifacts) | test infrastructure | n/a — operational |
| **Model-dependent test fragility** (`test_anvil_teacher_e2e.py` fails when LiteLLM gateway is up — empty student trajectory) | anvil/teacher | n/a — operational |
| **`anvil/gate.py::_default_check_runner` hardcodes `["uv","run","pytest",…]`** — would break offline if exercised live | anvil/teacher | n/a — operational |
| **Phase 6 hardening** (rootless containers, SBOM, signed builds, retention reaper, telemetry) | harness-ide, station | PLAN_01 §3.1, §7 Phase 6; PLAN_03 §4.11 |
| **Landlock / seccomp layered on top of bwrap** | harness-ide | PLAN_01 §3.1 line 312; PLAN_03 §1.5 |
| **Multi-harness multiplex by `clientId`** | harness-ide | PLAN_01 §6.3 line 591 |
| **Capability-token / signed-bearer-token auth** | harness-ide | PLAN_01 §6.2 line 577-580 |
| **`policy` approval scope as a first-class type** | harness-ide | PLAN_01 §3.3 line 326-335 |
| **`auto_review` approvals_reviewer** | harness-ide | PLAN_01 §3.2 line 322 |
| ~~G5 distiller~~ **now built**; remaining: **G4 held-out eval corpus + split + noise band** | anvil/teacher | PLAN_04 §7 Phase 1/3 |
| **Edge-cost guards wired into the live gate + enforced by `promote`** (computed in `cost.py`, but `cli.py:282` never passes the verdict and `promote.py:42` gates on `met` only) | anvil/teacher | PLAN_04 §7 Phase 3; PLAN_05 §0.3 constraint 6 |
| **Gate-component lockout test** (fail the run if a bundle targets verifier/eval/registry — "the single most important rule", 07 §7.2) | anvil | PLAN_04 §6.1 |
| **Kill switches / canary / `promote` auto-revert** (autonomy safety; all absent) | anvil | PLAN_04 §7 Phase 6 |
| **ClipMind egress gate + redaction + injection/redaction adversarial corpus** (cloud planner ships ungated) | video-agent | PLAN_02 §6; ClipMind `01-trust-domains.md`, `00-adversarial-validation.md` |
| **Station merge-gate UI (R13) + real maker/checker enforcement** (substrate exists; UI/identity-check don't) | station | PLAN_03 §9; `autocode-station-requirements.md` §5.2, §4.4 |
| **Shared authorization-barrier spec** (proposer/compiler reinvented 3× — video-agent/station/anvil — no shared threat-model/audit-format) | cross-component | — |
| **Trajectory schema contract** (Anvil consumes `layer_distribution`; PLAN_01 runtime never commits to producing it) | harness-ide ↔ anvil | PLAN_01 ↔ PLAN_04 |
| **Top-level `new_plans/INDEX.md`** (README is ClipMind-only; no map of the 5 PLANs + Anvil + station + dependency order) | docs | — |
| **Broll + music_duck actual render** | video-agent | PLAN_02 §2.2, §5.1 |
| **`interview_to_article` + `livestream_vod_to_chapters` named intents** | video-agent | PLAN_02 §5.3 line 254-257 |
| ~~Channel B driver~~ **eval branch now built**; remaining: **weights trainer (`copycat/weights.py`) + `tos-check` command** | anvil/copycat | PLAN_05 §3 |

---

## 7. Closing-gate roll-up (one-line per plan)

| Plan | MVP gate (closing) | Hardening gate (closing) |
|---|---|---|
| **PLAN_01** | Phases 0–3 (lines 633-687): MCP server + REPL + tool registry + permission profile + audit log — **CLOSED**, with `policy` scope and `auto_review` as soft gaps. | Phase 6 (line 714-726): rootless workers + SBOM + signed builds + headless CI mode + retention reaper + telemetry — **OPEN** |
| **PLAN_02** | §2-§5 core (lines 60-264): typed CR + 16 ops + proposer/compiler + FFmpeg deterministic + multi-step plan + named intents — **CLOSED**. §3 perception backends — DEFERRED-DOCUMENTED. §7 UX — OPEN. | §8 productization (lines 357-405): web/desktop chat UI + Remotion opt-in — **OPEN** |
| **PLAN_03** | §9 carry-overs (lines 573-587) + hunk review + composer + plan mode + A/B compare + approval card — **CLOSED** (with Ask-why, merge gate, Inbox default as soft gaps). | §1-§5 full surface (lines 28-378) — **OPEN** (~80% traditional IDE, ~90% AI-IDE breadth) |
| **PLAN_04** | Phase 2 (line 451-461): root-cause analyst + reversible playbook deltas + ACE wiring + runtime loader — **CLOSED**. *Caveat:* the Phase-1 measurement substrate it rests on is incomplete — G4 held-out corpus absent; edge-cost guard built but inert (§4.7). | Phase 3 (line 462-474): G5 distiller **now built**; remaining: component manifest (the real AHE manifest, not the CLI census), held-out corpus, edge-cost **wiring + enforcement** — **OPEN** |
| **PLAN_05** | Phase 4 (line 414-426): registry + Channel A + Channel C-cheap + 5 patch bundles — **CLOSED**. *Caveat:* bundles were gated/promoted with edge-cost unenforced and no held-out split — promotions optimistic. Channel B eval **now built**. | Phase 5-7 (line 429-456): Terminal-Bench yardstick + autonomy (kill-switch/canary) + distillation **trainer** + `tos-check` command — **OPEN** |

**Empirical reality check (test suites run 2026-06-23):** harness-ide engine **65/65 green** (~90% working); station **6/8 views real**, 2 placeholder (~60%); video-agent **112 pass / 1 skip / 0 fail** (~95–100% of what's built); Anvil **200/200 unit green**, 1 live-model flake (~75%). One red test across the whole repo, and it's a local-model behavioral flake, not a defect. The MVP "CLOSED" marks above are accurate as *code-shipped* but, for PLAN_04/05, optimistic as *gates-actually-enforced*. Full per-component implement/work/test breakdown: `NEW_PLANS_REST_AUDIT.md` §9.

---

## 8. Source-doc & empirical addendum (2026-06-23)

§1–§7 audited each PLAN **against its own prose**. That left a blind spot: scope the *source docs* specified but the PLANs silently dropped was never compared, so it showed up as no gap. This section audits the source material and the live test suites. Full ranked detail: `NEW_PLANS_REST_AUDIT.md`.

### 8.1 Anvil self-maintenance engine (07) + eval flywheel (08) — never audited by §4/§5

PLAN_04/05 distilled the teacher + copycat legs from the `harness_copy_teacher/` (Anvil) program but dropped the **autonomous half** and the **rigor layer**. Verified against `autocode/anvil/`:

| Mechanism (source doc) | In a PLAN? | Built? | Note |
|---|---|---|---|
| Edge-cost guard enforcement (07 §7.1.2) | Captured | **built-but-inert** | Computed in `cost.py`; never wired into `gate` (`cli.py:282`); `promote.py:42` ignores `no_regression`. §4.7. |
| Held-out eval corpus + split + noise band (08 §8.1) — **the Phase-1 "do not proceed" gate** | Partial | **absent** | No `corpus build`/`held_out`/`eval` command; 5 bundles promoted without it |
| Statistical rigor: k≥3 replication, paired comparison, significance gating (08 §8.3) | **not captured** | **absent** | Verifier runs once (`verifier.py:159`). The most fully-uncaptured spec — no module, no plan bullet, no TODO box |
| Gate-component lockout test (07 §7.2 — "single most important rule") | Partial | **absent** | Only a docstring (`registry.py:9`); no assertion fails a run that targets the oracle |
| Kill switches (8 triggers, 07 §7.3) | Phase-6 box | **absent** | `killswitch.py` absent |
| Canary / shadow promotion + auto-revert (07 §7.4) | Phase-6 box | **absent** | `promote.py` never `git apply`s; no revert path |
| Prediction-calibration meta-signal (Correction 8) | Captured (schema) | **absent** | Writes `prediction_score.json`; nothing aggregates miss-rate into a kill signal |
| True G1 AHE component manifest (7 kinds + `prediction_metrics`/`edit_surface`, 04 §40-98) | gap G1 | **absent (decoy)** | `manifest.py` is a **CLI-flag census**, not the harness-component manifest — same name masks an unbuilt component |
| GEPA tier-4 prompt optimizer (04 §278) | dropped | **absent** | Correction 2 said *demote, not delete*; PLANs deleted it. Only tier-4 rung, unowned |
| Phase-0 `docs/research/anvil-design.md` (09 §13-17, the legality gate) | restated | **absent** | Cheapest unstarted item (~1 day) |
| Terminal-Bench external yardstick (08) + distillation **trainer** (Phase 7) | Phase-5/7 | **absent** | Until TB exists, "guards against overfitting to your own corpus" is unenforceable |

### 8.2 ClipMind security source docs vs PLAN_02 — never audited by §2

PLAN_02 kept ClipMind's **one structural barrier** (proposer/compiler + closed op grammar + sensitivity check) and the repo genuinely built it — that alone breaks the OCR→exfil chain (the planner cannot express exfiltration). But the defense-in-depth the source docs advertise is **neither in PLAN_02 nor built**:

- **Egress gate** (deny-by-default + approval) — absent; the cloud planner (`cli.py:27-45`, `--planner llm`) ships with **zero gating**. The one structurally-absent link in the canonical exploit chain.
- **Redaction pass** — absent; `bundle.py:43-45` inlines raw transcript text.
- **Instruction/data separation** — only a system-prompt sentence (`planner.py:97`), not enforced.
- **Per-derivative sensitivity labels + retention** — single scalar; the review's "most insightful point" is unbuilt.
- **Injection (C7) + redaction (C4) adversarial corpus** — absent (one shell-field rejection test only). The injection-resistance claim is asserted, not demonstrated.
- **Capture isolation** — dropped by design (PLAN_02 edits user footage, never records) — record as a *decision*, not an oversight.
- Open-Qs decided-by-omission: Q1 (cloud mode shipped without its required egress gate), Q2 (logical-only isolation), Q8 (no adversarial corpus).

### 8.3 autocode-station requirements + mockups vs PLAN_03 — never audited by §3

PLAN_03 §9 *lists* the requirements-doc surfaces as "carry forward" but never re-specs them. Of 21 hard requirements, **6 are absent from PLAN_03's body entirely** (R2 Workstreams, R7–R9 collaboration/presence/comments, R15 status model, R17 Browser-QA split, R18 New-Task wizard) and **8 more are placeholder/label-only** in the repo despite P0/P1 (R13 merge-gate is P0 and a pure diff dump; R4 Ask-why; R10 maker/checker label-only — `requires_checker` is `None` in the real path `approval.rs:422`, `Some()` only in a test fixture). Market research drops a **launch-blocker**: secured remote web access + **token auth** ("fatal impact" risk #4) — no auth model in any plan.

**Two mockups, not one.** `codestation-mockup-v2` (4 views, threads-first) is **superseded**; PLAN_03 + the repo followed `autocode-station-v3` (8 views, editor-first). v2-only casualties silently dropped: the **Skills view**, **voice input**, and the `@files`/`/skills` composer affordances. So the build does **not** match v2; whether v2 or v3 is the target is an open decision (§8.6).

### 8.4 Cross-cutting (folded into §6)

Three corpus-spanning gaps added to §6: the proposer/authorizer barrier **reinvented 3×** (video-agent/station/anvil, no shared spec); the **trajectory schema contract** unowned (Anvil consumes `layer_distribution`, PLAN_01 never commits to producing it); and **no top-level `new_plans/INDEX.md`** (README is ClipMind-only, mentions the 5 PLANs zero times).

### 8.5 Doc-integrity gaps

- The ClipMind **`README.md` document-map is ~93% aspirational** — advertises a 6-section, ~28-file tree; **26 of 28 don't exist**, including all 5 deep `02-security/01..05` specs and the `01-executive-summary.md` it tells you to "read first." Live source docs cross-reference these vapor files.
- The Anvil `manifest.py` is a **same-named decoy** for the unbuilt G1 manifest (§8.1).

### 8.6 Unowned decisions (the user must call these)

Anvil: tool-vs-research-artifact stopping point (Phase 4 vs 5–7); autonomy cap + "Anvil may not create new planning docs"; default `reuse_scope` + a `tos-check` command; harness-only vs rented-GPU distillation (RX 480 is not a trainer; 8GB QLoRA is "marginal"); codename (locked-in-by-default). ClipMind: Q1/Q2/Q8. Station: **v2 vs v3 target**; approve-for-session taxonomy; Skills-view fate; CRDT depth vs modelled-presence (req-doc §8 vs PLAN_03 §3.3 conflict); web/remote auth architecture; status-model ownership.

---

## 9. 2026-06-23 implementation status (verdicts updated)

A build cycle closed a batch of the gaps above. Verdicts below are **gate-verified** (commands re-run, not read). Use this section as the current truth where it contradicts the older §1–§5 rows.

### 9.1 Verdict flips — now IMPLEMENTED (was PARTIAL/MISSING)

| Gap (older §) | Was | Now | Evidence |
|---|---|---|---|
| §1.1 REPL keybindings `@` / `Ctrl+R` / `Ctrl+L` / `Double-Esc` | ❌ | ✅ (4 of 5; `Ctrl+G` external editor still open) | `harness-ide/src/ui/{composer,app}.rs`; `cargo test --workspace` 81 |
| §1.2.3 LSP `lsp_hover` (stub) + `lsp_workspace_symbols` + `lsp_format` | 🟡/❌ | ✅ (8 of 14 now; 6 remain) | `src/tools/lsp.rs` + `tools/mod.rs` dispatch |
| §1.2.6 `git_push` + `open_pr` | ❌ | ✅ | `src/tools/git.rs:229,335` + specs `:539,550`; `plan_01_gaps.rs` |
| §1.3 `policy` approval scope as first-class data | 🟡 | ✅ | `core/approval.rs` `ApprovalScope{Once,Session,Project,Policy}` + `PolicyApprover` + `ApprovalOutcome::Pending` |
| §1.4 semantic 3-way merge (structured conflict report) | 🟡/❌ | ✅ | `core/merge.rs` → `MergeResult::Conflicts{Vec<ConflictRegion>}` (diffy Diff3) |
| §2.3 `broll` render (was parse-only) + `music_duck` render (was silent no-op) | ❌ | ✅ | `compiler/{timeline,ffmpeg_backend}.py` overlay + `sidechaincompress`; video-agent 142 |
| §2.1/§5.1 `jcut`/`lcut` ops | ❌ | ✅ | `schema/change_request.py` + `compiler/{validate,ffmpeg_backend}.py` (adelay) |
| §2.4 `interview_to_article` + `livestream_vod_to_chapters` intents | 🟡 | ✅ | `templates/intents.py` |
| §3.6 (R13) station Merge-gate + Ask-why + Inbox-default + maker/checker GUI | ❌/🟡 | ✅ | `crates/station/src/{app,editor}.rs`; station 30 tests |
| §4.7 gate-component lockout + ACE-Pruner prediction gate | ❌ | ✅ | `anvil/registry.py` `assert_not_gate_component`; `teacher/cli.py` prune eval-gate |
| §4.7 edge-cost guard *active* (was built-but-inert) | 🟡 | ✅ | `anvil/{gate,promote,cli}.py` — `promote` blocks on `no_regression`, gate CLI measures |
| §6 (cross-cut) trajectory-schema contract + shared authorization-barrier spec | ❌ | ✅ (spec docs) | `CROSS_CUTTING_CONTRACTS.md` §1/§2 |
| §8.5 ClipMind README map + top-level `INDEX.md` | ❌ | ✅ | `README.md` (flat), `INDEX.md` (new) |
| ClipMind egress gate + Bundle redaction/fencing | ❌ | ✅ | `video-agent/src/video_agent/{cli,agent}.py` |
| Cross-cutting env (`_repo_root`, Pillow/`evals`, harness-tester install, doctor) | ❌ | ✅ | harness-tester 190 passed; doctor 10+1skip |

### 9.2 Still MISSING / PARTIAL (the remaining work)

The full prioritized list is in `NEW_PLANS_REMAINING_TODO.md` (the "★ 2026-06-23 IMPLEMENTATION PASS" block). Headline gaps still open: PLAN_01 6 LSP tools + `semantic_search` + §6 auth/multiplex + Phase-6 hardening · PLAN_02 perception backends + Remotion + local-VLM + UI · PLAN_03 traditional-IDE breadth (tree-sitter/multi-cursor/PTY/DAP/marketplace) + A.3 station requirements (web-auth, browser-QA split, New-Task wizard, status-model) · Anvil G4 held-out corpus + statistical rigor (08 §8.3) + kill-switches/canary/auto-revert + real G1 manifest + GEPA · ClipMind adversarial corpus + per-derivative sensitivity/retention · the 73 doc-migration test failures · A.6 `[DECIDE]` · Channel C-weights trainer (hardware-gated).

### 9.3 Initial-vision check — the v2 mockup (`codestation-mockup-v2`)

The source `new_plans/` captures the **initial vision**, and `codestation-mockup-v2 (1).html` is its earliest concrete form: a **4-view, threads-first** product — nav `Threads` (default) · `Automations` · **`Skills`** · `Settings` (mockup L460-470) — with a **voice button "Voice (hold ^M)"** (L633) and a composer that takes **`drop images, @ files, / skills`** (L628). The repo (and PLAN_03) followed the later **v3** 8-view *governed* mockup (`autocode-station-v3.html`) and **silently dropped** the v2 Skills view, voice input, and `@files`/`​/skills` composer affordances. This is a **scope choice, not an accident** — recorded as the `v2-vs-v3` decision in §8.6 / TODO A.6. If the threads-first/Skills/voice vision is still wanted, those surfaces are *additional* remaining work on top of the v3 surface the repo already pursues.

---

*End of gap analysis. Closing gates and per-gap verification criteria are in `NEW_PLANS_REMAINING_TODO.md`. Ranked remaining work and empirical test status are in `NEW_PLANS_REST_AUDIT.md`.*

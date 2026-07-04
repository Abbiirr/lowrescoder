# NEW_PLANS_REMAINING_TODO.md — Remaining Work Checklist

**Date:** 2026-06-22 · **Last updated:** 2026-06-23
**Scope:** All five `lowrescoder/new_plans/PLAN_*.md` briefs.
**Companion doc:** `NEW_PLANS_GAPS.md` (the analysis this checklist is built from); `NEW_PLANS_REST_AUDIT.md` (source-doc + empirical audit).

> **2026-06-23 update.** Several boxes below are now **done** and marked `[x]` (the `sense` command, the distiller, Channel B's eval branch). Two closing gates are corrected (their "CLOSED" was optimistic — the measurement substrate they rest on does not exist). A new **Addendum** at the end adds all remaining work the original checklist never owned: the Anvil self-maintenance/eval safety layer, the ClipMind security stack, the autocode-station requirements/merge-gate, cross-cutting contracts, the empirical test gaps, and the unowned `[DECIDE]` list.
**Format:** Each task is a checkbox. Each task lists its verification criteria and the plan line(s) it closes. Closing gates are the higher-level milestones derived from the plan's phase table.

---

## ★ 2026-06-23 IMPLEMENTATION PASS — status + ALL remaining work (authoritative)

A build cycle (parallel subagents + a PLAN_01 session) closed a large batch. Every "DONE" below is **gate-verified**. This block is the authoritative current status; the headline `[x]`/`[ ]` boxes further down are kept in sync.

**DONE this cycle (gate-verified):**
- **Tier-0 0a–0f** — edge-cost guard *active* (`promote()` blocks on `no_regression`; gate CLI measures via `--baseline/--candidate-trajectories`; audit records `edge_cost_measured` honestly); ClipMind egress gate (deny-by-default, ungated `--planner llm` → exit 3); Anvil gate-component lockout (refused at gate **and** promote); station Inbox-default + maker/checker GUI confirm path; `INDEX.md` written + ClipMind `README.md` fixed; deterministic stubbed-gateway teacher-loop test (the repo's only red — resolved).
- **PLAN_01** — `policy` approval scope as first-class data (`ApprovalScope{Once,Session,Project,Policy}` + `PolicyApprover` + `ApprovalOutcome::Pending`); semantic 3-way merge (`core/merge.rs` → `MergeResult::Conflicts`, not a bool); `git_push` + `open_pr`; REPL keybindings (`@`+Tab fuzzy, `Ctrl+R`, `Ctrl+L`, `Double-Esc`); LSP `lsp_hover` (real) + `lsp_workspace_symbols` + `lsp_format`.
- **PLAN_02 Gate A** — `music_duck` (sidechaincompress) + `broll` (overlay+`source`) render; `jcut`/`lcut` ops; `interview_to_article` + `livestream_vod_to_chapters` templates.
- **PLAN_03** — Inbox-default, maker/checker GUI confirm, Ask-why hunk affordance, **Merge-gate view R13** (checklist + typed override, commit gated).
- **A.1** gate-component lockout + ACE-Pruner merge now prediction-gated · **A.2** egress + typed-fenced untrusted evidence + PII redaction · **A.4** `CROSS_CUTTING_CONTRACTS.md` (trajectory-schema + auth-barrier spec) · **A.5** deterministic teacher-loop test + CLI edge-cost/promote gating test · **Cross-cutting** `_repo_root()` fix, Pillow + internal `evals` + autocode-editable-in-harness-tester, doctor test pinned, configurable check-runner.
- **Gates:** harness-ide+station `cargo test --workspace` **81** · video-agent **142**(+1skip) · anvil `test_anvil_*.py` **210** · teacher e2e **1**(+1skip, offline) · harness-tester **190** · doctor 10(+1skip).

**ALL REMAINING WORK (prioritized):**
1. **PLAN_01 finish** — 6 more LSP tools (rename, code_action, completion, implementation, type_definition, inlay_hints, call_hierarchy); `semantic_search` (§2.2.2); capability/signed-bearer auth + clientId multiplex (§6); `Ctrl+G` external editor + `request_user_input`/`switch_thread` TUI cards; Phase-6 hardening (Landlock/seccomp, SBOM, signed builds, retention reaper, telemetry).
2. **PLAN_02 Gate B** — perception backends (faster-whisper, pyannote, PySceneDetect, PaddleOCR, YAMNet, InsightFace); Remotion opt-in; local Qwen2.5-VL planner; web/desktop UI.
3. **PLAN_03 breadth** — tree-sitter, multi-cursor/column-select, PTY terminal, tab-completion/edit-prediction, DAP debug, project switcher, side-by-side threads, worktree picker, minimap/soft-wrap/folding, find/replace-in-files, source-control panel, settings/keybindings UI, extension marketplace.
4. **A.1 Anvil eval/autonomy substrate** — G4 held-out corpus + split + measured noise band; statistical rigor (k≥3, paired, significance, pass@k vs pass^k — 08 §8.3); kill switches (8 triggers — 07 §7.3) + canary/shadow + `promote` auto-revert (`git apply`); tripwire eval set; diff-size/blast-radius limit; verifier-of-verifier fixtures + flaky quarantine (08 §8.4); prediction-calibration miss-rate aggregation; **real G1 7-kind AHE manifest** (the `manifest.py` is a CLI-census decoy); GEPA tier-4 (build or formally drop); Phase-0 `docs/research/anvil-design.md`; meta-eval dashboard (held-out trend, edge-cost trend, promotion-precision, calibration, flywheel-fuel-rate); Terminal-Bench yardstick.
5. **A.2 ClipMind security** — injection(C7)+redaction(C4) adversarial corpus; per-derivative sensitivity labels + retention reaper; record the capture-domain drop as a decision.
6. **A.3 station requirements** — secured remote/web token auth (market risk #4, "fatal"); shared review comments → "Send to agent" (R9); Browser-QA split + untrusted-context quarantine (R17); New-Task wizard (R18); status-model state machine + Inbox-bucket mapping (R15); adapter-mode ladder; AGENTS.md instruction-stack viewer; draft-diff-vs-verified state (P0).
7. **Initial-vision (v2 mockup) surfaces dropped when the repo followed v3** — `codestation-mockup-v2` is a **4-view threads-first** product (Threads/Automations/**Skills**/Settings) with a **voice button (hold ^M)** and **`@files` / `/skills` composer**; the repo follows the v3 8-view governed model and dropped the **Skills view**, **voice input**, and the **`@files`/`​/skills` composer affordances**. Either build them or record the v2-vs-v3 decision (A.6).
8. **A.5 test gaps** — offline unit test for `teacher/gateway.py`; station behavioral UI tests + committed snapshot baselines (today the wgpu tests only assert "renders without panic"); video-agent live-LLM planner test + scene-detection manifest assertion.
9. **Cross-cutting** — migrate/retire the 73 doc-lock/roadmap/rpc tests (the docs live in `lowrescoder/docs/`, not `autocode/docs/`).
10. **PLAN_05** — promote a Channel C-cheap bundle via `anvil teacher run --emit-harness-fix`; add the `tos-check` CLI command; enforce the build order (Channel B-weights gated on Channel C-cheap history).
11. **A.6 `[DECIDE]` (user calls)** — Anvil tool-vs-artifact stopping point / autonomy cap / default `reuse_scope` / harness-vs-rented-GPU distillation / codename; ClipMind Q1/Q2/Q8; station **v2-vs-v3** / approve-for-session taxonomy / Skills-view fate / CRDT-depth-vs-presence / web-auth / status-model owner.
12. **Forever-deferred / hardware-gated** — Channel C-weights trainer (`copycat/weights.py`, QLoRA on the RTX 4060 Ti).

> **Reading order**
> 1. The **Closing gates** at the top of each plan section are the operator-facing milestones. The boxes below them are the work.
> 2. Each box has `[ ]` — when all boxes under a gate are checked, the gate is met.
> 3. The plan-file line references in parentheses `(PLAN_NN.md:L#-L#)` are the contract. The `harness-ide:...` / `anvil:...` / `station:...` / `video-agent:...` references are the source target.
> 4. Verification criteria are what you'd script (a test, a CLI exit, a JSON shape, a UI affordance).

---

## 0. Plan-file line map (for reference)

| Plan | File | Line range |
|---|---|---|
| PLAN_01 — Harness IDE | `lowrescoder/new_plans/PLAN_01_HARNESS_IDE.md` | L1–L837 |
| PLAN_02 — Video Agent | `lowrescoder/new_plans/PLAN_02_VIDEO_AGENT.md` | L1–L558 |
| PLAN_03 — Full Codex/Cursor IDE | `lowrescoder/new_plans/PLAN_03_FULL_CODEX_IDE.md` | L1–L654 |
| PLAN_04 — Teacher Mode | `lowrescoder/new_plans/PLAN_04_TEACHER_MODE.md` | L1–L618 |
| PLAN_05 — Copycat Mode | `lowrescoder/new_plans/PLAN_05_COPYCAT_MODE.md` | L1–L558 |

The five briefs are paired:
- PLAN_01/03 compose: `harness-ide` (substrate) + `crates/station` (consumer).
- PLAN_04/05 compose: `anvil/teacher` (root-cause analyst) + `anvil/copycat` (capability acquisition).
- PLAN_02 is standalone (a separate product).

---

# PLAN_01 — Harness IDE (`harness-ide/`)

**Closing gate A — MVP (Phases 0–3):** MCP server + REPL + tool registry + permission profile + audit log. **CLOSED**, with the `policy` scope and `auto_review` as the soft gaps below. (PLAN_01.md:L633–L687)

**Closing gate B — Hardening (Phase 6):** rootless workers + SBOM + signed builds + headless CI mode + retention reaper + telemetry hooks. **OPEN**. (PLAN_01.md:L714–L726)

## 1.1 §1 REPL keybindings (PLAN_01.md:L60–L117, L446–L452)

- [ ] **Wire `@` file-fuzzy in composer.** Add `@` handler in `harness-ide/src/ui/app.rs:444-447`; reuse `palette::open_files` from `palette.rs:84-92`. **Verify:** typing `@foo` in the composer opens the file picker; selection inserts `@file:<path>` and the agent's `read_range` tool sees the file. (PLAN_01.md:L448, L132)
- [ ] **Wire `Ctrl+R` history search.** Add `Ctrl+R` chord in `harness-ide/src/ui/composer.rs:70-115`; show reverse-i-search overlay. **Verify:** `Ctrl+R` opens a search bar, typing filters composer history, `Enter` inserts the match.
- [ ] **Wire `Ctrl+L` clear.** Add `Ctrl+L` chord; clear the conversation column but preserve the session log. **Verify:** `Ctrl+L` empties the visible rows; `$IDE_HOME/sessions/<thread>.jsonl` is unchanged.
- [ ] **Wire `Ctrl+G` external editor.** Add `Ctrl+G` chord; push the current composer text to `$VISUAL` / `$EDITOR` and reload on close. **Verify:** `Ctrl+G` with no `VISUAL` set surfaces a clear error; with `VISUAL=vim`, `vim` opens with the composer text, `:wq` reloads it.
- [ ] **Wire `Double-Esc` edit-previous.** Detect double-tap on `Esc` within 500ms; load the previous user prompt into the composer. **Verify:** two `Esc` presses within 500ms populate the composer with the last user message.

## 1.2 §2 Tool surface — search (PLAN_01.md:L167–L172)

- [ ] **Implement `semantic_search`.** Add to `harness-ide/src/tools/mod.rs:29-80` dispatch; back it with a workspace index (start with `ripgrep`-style `head_limit` + a simple TF-IDF, then graduate to embeddings). **Verify:** `semantic_search(query="auth token rotation", head_limit=5)` returns ≥ 1 file:line:score result on a sample repo; respects `.gitignore`.

## 1.3 §2 Tool surface — LSP (PLAN_01.md:L175–L202)

- [ ] **Implement `lsp_workspace_symbols`.** Add to `harness-ide/src/tools/lsp.rs:281-316`. **Verify:** `lsp_workspace_symbols(query="TokenStore")` returns ≥ 1 location for a Rust symbol in a workspace with rust-analyzer on PATH; falls back to a regex search when no server.
- [ ] **Implement `lsp_rename`.** Add to dispatch; wrap `textDocument/rename`. **Verify:** `lsp_rename(file, line, col, "TokenStore_v2")` returns a `WorkspaceEdit` and the engine applies it; the file's hash changes; the hunk appears in the pending-hunk list.
- [ ] **Implement `lsp_code_action`.** Add; wrap `textDocument/codeAction`. **Verify:** `lsp_code_action(file, line, col)` returns at least the rust-analyzer "add missing import" or eslint "fix this" on a known-bad sample.
- [ ] **Implement `lsp_format`.** Add; wrap `textDocument/formatting` and `rangeFormatting`; return a `diff` content block. **Verify:** `lsp_format(file)` produces a no-op diff on a clean file and a non-empty diff on a `cargo fmt`-violating file.
- [ ] **Implement `lsp_completion`.** Add; wrap `textDocument/completion`; surface `CompletionItem[]`. **Verify:** `lsp_completion(file, line, col)` returns ≥ 1 item on a partial token in a Rust file with rust-analyzer.
- [ ] **Implement `lsp_implementation`.** Add; wrap `textDocument/implementation`. **Verify:** `lsp_implementation(file, line, col)` returns the implementing struct for a trait method.
- [ ] **Implement `lsp_type_definition`.** Add; wrap `textDocument/typeDefinition`. **Verify:** `lsp_type_definition(file, line, col)` returns the type definition location.
- [ ] **Implement `lsp_inlay_hints`.** Add; wrap `textDocument/inlayHint`. **Verify:** `lsp_inlay_hints(file)` returns ≥ 1 hint on a Rust file with rust-analyzer.
- [ ] **Implement `lsp_call_hierarchy`.** Add; wrap `prepareCallHierarchy` + `incomingCalls`/`outgoingCalls`. **Verify:** `lsp_call_hierarchy(file, line, col, "outgoing")` returns the called functions for a known Rust fn.
- [ ] **Replace `lsp_hover` stub.** `harness-ide/src/tools/lsp.rs:260-279` returns `<not available in v1 (LSP stub)>` — make it return real hover content when an LSP server is on PATH. **Verify:** `lsp_hover(file, line, col)` returns the type and 1-paragraph doc for a known symbol in a Rust file with rust-analyzer.

## 1.4 §2 Tool surface — Git (PLAN_01.md:L226–L239)

- [ ] **Implement `git_push`.** Add to `harness-ide/src/tools/git.rs:159-203` (alongside `git_commit`); approval-gated. **Verify:** `git_push(remote="origin", branch="main")` with no upstream returns a clear error; with upstream pushes the current branch; approval card shows the remote URL and risk class.
- [ ] **Implement `open_pr`.** Add; reads host (GitHub/GitLab/Bitbucket) from `git remote -v`; requires OAuth token (out of scope for v1 — emit a clear "OAuth not configured" error or wire a stub). **Verify:** `open_pr(title, body)` returns a `pr_url` or a structured error.

## 1.5 §2 Tool surface — Browser (PLAN_01.md:L242–L253)

- [ ] **Implement `browser_click` / `browser_type` / `browser_press`.** Replace `browser_unsupported` at `harness-ide/src/tools/browser.rs:151-155` with a Playwright/CDP backend. **Verify:** on a small HTML fixture, `browser_click(selector="#submit")` clicks the element and `browser_snapshot` reflects the new state.
- [ ] **Implement `browser_console`.** Add; returns the page's console messages. **Verify:** console messages from a fixture page are returned as `text` content blocks; labeled UNTRUSTED per PLAN_01 §2.7 (line 252).
- [ ] **Implement `browser_network`.** Add; returns the network log. **Verify:** `browser_network` lists at least the initial document request for a fixture page.
- [ ] **Implement `browser_screenshot`.** Add; returns the page as base64 PNG. **Verify:** `browser_screenshot` returns a non-empty `image` content block; dimensions match the viewport.

## 1.6 §2 Tool surface — Session (PLAN_01.md:L256–L263)

- [ ] **Implement `switch_thread`.** Add to `harness-ide/src/tools/session_tools.rs:75-94` (alongside `list_threads`). **Verify:** `switch_thread(thread_id="th_...")` switches the active thread; the conversation column reloads; the status bar updates the thread id.
- [ ] **Implement `request_user_input` TUI card.** `harness-ide/src/ui/app.rs` does not pause on `request_user_input` — add a modal card. **Verify:** when the agent calls `request_user_input(question, options)`, the composer pauses; the modal shows the question and options; the operator's selection is returned to the agent as a `tool_result`.

## 1.7 §3 Permission model — `policy` scope (PLAN_01.md:L326–L335)

- [ ] **Model `policy` approval scope as a first-class type.** Extend `harness-ide/src/core/approval.rs:10-28` with `enum Scope { Once, Session, Project, Policy }`; thread it through `Approver::request` (`approval.rs:36-38`). **Verify:** an approval with `scope=Policy` writes to `$IDE_HOME/policies/<rule>.yaml` and to the audit log; the rule persists across sessions; a rule with `scope=Once` does not persist.
- [ ] **Implement `approvals_reviewer: auto_review`.** Add a reviewer agent mode that, for low-risk `read_*` / `grep` / `lsp_*` calls, returns `Approved` without prompting. (PLAN_01.md:L322) **Verify:** in `auto_review` mode, `read_range` and `grep` complete without showing the approval card; `run_command` and `git_push` still prompt.

## 1.8 §4 Session and lifecycle (PLAN_01.md:L393–L435)

- [ ] **Add `hash_in` / `hash_out` to session events.** `harness-ide/src/core/session.rs:32-43` `SessionLog::append` — add `hash_in` and `hash_out` to the JSONL (already in `AuditEntry`; mirror the pattern in `audit.rs:22-40`). **Verify:** every `tool_call` event in `$IDE_HOME/sessions/<thread>.jsonl` carries `hash_in`; every `tool_result` carries `hash_out`; the chain verifies.
- [ ] **Implement `ide resume` with picker.** Add a `--resume <thread_id>` flag to `harness-ide/src/cli.rs:1-307`; on `repl` with no `--resume`, show a picker. **Verify:** `ide resume` lists ≥ 1 recent session; selecting one reloads the conversation; the audit log chain verifies.
- [ ] **Implement compaction.** Add a `compact` event + summary snapshot to `session.rs:32-43`; trigger on context budget threshold (>80%). **Verify:** when `context_pct` (currently always 0; see §1.10) exceeds 80%, the engine emits a `compact` event; the session log's tail has a typed `summary` block; the agent continues from the summary.
- [ ] **Implement parallel subagents.** Extend `harness-ide/src/agent/subagent.rs:74-135` with a parallel runner that uses `tokio::join!` over a `Vec<SubagentRequest>`. **Verify:** `request_subagent` with a list of N parallel subagents spawns N concurrent sub-threads; the parent's `tool_result` is the concatenated text results.
- [ ] **Implement forked subagent.** Add a `forked=true` flag to `request_subagent` that clones the parent conversation context. **Verify:** a forked subagent's first event is the parent's full conversation; subsequent events are isolated.
- [ ] **Implement background subagent.** Add a `background=true` flag; the subagent auto-denies on missing permission rather than blocking. **Verify:** a background subagent's `run_command` outside the trusted set returns a `denial` event without pausing the parent.

## 1.9 §6 Agent bridge — auth and multiplex (PLAN_01.md:L563–L626)

- [ ] **Implement capability-token auth (file-backed).** `HARNESS_IDE_WS_TOKEN_FILE` env in `harness-ide/src/mcp/http.rs:29-57`; the server reads the file, compares with the `Authorization: Bearer …` header. **Verify:** with the env set, a request without the token returns 401; with the token, returns 200; rotating the file invalidates the old token.
- [ ] **Implement signed-bearer-token auth (HMAC).** `HARNESS_IDE_WS_SHARED_SECRET_FILE` env; verify HMAC over `(timestamp, request_body)`. **Verify:** a request with a valid HMAC succeeds; an expired timestamp (`--ws-max-clock-skew-seconds=60`) returns 401; a tampered body returns 401.
- [ ] **Implement multi-harness multiplex by `clientId`.** Extend `mcp/mod.rs:100-138` to track multiple `clientId`s; route `tools/call` to the right client's session. **Verify:** two harnesses connect simultaneously; `tools/call` from each routes to its own session; sessions don't bleed.
- [ ] **Auto-generate `mcp.json`.** Add a `harness-ide mcp init` subcommand to `cli.rs:1-307` that writes `mcp.json` with the right `command` (local) or `url` + `headers` (remote). **Verify:** running `harness-ide mcp init` writes a valid `mcp.json` that Claude Code / Codex CLI accepts.

## 1.10 §5 Status bar (PLAN_01.md:L478–L487)

- [ ] **Wire `context_pct` updates.** `harness-ide/src/ui/app.rs:135` initializes `context_pct: 0` and never updates it. Hook the agent's LLM response into a `set_context_pct` call. **Verify:** after the first LLM call, the status bar shows the model-specific context percentage; after 10 calls, the bar reflects the cumulative usage.

## 1.11 §7 Phase 6 hardening (PLAN_01.md:L714–L726)

- [ ] **Layer Landlock / seccomp on bwrap.** Extend `harness-ide/src/sandbox.rs:46-84`. **Verify:** with `HARNESS_IDE_SANDBOX=1` and a 5.13+ kernel, the sandboxed process can read only the workspace and `:tmpdir`; with Landlock disabled, a clear `Landlock unsupported on this kernel` message.
- [ ] **Add SBOM generation.** `cargo cyclonedx` or `cargo metadata --format-version=1` in CI. **Verify:** the CI artifact includes `bom.xml`; the SBOM lists every crate with a license.
- [ ] **Add signed builds.** Cosign or sigstore for release binaries. **Verify:** `cosign verify-blob harness-ide` succeeds against the in-toto public key.
- [ ] **Add a retention reaper.** A cron-style background job that prunes session JSONLs older than N days. **Verify:** setting `HARNESS_IDE_RETENTION_DAYS=30` and waiting (or fast-forwarding the test clock) deletes sessions older than 30 days; the audit log retains its chain.
- [ ] **Add telemetry hooks.** Operator-visible-only counters (per-tool latency, approval decisions). **Verify:** `HARNESS_IDE_TELEMETRY=1` writes a JSONL of counters; no PII or file contents.

## 1.12 PLAN_01 closing gates

- [ ] **Closing gate A (MVP).** All boxes in §1.1–§1.8 are checked; `cargo test -p harness-ide` passes; the audit log is sha256-chained; the approval card shows all §3.4 fields. **Verify:** `cargo test --workspace` is green; an integration test runs the Phase 3 scenario from PLAN_01.md:L681–L684 ("an agent can run a 30-minute multi-file refactor under the `workspace` profile; every tool call is approved or auto-approved per policy; the audit log is complete and exportable").
- [ ] **Closing gate B (Hardening).** All boxes in §1.11 are checked; the LSP surface is 14/14; the browser surface is 7/7; the git surface is 10/10. **Verify:** the security test suite from `lowrescoder/new_plans/00-adversarial-validation.md` passes against the layered sandbox.

---

# PLAN_02 — Video Editing Agent (`video-agent/`)

**Closing gate A — Core complete:** typed CR + 16 ops + proposer/compiler + FFmpeg deterministic + multi-step plan + named intents. **CLOSED** (with broll/music_duck render and 2 named intents as the soft gaps). (PLAN_02.md:L60–L264)

**Closing gate B — Hardened product:** perception backends wired + Remotion opt-in + web/desktop UI. **OPEN**. (PLAN_02.md:L178–L202, L303–L353, L357–L405)

## 2.1 §2 Op vocabulary — `jcut` / `lcut` (PLAN_02.md:L233)

- [ ] **Add `JCutOp` to the grammar.** `video-agent/src/video_agent/schema/change_request.py:1-211`; ~10 lines (Pydantic + a `lead_seconds: float` field). **Verify:** `JCutOp` appears in `AnyOp` discriminated union; `validate.py:60-72` enforces `0 < lead_seconds < clip_duration`; `ffmpeg_backend.py:283-313` produces a filtergraph with `adelay` on the second clip's audio.
- [ ] **Add `LCutOp` to the grammar.** Same shape as `JCutOp` but with `trail_seconds`. **Verify:** same as above, mirrored.
- [ ] **Test J/L cut codegen.** Add a fixture in `video-agent/tests/test_ffmpeg_codegen.py:1+` that exercises the filtergraph for both ops.

## 2.2 §3 Perception backends (PLAN_02.md:L130–L176)

The README at `video-agent/README.md:106-107` ("Honest limits") explicitly defers these; this section lifts the deferral.

- [ ] **Wire `faster-whisper` for ASR.** Add `faster-whisper` to `pyproject.toml:6-21`; new module `video-agent/src/video_agent/perception/transcribe.py`; populates `EvidenceManifest.transcript`. **Verify:** on a fixture WAV, `transcribe.py` returns a `Transcript` with `words: [{t, w}]`; the bundle renders the transcript block.
- [ ] **Wire `pyannote-audio` for diarization.** Same; populates `speaker` on each transcript word. **Verify:** on a 2-speaker fixture, the transcript carries `speaker: "S1"` / `"S2"`.
- [ ] **Wire `PySceneDetect` for proper scene cuts.** Add `scenedetect` to `pyproject.toml:6-21`; new module `video-agent/src/video_agent/perception/pyscene.py`; populates `EvidenceManifest.scenes` with `ContentDetector` + `ThresholdDetector` results. **Verify:** the hand-rolled `scenes.py:21-44` is replaced or augmented; a 2-cut fixture returns exactly 2 scenes.
- [ ] **Wire `PaddleOCR` for on-screen text.** Add `paddleocr` to deps; new module `video-agent/src/video_agent/perception/ocr.py`; populates `on_screen_text`. **Verify:** on a frame containing "Q3 revenue +12%", `ocr.py` returns `{t, text, box}` with `text == "Q3 revenue +12%"`.
- [ ] **Wire `YAMNet` (or AudioSet) for music detection.** New module `video-agent/src/video_agent/perception/music.py`; populates `music`. **Verify:** on a 30s clip with a 10s score intro, `music.py` returns one `music` event with `start=0, end=10, type="score"`.
- [ ] **Wire `InsightFace` for face detection + embedding.** Add to deps; new module `video-agent/src/video_agent/perception/faces.py`; adds a `faces` field to the manifest. **Verify:** on a frame with 1 face, `faces.py` returns `{id: "face:42", embedding: "vec:..."}`.

## 2.3 §4 Render engine — broll + music_duck (PLAN_02.md:L188–L202)

- [ ] **Render `broll` via overlay path.** Extend `BrollOp` in `change_request.py:144-148` with an optional `source: str` field (local asset path); in `compiler/timeline.py:81-136`, render as a top-layer `overlay` over the time range. **Verify:** `BrollOp(source="assets/broll.mp4", ...)` produces a render with the asset layered over the source for the specified time range.
- [ ] **Render `music_duck` via sidechaincompress.** In `compiler/ffmpeg_backend.py:283-313` (or a new branch in `timeline.py:81-136`), emit a `sidechaincompress` filter keyed on the voice track. **Verify:** `MusicDuckOp(track="music", below="voice", ratio_db=-12)` produces a render where the music track is attenuated by 12 dB while the voice track is present. Currently a silent no-op at `ffmpeg_backend.py:263`.

## 2.4 §5 Named intent templates (PLAN_02.md:L249–L257)

- [ ] **Add `interview_to_article` template.** New entry in `video-agent/src/video_agent/templates/intents.py:139-144`; stitches `transcript` + `chapter` ops to produce a Markdown article. **Verify:** running `video-agent templates apply interview_to_article interview.mp4` produces a plan with `chapter` ops referencing the diarized speakers; the rendered article contains quoted segments.
- [ ] **Add `livestream_vod_to_chapters` template.** New entry; stitches `chapter` + `remove_segments` (waiting room) + `normalize_audio` ops. **Verify:** running the template produces a plan with `chapter` markers at ≥ 5-minute intervals; `remove_segments` covers the waiting-room periods.

## 2.5 §7 UX — web/desktop UI (PLAN_02.md:L303–L353)

- [ ] **Spec the chat-with-video UI.** The runtime contract is `EditSession` at `video-agent/src/video_agent/agent/session.py:54-92`; design a Tauri or web frontend that calls this contract. **Verify:** design doc with the §7.1 sketch realized in HTML; preview pane + CR diff + chat + composer.
- [ ] **Build the UI shell.** Tauri + a TS frontend. **Verify:** the UI calls `EditSession.propose` and renders the CR diff in a side-by-side; `Accept` calls `EditSession.apply`.
- [ ] **Multi-step plan panel.** A `Plan` view that shows the steps and their state (`pending` / `validating` / `preview` / `approved` / `rejected`). **Verify:** the UI lists every step in the plan with its current state; clicking a step shows the rendered preview.

## 2.6 §4 Render engine — Remotion opt-in (PLAN_02.md:L194)

- [ ] **Wire Remotion as opt-in.** Add a `RemotionBackend` in `video-agent/src/video_agent/compiler/`. **Verify:** `video-agent --backend remotion ...` produces a render via Remotion for "polished" templates (animated captions, spring zooms); falls back to FFmpeg for everything else.

## 2.7 §6 Local VLM planner (PLAN_02.md:L278–L294)

- [ ] **Wire Qwen2.5-VL-7B (Q4) as a local planner.** A `LocalLLMPlanner` in `video-agent/src/video_agent/agent/planner.py:92-131` that calls a local Qwen2.5-VL server. **Verify:** `video-agent --planner local ...` works without `OPENAI_API_KEY`; the planner consumes the bundle (with `transcript` populated) and emits a CR.

## 2.8 PLAN_02 closing gates

- [ ] **Closing gate A (Core complete).** All boxes in §2.1–§2.4 are checked; `pytest video-agent/tests/` is green (currently 112 pass + 1 skipped); the broll/music_duck ops render; the two missing named intents are added. **Verify:** the end-to-end test `tests/test_render_e2e.py::test_rerender_is_frame_identical` still passes after the new ops are added; the bundle renders populated `transcript` + `on_screen_text` + `music` fields.
- [ ] **Closing gate B (Hardened product).** All boxes in §2.5–§2.7 are checked; the UI is shipping; the local-VLM path is shipping. **Verify:** the UI demos the §7.1 sketch; a user can load a video, type "polish for YouTube," and get a CR diff that they can accept.

---

# PLAN_03 — Full Codex/Cursor IDE (`harness-ide/crates/station/`)

**Closing gate A — MVP (§9 carry-overs + hunk review + composer + plan mode + A/B compare + approval card):** **CLOSED** (with Ask-why, merge gate, Inbox default as soft gaps). (PLAN_03.md:L573–L587)

**Closing gate B — Hardened full surface:** §1–§5. **OPEN** (~80% traditional IDE, ~90% AI-IDE breadth). (PLAN_03.md:L28–L378)

## 3.1 §9 carry-overs — soft gaps (PLAN_03.md:L573–L587)

- [ ] **Add `Ask-why` to the pending-hunk toolbar.** `harness-ide/crates/station/src/editor.rs:585-610` has Accept / Reject buttons; add a third button that sends a `request_clarification` to the harness. **Verify:** clicking `Ask-why` on a pending hunk routes a message to the harness; the harness's reply appears in the agent panel.
- [ ] **Build the Merge gate view.** A `View::Merge` in `harness-ide/crates/station/src/app.rs:1226-1233` with a checklist (tests, lint, comments resolved, maker/checker, dirty-worktree conflict). **Verify:** opening Merge shows the checklist; all boxes must be checked before `git_commit` is enabled; the override path requires a typed note.
- [ ] **Inbox as default view.** `harness-ide/crates/station/src/app.rs:169` initializes `view: View::Editor`; change to `View::Inbox`. **Verify:** launching the app shows the Inbox rail slot as the default; Esc returns to the previous view.

## 3.2 §1 Codex app — Phase-6 (PLAN_03.md:L28–L110)

- [ ] **Add project switcher and persisted project list.** `harness-ide/crates/station/src/main.rs:27-30` opens a single root; add a `~/.config/autocode-station/projects.toml` and a project picker. **Verify:** `Cmd+Shift+P` opens a project picker; selection switches the workspace and reloads the file tree.
- [ ] **Implement side-by-side threads.** `harness-ide/crates/station/src/harness/mod.rs:74-135` holds a single `self.session`; add a `Vec<ThreadSession>` and a tab strip. **Verify:** `Cmd+T` opens a new thread; the tab strip shows the active thread; switching threads preserves their conversation.
- [ ] **Add worktree picker.** A `Worktree` mode that runs the harness in a `git worktree` checkout. **Verify:** selecting `Worktree` mode creates `~/worktrees/<branch>`; the agent runs in that worktree; results round-trip back to the main checkout on merge.
- [ ] **Real integrated terminal (PTY).** Replace the `run_command` panel (`harness-ide/crates/station/src/app.rs:1165-1224`) with a PTY-backed terminal. **Verify:** the terminal is a real PTY (xterm.js or platform-native); `vim`, `htop`, etc. work; the agent can `cat` the running dev server's output.
- [ ] **Named Actions.** A `.codex/actions.toml` (or `autocode-station/actions.toml`) parser; UI in `View::Settings`. **Verify:** the agent can call `pnpm test` via the `run_action` tool; the action's `name`, `description`, and `command` are visible in the UI.
- [ ] **Approval scopes (once/thread/session).** Extend the approval card at `harness-ide/crates/station/src/app.rs:291-387` with `for thread` and `for session` buttons. **Verify:** an approval granted `for session` applies to every matching tool call in the same session; the audit log records the scope.
- [ ] **Sandbox controls (UI).** A `View::Sandbox` exposing bwrap profiles and Landlock status. **Verify:** the UI shows the active profile, the workspace root, and the network allow/deny list.
- [ ] **Skills discovery + UI.** A `$IDE_HOME/skills/` loader; UI in `View::Settings`. **Verify:** placing a `SKILL.md` in the directory shows up in the UI; the skill is available to the agent.
- [ ] **MCP registry UI.** A `View::Mcp` that reads `mcp.json` and shows the registered servers. **Verify:** adding a server to `mcp.json` shows up in the UI; the server's tools are listed.
- [ ] **In-app browser (real webview).** Replace the `View::BrowserQa` placeholder at `harness-ide/crates/station/src/app.rs:650` with an embedded webview. **Verify:** the browser renders a public URL; the agent can call `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_screenshot`; element comments work.
- [ ] **Task sidebar (plan/sources/summary).** Extend the right agent panel at `harness-ide/crates/station/src/app.rs:626-631` with tabs for `Plan` / `Sources` / `Summary`. **Verify:** the `Plan` tab shows the agent's structured plan; the `Summary` tab shows the working diff.
- [ ] **Voice dictation (^M).** Wire `Ctrl+M` to OS-level audio capture + STT. **Verify:** hold `Ctrl+M`, speak, release; the transcript is editable in the composer before send.
- [ ] **Drag-drop image input.** A file drop handler that stores the image and references it in the conversation context. **Verify:** dropping a PNG into the composer attaches it; the agent sees the image in the next turn.
- [ ] **Screenshots ("Appshots").** Capture the frontmost window and send to the agent. **Verify:** the screenshot appears in the conversation context with the file's hash.
- [ ] **Memories.** Local Markdown in `$IDE_HOME/memories/`; inject into the harness system prompt. **Verify:** placing a memory in the directory is visible in the UI; the agent references it on the next session.
- [ ] **Floating pop-out thread window.** An OS window with `alwaysOnTop`. **Verify:** clicking "Pop out" on a thread detaches it to a second monitor; the thread continues.

## 3.3 §2 Cursor features (PLAN_03.md:L115–L170)

- [ ] **Tab completion (single + multi-line).** A local small-model completion engine; ghost text overlay. **Verify:** typing a partial line shows a ghost-text suggestion; `Tab` accepts; the suggestion is computed in <50ms for the easy case.
- [ ] **Cursor prediction.** After accepting a completion, jump to the next likely edit point. **Verify:** the cursor moves to the predicted location; the move is a soft suggestion (operator can override).
- [ ] **@-symbol context injection.** A `@` picker in the composer (`@file`, `@folder`, `@codebase`, `@git`, `@docs`, `@web`). **Verify:** typing `@file` opens a fuzzy file picker; `@codebase` does a semantic search; `@git` attaches the working diff.
- [ ] **Slash commands.** `CmdId` enum in `harness-ide/crates/station/src/palette.rs:21-35`; one trait method on `Harness`. **Verify:** `/edit`, `/test`, `/explain`, `/review`, `/commit`, `/refactor`, `/doc`, `/agent`, `/init`, `/fix`, `/simplify`, `/security-review` are all wired.
- [ ] **Background agents.** A `Vec<BackgroundSession>` next to `self.session` (`harness-ide/crates/station/src/app.rs:110`); a `Tasks` tab on the agent panel. **Verify:** clicking "Run in background" on a prompt spawns a background session; the foreground remains interactive; the background result streams back when done.
- [ ] **Subagents.** A `Harness::spawn_subagent` method; the agent panel shows subagent rows. **Verify:** a parent agent spawns a subagent; the subagent's tool calls are visible in the parent's agent panel; the parent receives a single text result.
- [ ] **Multi-model routing.** A model selector that enumerates Claude / GPT / Gemini / Grok / Kimi. **Verify:** the model combo box lists every model with its cost; switching models changes the next LLM call.
- [ ] **BYOK + cost tracking.** A settings panel for per-provider keys; the existing `cost_usd` / `tokens` are per-thread. **Verify:** the status bar shows per-thread cost; the settings panel lets the operator set a daily cost cap.
- [ ] **Context window indicator.** The existing tokens shown against a model-specific limit. **Verify:** the status bar shows `tokens / limit`; the bar turns yellow at 80%, red at 95%.
- [ ] **Token breakdown by tool / file / model.** A panel that breaks down the tokens per tool call. **Verify:** the panel lists every tool call with its token count; summing equals the session total.
- [ ] **Rate-limit awareness.** A panel that shows the per-provider rate-limit status. **Verify:** the panel shows requests-per-minute remaining; a back-pressure indicator when near the limit.
- [ ] **.cursorrules.** Project-level rules loaded into the harness system prompt. **Verify:** placing `.cursorrules` in the workspace is read at session start; the agent obeys the rules.

## 3.4 §3 Zed features (PLAN_03.md:L176–L213)

- [ ] **Tree-sitter native.** Replace the hand-rolled `harness-ide/crates/station/src/highlight.rs` with tree-sitter; add a `tree-sitter` dep. **Verify:** syntax highlighting uses the CST; code-folding and outline-from-AST are available.
- [ ] **Multi-buffer.** A single editor surface that hosts multiple selections across multiple files. **Verify:** selecting 12 occurrences of a symbol across 4 files and pressing `Cmd+Shift+I` opens them in a multi-buffer; one edit applies to all.
- [ ] **ACP (Agent Client Protocol).** Implement the editor↔agent protocol for embedding third-party agents. **Verify:** Claude Code, Codex CLI, and OpenCode can be embedded via ACP.
- [ ] **Edit Prediction (Tab).** A local model for the easy case; cloud for hard cases. **Verify:** typing in the editor shows a ghost-text suggestion; `Tab` accepts; the suggestion is computed in <50ms.
- [ ] **CRDT-based collab.** Real-time multi-cursor editing. **Verify:** two operators editing the same file see each other's cursors in <100ms.
- [ ] **Remote projects.** Open a folder over SSH. **Verify:** `File > Open Remote > ssh://...` opens a folder; the UX is identical to local.

## 3.5 §4 Traditional IDE features (PLAN_03.md:L218–L322)

- [ ] **Multi-root workspaces.** Multiple roots in the workspace. **Verify:** `File > Add Folder to Workspace` adds a second root; the file tree shows both.
- [ ] **File watcher.** inotify / fsevents / ReadDirectoryChangesW. **Verify:** editing a file outside the IDE updates the file tree within 1s.
- [ ] **Multi-cursor / column select.** Replace the single `TextEdit::multiline` at `harness-ide/crates/station/src/editor.rs:1+` with a multi-cursor TextEdit. **Verify:** `Cmd+D` selects the next occurrence; `Alt+Click` adds a cursor.
- [ ] **Soft wrap.** Toggle in the status bar. **Verify:** `View > Toggle Word Wrap` wraps long lines; the gutter updates.
- [ ] **Minimap.** A second `TextEdit` over the gutter. **Verify:** the minimap is a 200x zoomed-out view of the buffer; clicking the minimap scrolls the editor.
- [ ] **Code folding.** Tree-sitter-based fold ranges. **Verify:** clicking the gutter fold icon collapses a function; the buffer saves with the fold state.
- [ ] **Snippets.** Snippet engine with user snippets. **Verify:** typing a snippet prefix and pressing `Tab` expands it.
- [ ] **Vim/Helix modal editing.** A modal editing mode. **Verify:** pressing `Esc` enters normal mode; `i` enters insert; `:w` saves.
- [ ] **LSP completion / hover / rename UI.** Wire `egui::Popup` for completion; `response.on_hover_text` for hover. **Verify:** typing a partial token shows a completion popup; hovering a symbol shows the type and doc; `F2` renames across the workspace.
- [ ] **Inlay hints / semantic tokens.** Tree-sitter-driven inlay hints. **Verify:** Rust types appear in the gutter; toggling inlay hints in settings hides them.
- [ ] **Call hierarchy.** A panel that shows the incoming and outgoing calls of a function. **Verify:** `Shift+F12` on a function shows the call hierarchy.
- [ ] **Find / replace (cross-file).** A replace-in-files mode. **Verify:** `Cmd+Shift+H` opens replace-in-files; the replace is staged in the file tree.
- [ ] **Source control panel.** A full `View::SourceControl` with branch / remote / stash / tag / blame. **Verify:** the panel shows the current branch, ahead/behind, the working diff, and a button to commit.
- [ ] **Diff gutter (per-line).** Add a per-line gutter marker for added/modified/deleted. **Verify:** the gutter shows a green `+` for added, a yellow `~` for modified, a red `-` for deleted.
- [ ] **Inline PR comments.** A commentable surface on the diff. **Verify:** clicking a line in the diff opens a comment; the comment round-trips into the agent's prompt.
- [ ] **Debug (DAP).** Breakpoints, step / watch / call stack, `launch.json`. **Verify:** setting a breakpoint and pressing F5 starts the debugger; the call stack is visible.
- [ ] **Tasks + problem matchers + test runner.** A `tasks.json` parser and a test runner UI. **Verify:** `Cmd+Shift+B` runs the build task; failed tests appear in the Problems panel.
- [ ] **Multiple terminals + shell detection + terminal links.** Replace the `run_command` panel with a full PTY terminal. **Verify:** `Ctrl+Shift+\`` opens a new terminal; the shell is detected from the path; file:line links are clickable.
- [ ] **Notification toasts (top-right).** A toast system in the top-right corner. **Verify:** approval cards never overlap toasts; toasts auto-dismiss after 5s.
- [ ] **Zen / focus mode.** A toggle that hides the rail and the status bar. **Verify:** `Cmd+K Z` enters Zen mode; `Cmd+K Z` again exits.
- [ ] **Zoom.** Per-window or per-editor zoom. **Verify:** `Cmd++` and `Cmd+-` zoom the editor.
- [ ] **Settings (JSON).** A JSON settings file with a UI. **Verify:** the settings are saved to `~/.config/autocode-station/settings.json`; the UI is the canonical view of the file.
- [ ] **Keybindings (rebindable).** A keybindings editor. **Verify:** `Cmd+K Cmd+S` opens the keybindings file; the operator can rebind any shortcut.
- [ ] **Icon themes.** A theme picker with multiple icon themes. **Verify:** selecting a theme updates the file tree icons.
- [ ] **Profiles (synced).** Settings + keybindings synced across machines. **Verify:** changing a setting on one machine updates the other within 5 minutes.
- [ ] **Extension marketplace.** A registry of extensions. **Verify:** the marketplace is browsable; installing an extension registers its commands, panels, and providers.

## 3.6 §4.11 Configurability + §4.10 Window + §5.4 Trust/safety (PLAN_03.md:L316–L322, L360–L367)

- [ ] **Per-tool permission scopes (UI).** A panel in `View::Settings` for per-tool allow/ask/deny. **Verify:** denying `run_command` causes every `run_command` call to return a `denial` event.
- [ ] **Checkpoints / time-travel.** A `git stash` wrapper + history list. **Verify:** pressing `Cmd+Shift+R` opens the checkpoint list; selecting one restores the buffer.
- [ ] **Privacy mode.** A toggle in the status bar. **Verify:** enabling privacy mode disables training and sets the provider to a private one.
- [ ] **Settings sync.** A sync adapter (file / git). **Verify:** changing a setting on one machine updates the other.
- [ ] **Cloud sync of thread history.** An opt-in cloud sync. **Verify:** enabling cloud sync syncs the thread history across machines; the cloud endpoint is user-controlled.

## 3.7 PLAN_03 closing gates

- [ ] **Closing gate A (MVP).** All boxes in §3.1 are checked; `cargo test -p autocode-station` passes; the trust-domain spine is in place. **Verify:** the §9 carry-overs (PLAN_03.md:L573–L587) are all in place; the hunk review flow works end-to-end; the A/B compare view spawns two harnesses.
- [ ] **Closing gate B (Hardened full surface).** All boxes in §3.2–§3.6 are checked. **Verify:** the operator can use the IDE for a 30-minute multi-file refactor without leaving it; the LSP surface is 14/14 (driven by `harness-ide::tools::lsp`); the browser surface is 7/7; the DAP surface is complete; the extension marketplace has ≥ 1 extension.

---

# PLAN_04 — Teacher Mode (`autocode/anvil/teacher/`)

**Closing gate A — MVP (Phases 1–2):** online teacher with reversible playbook deltas + ACE wiring + runtime loader — **CODE-CLOSED**, but the measurement substrate it depends on is **NOT complete**: G2/G3 (recorder/verifier) ship, but **G4 (held-out corpus + split + noise band) is absent** and the edge-cost guard is built-but-inert (§4.4). By the Anvil plan's own Phase-1 "do not proceed past this gate" rule, Gate A is **not** fully met. (PLAN_04.md:L427–L461)

**Closing gate B — Manual self-maintenance loop (Phase 3):** G1 manifest + G5 distiller + G8 prediction-contract scorer + manual loop CLI. **OPEN**. (PLAN_04.md:L462–L474)

**Closing gate C — Copycat + hardening (Phases 4–7):** copycat channels A + C-cheap + Terminal-Bench yardstick + autonomy + distillation. **OPEN**. (PLAN_04.md:L476–L527)

## 4.1 §6 Manual MVP — `sense` command (PLAN_04.md:L389–L424)

- [x] **Add `sense` command to teacher CLI.** ✅ **DONE** — `teacher/cli.py:159` exports `sense` (clusters last-N failed trajectories, ranked by `frequency × severity × (1 + is_tool_missing_capability × 2)`). *(Was open; built after the original audit.)*

## 4.2 §7 Phase 1 — measurement substrate hardening (PLAN_04.md:L437–L448)

- [ ] **Build a corpus aggregator.** A new module `autocode/src/autocode/anvil/teacher/corpus.py` that reads `$IDE_HOME/sessions/*.jsonl` and the trajectory store, and produces a held-out split. **Verify:** `autocode anvil teacher corpus build` writes `$AUTOCODE_HOME/teacher/corpus@v3/{train,held_out}.jsonl` with ≥ 50 replayable cases and a marked `oracle_strength` per case.
- [ ] **Compute the multi-objective metric.** Implement `autocode/src/autocode/anvil/teacher/eval.py` per `lowrescoder/new_plans/harness_copy_teacher/08_EVALUATION_AND_VERIFICATION.md` §8.2. **Verify:** `autocode anvil teacher eval --corpus corpus@v3` writes `eval_report.json` with `pass_at_1` (mean ± spread), `layer_distribution.L1/L2/L3/L4`, `latency_p50`, `tokens_per_task`; the noise band is measured.

## 4.3 §7 Phase 3 — component manifest + distiller (PLAN_04.md:L462–L474)

- [ ] **Build the component manifest by introspecting existing code.** A new module `autocode/src/autocode/anvil/manifest.py` per `lowrescoder/new_plans/harness_copy_teacher/04_ARCHITECTURE.md` §4.1. **Verify:** `autocode anvil manifest dump` writes `$AUTOCODE_HOME/manifest.yaml` listing every tool, middleware, prompt, and memory store with its `prediction_metrics` field.
- [x] **Build the distiller → layered evidence corpus.** ✅ **DONE (as `teacher/distill.py`)** — 456 LOC, Layer 0–3 per-cluster drill-down, driven by `anvil teacher sense`, 18 tests. *Note:* this is the per-cluster distiller; the standalone `anvil/distill.py` name in the original box was not used. The **held-out eval corpus** (the `corpus build` box in §4.2) is still open and is the actual remaining gap.
- [ ] **Build the prediction-contract scorer.** A new module `autocode/src/autocode/anvil/score.py` that compares predicted vs actual and emits a `prediction_score.json`. **Verify:** the scorer reads `prediction_contract.json` + `eval_report.json` and writes `prediction_score.json` with `met: bool`, `no_regression: bool`, and a per-`no_regression_on` value (PLAN_04.md:L58, L161, L218, L262).

## 4.4 §7 Phase 3 — wire + enforce edge-cost guards (PLAN_04.md:L58, L218, L262)

> **Status correction:** the three guards (`layer_distribution.L4`, `latency_p50`, `tokens_per_task`) **are now measured** — `teacher/cost.py` implements `measure`/`compare`/`EdgeCostVerdict` (15 tests). They are **not enforced in the live flow**, which is the real remaining work and the single highest-ROI fix in the repo:

- [ ] **Wire `edge_cost_verdict` into the live `gate` call.** `cli.py:282` calls `gate(_bundle_dir(...))` with no verdict, so `gate.py:115` records `edge_cost_measured: False` and defaults `no_regression` to True. Measure baseline-vs-candidate trajectories and pass the verdict. **Verify:** a gated bundle records `edge_cost_measured: True`; a regressing verdict sets `no_regression: False`. **(~few lines; machinery already exists.)**
- [ ] **Make `promote()` block on `no_regression`.** `promote.py:42` raises only on `not score["met"]`; `no_regression` is recorded at `:58` but never gated on (the docstring `:3-4` claims it is). Add the guard. **Verify:** a bundle with `met: true, no_regression: false` is **refused** by `promote`.
- [ ] **Measure off the held-out split** (depends on the `corpus build` box in §4.2). **Verify:** the verdict's deltas are computed against the frozen held-out set, not an ad-hoc trajectory pair.

## 4.5 §7 Phase 4 — copycat channels A + C-cheap (PLAN_04.md:L476–L487)

See PLAN_05 §5.2 (Channel A) and §5.4 (Channel C-cheap). These are shared work with PLAN_05.

## 4.6 §7 Phase 5 — Terminal-Bench yardstick (PLAN_04.md:L489–L497)

- [ ] **Wire the Terminal-Bench harness.** A new module `autocode/src/autocode/anvil/terminal_bench.py` that runs the TB Docker tasks and reuses the verifier interface. **Verify:** `autocode anvil terminal-bench run` produces a TB report; the report is comparable to TB's published results.
- [ ] **Build a meta-evaluation dashboard.** A small web UI (or a Markdown report) that shows held-out `pass_at_1` trend, edge-cost trend, promotion precision, prediction calibration, flywheel fuel rate. **Verify:** the dashboard is regenerated on every cycle; the operator can read the trend at a glance.

## 4.7 §7 Phase 6 — autonomy (gated) (PLAN_04.md:L499–L507)

- [ ] **Implement kill switches + tripwire evals.** A `autocode/src/autocode/anvil/killswitch.py` that halts the loop on a regression. **Verify:** a regression in `pass_at_1` trips the kill switch; the loop halts; the operator is notified.
- [ ] **Shadow-canary automation.** A `autocode/src/autocode/anvil/canary.py` that runs the patch in shadow before promoting. **Verify:** a patch promoted via canary shows a 7-day shadow period with no regression.
- [ ] **Bounded autonomous cycle.** A `autocode/src/autocode/anvil/autonomy.py` that runs `propose → gate → shadow → promote/revert` with daily cost/time budgets. **Verify:** the cycle runs unattended for N cycles; every promotion is auditable.

## 4.8 PLAN_04 closing gates

- [ ] **Closing gate A (MVP).** All boxes in §4.1 are checked; the `sense` command is exported; the corpus is ≥ 50 cases. **Verify:** the operator runs `autocode anvil teacher sense → propose → gate → promote` for at least one cluster and the playbook delta is loaded into the runtime.
- [ ] **Closing gate B (Manual self-maintenance).** All boxes in §4.2–§4.4 are checked. **Verify:** at least one patch bundle goes `sense → propose → gate → promote`, meets its prediction on the held-out subset, regresses nothing on the edge guards, and is logged with a `decision.md`.
- [ ] **Closing gate C (Copycat + hardening).** All boxes in §4.5–§4.7 are checked. **Verify:** ≥ 1 copycat-derived component and ≥ 1 self-distillation-derived harness fix are promoted; a multi-cycle run shows held-out `pass_at_1` flat-or-up and edge-cost flat-or-down across ≥ 4 cycles.

---

# PLAN_05 — Copycat Mode (`autocode/anvil/`)

**Closing gate A — MVP (Phase 4):** registry + Channel A + Channel C-cheap + 5 patch bundles (1 fully promoted, 4 gated_pass). **CODE-CLOSED**; Channel B's eval branch is **now also built** (prior "Channel B absent" is stale). *Caveat:* the 5 bundles were gated/promoted with the edge-cost guard unenforced and no held-out split, so the promotions are optimistic (see §4.4). (PLAN_05.md:L414–L426)

**Closing gate B — Hardened (Phases 5–7):** Terminal-Bench yardstick + autonomy + distillation lane. **OPEN**. (PLAN_05.md:L429–L456)

## 5.1 §1 Authorization registry (PLAN_05.md:L88–L141)

- [ ] **Add `weights`-scope ToS check enforcement.** `autocode/src/autocode/anvil/registry.py:99-103` already enforces `weights` requires `tos_check`; add a CLI command that reads the current ToS and records the date + clause summary. **Verify:** `autocode anvil copycat tos-check anthropic` writes the date + clause summary to `anvil/copycat/registry.yaml`; a `weights`-scope channel run without a ToS check fails with a clear error.

## 5.2 §2 Channel A — structural imitation (PLAN_05.md:L145–L184)

- [ ] **Add a `weights`-scope `claude-code` target** to `anvil/copycat/registry.yaml`. **Verify:** the registry validates the new target; `autocode anvil copycat census claude-code` walks the `research-components/claude-code-sourcemap` mirror.
- [ ] **Add a `weights`-scope `openai-codex` target.** Same.
- [ ] **Add a `weights`-scope `opencode` target.** Same.
- [ ] **Add a `weights`-scope `aider` target.** Same.
- [ ] **Add a `weights`-scope `pi-mono` target.** Same.
- [ ] **Add a `weights`-scope `open-swe` target.** Same.
- [ ] **Add a `weights`-scope `goose` target.** Same.
- [ ] **Rank gaps by `tool.missing_capability` bias** (per PLAN_05.md:L470). Extend `autocode/src/autocode/anvil/gapdiff.py:198-246` with the same `rank = frequency × severity × (1 + is_tool_missing_capability × 2)` rule used in `anvil/teacher/taxonomy.py:88-98`. **Verify:** the gap-diff output is sorted by rank; the operator can pick the top-3.

## 5.3 §3 Channel B — outcome distillation (PLAN_05.md:L188–L237)

- [x] **Implement the eval-oracle branch.** ✅ **DONE** — `copycat/outcome.py` (408 LOC) drives an authorized target and captures verified diffs; CLI-wired (`cli.py:199`, `outcome` command); 22 tests (`test_anvil_copycat_channel_b.py`). *(Was open; built after the original audit.)*
- [x] **Implement the distillation branch (dataset render, gated by ToS check).** ✅ **DONE** — `copycat/distill.py` (154 LOC) renders the verified-outcome corpus into a training dataset, CLI-wired (`cli.py`, `distill` command), ToS-gated via `registry.py:84-104`. *Note:* this is the **dataset renderer**; the actual QLoRA/SOD **trainer** (`copycat/weights.py`) is the separate open box in §5.4, and no `tos-check` command exists yet to record the ToS read (see Addendum).
- [ ] **Wire the rate limit** (per PLAN_05.md:L486): default 50 runs/day, tunable from the eval-corpus growth curve. **Verify:** the rate limit is enforced; the corpus growth rate is logged.

## 5.4 §4 Channel C — self-distillation (PLAN_05.md:L241–L287)

- [ ] **Promote at least one Channel C-cheap bundle.** The teacher emits `self_distill` bundles at `autocode/src/autocode/anvil/teacher/loop.py:188-251`; the operator must run `autocode anvil teacher run --emit-harness-fix` against a real trajectory diff and promote the bundle. **Verify:** a `pb_*` directory under `anvil/patch_bundles/` with `channel: self_distill` and `status: promoted`.
- [ ] **Implement the weights branch (Phase 7).** A new module `autocode/src/autocode/anvil/copycat/weights.py` that runs QLoRA / step-wise OPD on the local 1.5B model on the RTX 4060 Ti. **Verify:** the training pipeline runs; the distilled adapter is stored in `$AUTOCODE_HOME/copycat/adapters/<name>/`; the prediction contract is enforced.

## 5.5 §5 Build order (PLAN_05.md:L301–L316)

- [ ] **Enforce the build order.** Extend `autocode/src/autocode/anvil/cli.py:64-70` `_enforce_or_exit` to refuse Channel B-eval until ≥ 1 Channel A bundle is promoted, and refuse Channel B-weights until ≥ 1 Channel C-cheap bundle is promoted. **Verify:** the order is enforced; a `weights`-scope run with no Channel C-cheap history returns a clear error.

## 5.6 §6 Manual MVP CLI (PLAN_05.md:L326–L365)

- [ ] **Add a `census --all` command.** Aggregate all targets in the registry. **Verify:** the command produces one census file per target in `anvil/copycat/census/`.
- [ ] **Add a `gap-diff --all --json` command.** Same; with a `--json` flag for machine-readable output. **Verify:** the JSON output is parseable by the distiller (`anvil/distill.py`).

## 5.7 §7 Phases 5–7 (PLAN_05.md:L429–L456)

- [ ] **Wire Terminal-Bench.** Reuse `autocode/src/autocode/anvil/terminal_bench.py` from PLAN_04 §4.6.
- [ ] **Implement kill switches + canary.** Reuse from PLAN_04 §4.7.
- [ ] **Distillation lane (QLoRA + SOD).** Reuse from PLAN_04 §4.8.

## 5.8 PLAN_05 closing gates

- [ ] **Closing gate A (MVP).** All boxes in §5.2 are checked; the 8 reference targets are registered; at least one Channel C-cheap bundle is promoted. **Verify:** the operator can run `autocode anvil copycat census --all → gap-diff --all → propose <cap> → gate → promote` and the bundle meets its prediction.
- [ ] **Closing gate B (Hardened).** All boxes in §5.3–§5.7 are checked. **Verify:** Channel B-eval and Channel B-weights are both shipping; the distillation lane is shipping; a multi-cycle run shows held-out `pass_at_1` flat-or-up.

---

# Cross-cutting work (none of the five plans owns this)

## X.1 Test environment (operational, not in any plan)

- [ ] **Fix `_repo_root()` to handle the suite split.** The autocode core's `_repo_root()` searches upward for a dir containing `CLAUDE.md`; it overshoots to the suite-root `autocode-full/CLAUDE.md`. **Verify:** the test that fails on this runs green.
- [ ] **Migrate the doc-lock/roadmap-lock tests.** The docs they guard (`docs/plan/archive/phase5-agent-teams.md`, `docs/reference/rpc-schema-v1.md`) live in `lowrescoder/docs/`, not in `autocode/docs/`. Either copy the docs or retire the tests. **Verify:** the doc-lock tests pass.
- [ ] **Install missing optional deps into the autocode venv.** Pillow + the `evals` package. **Verify:** the vhs/tui-reference tests and the eval-import tests pass.
- [ ] **Fix `test_doctor_git_check`.** `git init` the repo (or skip the doctor git test in a no-git fixture). **Verify:** the doctor test passes.
- [ ] **Install `autocode` into the harness-tester venv.** `pip install -e ../autocode` in the harness-tester environment. **Verify:** the 3 harness-tester failures clear.

## X.2 Operational hazards in the test suite

- [ ] **Make `test_anvil_teacher_e2e.py` deterministic.** The test fails when the LiteLLM gateway is up because the small coding-alias model returns an empty student trajectory. Either pin the model, mock the gateway, or skip on empty. **Verify:** the test passes deterministically.
- [ ] **Decouple `anvil/gate.py::_default_check_runner` from `uv run pytest`.** The function hardcodes `["uv","run","pytest",…]` and would break offline. **Verify:** the runner accepts a configurable command; the default is still `uv run pytest` for back-compat.

## X.3 Operator-facing notes

- [ ] **Update the harness-ide README.** The README's "every §2–6 feature implemented" is overstated. **Verify:** the README's "Status" section matches NEW_PLANS_GAPS.md §1.8.
- [ ] **Update the autocode-station README.** Similarly, the README should reflect that §3 (Zed/ACP), §4 (traditional IDE), and most of §5 (memories, skills, MCP UI) are not built.
- [ ] **Add `docs/plan/NEW_PLANS_GAPS.md` and `NEW_PLANS_REMAINING_TODO.md` to the docs index.** These are the canonical gap analysis and checklist; they should be discoverable from `lowrescoder/new_plans/README.md`.

---

# Addendum — remaining work the original checklist never owned (2026-06-23)

The boxes above were derived from PLAN_01–05 against their own prose. These come from the **source docs** (`harness_copy_teacher/`, ClipMind, autocode-station requirements/mockups) and the **empirical test run**. Anchors are `file:line` / doc section. Items already covered above (corpus build §4.2, kill-switches/canary/autonomy §4.7, Terminal-Bench §4.6, ToS-check command §5.1) are **not** repeated.

## A.1 Anvil self-maintenance safety layer (07/08 — the autonomous half)

- [ ] **Gate-component lockout test.** Assert that fails the run if a patch bundle's `manifest_entry` targets the verifier / eval suite / metrics / registry / kill switches. 07 §7.2 calls this "the single most important rule"; today it's only a docstring (`registry.py:9`). **Verify:** a bundle targeting `verifier.py` is refused at gate time.
- [ ] **Prediction-calibration / miss-rate aggregation.** Aggregate the per-bundle `prediction_score.json` stream into a rolling miss-rate; trip a kill signal on systematic misses (Correction 8, `04_ARCHITECTURE.md:232`). **Verify:** N consecutive prediction misses raises a calibration alarm independent of eval scores.
- [ ] **Build the *real* G1 AHE component manifest** (distinct from the CLI-census `manifest.py`). 7 kinds (system_prompt/tool/middleware/skill/subagent/memory) with `prediction_metrics` + `edit_surface` (`04_ARCHITECTURE.md:40-98`). **Verify:** copycat/teacher proposals can be scoped to a manifest entry's legal claim space. *(The §4.3 manifest box conflated this with the CLI census — this is the unbuilt one.)*
- [ ] **Decide GEPA tier-4 prompt optimizer:** build it (`04 §278`) or formally drop it. Correction 2 said *demote, not delete*; it was deleted. **Verify:** either a `gepa`-backed optimizer exists for `system_prompt` edits, or a one-line decision records the drop.
- [ ] **Make the ACE Pruner merge prediction-gated.** `teacher/cli.py:313` `prune` is an unguarded rewrite; 06 §6.3 requires "does pass@1 hold after pruning?". **Verify:** `prune` runs an eval gate on the merge and refuses on regression.
- [ ] **Write Phase-0 `docs/research/anvil-design.md`** (the north-star-legality gate, `09 §13-17`). **Verify:** the doc exists and a reviewer would not flag the program Critical. *(~1 day; cheapest unstarted item.)*

## A.2 ClipMind security stack (PLAN_02 / `video-agent/` — none in the original checklist)

- [ ] **Egress/approval gate around the cloud planner.** `video-agent/src/video_agent/cli.py:27-45` (`--planner llm`) ships with zero gating — the one structurally-absent link in the OCR→exfil chain. Add deny-by-default + explicit approval before any Bundle leaves the box. **Verify:** an LLM-planner run without approval is refused; resolves Open-Q1. *(Highest ClipMind ROI; small code.)*
- [ ] **Redact the Bundle + enforce instruction/data separation.** `agent/bundle.py:43-45` inlines raw transcript text; `planner.py:97` "separation" is only a prompt sentence. Fence untrusted evidence in a typed field; PII-mask before egress. **Verify:** the Bundle carries untrusted text in a clearly-fenced field; a PII pass runs pre-egress.
- [ ] **Build the injection (C7) + redaction (C4) adversarial corpus.** Today: one shell-field rejection test. **Verify:** a test feeds OCR/transcript injection and asserts it lands as evidence and the compiler rejects any exfil-shaped CR; resolves Open-Q8.
- [ ] **Per-derivative sensitivity labels + retention reaper** (`01-trust-domains.md:20`, `00-adversarial-validation.md:51`). Replace the single scalar `sensitivity` (`change_request.py:203`). **Verify:** transcripts/OCR inherit source sensitivity; a retention clock prunes derivatives.
- [ ] **Fix the ClipMind doc-map** (`README.md:24-71`): 26 of 28 advertised files don't exist, including all 5 `02-security/01..05` specs. Either write them or rewrite the map to the flat reality and kill the dead "read these three" links. **Verify:** every README link resolves.
- [ ] **Record the capture-domain drop as an explicit decision** (PLAN_02 edits user footage, never records) so the absent `03-capture-isolation` threat class is a decision, not an oversight.

## A.3 autocode-station (PLAN_03 — beyond the §3.1 soft gaps)

- [ ] **Real maker/checker *enforcement* (R10).** `requires_checker` is `None` in the real path (`approver.rs` / `core/approval.rs:422`), `Some()` only in a test fixture (`app.rs:1392`). Set it on high/critical-risk actions and enforce `maker_actor ≠ checker_actor`. **Verify:** a maker cannot self-approve a high-risk action in the station UI.
- [ ] **Secured remote/web access + token auth** (market-research risk #4, "fatal impact"; req-doc Narrow mode R19). No auth model in any plan. **Verify:** the UI served on the network requires a token; localhost-bound by default.
- [ ] **Shared review comments → "Send to agent" (R9, P1).** Attributed, file:line-anchored, resolvable; blocks commit. The Review view is currently a read-only diff (`app.rs:981-995`). **Verify:** a comment on a diff line round-trips into the agent's prompt.
- [ ] **Browser-QA split: Preview Browser + Chrome Bridge + untrusted-context label (R17, P1).** Beyond the §3.2 webview box — the security-sensitive untrusted-page quarantine. **Verify:** Chrome-bridge pages are labelled untrusted and sandboxed from the trusted context.
- [ ] **New-Task wizard (R18)** and **status-model state machine + Inbox bucket mapping (R15).** Absent from plan and repo. **Verify:** a `New Task` flow (intent→context→execution→preview) exists; ~20 states map to exactly one Inbox bucket.
- [ ] **Decide v2 vs v3 target, and the Skills-view fate.** The repo follows the v3 (editor-first) mockup; `codestation-mockup-v2` (threads-first, Skills view, voice composer) is superseded. **Verify:** a one-line decision records which mockup is canonical, so the dropped v2 surfaces are a choice, not drift.

## A.4 Cross-cutting contracts

- [ ] **Define the trajectory schema contract** referenced by both PLAN_01 (runtime/producer) and the Anvil docs (consumer). Anvil's `teacher/recorder.py` consumes `layer_distribution`; PLAN_01 never commits to emitting it. **Verify:** a shared schema doc exists; the harness emits trajectories the recorder parses end-to-end.
- [ ] **Write a shared authorization-barrier spec.** The proposer/authorizer pattern is implemented 3× (`video-agent/compiler/validate.py`, station `approver.rs`, anvil `gate.py`+`registry.py`) with no shared threat-model/audit-format. **Verify:** one spec defines approval semantics + audit-log format; the three reference it. *(Spec only — not forcing a shared cross-language lib.)*
- [ ] **Write a top-level `new_plans/INDEX.md`.** The README is ClipMind-only (mentions the 5 PLANs zero times); the only index covers Anvil. Map the 5 PLANs + Anvil + ClipMind + station with their dependency edges (Anvil↔PLAN_01 trajectories; PLAN_03↔PLAN_01 shared crate). **Verify:** the index lists every plan + its component + dependency order.

## A.5 Empirical test gaps (from the 2026-06-23 run — `NEW_PLANS_REST_AUDIT.md` §9)

- [ ] **Make the Anvil teacher live loop deterministic.** `test_anvil_teacher_e2e.py` is the only red test (local-model returns empty trajectory). Add a stubbed-gateway variant. **Verify:** the loop is verified green without depending on local-model behavior. *(Also tracked operationally in X.2.)*
- [ ] **Offline unit test for `teacher/gateway.py`** (74 LOC, only exercised by the skip-gated integration test). **Verify:** `gateway_ready` / `make_gateway_llm` have offline coverage.
- [ ] **Anvil CLI edge-cost/promote gating test** (after A.1/§4.4 wiring lands). **Verify:** a regressing verdict blocks promotion at the CLI level.
- [ ] **Station behavioral UI tests + committed snapshot baselines.** The wgpu tests only assert "renders without panic"; nothing drives Accept/Reject, the palette, or the approval-card click path; no snapshot baselines committed. **Verify:** a simulated-event test drives the hunk-accept path; `UPDATE_SNAPSHOTS` baselines exist.
- [ ] **video-agent live-LLM planner test + scene-detection manifest assertion** (1 skip / 0 active for live-LLM; scene detection is parser-only). **Verify:** a recorded-fixture or local-gateway test covers `LLMPlanner`; a 2-cut fixture asserts 2 scenes in the manifest.

## A.6 Unowned `[DECIDE]` list (decisions, not code — the user must call these)

- [ ] **Anvil:** tool-vs-research-artifact stopping point (stop ~Phase 4, or push to 5–7?); autonomy cap + "Anvil may not create new planning docs"; default `reuse_scope`; harness-only vs rented-GPU distillation (RX 480 is not a trainer; 8GB QLoRA is "marginal"); codename "Anvil" (locked-in-by-default).
- [ ] **ClipMind:** Q1 (cloud mode + its required egress gate), Q2 (logical-only isolation OK?), Q8 (build the adversarial corpus?).
- [ ] **Station:** v2-vs-v3 target; approve-for-session taxonomy; Skills-view fate; CRDT depth vs modelled-presence (req-doc §8 vs PLAN_03 §3.3 conflict); web/remote auth architecture; status-model ownership.

---

# Summary — top-priority TODO by ROI

Ranked by **value × ease of completion**. **Tier 0 (correctness/safety)** items were added 2026-06-23 — they remove a false-green or close a launch-blocking gap and mostly cost a few lines because the machinery already exists. **Tier 1 (feature MVP)** is the original fastest-path-to-MVP set.

**Tier 0 — correctness & safety — ✅ ALL DONE (gate-verified 2026-06-23):**

| Rank | Item | Plan | Status |
|---|---|---|---|
| 0a | Wire `edge_cost_verdict` into the live gate + `promote()` blocks on `no_regression` + honest `edge_cost_measured` | PLAN_04/05 | ✅ DONE (`test_anvil_*.py` 210) |
| 0b | Egress/approval gate around the ClipMind cloud planner (deny-by-default, exit 3) | PLAN_02 | ✅ DONE (video-agent 142) |
| 0c | Gate-component lockout — refuses bundles targeting the oracle, at gate + promote | PLAN_04 | ✅ DONE (3 tests) |
| 0d | Station Inbox-as-default + maker/checker confirm path in the GUI | PLAN_03 | ✅ DONE (Rust 81) |
| 0e | `new_plans/INDEX.md` + ClipMind README doc-map fix | docs | ✅ DONE (links resolve) |
| 0f | Deterministic stubbed-gateway teacher-loop test (the only red, resolved) | PLAN_04 | ✅ DONE (e2e 1 pass/1 skip) |

**Tier 1 — feature MVP (the original fastest path):**

| Rank | Item | Plan | Effort | Closes |
|---|---|---|---|---|
| 1 | Render `music_duck` via sidechaincompress (PLAN_02 §4) | PLAN_02 | ~30 LOC | PLAN_02 §4.1, §5.1 |
| 2 | Render `broll` via overlay path with `source` field (PLAN_02 §4) | PLAN_02 | ~50 LOC | PLAN_02 §4.1, §5.1 |
| 3 | Add `interview_to_article` and `livestream_vod_to_chapters` intent templates (PLAN_02 §5.3) | PLAN_02 | ~80 LOC | PLAN_02 §5.3 |
| 4 | Implement `git_push` + `open_pr` tools (PLAN_01 §2.2.6) | PLAN_01 | ~120 LOC | PLAN_01 §2.2.6, §7 Phase 1 |
| 5 | Wire `@` file-fuzzy, `Ctrl+R` history search, `Ctrl+L` clear, `Ctrl+G` external editor, `Double-Esc` edit-previous (PLAN_01 §5.1) | PLAN_01 | ~200 LOC | PLAN_01 §5.1, §1.1 |
| 6 | Add the missing 9 LSP tools (PLAN_01 §2.2.3) | PLAN_01 | ~600 LOC | PLAN_01 §2.2.3, §7 Phase 1 |
| 7 | Add `Ask-why` to the pending-hunk toolbar (PLAN_03 §9) | PLAN_03 | ~30 LOC | PLAN_03 §9 |
| 8 | Build the Merge gate view with checklist (PLAN_03 §9, R13) | PLAN_03 | ~250 LOC | PLAN_03 §9 |
| 9 | Add the 6 missing reference targets to the registry (PLAN_05 §2) | PLAN_05 | ~30 LOC | PLAN_05 §2 |
| 10 | Promote a Channel C-cheap bundle via `anvil teacher run --emit-harness-fix` (PLAN_05 §4) | PLAN_05/04 | ops | PLAN_05 §4, PLAN_04 §5.2 |

---

*End of remaining-work checklist. Each box references the plan line that defines it and the file:line target for the implementation. Closing gates are the milestones a plan reader would mark as "done."*

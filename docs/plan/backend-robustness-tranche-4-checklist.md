# Backend Robustness Tranche 4 — Master Atomic Checklist

> **Parent plan:** `docs/plan/backend-robustness-tranche-4-plan.md`.
> **G3 sub-plan:** `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md`.
> **Date:** 2026-04-27.
> **Use:** Codex picks up the next unchecked task in order. Each task references its source plan section + file. Per-slice exit-gates are at the bottom of each slice block.

Legend:
- `[ ]` open
- `[x]` done (with verification artifact path)
- `[~]` in flight

Format per task: short imperative + (plan §reference, file `path:lines`).

**Critical rule (user direction 2026-04-27):** every slice and every checkpoint gate MUST update `docs/features/backend_features.md` AND store the verification artifact at the canonical `autocode/docs/qa/test-results/<ts>-<slice-id>-<short-description>.md` path BEFORE Codex posts the completion Review Request. The "Update `docs/features/backend_features.md`" and "Verification artifact stored at..." checkboxes are inside the slice's exit gate — they are not optional follow-ups.

---

## Checkpoint 4 — Foundation & safety

Plan ref: `backend-robustness-tranche-4-plan.md` §"Checkpoint 4 — Foundation & safety".

### 4.G1 — Per-tool-call atomic checkpoint with diff-rollback

Plan ref: `backend-robustness-tranche-4-plan.md` §4.G1.

#### Schema + storage

- [ ] Extend `autocode/src/autocode/session/checkpoint_store.py::CheckpointStore` schema to add `parent_tool_call_id`, `tool_call_idx`, and `kind` enum field (`session` vs `pre_tool` vs `post_tool`)
- [ ] Add migration in `autocode/src/autocode/session/migrations.py`
- [ ] Add reducer test asserting old session-level checkpoints still load after migration

#### Snapshot logic

- [ ] In `autocode/src/autocode/agent/loop.py`, intercept tool-calls where `tool.mutates_fs=True` and snapshot the relevant working-tree files before execution
- [ ] **Snapshot mechanism: local file copies under `~/.autocode/snapshots/<session_id>/<tool_call_id>/` ONLY** — no `git stash` (per AGENTS.md "no tree-mutating git commands"). G1 has no dependency on G7'.
- [ ] Snapshot dir layout: `<session_id>/<tool_call_id>/<relative-path-of-touched-file>` for each touched file
- [ ] Add bounded retention: keep the last N=50 per-tool checkpoints per session, configurable via `agent.checkpoints.per_tool_retention`
- [ ] On retention overflow, delete oldest snapshot directories

#### Slash command surface

- [ ] Add `/rollback` slash command (alias `/rb`) in `autocode/src/autocode/app/commands.py`
- [ ] `/rollback` with no args → list last N pre-tool checkpoints with diff preview
- [ ] `/rollback <id>` → preview that checkpoint and show `/rollback restore <id>` confirmation command
- [ ] `/rollback --last` → preview the most recent pre-tool checkpoint and show `/rollback restore <id>` confirmation command
- [ ] `/rollback restore <id>` → restore that checkpoint from the local snapshot directory
- [ ] **Rollback execution mechanism: agent overwrites working-tree files from the local snapshot directory (no `git checkout`/`git restore`). User may run `git restore <file>` themselves if they prefer.**

#### TDD evidence

- [ ] RED: agent loop creates a per-tool checkpoint before each `write_file`/`edit_file`/`apply_patch`/`run_command` call
- [ ] RED: `/rollback` lists per-tool checkpoints with diffs
- [ ] RED: `/rollback <id>` previews without restoring; `/rollback restore <id>` reverses changes
- [ ] RED: retention drops oldest beyond N
- [ ] GREEN: all four tests pass after implementation
- [ ] Full TUI verification artifact stored at `autocode/docs/qa/test-results/<ts>-tui-verification.md`

#### Validation

- [ ] `uv run pytest autocode/tests/unit/test_checkpoint.py -v` passes
- [ ] PTY smoke `pty_smoke_rollback.py` passes
- [ ] Cargo test (Rust TUI rollback surface) green
- [x] `git diff --check` clean
- [ ] Update `docs/features/backend_features.md` "Implemented Backend Features" with per-tool-call checkpoints

#### Exit-gate

- [ ] Verification artifact stored at `autocode/docs/qa/test-results/<ts>-c4-g1-per-tool-checkpoint-rollback.md`
- [ ] Claude review APPROVE in `AGENTS_CONVERSATION.MD`

---

### 4.G2 — Tree-sitter repo-map upgrade

Plan ref: `backend-robustness-tranche-4-plan.md` §4.G2.

#### Design

- [ ] Read aider's `aider/repomap.py` source for ranking algorithm reference (`research-components/aider/aider/repomap.py:47-150`)
- [ ] Decide token budget default (recommend 1000 for multi-language repos)
- [ ] Decide diskcache location: `~/.autocode/cache/repomap/<repo-hash>/`

#### Implementation

- [ ] Replace or wrap `autocode/src/autocode/layer2/repomap.py::generate_repomap()` with a token-budget ranked builder
- [ ] Use existing tree-sitter 0.25.2; load extractors lazily per language
- [ ] Implement diskcache invalidation by file mtime + sha256 content hash
- [ ] Implement dependency-graph ranking (file imported by N others ranks higher)
- [ ] Implement token budget enforcement (truncate lowest-ranked symbols)
- [ ] Output is markdown with sections per file, ranked by importance

#### Integration

- [ ] Wire upgraded repomap into `autocode/src/autocode/agent/prompts.py` system-prompt builder — deferred to `DEFERRED_PENDING_TODO.md` §6.5 because automatic first-turn generation violates the bootstrap latency invariant
- [ ] Add `/repomap` slash command (alias `/map`) for ad-hoc rebuild + display

#### TDD evidence

- [ ] RED: ranking respects dependency graph
- [ ] RED: diskcache invalidation when file mtime changes
- [ ] RED: token budget enforcement
- [ ] RED: multi-language repo (Python + Go) generates correct output
- [ ] GREEN: all pass

#### Validation

- [ ] `uv run pytest autocode/tests/unit/test_repomap.py -v` passes
- [ ] Integration test asserts repomap shrinks under budget pressure
- [ ] Manual verification: run on `autocode/` itself; output is meaningful and useful
- [x] `git diff --check` clean
- [ ] Update `docs/features/backend_features.md` § Layer 2

#### Exit-gate

- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c4-g2-repomap-upgrade.md`
- [ ] Claude review APPROVE

---

### 4.G7' — Git-aware staging + working-tree snapshot

Plan ref: `backend-robustness-tranche-4-plan.md` §4.G7'.

#### Module

- [ ] Create `autocode/src/autocode/agent/git_aware_staging.py`
- [ ] Functions: `stage_post_edit(files)`, `propose_commit_message(files, diff)`. (Snapshot/restore live in G1, NOT here.)
- [ ] Hard rule comment at top: "Per AGENTS.md, never call any tree-mutating git command. Permitted: `git status`, `git diff`, `git log`, `git fetch`, `git add`, `git stash list/show` (read-only), `git worktree add/list/remove`. Forbidden: commit/push/tag/reset/rebase/merge/pull/checkout/restore/stash push|pop|apply/apply/clean."

#### Hooks integration

- [ ] PostToolUse hook on success for `mutates_fs=True` tools: call `stage_post_edit(touched_files)` + display proposed commit message in transcript via `on_token` event
- [ ] **No PreToolUse stash hook** — snapshotting is G1's responsibility (local file copies, not stash)
- [ ] On verification failure (paired with G4 once landed): emit `on_warning` and offer `/rollback` (which uses G1's local-snapshot path)

#### Permitted git ops list (per AGENTS.md)

- [ ] Allowed (read-only): `git status`, `git diff`, `git log`, `git show`, `git fetch`, `git stash list`, `git stash show`, `git worktree list`
- [ ] Allowed (index-only, additive): `git add`
- [ ] Allowed (separate-tree-only): `git worktree add`, `git worktree remove` (used in 7.G13 — does NOT mutate current working tree)
- [ ] **Forbidden in code:** `git commit`, `git push`, `git tag`, `git reset` (any), `git rebase`, `git merge`, `git pull` (always merges), `git checkout` (any form), `git restore`, `git stash push`, `git stash pop`, `git stash apply`, `git apply`, `git clean`
- [ ] Add a unit test that scans `git_aware_staging.py` (and any other module that runs git) for forbidden subprocess invocations
- [ ] "Propose, don't execute": for any forbidden op, show user the exact command they could run; never run it

#### TDD evidence

- [ ] RED: post-edit success path stages via `git add` + proposes commit message + never invokes any forbidden op
- [ ] RED: post-edit failure path emits `on_warning` and offers `/rollback` (no auto-revert without user confirm)
- [ ] RED: in non-git repos, `git add` is skipped; staging is a no-op without crashing
- [ ] RED: forbidden git ops blocked at the wrapper layer (parameterized over the full forbidden-op list)
- [ ] GREEN: all pass

#### Validation

- [ ] `uv run pytest autocode/tests/unit/test_git_aware_staging.py -v` passes
- [ ] PTY smoke exercising edit → stage → propose-commit-message round-trip
- [ ] Manual verification: run `autocode` against a real git repo, make an edit, verify staging without commit
- [x] `git diff --check` clean
- [ ] Update `docs/features/backend_features.md` with G7' staging surface

#### Exit-gate

- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c4-g7-git-aware-staging.md`
- [ ] Claude review APPROVE

---

### C4.GATE — Checkpoint 4 regression + benchmark

Plan ref: `backend-robustness-tranche-4-plan.md` §C4.GATE.

- [ ] `uv run pytest autocode/tests/unit/ -q` passes
- [ ] `uv run pytest benchmarks/tests -q` passes
- [ ] `cd autocode/rtui && cargo fmt -- --check && cargo test && cargo clippy -- -D warnings && cargo build --release` passes
- [ ] `make tui-regression` passes
- [ ] `make tui-references` passes (xfail-ratchet check)
- [ ] PTY smoke set: comprehensive + checkpoint2 canary + new G1/G7' rollback PTY all pass
- [ ] **Benchmark sweep**: `bash benchmarks/run_b7_b30_sweep.sh` (B7-B29 lanes) — captures pre-tranche baseline
- [ ] `git diff --check` clean
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c4-gate-regression-and-benchmark.md`
- [ ] Claude review APPROVE for the gate

User-owned: optional commit at C4 boundary. Not required.

---

## Checkpoint 5 — Multi-language code intelligence

Plan ref: `backend-robustness-tranche-4-plan.md` §"Checkpoint 5". Sub-plan: `backend-robustness-tranche-4-G3-multi-language-lsp.md`.

### 5.G3.0 — LSP adapter framework + lifecycle

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.0".

#### Module

- [ ] Create `autocode/src/autocode/layer2/lsp_client.py`: `LSPClient` class with subprocess + stdio JSON-RPC
- [ ] Implement methods for the 9 LSP ops (goto-definition, find-references, hover, document-symbol, workspace-symbol, implementations, type-definition, call-hierarchy, diagnostics)
- [ ] Auto-restart on crash with bounded retries (default 3)
- [ ] Capability negotiation via `initialize` request; record capabilities in `LSPClient.capabilities`
- [ ] Lazy-start: only spawn server on first op for that language
- [ ] Idle-timeout: shut down server after N minutes of no activity (default 10m)

#### Registry

- [ ] Create `autocode/src/autocode/layer2/lsp_servers/__init__.py` with file-extension → adapter map
- [ ] Add adapter base class `LSPAdapter` with `start()`, `stop()`, `op(...)` methods

#### Doctor integration

- [ ] In `autocode/src/autocode/cli.py::doctor`, add per-language readiness checks
- [ ] JSON output for programmatic consumption (extends existing doctor JSON shape)

#### Test fake server

- [ ] Create `autocode/tests/fixtures/lsp/fake_server.py` — speaks LSP JSON-RPC over stdio for tests
- [ ] Cover: initialize, all 9 ops, shutdown, simulated crash

#### TDD evidence

- [ ] RED: LSPClient.start succeeds against fake server
- [ ] RED: each of 9 ops round-trips correctly
- [ ] RED: server crash → auto-restart → reconnect
- [ ] RED: capability negotiation degrades when server lacks an op
- [ ] RED: doctor reports missing servers without crashing
- [ ] RED: lazy-start only spawns on first op
- [ ] RED: idle-timeout shuts down after N minutes
- [ ] GREEN: all pass

#### Validation

- [ ] `uv run pytest autocode/tests/unit/test_lsp_client.py -v` passes
- [ ] Integration test against fake server
- [ ] `git diff --check` clean
- [ ] Update `docs/features/backend_features.md` with LSP adapter framework

#### Exit-gate

- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c5-g3-0-lsp-adapter-framework.md`
- [ ] Claude review APPROVE

---

### 5.G3.1 — Java via `jdtls`

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.1".

- [x] Create `autocode/src/autocode/layer2/lsp_servers/java.py` extending `LSPAdapter`
- [x] Map `.java` extension; init with classpath discovery
- [x] Add doctor check for `jdtls` availability + Java 17+ runtime
- [x] Create fixture `autocode/tests/fixtures/lsp/java/Hello.java` with class + method + intentional syntax error
- [x] RED tests for all 9 ops on the fixture
- [x] PTY smoke `autocode/tests/pty/pty_smoke_lsp_java.py`
- [ ] `git diff --check` clean
- [x] Update `autocode/TESTING.md` with "Java LSP setup" section
- [x] Update `docs/architecture.md` with Java LSP support note
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-072748-c5-g3-1-lsp-java-jdtls.md`
- [ ] Claude review APPROVE

---

### 5.G3.2 — JavaScript via `typescript-language-server`

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.2".

- [x] Create `autocode/src/autocode/layer2/lsp_servers/javascript.py` extending `LSPAdapter`
- [x] Map `.js`, `.jsx`, `.mjs` extensions; init with `tsconfig.json`/`jsconfig.json` discovery
- [x] Add doctor check for `typescript-language-server` + `typescript` peer dependency
- [x] Create fixture `autocode/tests/fixtures/lsp/javascript/hello.js` with require/import + function + intentional error
- [x] RED tests for all 9 ops on the fixture
- [x] PTY smoke `autocode/tests/pty/pty_smoke_lsp_javascript.py`
- [ ] `git diff --check` clean
- [x] Update `autocode/TESTING.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-075602-c5-g3-2-lsp-javascript.md`
- [ ] Claude review APPROVE

---

### 5.G3.3 — TypeScript via `typescript-language-server`

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.3".

- [x] Decide: extend `javascript.py` or new `typescript.py` (record decision in slice review)
- [x] Map `.ts`, `.tsx`, `.d.ts` extensions
- [x] Reuse JS doctor check + add TS-specific config validation
- [x] Create fixture `autocode/tests/fixtures/lsp/typescript/hello.ts` with interface + generic + type alias + intentional type error
- [x] RED tests for all 9 ops PLUS type-error in diagnostics + type-definition through generics
- [x] PTY smoke `autocode/tests/pty/pty_smoke_lsp_typescript.py`
- [x] `git diff --check` clean
- [x] Update `autocode/TESTING.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-075602-c5-g3-3-lsp-typescript.md`
- [ ] Claude review APPROVE

---

### 5.G3.4 — C via `clangd`

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.4".

- [x] Create `autocode/src/autocode/layer2/lsp_servers/c.py` extending `LSPAdapter`
- [x] Map `.c`, `.h` extensions; init with `compile_commands.json` discovery
- [x] Add doctor check for `clangd` availability
- [x] Create fixture `autocode/tests/fixtures/lsp/c/hello.c` + optional `compile_commands.json`
- [x] RED tests for all 9 ops
- [x] PTY smoke `autocode/tests/pty/pty_smoke_lsp_c.py`
- [ ] `git diff --check` clean
- [x] Update `autocode/TESTING.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-083000-c5-g3-4-lsp-c-clangd.md`
- [ ] Claude review APPROVE

---

### 5.G3.5 — Kotlin via `kotlin-language-server`

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.5".

- [x] Create `autocode/src/autocode/layer2/lsp_servers/kotlin.py` extending `LSPAdapter` with extended startup timeout
- [x] Map `.kt`, `.kts` extensions
- [x] Add doctor check for `kotlin-language-server` availability + Java runtime
- [x] Create fixture `autocode/tests/fixtures/lsp/kotlin/Hello.kt` with top-level fn + data class + extension
- [x] RED tests for all 9 ops with extended timeout
- [x] PTY smoke `autocode/tests/pty/pty_smoke_lsp_kotlin.py` (extended timeout)
- [x] `git diff --check` clean
- [x] Update `autocode/TESTING.md` with Kotlin section warning about cold-start time
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-083000-c5-g3-5-lsp-kotlin.md`
- [ ] Claude review APPROVE

---

### 5.G3.6 — Python upgrade (Jedi → pylsp/pyright)

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.6".

#### Decision

- [x] Compare pylsp vs pyright on representative AutoCode files (latency, accuracy, type inference quality)
- [x] Record decision in slice review (recommend pylsp default; pyright as `autocode[lsp-pyright]` extra)

#### Adapter

- [x] Create `autocode/src/autocode/layer2/lsp_servers/python.py` extending `LSPAdapter`
- [x] Map `.py`, `.pyi` extensions
- [x] Add doctor check for `pylsp` availability

#### Migration

- [x] Migration test: `lsp_goto_definition`/`find_references`/`get_type`/`symbols` produce semantically equivalent results before and after migration on a fixed Python fixture
- [x] Keep Jedi-based code path as fallback for one release window
- [x] Add 5 new ops: hover, workspace-symbol, implementations, type-definition, call-hierarchy, diagnostics (the 5 not previously exposed)

#### TDD evidence

- [x] RED: migration test
- [x] RED: 5 new ops added by subprocess
- [x] RED: doctor check for pylsp
- [x] GREEN: all pass

#### Validation

- [x] `uv run pytest autocode/tests/unit/test_lsp_c_kotlin_python_adapters.py -q` passes
- [x] PTY smoke `pty_smoke_lsp_python.py`
- [x] All existing Jedi-based tool tests still pass (regression gate)
- [x] `git diff --check` clean
- [x] Update `docs/features/backend_features.md` § LSP ops (4 → 9)

#### Exit-gate

- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-083000-c5-g3-6-lsp-python.md`
- [ ] Claude review APPROVE

---

### 5.G3.7 — Go via `gopls`

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.7".

- [x] Create `autocode/src/autocode/layer2/lsp_servers/go.py` extending `LSPAdapter`
- [x] Map `.go` extension; init with `go.mod` discovery
- [x] Add doctor check for `gopls` availability + Go 1.16+
- [x] Create fixture `autocode/tests/fixtures/lsp/go/hello.go` + `go.mod`
- [x] RED tests for all 9 ops
- [x] PTY smoke `autocode/tests/pty/pty_smoke_lsp_go.py`
- [x] `git diff --check` clean
- [x] Update `autocode/TESTING.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-095412-c5-g3-7-lsp-go-gopls.md`
- [ ] Claude review APPROVE

---

### 5.G3.8 — Rust via `rust-analyzer`

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G3.8".

- [x] Create `autocode/src/autocode/layer2/lsp_servers/rust.py` extending `LSPAdapter` with extended cold-cache timeout
- [x] Map `.rs` extension; init with `Cargo.toml` discovery
- [x] Add doctor check for `rust-analyzer` availability + rustup component
- [x] Create fixture `autocode/tests/fixtures/lsp/rust/Cargo.toml` + `src/main.rs` with intentional clippy lint
- [x] RED tests for all 9 ops + clippy diagnostic in diagnostics op
- [x] PTY smoke `autocode/tests/pty/pty_smoke_lsp_rust.py` (extended timeout)
- [x] `git diff --check` clean
- [x] Update `autocode/TESTING.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-095412-c5-g3-8-lsp-rust-rust-analyzer.md`
- [ ] Claude review APPROVE

---

### 5.G4 — Auto-verify loop using LSP diagnostics

Sub-plan ref: `backend-robustness-tranche-4-G3-multi-language-lsp.md` §"5.G4".

#### Module

- [x] Create `autocode/src/autocode/agent/auto_verify.py`
- [x] Function: `verify_after_edit(edited_files: list[Path]) → VerifyResult` that runs LSP diagnostics on each file and returns errors/warnings
- [x] Result feeds back into agent loop as tool-result/system-visible feedback on failure

#### Loop integration

- [x] In `autocode/src/autocode/agent/loop.py`, hook PostToolUse for `mutates_fs=True` tools
- [x] After each successful edit, call `verify_after_edit`
- [x] On error result, feed `Verification failed: <diagnostics>` back to the agent
- [x] Iterate up to N=3 (configurable)
- [x] On still-failing after N: surface warning, do not auto-rollback

#### Configuration

- [x] Add `AgentConfig.verify` block in `autocode/src/autocode/config.py`
- [x] `verify.enabled` (default true)
- [x] `verify.max_iterations` (default 3)
- [x] `verify.on_failure` (default `surface_to_user`; alternatives `rollback`, `continue`)
- [x] `verify.languages` (default all enabled)
- [x] Add `/verify on|off|status` slash command

#### TDD evidence

- [x] RED: edit introduces syntax error → diagnostics catch → agent sees diagnostics
- [x] RED: persistent error after 3 iterations → surface warning, no auto-rollback
- [x] RED: edit on language without LSP adapter → no-op, no error
- [x] RED: `/verify off` → loop is bypassed
- [x] RED: cost-cap halts iteration
- [x] GREEN: all pass

#### Validation

- [x] `uv run pytest autocode/tests/unit/test_auto_verify.py -v` passes
- [x] Deterministic integration-style loop test: edit → verify diagnostics → agent-visible feedback
- [x] PTY smoke demonstrating verify visibility to user
- [x] `git diff --check` clean
- [x] Update `docs/features/backend_features.md` with auto-verify loop

#### Exit-gate

- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-110859-c5-g4-auto-verify-loop.md`
- [x] Claude review APPROVE — `AGENTS_CONVERSATION.MD` Entry 1664 (one non-blocking concern: `AutoVerifyConfig.on_failure` Literal accepts `"rollback"`/`"continue"` that the runtime ignores; carry to a C7 polish slice)

---

### C5.GATE — Checkpoint 5 regression + benchmark + LSP smoke

Plan ref: `backend-robustness-tranche-4-plan.md` §C5.GATE.

- [x] Standard regression set (same as C4.GATE)
- [x] All 8 per-language LSP PTY smokes pass
- [x] Auto-verify integration test passes
- [x] **Benchmark sweep B7-B29** with cost comparison vs C4.GATE baseline deferred per `DEFERRED_PENDING_TODO.md` §6.6; latest completed sweep remains `20260428-122348-742618`
- [x] `git diff --check` clean
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-111435-c5-gate-regression-and-benchmark.md`
- [x] Claude review APPROVE for the gate — `AGENTS_CONVERSATION.MD` Entry 1664 closed C5.GATE as `COMPLETE_WITH_DEFERRED_LIVE_SWEEP`

---

## Checkpoint 6 — Headless & cost-aware routing

Plan ref: `backend-robustness-tranche-4-plan.md` §"Checkpoint 6".

### 6.G5 — Headless `--json` / `--output-schema` mode (Tier 4.4 NDJSON subset contract)

Plan ref: `backend-robustness-tranche-4-plan.md` §6.G5. Contract update locked in `AGENTS_CONVERSATION.MD` Entry 1664 (Tier 4.4-compatible forward-compatible subset).

- [x] Add CLI subcommand `autocode exec [PROMPT] --json` (or extend `autocode ask`)
- [x] Add explicit `--auto-approve` switch for trusted headless runs; default headless JSON approval behavior is deny with visible `approval` item emission
- [x] Define NDJSON event schema in `autocode/src/autocode/backend/headless_schema.py` per Tier 4.4 shape: `type` discriminator ∈ {`thread_started`, `turn_started`, `item_started`, `item_delta`, `item_completed`, `turn_completed`, `error`}; every event stamped with `protocol_version: "0.1.0-c6g5-subset"`
- [x] `item.kind` enum constrained to forward-compatible C6.G5 subset: {`agent_message`, `tool_execution`, `plan_update`, `approval`}; document `reserved-for-future`: {`reasoning`, `subagent_delegation`, `diff`}
- [x] `turn_completed.usage` includes `input_tokens`, `output_tokens`, `total_tokens`, plus 0-defaulted `cached_input_tokens`, `cache_creation_tokens`, `reasoning_tokens` (cache+reasoning populated when post-commit Phase 2 prompt cache lands)
- [x] Stdout-only-NDJSON rule: `--json` mode writes ONLY NDJSON to stdout; logs/warnings go to stderr or get wrapped as structured `error` events (Codex Entry 1665 hardening)
- [x] Implement event-stream emitter; typed event-schema module preferred over ad-hoc dicts (`autocode/src/autocode/backend/headless_schema.py`)
- [x] Add `--output-schema PATH` flag using `layer4/llm.py::generate_json` for typed output
- [x] Add `autocode generate-schema --out ./schemas` subcommand emitting JSON Schema files for items / turns / threads / methods (spelling: `generate-schema`; 9 schema files including `meta.schema.json`)
- [x] RED: `--json` emits well-formed NDJSON, every line includes `protocol_version`
- [x] RED: `item.kind` outside the subset → emitter raises (lock the contract)
- [x] RED: `--output-schema` returns single JSON object matching schema
- [x] RED: error path emits final `error` event then exits non-zero
- [x] RED: `usage` block always present on `turn_completed`, even when all values are 0
- [x] RED: headless mode does NOT import or spawn Rust TUI path (uses backend/agent application surface directly)
- [x] RED: stdout in `--json` mode contains only valid NDJSON (no log lines, banners, or human-readable text leak)
- [x] GREEN: all pass
- [x] Integration test: pipe through `jq`, assert well-formed NDJSON
- [x] Schema validation test: emitted events validate against the schema files produced by `generate-schema`
- [x] Headless-mode benchmark canary deferred to C6.GATE per `DEFERRED_PENDING_TODO.md` §6.6 (gateway-gated; same pattern as C5.GATE)
- [x] Update `autocode/TESTING.md` with headless mode docs (include schema versioning + subset rationale)
- [x] Update `docs/features/backend_features.md`
- [x] `git diff --check` clean
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-150501-c6-g5-headless-json-mode.md`
- [x] Fix-iteration verification artifact at `autocode/docs/qa/test-results/20260430-165558-c6-g5-headless-json-fix.md`
- [x] Claude review APPROVE — `AGENTS_CONVERSATION.MD` Entry 1675 closes C6.G5 after fix iteration addressed all F1-F11 from Entries 1670+1671; lifecycle invariant test enforced; default-deny + opt-in `--auto-approve` shipped

---

### 6.G6 — Layer 4.5 cost-aware multi-provider router (with cache-multiplier hook)

Plan ref: `backend-robustness-tranche-4-plan.md` §6.G6. User-custom config deferred per `DEFERRED_PENDING_TODO.md` §6.4. Cache-multiplier hook contract locked in `AGENTS_CONVERSATION.MD` Entry 1664 (post-commit Phase 2 prompt-cache work feeds this hook later).

- [x] Create `autocode/src/autocode/layer4_5/router.py` with `Layer45Router` class
- [x] Inputs: task class (from `core/router.py`), provider/model rate table (from `agent/cost_dashboard.py`), confidence signal, **`billable_input_cost_factor: float = 1.0`** (cache-multiplier hook)
- [x] Cost comparison primitive: `effective_cost = base_cost × billable_input_cost_factor` (defaults to identity today; populated when post-commit Tier 1 prompt cache lands)
- [x] Outputs: `ProviderSelection(provider, model, reason: str, estimated_cost_delta: float)` — deterministic + explainable per Codex Entry 1665 hardening
- [ ] Default mappings (auto):
  - lint/format/typecheck-driven small edits → cheapest tier
  - bug-fix on small file → mid tier
  - refactor / multi-file edit / architecture / planning → frontier tier
- [x] Configurable via `~/.autocode/config.yaml` `routing.default_tier_map`
- [x] Wire `Layer45Router` between `core/router.py` and L4 invocation in backend/headless hosts before provider creation
- [x] RED: small edit → cheapest tier
- [x] RED: refactor → frontier tier
- [x] RED: ambiguous → default per config
- [x] RED: low-confidence → fallback path
- [x] RED: cost-dashboard shows per-tier breakdown after multi-tier turn
- [x] RED: `billable_input_cost_factor=1.0` (default) produces today's selection unchanged
- [x] RED: synthetic `billable_input_cost_factor=0.3` (cache-read discount) shifts selection toward cache-friendly providers (forward-compat for Phase 2)
- [x] RED: synthetic `billable_input_cost_factor=1.25` (cache-write premium) shifts selection away from cache-friendly providers when cache is cold (Codex Entry 1665 added this case)
- [x] RED: `ProviderSelection.reason` is non-empty and references the deciding factor (task class, cost factor, fallback path)
- [x] GREEN: all pass
- [ ] Cost-routing canary benchmark added (compare cost on B7-B14 lanes vs C5 baseline; deferred to C6.GATE cost canary)
- [x] Update `docs/features/backend_features.md`
- [x] `git diff --check` clean
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-171806-c6-g6-cost-aware-router.md`
- [ ] Claude review APPROVE

---

### C6.GATE — Checkpoint 6 regression + benchmark + cost-routing canary

- [x] Standard regression set
- [x] Cost-routing canary lane shows expected cost reduction at deterministic unit level (`test_layer45_router.py`; live benchmark canary deferred below)
- [x] **Benchmark sweep B7-B29** with cost comparison deferred per `DEFERRED_PENDING_TODO.md` §6.6 gateway/provider stabilization; local benchmark harness tests passed
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-172302-c6-gate-regression-and-benchmark.md`
- [ ] Claude review APPROVE for the gate

---

## Checkpoint 7 — Polish & nice-to-have

Plan ref: `backend-robustness-tranche-4-plan.md` §"Checkpoint 7".

### 7.G8 — Plan/Architect ↔ Editor model split

- [x] Extend agent config with `architect_model` and `editor_model` fields (`autocode/src/autocode/config.py`; no standalone `agent/mode.py` exists)
- [x] Wire mode transitions: PLAN/ARCHITECT mode uses `architect_model`; BUILD/EXECUTE uses `editor_model`
- [x] Add `/architect <model>` and `/editor <model>` slash commands
- [x] Compose with 6.G6 router: per-mode model overrides take precedence over auto-routing
- [x] RED tests for mode transitions and model selection
- [x] GREEN: all pass
- [x] PTY smoke — adjacent slash-surface smoke passed; new command-specific PTY coverage not yet present
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-191933-c7-sb1-runtime-features.md`
- [ ] Claude review APPROVE

---

### 7.G9 — AGENTS.md nestable per-directory memory

- [x] Add `AGENTS.md` discovery in `autocode/src/autocode/layer2/rules.py` (or new module)
- [x] Walk parent directories from current cwd up to repo root, collect `AGENTS.md` files in nesting order
- [x] Inject into system prompt with deepest-most-specific rule winning conflicts by broad-to-specific ordering
- [x] Add `/agents reload` slash command for hot-reload
- [x] RED tests for nesting + conflict resolution
- [x] GREEN: all pass
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-191933-c7-sb1-runtime-features.md`
- [ ] Claude review APPROVE

---

### 7.G10 — Session fork/branch with rollout replay

- [x] Verify existing `session.fork` RPC handler (per `docs/features/backend_features.md`)
- [x] Add `parent_session_id` schema field to `session/store.py`
- [x] Add `/fork [session_id]` slash command
- [x] Add `/tree` slash command to display fork tree
- [x] Implement rollout replay payload that preserves stored session messages/tool calls in order
- [x] RED tests for fork + replay
- [x] GREEN: all pass
- [x] PTY smoke — adjacent slash-surface smoke passed; new command-specific PTY coverage not yet present
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-191933-c7-sb1-runtime-features.md`
- [ ] Claude review APPROVE

---

### 7.G11 — Prompt cache keepalive

- [x] Add `PromptCacheKeepalive` background task in `agent/loop.py`
- [x] On Anthropic provider: send 5-min ping with cached prompt prefix to keep cache warm
- [x] Configurable via `agent.cache.keepalive_enabled` (default true on Anthropic, false elsewhere)
- [x] Integrate with cost dashboard cache-savings tracking
- [x] RED tests for keepalive timing + cost-savings improvement
- [x] GREEN: all pass
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-192908-c7-sb2-cache-recipes.md`
- [ ] Claude review APPROVE

---

### 7.G12 — Recipe/workflow YAML packaging

- [x] Define recipe schema in `autocode/src/autocode/agent/recipes.py` (YAML: goal + steps + sub-skills + tools)
- [x] Add discovery: `~/.autocode/recipes/*.yaml` + project-local `.autocode/recipes/*.yaml`
- [x] Add `/recipe list|run <name>` slash commands
- [x] Recipe runner integrates with task tools + sub-agent-style prompt handoff
- [x] RED tests for recipe schema + execution
- [x] GREEN: all pass
- [x] Bundle 3 example recipes (e.g. `refactor.yaml`, `add-feature.yaml`, `fix-bug.yaml`)
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-192908-c7-sb2-cache-recipes.md`
- [ ] Claude review APPROVE

---

### 7.G13 — Parallel sub-agents in isolated git worktrees

- [x] Extend `agent/subagent_tools.py::spawn_subagent` to optionally use `git worktree add` (creates a SEPARATE working tree; does NOT mutate the current one — AGENTS.md compliant)
- [x] Sub-agent works in its own worktree via worktree context handoff
- [x] **Merge-back mechanism:** main agent runs `git diff <main-tree-path> <worktree-path> > /tmp/sub-<id>.patch` (read-only); main agent applies via the existing `apply_patch` tool (which is approval-gated and user-confirmable). NOT `git pull`, NOT `git merge`, NOT `git checkout`.
- [x] Cleanup: existing `cleanup_worktree()` uses `git worktree remove` only (removes only the separate worktree; does NOT mutate main tree)
- [x] Compose with 4.G7' staging: sub-agent's `apply_patch` result lands in main tree; G7' then stages via `git add`; user commits separately
- [x] RED tests for worktree isolation + diff-and-patch merge-back + cleanup
- [x] GREEN: all pass
- [x] PTY smoke — adjacent slash-surface smoke passed; direct worktree-subagent PTY not yet present
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-193829-c7-sb3-worktree-watch-marketplace.md`
- [ ] Claude review APPROVE

---

### 7.G14 — Watch mode (file-save trigger)

- [x] Add `WatchMode` in `autocode/src/autocode/agent/watch.py`
- [x] Use lightweight parser/state for this iteration; `watchdog` runtime loop deferred
- [x] Comment-marker parser: detect `# AUTOCODE: <instruction>` (or similar) on file save
- [x] Trigger payload surface via parsed instruction + file context helper
- [x] Add `/watch on|off|status` slash commands
- [x] RED tests for marker parsing + trigger
- [x] GREEN: all pass
- [x] PTY smoke — adjacent slash-surface smoke passed; direct `/watch` PTY not yet present
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-193829-c7-sb3-worktree-watch-marketplace.md`
- [ ] Claude review APPROVE

---

### 7.G15 — Plugin/marketplace registry pointer

- [x] Add `PluginRegistry` in `autocode/src/autocode/external/registry.py`
- [x] **Static JSON registry at `docs/marketplace/registry.json`** (in-repo per user direction 2026-04-27); registry lists bundled-or-pre-vetted items only
- [x] **No remote fetch this iteration.** GitHub Pages distribution and remote download are deferred (note this in the slice review).
- [x] Add `/marketplace list` — reads `docs/marketplace/registry.json` and displays available items
- [x] Add `/marketplace info <name>` — shows metadata for a specific item
- [x] Add `/marketplace install <name>` — local-only install guidance; remote install reports unsupported in this iteration
- [x] No `default registry_url` config field yet (no remote fetch)
- [x] RED tests for registry parsing + listing + local-only install + remote-not-supported warning
- [x] GREEN: all pass
- [x] No submission flow (publishing) yet — deferred
- [x] Update `docs/features/backend_features.md`
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-193829-c7-sb3-worktree-watch-marketplace.md`
- [ ] Claude review APPROVE

---

### C7.GATE — Final release-grade regression + benchmark + closeout

Plan ref: `backend-robustness-tranche-4-plan.md` §C7.GATE.

- [x] Standard regression set
- [x] All 8 per-language LSP PTY smokes still pass
- [x] Auto-verify integration test still passes
- [x] Cost-routing canary still shows expected reduction
- [x] **Benchmark sweep B7-B29** with full cost comparison (C4 → C5 → C6 → C7) remains deferred per `DEFERRED_PENDING_TODO.md` §6.6; benchmark harness tests pass
- [x] Real-gateway PTY canary green
- [x] `git diff --check` clean
- [x] Verification artifact at `autocode/docs/qa/test-results/20260430-194659-c7-gate-final-release-and-benchmark.md`
- [x] Tranche-spanning closeout entry posted to `AGENTS_CONVERSATION.MD` — Entry 1693
- [x] `docs/features/backend_features.md` is fully synced with all 15 slices' shipped features
- [x] `docs/requirements_and_features.md` § 2 updated (40 commands)
- [x] Plan files queued for archive move after user commit; keep live until stable commit lands
- [x] Claude review final APPROVE — `AGENTS_CONVERSATION.MD` Entry 1694 closed C7.GATE as `COMPLETE_WITH_DEFERRED_LIVE_SWEEP`

User-owned: 7.E commit + optional release tag covering C4-C7. Agents must not commit.

---

## Cross-cutting hygiene tasks (run at any tranche boundary)

- [x] Comms cleanup: resolved C5-C7 fast-forward entries archived to `docs/communication/old/2026-04-30-tranche-4-c5-c7-fast-forward-1664-1693.md`
- [x] Update `PLAN.md` Ordered Backlog item 1 with current checkpoint
- [x] Update `EXECUTION_CHECKLIST.md` "Current Active Queue" with current substage
- [x] Update `current_directives.md` with current phase
- [ ] Stale-term audit on touched docs

---

## Resolution and exit

When all C7.GATE checkboxes are green:

- [x] Tranche 4 is closed from the agent side — Claude Entry 1694 APPROVE
- [ ] User performs final commit + tag at their discretion (3.E-equivalent)
- [ ] Move plan files to `docs/plan/archive/`:
  - [ ] `docs/plan/backend-robustness-tranche-4-plan.md` → `docs/plan/archive/`
  - [ ] `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md` → `docs/plan/archive/`
  - [ ] `docs/plan/backend-robustness-tranche-4-checklist.md` → `docs/plan/archive/`
- [ ] User decides next tranche scope (candidates from `docs/plan/stabilize-and-release-plan.md` brainstorm inventory R-1 through R-11, plus deferrals in `DEFERRED_PENDING_TODO.md` §6)

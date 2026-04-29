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
- [ ] Claude review APPROVE

---

### C5.GATE — Checkpoint 5 regression + benchmark + LSP smoke

Plan ref: `backend-robustness-tranche-4-plan.md` §C5.GATE.

- [x] Standard regression set (same as C4.GATE)
- [x] All 8 per-language LSP PTY smokes pass
- [x] Auto-verify integration test passes
- [x] **Benchmark sweep B7-B29** with cost comparison vs C4.GATE baseline deferred per `DEFERRED_PENDING_TODO.md` §6.6; latest completed sweep remains `20260428-122348-742618`
- [x] `git diff --check` clean
- [x] Verification artifact at `autocode/docs/qa/test-results/20260429-111435-c5-gate-regression-and-benchmark.md`
- [ ] Claude review APPROVE for the gate

---

## Checkpoint 6 — Headless & cost-aware routing

Plan ref: `backend-robustness-tranche-4-plan.md` §"Checkpoint 6".

### 6.G5 — Headless `--json` / `--output-schema` mode

Plan ref: `backend-robustness-tranche-4-plan.md` §6.G5.

- [ ] Add CLI subcommand `autocode exec [PROMPT] --json` (or extend `autocode ask`)
- [ ] Define NDJSON event schema in `autocode/src/autocode/backend/schema.py` (events: `request_ack`, `status`, `token`, `thinking`, `tool_call`, `tool_result`, `cost_update`, `warning`, `error`, `done`)
- [ ] Implement event-stream emitter
- [ ] Add `--output-schema PATH` flag using `layer4/llm.py::generate_json` for typed output
- [ ] RED: `--json` emits well-formed NDJSON
- [ ] RED: `--output-schema` returns single JSON object matching schema
- [ ] RED: error path emits final `error` event then exits non-zero
- [ ] GREEN: all pass
- [ ] Integration test: pipe through `jq`, assert well-formed NDJSON
- [ ] Add headless-mode benchmark to canary
- [ ] Update `autocode/TESTING.md` with headless mode docs
- [ ] Update `docs/features/backend_features.md`
- [ ] `git diff --check` clean
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c6-g5-headless-json-mode.md`
- [ ] Claude review APPROVE

---

### 6.G6 — Layer 4.5 cost-aware multi-provider router

Plan ref: `backend-robustness-tranche-4-plan.md` §6.G6. User-custom config deferred per `DEFERRED_PENDING_TODO.md` §6.4.

- [ ] Create `autocode/src/autocode/layer4_5/router.py` with `Layer45Router` class
- [ ] Inputs: task class (from `core/router.py`), provider/model rate table (from `agent/cost_dashboard.py`), confidence signal
- [ ] Outputs: `ProviderSelection(provider, model)` with deterministic fallback
- [ ] Default mappings (auto):
  - lint/format/typecheck-driven small edits → cheapest tier
  - bug-fix on small file → mid tier
  - refactor / multi-file edit / architecture / planning → frontier tier
- [ ] Configurable via `~/.autocode/config.yaml` `routing.default_tier_map`
- [ ] Wire `Layer45Router` between `core/router.py` and L4 invocation in `agent/loop.py`
- [ ] RED: small edit → cheapest tier
- [ ] RED: refactor → frontier tier
- [ ] RED: ambiguous → default per config
- [ ] RED: low-confidence → fallback path
- [ ] RED: cost-dashboard shows per-tier breakdown after multi-tier turn
- [ ] GREEN: all pass
- [ ] Cost-routing canary benchmark added (compare cost on B7-B14 lanes vs C5 baseline; expect 20-40% reduction)
- [ ] Update `docs/features/backend_features.md`
- [ ] `git diff --check` clean
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c6-g6-cost-aware-router.md`
- [ ] Claude review APPROVE

---

### C6.GATE — Checkpoint 6 regression + benchmark + cost-routing canary

- [ ] Standard regression set
- [ ] Cost-routing canary lane shows expected cost reduction
- [ ] **Benchmark sweep B7-B29** with cost comparison
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c6-gate-regression-and-benchmark.md`
- [ ] Claude review APPROVE for the gate

---

## Checkpoint 7 — Polish & nice-to-have

Plan ref: `backend-robustness-tranche-4-plan.md` §"Checkpoint 7".

### 7.G8 — Plan/Architect ↔ Editor model split

- [ ] Extend `agent/mode.py` with `architect_model` and `editor_model` config fields
- [ ] Wire mode transitions: PLAN/ARCHITECT mode uses `architect_model`; BUILD/EXECUTE uses `editor_model`
- [ ] Add `/architect <model>` and `/editor <model>` slash commands
- [ ] Compose with 6.G6 router: per-mode model overrides take precedence over auto-routing
- [ ] RED tests for mode transitions and model selection
- [ ] GREEN: all pass
- [ ] PTY smoke
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g8-architect-editor-split.md`
- [ ] Claude review APPROVE

---

### 7.G9 — AGENTS.md nestable per-directory memory

- [ ] Add `AGENTS.md` discovery in `autocode/src/autocode/layer2/rules.py` (or new module)
- [ ] Walk parent directories from current cwd up to repo root, collect `AGENTS.md` files in nesting order
- [ ] Inject into system prompt with deepest-most-specific rule winning conflicts
- [ ] Add `/agents reload` slash command for hot-reload
- [ ] RED tests for nesting + conflict resolution
- [ ] GREEN: all pass
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g9-agents-md-nestable.md`
- [ ] Claude review APPROVE

---

### 7.G10 — Session fork/branch with rollout replay

- [ ] Verify existing `session.fork` RPC handler (per `docs/features/backend_features.md`)
- [ ] Add `parent_session_id` schema field to `session/store.py`
- [ ] Add `/fork [session_id]` slash command
- [ ] Add `/tree` slash command to display fork tree
- [ ] Implement rollout replay (re-run a session's tool calls in order, optionally with different model)
- [ ] RED tests for fork + replay
- [ ] GREEN: all pass
- [ ] PTY smoke
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g10-session-fork-branch.md`
- [ ] Claude review APPROVE

---

### 7.G11 — Prompt cache keepalive

- [ ] Add `PromptCacheKeepalive` background task in `agent/loop.py`
- [ ] On Anthropic provider: send 5-min ping with cached prompt prefix to keep cache warm
- [ ] Configurable via `agent.cache.keepalive_enabled` (default true on Anthropic, false elsewhere)
- [ ] Integrate with cost dashboard cache-savings tracking
- [ ] RED tests for keepalive timing + cost-savings improvement
- [ ] GREEN: all pass
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g11-prompt-cache-keepalive.md`
- [ ] Claude review APPROVE

---

### 7.G12 — Recipe/workflow YAML packaging

- [ ] Define recipe schema in `autocode/src/autocode/agent/recipes.py` (YAML: goal + steps + sub-skills + tools)
- [ ] Add discovery: `~/.autocode/recipes/*.yaml` + project-local `.autocode/recipes/*.yaml`
- [ ] Add `/recipe list|run <name>` slash commands
- [ ] Recipe runner integrates with task tools + sub-agents
- [ ] RED tests for recipe schema + execution
- [ ] GREEN: all pass
- [ ] Bundle 3 example recipes (e.g. `refactor.yaml`, `add-feature.yaml`, `fix-bug.yaml`)
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g12-recipes.md`
- [ ] Claude review APPROVE

---

### 7.G13 — Parallel sub-agents in isolated git worktrees

- [ ] Extend `agent/subagent_tools.py::spawn_subagent` to optionally use `git worktree add` (creates a SEPARATE working tree; does NOT mutate the current one — AGENTS.md compliant)
- [ ] Sub-agent works in its own worktree
- [ ] **Merge-back mechanism:** main agent runs `git diff <main-tree-path> <worktree-path> > /tmp/sub-<id>.patch` (read-only); main agent applies via the existing `apply_patch` tool (which is approval-gated and user-confirmable). NOT `git pull`, NOT `git merge`, NOT `git checkout`.
- [ ] Cleanup: `git worktree remove` on sub-agent completion (removes only the separate worktree; does NOT mutate main tree)
- [ ] Compose with 4.G7' staging: sub-agent's `apply_patch` result lands in main tree; G7' then stages via `git add`; user commits separately
- [ ] RED tests for worktree isolation + diff-and-patch merge-back + cleanup
- [ ] GREEN: all pass
- [ ] PTY smoke
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g13-worktree-subagents.md`
- [ ] Claude review APPROVE

---

### 7.G14 — Watch mode (file-save trigger)

- [ ] Add `WatchMode` in `autocode/src/autocode/agent/watch.py`
- [ ] Use `watchdog` Python library for cross-platform file watching
- [ ] Comment-marker parser: detect `# AUTOCODE: <instruction>` (or similar) on file save
- [ ] Trigger agent turn with the parsed instruction + file context
- [ ] Add `/watch on|off|status` slash commands
- [ ] RED tests for marker parsing + trigger
- [ ] GREEN: all pass
- [ ] PTY smoke
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g14-watch-mode.md`
- [ ] Claude review APPROVE

---

### 7.G15 — Plugin/marketplace registry pointer

- [ ] Add `PluginRegistry` in `autocode/src/autocode/external/registry.py`
- [ ] **Static JSON registry at `docs/marketplace/registry.json`** (in-repo per user direction 2026-04-27); registry lists bundled-or-pre-vetted items only
- [ ] **No remote fetch this iteration.** GitHub Pages distribution and remote download are deferred (note this in the slice review).
- [ ] Add `/marketplace list` — reads `docs/marketplace/registry.json` and displays available items
- [ ] Add `/marketplace info <name>` — shows metadata for a specific item
- [ ] Add `/marketplace install <name>` — **local-only install: copies bundled item from in-repo source to `~/.autocode/skills/<name>/` or `~/.autocode/recipes/<name>/`**. If the registry entry's source is not bundled in-repo, the command emits a clear "remote install not supported in this iteration" warning with a suggested manual install command.
- [ ] No `default registry_url` config field yet (no remote fetch)
- [ ] RED tests for registry parsing + listing + local-only install + remote-not-supported warning
- [ ] GREEN: all pass
- [ ] No submission flow (publishing) yet — file as forward-looking item in `DEFERRED_PENDING_TODO.md`
- [ ] Update `docs/features/backend_features.md`
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-g15-marketplace-registry.md`
- [ ] Claude review APPROVE

---

### C7.GATE — Final release-grade regression + benchmark + closeout

Plan ref: `backend-robustness-tranche-4-plan.md` §C7.GATE.

- [ ] Standard regression set
- [ ] All 8 per-language LSP PTY smokes still pass
- [ ] Auto-verify integration test still passes
- [ ] Cost-routing canary still shows expected reduction
- [ ] **Benchmark sweep B7-B29** with full cost comparison (C4 → C5 → C6 → C7)
- [ ] Real-gateway PTY canary green
- [ ] `git diff --check` clean
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c7-gate-final-release-and-benchmark.md`
- [ ] Tranche-spanning closeout entry posted to `AGENTS_CONVERSATION.MD`
- [ ] `docs/features/backend_features.md` is fully synced with all 15 slices' shipped features
- [ ] `docs/requirements_and_features.md` § 2 updated (38 tools → final count, etc.)
- [ ] Plan file `backend-robustness-tranche-4-plan.md` marked RESOLVED + queued for archive move
- [ ] Claude review final APPROVE

User-owned: 7.E commit + optional release tag covering C4-C7. Agents must not commit.

---

## Cross-cutting hygiene tasks (run at any tranche boundary)

- [ ] Comms cleanup: archive bilaterally-resolved entries, update `AGENTS_CONVERSATION.MD` archive comments
- [ ] Update `PLAN.md` Ordered Backlog item 1 with current checkpoint
- [ ] Update `EXECUTION_CHECKLIST.md` "Current Active Queue" with current substage
- [ ] Update `current_directives.md` with current phase
- [ ] Stale-term audit on touched docs

---

## Resolution and exit

When all C7.GATE checkboxes are green:

- [ ] Tranche 4 is closed from the agent side
- [ ] User performs final commit + tag at their discretion (3.E-equivalent)
- [ ] Move plan files to `docs/plan/archive/`:
  - [ ] `docs/plan/backend-robustness-tranche-4-plan.md` → `docs/plan/archive/`
  - [ ] `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md` → `docs/plan/archive/`
  - [ ] `docs/plan/backend-robustness-tranche-4-checklist.md` → `docs/plan/archive/`
- [ ] User decides next tranche scope (candidates from `docs/plan/stabilize-and-release-plan.md` brainstorm inventory R-1 through R-11, plus deferrals in `DEFERRED_PENDING_TODO.md` §6)

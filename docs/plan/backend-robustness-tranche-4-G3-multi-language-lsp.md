# Tranche 4 — G3 Multi-Language LSP (Sub-Plan)

> **Parent plan:** `docs/plan/backend-robustness-tranche-4-plan.md` § Checkpoint 5.
> **Master checklist:** `docs/plan/backend-robustness-tranche-4-checklist.md` §5.G3.
> **Date:** 2026-04-27.
> **Scope:** the multi-language LSP work for Checkpoint 5 of Tranche 4, broken into 9 sub-slices: 1 adapter framework + 8 per-language sub-slices. The auto-verify loop (G4) is documented in the parent plan and depends on this work landing first.

---

## Why this is its own sub-plan

Multi-language LSP is the largest single work item in Tranche 4. It splits cleanly into a foundation (adapter framework + lifecycle + doctor) and 8 per-language adapters, each a self-contained slice. Order is user-specified: **Java → JavaScript → TypeScript → C → Kotlin → Python → Go → Rust** (per user direction 2026-04-27).

Each sub-slice ships:
1. An adapter under `autocode/src/autocode/layer2/lsp_servers/<lang>.py`
2. The 9 LSP ops minimum (defined in §"LSP operation surface" below)
3. A doctor check for language server availability
4. A focused PTY smoke against a fixture file in that language
5. Documentation update in `autocode/TESTING.md` and `docs/architecture.md`
6. An entry added to the master checklist `§5.G3.<n>`

---

## Current state baseline (2026-04-27)

Per `docs/features/backend_features.md`:
- AutoCode has 4 of 9 LSP-style ops (`lsp_goto_definition`, `lsp_find_references`, `lsp_get_type`, `lsp_symbols`)
- These are Jedi-backed (Python only, in-process)
- No subprocess-based LSP server management
- No multi-language support

Tranche 4 G3 closes this gap with a **subprocess-based LSP client** that talks JSON-RPC over stdio to standard LSP servers (the same protocol Cursor, opencode, Continue, and Zed use).

---

## Operating cadence within G3

- Each per-language slice ships independently. Codex picks them in user-specified order.
- After 5.G3.0 (adapter framework) lands and is APPROVE'd, languages can ship serially or in parallel by Codex's choice (default: serial in user order).
- Each language slice can be reviewed and APPROVE'd before the next is started, or batched as Codex prefers.
- Auto-verify (5.G4) waits until at least 5.G3.0 + 5.G3.6 (Python upgrade) are landed; recommended to wait until at least 5 of 8 languages are done so verify is broadly useful.

---

## 5.G3.0 — LSP adapter framework + lifecycle

**Goal:** a single subprocess-based LSP client that any language adapter can register against. Doctor checks integrate.

### Surface

- New module `autocode/src/autocode/layer2/lsp_client.py`:
  - `class LSPClient` — owns a subprocess + stdio pipes + JSON-RPC framing
  - `class LSPServerConfig` — language id, executable path, init params, root URI
  - `LSPClient.start(config) → LSPClient instance`
  - `LSPClient.stop() / shutdown()`
  - Methods: `goto_definition`, `find_references`, `hover`, `document_symbol`, `workspace_symbol`, `implementations`, `type_definition`, `call_hierarchy`, `diagnostics`
  - Auto-restart on crash with backoff; bounded retries
  - Capability negotiation with `initialize` request; gracefully degrade if server doesn't support an op

- New module `autocode/src/autocode/layer2/lsp_servers/__init__.py`:
  - Registry of language → adapter mapping
  - File-extension → adapter resolution (e.g. `.go` → gopls adapter)

- Doctor integration in `autocode/src/autocode/cli.py` doctor command:
  - Per-language readiness checks (executable in PATH, version compatible, server starts within 2s)
  - JSON output for programmatic consumption

### TDD

- RED unit test: `LSPClient.start` against a fake LSP server (a Python fixture that speaks LSP JSON-RPC) succeeds.
- RED unit test: each of the 9 ops round-trips correctly against the fake server.
- RED unit test: server crash → auto-restart → reconnect within bounded retries.
- RED unit test: capability negotiation degrades gracefully when server lacks an op.
- RED unit test: doctor reports missing servers without crashing.

### Validation

- Focused unit tests in `autocode/tests/unit/test_lsp_client.py`.
- Integration test that spawns the fake server and exercises full lifecycle.
- No PTY smoke yet (waits for first real-language adapter to make assertions meaningful).

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-0-lsp-adapter-framework.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.0.

---

## 5.G3.1 — Java via `jdtls` (Eclipse JDT Language Server)

**Server:** `jdtls` (Eclipse JDT Language Server) — https://github.com/eclipse-jdtls/eclipse.jdt.ls
**Install path:** typically `/usr/local/share/jdtls/bin/jdtls` or `~/.local/share/jdtls/bin/jdtls`. Doctor check: `jdtls --version`.
**Notable quirks:** requires Java 17+ runtime; uses workspace data directory.

### Adapter

- New file `autocode/src/autocode/layer2/lsp_servers/java.py`.
- Maps `.java` extension to the jdtls adapter.
- Init params include classpath discovery via `pom.xml` / `build.gradle` if present.

### Fixture for testing

- New `autocode/tests/fixtures/lsp/java/Hello.java` — minimal class with **project-local** method definitions and references (e.g. `Hello.greet()` defined in same file, called from `Hello.main()`); a simple project-local interface + impl pair; an intentional syntax error for diagnostics.
- Determinism: NO assertions on `System.out.println` / `java.util.*` / JDK Javadoc — those depend on the user's JDK source availability. All assertions target fixture-internal symbols.
- All other languages follow the same rule: assertions target project-local symbols only.

### TDD per-op

**Determinism rule:** assertions target **project-local symbols defined in the fixture**, NOT JDK or external library symbols. Reason: JDK source / Javadoc availability varies across CI machines (some have `src.zip`, some don't); LSP servers differ on whether they index third-party sources by default. Project-local symbols always resolve.

- RED: goto-definition on a project-local method call (e.g. `Hello.greet()` defined in the fixture) returns the fixture file location.
- RED: find-references on `Hello.greet` finds all callers in the fixture.
- RED: hover on the `Hello` class returns Javadoc derived from the fixture's own `/** ... */` comment.
- RED: document-symbol returns class + method tree.
- RED: workspace-symbol finds `Hello` class.
- RED: implementations on a fixture-defined interface returns the fixture-defined implementing classes.
- RED: type-definition follows fixture-defined generics.
- RED: call-hierarchy shows fixture-internal callers.
- RED: diagnostics flags an intentional fixture-internal syntax error.

### Validation

- Focused unit tests via fake LSP server (where deterministic) and against real jdtls (smoke).
- PTY smoke `autocode/tests/pty/pty_smoke_lsp_java.py` exercising the 9 ops.
- Doctor check passes.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-1-lsp-java-jdtls.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.1.

---

## 5.G3.2 — JavaScript via `typescript-language-server`

**Server:** `typescript-language-server` (npm) — handles both JS and TS.
**Install path:** typically `npm install -g typescript-language-server typescript`. Doctor check: `typescript-language-server --version`.
**Notable quirks:** requires `typescript` peer dependency; uses `tsconfig.json` / `jsconfig.json` for project context.

### Adapter

- New file `autocode/src/autocode/layer2/lsp_servers/javascript.py`.
- Maps `.js`, `.jsx`, `.mjs` extensions.
- Init params: workspace root + `tsconfig.json` discovery.

### Fixture

- `autocode/tests/fixtures/lsp/javascript/hello.js` — a file with require/import, a function, references.

### TDD per-op

Same 9 RED tests as 5.G3.1, adapted for JavaScript semantics.

### Validation

- PTY smoke `autocode/tests/pty/pty_smoke_lsp_javascript.py`.
- Doctor check passes.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-2-lsp-javascript.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.2.

---

## 5.G3.3 — TypeScript via `typescript-language-server`

**Server:** same as 5.G3.2 (`typescript-language-server` handles both).
**Notable quirks:** TypeScript-specific: type-definition is meaningful (vs. JS where it's structural); diagnostics include type errors.

### Adapter

- Extend `autocode/src/autocode/layer2/lsp_servers/javascript.py` to also serve `.ts`, `.tsx`, `.d.ts`, OR
- New file `autocode/src/autocode/layer2/lsp_servers/typescript.py` that imports javascript adapter and adds TS-specific routing.
- Decision goes in the slice review.

### Fixture

- `autocode/tests/fixtures/lsp/typescript/hello.ts` — interface, generic function, type alias.

### TDD

Same 9 RED tests + extra: type errors in diagnostics, type-definition through generics.

### Validation

PTY smoke + doctor check.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-3-lsp-typescript.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.3.

---

## 5.G3.4 — C via `clangd`

**Server:** `clangd` — typically installed via system package (`apt install clangd` / `brew install llvm`). Doctor check: `clangd --version`.
**Notable quirks:** requires `compile_commands.json` for accurate diagnostics on multi-file projects; falls back to single-file mode.

### Adapter

- New file `autocode/src/autocode/layer2/lsp_servers/c.py`.
- Maps `.c`, `.h` extensions.
- Init params: workspace root + `compile_commands.json` discovery.

### Fixture

- `autocode/tests/fixtures/lsp/c/hello.c` — a function, includes, a struct, intentional warning for diagnostics.
- Optional `compile_commands.json` pointing at the fixture.

### TDD per-op

Same 9 RED tests.

### Validation

PTY smoke + doctor check.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-4-lsp-c-clangd.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.4.

---

## 5.G3.5 — Kotlin via `kotlin-language-server`

**Server:** `kotlin-language-server` — https://github.com/fwcd/kotlin-language-server
**Install path:** typically distributed as a tarball; doctor check: `kotlin-language-server --version`.
**Notable quirks:** slow startup (10-30s); large memory footprint; uses Gradle/Maven project resolution.

### Adapter

- New file `autocode/src/autocode/layer2/lsp_servers/kotlin.py`.
- Maps `.kt`, `.kts` extensions.

### Fixture

- `autocode/tests/fixtures/lsp/kotlin/Hello.kt` — top-level function, data class, extension function.

### TDD

Same 9 RED tests; tests need to allow longer startup timeout.

### Validation

PTY smoke (with extended timeout) + doctor check.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-5-lsp-kotlin.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.5.

---

## 5.G3.6 — Python upgrade (Jedi → pylsp or pyright)

**Why now:** the existing `lsp_*` tools are Jedi-backed and in-process. Migrating to subprocess-based pylsp / pyright unifies the LSP client surface across all languages and unlocks features Jedi doesn't have (e.g. workspace-wide symbol search, call hierarchy).

**Decision in the slice:** pylsp vs pyright.
- `pylsp` (Python LSP Server, community fork of `python-language-server`) — pure Python, easier to bundle as an optional extra.
- `pyright` — Microsoft's TypeScript-based Python type checker; faster, better type inference, but requires Node.js.
- **Recommendation in the slice review:** pylsp first (matches our Python-tool-chain norm); pyright as an optional extra (`autocode[lsp-pyright]`).

### Adapter

- New file `autocode/src/autocode/layer2/lsp_servers/python.py`.
- Maps `.py`, `.pyi` extensions.

### Migration path

- Existing `lsp_goto_definition` / `lsp_find_references` / `lsp_get_type` / `lsp_symbols` tools must continue to work the same way (semantic equivalence).
- New ops added: `hover`, `workspace-symbol`, `implementations`, `type-definition`, `call-hierarchy`, `diagnostics`.
- Add a migration test: same LSP ops produce equivalent results for a fixture file before and after the migration.

### Fixture

- Reuse existing Python fixtures from `autocode/tests/fixtures/`.

### TDD

- RED: migration test — Jedi result vs subprocess result on canonical fixture.
- RED: 5 new ops added by subprocess (the ones Jedi didn't expose).
- RED: doctor check for pylsp.

### Validation

- Focused unit tests + PTY smoke + doctor check.
- **Risk gate:** ensure the Jedi-based code path is still reachable as a fallback for the duration of one release; remove the fallback in a later slice.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-6-lsp-python.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.6.

---

## 5.G3.7 — Go via `gopls`

**Server:** `gopls` — official Go language server. Install: `go install golang.org/x/tools/gopls@latest`. Doctor check: `gopls version`.
**Notable quirks:** requires `go.mod` for module-aware operation; module-mode resolution is Go 1.16+.

### Adapter

- New file `autocode/src/autocode/layer2/lsp_servers/go.py`.
- Maps `.go` extension.

### Fixture

- `autocode/tests/fixtures/lsp/go/hello.go` + `go.mod` — package, function, interface, struct.

### TDD

Same 9 RED tests.

### Validation

PTY smoke + doctor check.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-7-lsp-go-gopls.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.7.

---

## 5.G3.8 — Rust via `rust-analyzer`

**Server:** `rust-analyzer` — official Rust language server. Install: `rustup component add rust-analyzer`. Doctor check: `rust-analyzer --version`.
**Notable quirks:** requires `Cargo.toml` for project context; sometimes slow on cold cache; has rich diagnostics.

### Adapter

- New file `autocode/src/autocode/layer2/lsp_servers/rust.py`.
- Maps `.rs` extension.

### Fixture

- `autocode/tests/fixtures/lsp/rust/Cargo.toml` + `src/main.rs` — function, struct, trait, impl, intentional clippy lint.

### TDD

Same 9 RED tests.

### Validation

PTY smoke (extended timeout for cold cache) + doctor check.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g3-8-lsp-rust-rust-analyzer.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G3.8.

---

## 5.G4 — Auto-verify loop using LSP diagnostics

**Position:** after 5.G3.0 + 5.G3.6 (or later, Codex's choice — but Python is the dogfood test).
**Per user direction 2026-04-27:** "always verify after each edit that code will compile use ide like intelligence for it" → use LSP `diagnostics` op.

### Surface

- Hook into `agent/loop.py` PostToolUse for `mutates_fs=True` tools (`write_file`, `edit_file`, `apply_patch`).
- After each successful edit, the verify loop:
  1. Identifies the language of the touched file (from extension)
  2. Runs the LSP diagnostics op via the appropriate adapter
  3. If diagnostics return errors (severity = Error), feeds them back to the agent as a system message: "Verification failed: <diagnostics>. Try again."
  4. The agent attempts a fix.
  5. Repeat up to N iterations (default N=3, configurable via `agent.verify.max_iterations`).
  6. If still failing after N: surface to the user via `on_warning`, halt without rolling back (G7' rollback is user-confirmable).

### Composability

- Pairs with 4.G7' git-aware staging: pre-edit stash, post-edit verify, on-failure offer rollback.
- Pairs with 4.G1 per-tool checkpoints: rollback target is the pre-edit checkpoint.
- Composes with 6.G6 cost-routing: verify-loop fixes can use a cheaper model (verify is L4 fallback).

### Configuration

- `agent.verify.enabled` (default: true)
- `agent.verify.max_iterations` (default: 3)
- `agent.verify.on_failure` (default: `surface_to_user`; alternatives: `rollback`, `continue`)
- `agent.verify.languages` (default: all enabled languages; can opt out per-language)

### TDD

- RED: edit introduces a syntax error → diagnostics catch it → agent fixes it → diagnostics clean → done.
- RED: edit introduces a syntax error that the agent cannot fix in 3 iterations → surface warning, do not auto-rollback.
- RED: edit on a language without an LSP adapter → verify loop is a no-op (does not error).
- RED: edit followed by user-explicit `/verify off` → no verify run.

### Validation

- Focused unit tests + integration test that runs the full edit→verify→fix→verify→done loop against a real Python file via pylsp.
- PTY smoke that demonstrates the verify loop visibly to the user.

### Artifact

`autocode/docs/qa/test-results/<ts>-c5-g4-auto-verify-loop.md`

### Atomic tasks

See `backend-robustness-tranche-4-checklist.md` §5.G4.

---

## C5.GATE — Checkpoint 5 regression + benchmark + LSP smoke

After all 8 languages + auto-verify ship, run:
- Standard regression set (Python unit, Rust TUI, benchmark harness, Track 1, Track 4, PTY smoke, real-gateway canary)
- All 8 per-language LSP PTY smokes
- Auto-verify loop integration test
- Benchmark sweep B7-B29 with cost comparison vs C4.GATE baseline

**Artifact:** `autocode/docs/qa/test-results/<ts>-c5-gate-regression-and-benchmark.md`.

---

## Risk register (G3 specific)

| Risk | Severity | Mitigation |
|---|---|---|
| Language servers not in PATH on user machine | High | Doctor check + clear "install X" message; tools that need them return "language not supported"; fallback to existing tools (e.g. Jedi for Python, ripgrep for cross-language search) |
| LSP server crashes / hangs | Medium | Auto-restart with bounded retries; timeout on op-level (default 5s); doctor reports unhealthy state |
| Capability mismatches across LSP servers | Medium | Per-op feature detection during initialize; tools that need an unsupported op surface clearly |
| Subprocess management on Windows | Medium-High | Use `asyncio.subprocess` with proper cleanup; unit-test on at least one Windows-style path; doctor warns on Windows about specific server availability |
| Memory footprint | Medium | Lazy-start LSP servers (only spawn when first op is requested for that language); idle-timeout shutdown after N minutes |
| Migration breaks existing Jedi-based tools | High | Explicit migration test (5.G3.6); keep Jedi as a fallback for one release |
| Auto-verify infinite-loops on intractable errors | Medium | Hard iteration cap (3); halt-on-cost-cap; user-explicit override |

---

## References

- Parent plan: `docs/plan/backend-robustness-tranche-4-plan.md`
- Master checklist: `docs/plan/backend-robustness-tranche-4-checklist.md`
- LSP spec: https://microsoft.github.io/language-server-protocol/
- Existing LSP-style code: `autocode/src/autocode/agent/lsp_tools.py` (Jedi-backed; will be migrated in 5.G3.6)
- Doctor command: `autocode/src/autocode/cli.py::doctor`
- Backend feature inventory: `docs/features/backend_features.md`

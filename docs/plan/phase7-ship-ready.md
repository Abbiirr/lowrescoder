# Phase 7 — Ship-Ready: Close Gaps, Wire Runtime, Build Executable

> Status: **COMPLETE (rev 4 — all sprints done, all benchmarks green)**
> Depends on: Phase 5 (complete), Phase 6 (complete)
> Last updated: 2026-03-30
> Review: APPROVED — 1402 tests pass, 110/110 benchmarks green (23/23 lanes at 100%)

---

## 1. Problem Statement

Phase 5 and 6 delivered 32 modules with 1348 tests. Many of those gaps are now
closed: the runtime-parity slice is live, the packaged executable builds, and
the inline frontend now has edit-specific diff approval plus profiler-backed
session summaries. What remains is final closeout: full verification, benchmark
reruns, and the last source-of-truth doc sync.

This phase closes every gap between "code exists" and "product ships."

---

## 2. Guiding Principles

1. **Wire before write.** Prefer integrating existing modules over writing new ones.
2. **Build what you can test.** Every wiring change must be verified by running
   the actual product, not just unit tests.
3. **Decide contracts first, then implement.** Config format, operating modes,
   and module ownership must be decided before coding starts (Sprint 7A0).
4. **Benchmark gating is tiered.** Unit/integration per sprint, sentinel subset
   for quick checks, full B7-B29 only in Sprint 7E.
5. **Inline app is the packaged executable frontend.** The Phase 7 PyInstaller
   binary uses `inline/app.py`. Source-tree/dev usage via `autocode chat` may
   still prefer Go TUI when the binary exists on PATH. Go TUI wiring is Phase 8.

---

## 3. Operating Modes (per Codex Entry 841 concern #2)

AutoCode has three operating modes. The executable must work in all three,
but product/local is the primary shipping target.

| Mode | LLM Source | Network | Config |
|------|-----------|---------|--------|
| **product/local** | Ollama on localhost | Optional | Default. `./autocode chat` just works. |
| **benchmark/parity** | LLM Gateway via `openrouter` provider + `api_base=http://localhost:4000/v1` | Required | Benchmarks only. `.env` sets `AUTOCODE_LLM_API_BASE` + model alias. Not a separate provider — same `openrouter` provider with different base URL. |
| **subscription/external** | OpenRouter, cloud APIs | Required | Opt-in. User provides API key. |

The executable defaults to product/local. Benchmark mode is activated by
`.env` setting `AUTOCODE_LLM_API_BASE` to the gateway URL (same `openrouter`
provider, different base URL — no new provider type needed). External mode
is activated by setting an API key in config.

---

## 4. Module Ownership Matrix (per Codex Entry 841 concern #5)

Every module must be classified before wiring begins.

### Must be product-runtime live (wire in Sprint 7A)

| Module | Wire Into | Rationale |
|--------|-----------|-----------|
| `sandbox.py` | `tools.py` | Shell safety is a product requirement |
| `delegation.py` | `loop.py` | Subagent depth limits prevent runaway |
| `middleware.py` | `loop.py` | Dangerous command guard, repetition detection |
| `tool_shim.py` | `loop.py` | Support weak/local models without tool calling |

### Stay experimental / internal (not wired into default runtime)

| Module | Rationale |
|--------|-----------|
| `edit_strategy.py` | Needs more model testing before default selection |
| `worktree.py` | Requires explicit user opt-in for risky operations |
| `remote_compaction.py` | Needs cheap model availability, not guaranteed locally |
| `orchestrator.py` | Multi-agent orchestration is Phase 8+ scope |
| `sop_runner.py` | Pipeline execution is Phase 8+ scope |

### Evaluation-only (never in product runtime)

| Module | Rationale |
|--------|-----------|
| `eval/harness.py` | Eval-only, not user-facing |
| `eval/context_packer.py` | Simulated strategies, eval scoring only |
| `eval/real_strategies.py` | Eval corpus search, not runtime context |

---

## 5. Sprint Plan

### Sprint 7A0: Canonical Runtime Contract (1 hour)

**Goal:** Decide the 3 open contracts before any implementation starts.
Per Codex Entry 841 concern #1.

| # | Decision | Current State | Proposed Resolution |
|---|----------|--------------|---------------------|
| 1 | **Config format** | Runtime reads YAML (`config.py`), installer writes TOML (`installer.py`) | Canonical: **YAML** (matches live runtime). Fix installer to write YAML. TOML migration is future work, not Phase 7. |
| 2 | **Config path** | Runtime: `~/.autocode/config.yaml`. Installer was `~/.config/autocode/` | Canonical: **`~/.autocode/config.yaml`** (matches runtime). Installer reverted to match. Done. |
| 3 | **First shipping platform** | PyInstaller spec exists, untested | **Linux x86_64 only.** macOS/Windows are Phase 8. |
| 4 | **Default local LLM endpoint** | `DEFAULT_OLLAMA_API_BASE` is `http://localhost:4000` (gateway) | Product/local: change to **`http://localhost:11434`** (direct Ollama default). Benchmark/parity: `.env` override sets `AUTOCODE_LLM_API_BASE=http://localhost:4000/v1` (gateway). The gateway is the **exception**, not the default. A fresh machine with Ollama installed works without any gateway. |

**Deliverable:** Updated `config.py`, `installer.py`, and this plan doc.

**Tests:** Update `test_config.py` for new canonical path. Update `test_installer.py`
to expect YAML output instead of TOML. Add 1 compatibility test verifying the
path/format transition. Budget ~5 test changes.

### Sprint 7A: Wire 4 Product-Runtime Modules (2 hours)

**Goal:** The 4 modules classified as "must be product-runtime live" become
live in the actual agent loop.

**Research patterns guiding each wiring decision:**

| # | Task | Module | Wire Into | Pattern Source |
|---|------|--------|-----------|---------------|
| 1 | Sandbox for shell commands | `sandbox.py` | `tools.py` `_handle_run_command()` | **Codex** `mcp_tool_call.rs`: tool → approval → sandbox dispatch |
| 2 | Delegation for subagents | `delegation.py` | `loop.py` constructor | **Codex** `agents.max_depth`. **OpenCode** per-subagent permission rules |
| 3 | Middleware into agent loop | `middleware.py` | `loop.py` | **Goose** `ToolInspectionManager`: inspector stack before tool execution |
| 4 | Tool shim for weak models | `tool_shim.py` | `loop.py` | **Goose** `GOOSE_TOOLSHIM`: text-based tool parsing |

**Not wired this sprint:** edit_strategy, worktree, remote_compaction, orchestrator
(per ownership matrix — experimental/internal).

**Tests:** 4 integration tests verifying each wiring point.

**Gate:** Unit + integration tests pass. No benchmark run required.

**Implementation update (2026-03-29):**
- Shared `factory.py` now preserves `task_store`, `subagent_manager`,
  `memory_context`, `delegation_policy`, and compaction settings instead of
  dropping backend runtime state.
- `backend/server.py` and `tui/app.py` now create their loops through the same
  shared factory path as inline mode.
- `loop.py` now invokes `after_model`, `before_compaction`, and
  `after_compaction` hooks, and `spawn_subagent` is hard-gated by
  `DelegationPolicy` in the live runtime path.
- `subagent.py` now releases delegation slots when background subagents finish.
- Targeted verification artifacts:
  `docs/qa/test-results/20260329-125418-phase7-runtime-parity-pytest.md`,
  `docs/qa/test-results/20260329-125431-phase7-runtime-parity-ruff.md`.

### Sprint 7B: Build Actual Executable (2 hours)

**Goal:** `pyinstaller autocode.spec` produces a working Linux x86_64 binary.

Per Codex Entry 841 concern #4 — platform-aware, not "run until it works."

| # | Task | Details |
|---|------|---------|
| 1 | Platform scope | **Linux x86_64 only.** macOS/Windows deferred. |
| 2 | Build mode | Try `--onefile` first. If temp-dir extraction fails (noexec mount), fall back to `--onedir`. Document which mode ships. |
| 3 | Install PyInstaller | Use a temporary toolchain (`uv run --with pyinstaller pyinstaller`) or add it explicitly to the env. |
| 4 | Build | `cd autocode && pyinstaller autocode.spec` |
| 5 | Size target | Measure actual size. UPX compression is **optional**, not mandatory. No <100MB hard target. |
| 6 | Smoke test | `./dist/autocode version`, `./dist/autocode --help`, `./dist/autocode doctor`, `./dist/autocode setup` |
| 7 | Hidden import fixes | Iterate spec until all runtime imports resolve |
| 8 | temp-dir handling | If `--onefile`, test with `--runtime-tmpdir /tmp/autocode` to avoid noexec issues |

**Implementation update (2026-03-29):**
- PyInstaller build succeeded via stored artifact
  `autocode/docs/qa/test-results/20260329-131744-phase7-pyinstaller-build.md`.
- Packaged smoke succeeded for `version`, `--help`, and `setup`
  via `autocode/docs/qa/test-results/20260329-132046-phase7-pyinstaller-setup-smoke.md`.
- The packaged `doctor` command runs, but the current host still reports
  missing Ollama service and missing `lancedb` in the local environment
  (`autocode/docs/qa/test-results/20260329-131945-phase7-pyinstaller-smoke.md`).

**Gate:** Binary builds, packaged CLI launches, `setup` succeeds on a clean temp HOME, and host dependency failures are explicit rather than silent packaging crashes.

### Sprint 7C: Missing P0 Features (2 hours)

**Goal:** Fill the remaining P0 gaps.

| # | Feature | Pattern Source | Details |
|---|---------|---------------|---------|
| 1 | **Config path reconciliation** | **Codex** `config/edit.rs` atomic writes | DONE — installer reverted to `~/.autocode/config.yaml` matching runtime. No migration needed. |
| 2 | **Edit-specific accept/reject** | **Aider** `io.py` `confirm_ask()` | After diff preview in `inline/app.py`, prompt "Apply this edit? [y/n]". On reject, discard changes. Narrow scope: edit-specific only, not general approval (that already exists). |
| 3 | **Edit conflict detection** | **Codex** field-level merge | `agent/conflict.py`: check file mtime before write. Current shipping version is observed-mtime warning/blocking: overwrite-style writes are blocked after an external change unless the user explicitly re-approves from a fresh preview; targeted `edit_file` operations warn and apply against current contents. |

**Implementation update (2026-03-29):**
- Inline `edit_file` approvals now show a real diff preview and explicit
  `Apply` / `Reject` wording.
- Tool handlers now track observed mtimes: `write_file` blocks blind overwrites
  after an external change, while `edit_file` warns and applies against current
  contents.
- Verification landed in the focused Phase 7 closeout suite:
  `autocode/docs/qa/test-results/20260329-131654-phase7-closeout-focused-pytest.md`.

**Tests:** Focused regression coverage added for preview rendering, summary output,
and conflict behavior.

**Gate:** Unit tests pass.

### Sprint 7D: P1 Polish (1-2 hours)

| # | Feature | Details |
|---|---------|---------|
| 1 | **Shell completions** | Already exists via Typer (`--install-completion`, `--show-completion`). Task is **verify + document**, not implement. Add to user guide. Smoke test in binary. (Per Codex Entry 841 concern #3.) |
| 2 | **Routing quality benchmark** | 20 scenarios with known optimal layer. Run PolicyRouter. Measure correct-layer %, cost savings. Store as eval artifact. |
| 3 | **Wire profiler into runtime** | Add `Profiler` to AgentLoop. Profile LLM calls + tool calls. Show p50/p95 in completion summary. |
| 4 | **User guide** | `docs/guide/getting-started.md`: install, configure, first chat, doctor. `docs/guide/commands.md`: all CLI commands with examples. |

**Implementation update (2026-03-29):**
- `Profiler` is now wired into the live loop via the shared factory and appears
  in session summaries.
- The user guides already existed in `docs/guide/`; Phase 7 work here is
  verification/sync rather than first creation.

**Tests:** Focused profiler/session-summary regressions are covered in the
closeout suite.

**Gate:** Unit tests pass.

### Sprint 7E: Final Verification (1 hour)

**Goal:** Full regression + benchmark pass before declaring ship-ready.

**Tiered verification (per Codex Entry 841 concern #6):**

| # | Check | Target | When |
|---|-------|--------|------|
| 1 | All unit/integration tests | 1370+ tests, 0 failures | This sprint |
| 2 | Full B7-B14 benchmarks | ≥ 37/40 (92.5%) | This sprint only |
| 3 | Full B15-B29 benchmarks | ≥ 62/75 (82.7%) | This sprint only |
| 4 | PyInstaller binary | Builds, doctor runs, version prints | This sprint |
| 5 | Gateway smoke test | swebench + tools respond | This sprint |
| 6 | Docs consistency | current_directives.md matches all counts/scores | This sprint |
| 7 | Codex approval | No NEEDS_WORK or REJECT | This sprint |

**Per-sprint gates (Sprints 7A0-7D):**
- Unit + integration tests pass
- Sentinel benchmark: B9-PROXY only (5 tasks, fast, no Docker deps)
- No full B7-B14 run until 7E

---

## 6. Implementation Order

```
7A0 (contracts) → 7A (wire 4 modules) → 7B (executable) → 7C (P0 gaps) → 7D (polish) → 7E (verify)
```

---

## 7. Files to Modify

### Sprint 7A0
- `autocode/src/autocode/config.py` — canonical config path
- `autocode/src/autocode/packaging/installer.py` — write YAML not TOML

### Sprint 7A
- `autocode/src/autocode/agent/tools.py` — sandbox wiring
- `autocode/src/autocode/agent/loop.py` — middleware + tool shim + delegation

### Sprint 7B
- `autocode/autocode.spec` — fix hidden imports
- New: `autocode/tests/unit/test_executable.py`

### Sprint 7C
- `autocode/src/autocode/packaging/installer.py` — YAML config
- `autocode/src/autocode/inline/app.py` — accept/reject for edits
- New: `autocode/src/autocode/agent/conflict.py`

### Sprint 7D
- New: `docs/guide/getting-started.md`
- New: `docs/guide/commands.md`
- New: `autocode/src/autocode/eval/routing_benchmark.py`
- `autocode/src/autocode/agent/loop.py` — profiler wiring

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Wiring breaks existing tests | Per-sprint unit gate, sentinel benchmark |
| PyInstaller can't find tree-sitter | hiddenimports iteration, Linux-only scope |
| Config path change breaks existing users | No existing users yet (pre-release) |
| Middleware overhead | Profile with Profiler, keep guards O(1) |
| Provider variance in benchmarks | Full benchmark only in 7E, sentinel per sprint |

---

## 9. Success Criteria

Phase 7 is complete when:
1. Canonical config contract decided and implemented
2. 4 product-runtime modules wired into actual agent loop
3. Linux x86_64 binary builds and passes smoke test
4. Edit accept/reject and conflict detection work
5. User guide exists
6. 1370+ tests pass, benchmarks stable
7. Codex approves the final state

---

## 10. Research Basis

Official docs:
- Codex approvals & security: https://developers.openai.com/codex/agent-approvals-security
- Codex subagents: https://developers.openai.com/codex/subagents
- Claude Code hooks/worktree: https://code.claude.com/docs/en/hooks
- PyInstaller runtime caveats: https://pyinstaller.org/en/v6.14.2/usage.html
- Typer CLI completions: https://typer.tiangolo.com/

Local research corpus: `research-components/` (Codex, Goose, Aider, Claude Code, OpenCode)

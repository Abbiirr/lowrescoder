# AutoCode — Full Project Status

**Date:** 2026-04-10
**Phase:** Post-Phase-8 frontier — Claude Code primary TUI parity, large-codebase comprehension, native external-harness orchestration, and Terminal-Bench improvement
**Test Suite:** 1630+ passed, 0 failed in the latest stored full-suite artifact, 4 skipped

---

## 1. Product Overview

AutoCode is an edge-native AI coding assistant CLI. Local-first, deterministic-first, targeting consumer hardware (8GB VRAM, 16GB RAM). The system uses deterministic classical AI as the primary intelligence layer, invoking LLMs only when necessary — the opposite of how most AI coders work.

**Architecture:** 4-Layer Intelligence Model

| Layer | Purpose | Latency | Status |
|-------|---------|---------|--------|
| L1: Deterministic | Tree-sitter, LSP, static analysis, pattern matching | <50ms | DONE |
| L2: Retrieval | AST-aware chunking, BM25 + vector search, repo map | 100-500ms | DONE |
| L3: Constrained Gen | Grammar-constrained decoding, small model (1.5B-3B) | 500ms-2s | PLANNED |
| L4: Full Reasoning | 7B+ model, multi-file planning, architect/editor | 5-30s | DONE |

**Tech Stack:** Python 3.11+ backend, Go + Bubble Tea TUI, JSON-RPC over stdin/stdout, tree-sitter 0.25.2, Jedi (planned), LanceDB, Jina v2 embeddings, LLM Gateway (9 providers, auto-failover).

---

## 2. Phases Complete

### Phase 0-7: Core Platform (COMPLETE)

| Phase | Focus | Key Deliverables |
|-------|-------|------------------|
| 0 | Foundation | Project structure, uv workspace, submodules |
| 1 | L1 Deterministic | Tree-sitter parsing, symbol extraction, AST queries |
| 2 | L2 Retrieval | BM25 + vector search, AST-aware chunking, repo map |
| 3 | Agent Core | AgentLoop, tool registry, approval system, inline frontend |
| 4 | Agent Orchestration | Middleware stack, planning guard, verification tracker |
| 5 | Agent Teams | Subagent delegation, worktree isolation, MCP server |
| 6 | External Integration | LLM Gateway, provider registry, multi-model support |
| 7 | Quality & Polish | Sprint verification, benchmark lanes, Go TUI |

### Phase 8: Internal Orchestration (COMPLETE)

8 sprints completed. Live frontend switch-over is done.

Key landed pieces:
- Orchestrator runtime on the live frontend path
- Active working set tracking (hot-file bias for retrieval)
- Research mode (`/research on/off/status`, `/comprehend`)
- External harness adapter contract (`HarnessAdapter` protocol)
- Packaging/install substrate (`installer`, `bootstrap`, `doctor`)

### Current Frontier Priority

The current top backlog item is no longer generic “frontend polish.” It is a specific Claude Code parity pass for the primary full-screen TUI:

- Claude-style single-column chat-first hierarchy
- footer-first status presentation
- fixed-width braille/shimmer thinking spinner
- compact grouped tool-call rows
- narrow-terminal hardening
- gated rollout behind `claude_like` until review and smoke gates pass

Current implementation state:
- a first Go TUI parity slice is already landed in the active worktree
- landed: prompt/header/spinner/footer simplification and initial compact tool-row styling
- still open: approval prompt parity, completion scrollback consistency, narrow-terminal hardening, focused Go TUI tests, and smoke artifacts

---

## 3. Internal Benchmark Dashboard

**23 lanes, all GREEN**

| Lane | Type | Tasks | Status | Model | Date |
|------|------|-------|--------|-------|------|
| B7 | SWE-Bench Pilot | 10 | **GREEN 10/10** | swebench | 2026-04-03 |
| B8 | SWE-Bench (matplotlib) | 10 | **GREEN 10/10** | swebench | 2026-04-03 |
| B9-PROXY | Terminal-Bench Equivalent | 10 | **GREEN 10/10** | terminal_bench | 2026-04-03 |
| B10-PROXY | Multilingual Equivalent | 10 | **GREEN 10/10** | swebench | 2026-04-03 |
| B11 | SWE-Bench Subset | 5 | GREEN 5/5 | tools | 2026-03-26 |
| B12-PROXY | Proxy Tasks | 5 | GREEN 5/5 | tools | 2026-03-30 |
| B13-PROXY | Proxy Tasks | 5 | GREEN 5/5 | tools | 2026-03-26 |
| B14-PROXY | Proxy Tasks | 5 | GREEN 5/5 | tools | 2026-03-30 |
| B15 | Intake Mutation | 5 | GREEN 5/5 | tools | 2026-03-31 |
| B16 | Requirements Feature | 5 | GREEN 5/5 | tools | 2026-03-29 |
| B17 | Long Horizon | 5 | GREEN 5/5 | tools | 2026-03-30 |
| B18 | Held-out Prototype | 5 | GREEN 5/5 | tools | 2026-03-26 |
| B19 | Multilingual | 5 | GREEN 5/5 | tools | 2026-03-29 |
| B20 | Terminal Ops | 5 | GREEN 5/5 | tools | 2026-03-31 |
| B21 | Regression Contract | 5 | GREEN 5/5 | tools | 2026-03-31 |
| B22 | Corruption | 5 | GREEN 5/5 | tools | 2026-04-01 |
| B23 | Sync | 5 | GREEN 5/5 | tools | 2026-03-31 |
| B24 | Misc | 5 | GREEN 5/5 | tools | 2026-03-29 |
| B25 | Misc | 5 | GREEN 5/5 | tools | 2026-03-31 |
| B26 | Misc | 5 | GREEN 5/5 | tools | 2026-03-25 |
| B27 | Misc | 5 | GREEN 5/5 | tools | 2026-03-29 |
| B28 | Misc | 5 | GREEN 5/5 | tools | 2026-03-30 |
| B29 | Misc | 5 | GREEN 5/5 | tools | 2026-03-29 |

**Current: 23/23 GREEN** (`120/120`, `100%`)

### Key Findings
- B9-PROXY went from 0/10 (rate-limited) to 3/10 (`tools`) to **10/10** (`terminal_bench` + curl fixture fix)
- B8 expansion work was later closed out into the canonical 23/23 green state
- `terminal_bench` alias (Grok-4.1 + Grok-code-fast-1 + Qwen-3-235B) dramatically outperforms `tools` on complex tasks
- current source-of-truth docs treat the 23/23 green state as canonical unless a new reproducible regression supersedes it

---

## 4. B30 — Terminal-Bench v2.0 (External Benchmark via Harbor)

### Pipeline

```
Harbor CLI -> AutoCodeHarborAgent (v0.3.0) -> LLM Gateway -> Docker container
```

### Adapter Evolution

| Version | Features | Score |
|---------|----------|-------|
| v0.1 | Raw HTTP, single run_command tool | 0% |
| v0.2 | Doom-loop detection, marker sync, JSON sanitization | 0% |
| v0.3.1 | write_file + read_file tools, planning step, pre-completion verification, error resilience, anti-hallucination prompt, tool-pair-safe context compaction | 40% best |

### v0.3.0 Harness Improvements (All 6 Implemented)

1. **write_file + read_file tools** — base64 encoding bypasses all shell quoting/heredoc issues
2. **Raised exit threshold** — from 2 to 5 text-only responses + nudge injection
3. **Error resilience** — errors don't burn turn budget, history sanitized on provider rejection
4. **Anti-hallucination prompt** — explicit "NO apply_patch, NO edit_file" guidance
5. **Tool-pair-safe context compaction** — preserves tool_call/response pairs, summarizes trimmed middle
6. **Planning + verification** — forced planning step, pre-completion verification injection

### Root Cause Analysis

The initial 0% score was traced to 6 harness issues before the adapter recovery pass:
- Heredoc doom loops (13+ retries per file write)
- Premature exit after 2 text responses
- 30-70% of turns wasted on provider errors
- apply_patch tool hallucination
- Context trim creating orphaned tool responses
- Missing harness patterns (planning, verification, bootstrap)

### Models Tested

| Model Alias | Backend | B30 Score | Notes |
|-------------|---------|-----------|-------|
| tools | Free-tier (Cloudflare, Groq, Mistral) | 0% | Too weak for terminal tasks |
| coding | Free-tier rotation | 0% | Same + Cloudflare daily limit |
| terminal_bench | xAI Grok-4.1 + Grok-code-fast-1 + Qwen-3-235B | 40% best | Strongest current B30 path |

### Next Steps for B30
- keep the current `40%` result as the best confirmed baseline
- use the calibration pair:
  - `break-filter-js-from-html`
  - `build-cython-ext`
- improve task-family strategy overlays before broadening the subset again

---

## 5. Agent Communication Log

**Active entries:** see `AGENTS_CONVERSATION.MD` header for the live range
**Key threads:**

| Thread | Status | Summary |
|--------|--------|---------|
| B30 Terminal-Bench | Active | Harbor baseline recovery complete, score-improvement work still open |
| External Adapter Contract | Active | HarnessAdapter protocol and adapter files landed; deeper live orchestration still frontier work |
| Active Working Set | Complete | Hot-file tracking + search bias landed (Entry 959) |
| Research Mode | Complete | /research, /comprehend commands landed (Entry 962) |
| Installability + /loop | Complete | install smoke and loop smoke artifacts are stored; plain command contract is landed |

---

## 6. Harness Brief Audit (vs harness_starter_prompt_v2.md)

| Component | Status | Coverage |
|-----------|--------|----------|
| Three core skills (plan-first, build-verified, review-and-close) | MISSING | Only agent-comms skill exists |
| Stop-time verification gate | PARTIAL | Soft nudge in middleware, not hard block |
| Pre-tool-use guard | PARTIAL | Dangerous command blocking, no rewriting |
| Verification wrapper (verify.sh/verify.json) | PARTIAL | Fixture-level only, no harness-level schema |
| Rollback / checkpoint safety net | PARTIAL | Worktrees + SQLite checkpoints, not auto-invoked |
| Minimal repo search helper | PARTIAL | L1+L2 mature, no standalone symfind |
| Role separation (Plan/Build/Review) | PARTIAL | 3 modes exist, no tool-level enforcement |
| Artifact and evidence system | PARTIAL | Plan artifacts + tool call logging, missing commands.log/diff.patch/risk.md/verify.json |
| Hooks layer | PARTIAL | Internal middleware hooks, not wired to Claude Code/Codex |
| Phase 2 (embeddings/MCP) | PARTIAL | Jina v2 embeddings + MCP server, LanceDB not active |

**Overall: ~60-70% infrastructure exists.** Phase 1 harness build would be integration and artifact glue, not ground-up work.

---

## 7. Repository Structure

```
lowrescoder/                    # Git superproject
  autocode/                     # Python backend + Go TUI (submodule)
    src/autocode/
      agent/                    # AgentLoop, tools, middleware, prompts, approval, worktree
      layer1/                   # Tree-sitter parsing, symbol extraction
      layer2/                   # BM25 + vector search, embeddings, repo map
      layer3/                   # Constrained generation (planned)
      layer4/                   # LLM gateway integration
      external/                 # MCP server, harness adapter contract
      session/                  # Task store, checkpoint store, models
      tui/                      # Textual TUI, commands
      inline/                   # Inline frontend
      backend/                  # JSON-RPC backend server
      packaging/                # Installer, bootstrap
      eval/                     # Evaluation harness
    cmd/autocode-tui/           # Go Bubble Tea TUI
    tests/unit/                 # 1630+ unit tests
  benchmarks/                   # Benchmark harness (submodule)
    adapters/                   # AutoCode adapter, Harbor adapter
    e2e/external/fixtures/      # B9-B30 task fixtures
    benchmark_runner.py         # Lane runner
  docs/                         # Documentation (submodule)
  training-data/                # Training data (submodule)
```

---

## 8. LLM Gateway

OpenAI-compatible proxy at `http://localhost:4000/v1` aggregating 9 free providers with automatic failover, latency-based routing, and 5-hour caching.

**Model Aliases:**

| Alias | Use Case | Providers |
|-------|----------|-----------|
| tools | General tool calling | Free-tier rotation |
| coding | Code generation | Free-tier rotation |
| terminal_bench | Terminal-Bench / hard tasks | xAI Grok-4.1, Grok-code-fast-1, Qwen-3-235B, Gemini-3-flash |
| thinking | Reasoning | Free-tier rotation |
| local | Ollama fallback | qwen3.5:9b |

---

## 9. What's Next

### Immediate
- large-codebase comprehension validation on genuinely large repos
- external-harness event normalization and deeper live orchestration
- B30 score-improvement work beyond the baseline Harbor recovery
- use `EXECUTION_CHECKLIST.md` plus `PLAN.md` as the live backlog pair

### Medium-term (Harness Phase 1)
- Three core skills: plan-first, build-verified, review-and-close
- Hard verification gate (block completion without evidence)
- verify.json schema + portable verification wrapper
- Artifact collection: commands.log, diff.patch, risk.md
- Wire enforcement hooks to Claude Code settings.json

### Long-term
- L3 constrained generation (llama-cpp-python + grammar)
- LanceDB persistent embeddings
- External benchmark parity targets

---

## 10. Key Metrics

| Metric | Value |
|--------|-------|
| Unit tests passing | 1630 |
| Benchmark lanes GREEN | 23/23 |
| Benchmark score | 120/120 (100%) |
| Agent communication entries | active range tracked in `AGENTS_CONVERSATION.MD` |
| Phases complete | 0-8 |
| Modules in src/autocode/ | 15+ |
| Supported LLM providers | 9 (free-tier) + Ollama |
| B30 adapter version | 0.3.1 |
| B9-PROXY score | 10/10 (100%) with terminal_bench |

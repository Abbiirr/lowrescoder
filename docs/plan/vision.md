# AutoCode Vision — Phase 4 → 5 → 6 → 7

> Last updated: 2026-02-18
> Status: Draft — Codex-reviewed (Entry 498), corrections applied

---

## What We Have Now (Post-Phase 4)

AutoCode is a working edge-native AI coding assistant CLI with a 4-layer deterministic-first architecture. It is local-first and fully local-capable, running on consumer hardware (8GB VRAM, 16GB RAM), with an optional cloud fallback via OpenRouter.

| Capability | Layer | Status |
|-----------|-------|--------|
| Tree-sitter parsing (Python, Go, JS, TS, Rust) | L1 | Working |
| AST-aware chunking | L1 | Working |
| BM25 + vector search (LanceDB + jina-v2-base-code) | L2 | Working |
| Repo map generation | L2 | Working |
| Ollama L4 integration (Qwen3-8B Q4_K_M) | L4 | Working |
| Agent loop with tools (search, read, write, shell) | L4 | Working |
| OpenRouter cloud fallback | L4 | Working |
| Go TUI (Bubble Tea) + Python backend (JSON-RPC) | Infra | Working |
| Inline REPL (Rich + prompt_toolkit) | Infra | Working |
| Session management + checkpoints | Infra | Working |
| 1015+ tests passing, ruff clean, mypy 52 baseline | QA | Stable |

### What's Missing

- No architect/editor pattern — single-pass LLM only, no iterative planning
- No structured code editing — LLM outputs raw text, no diff/patch workflow
- No L3 constrained generation — no grammar-constrained small model
- No eval framework — no systematic measurement of quality or regressions
- No MCP server — cannot be used by Claude Code, Codex, or OpenCode
- No external tool integration — no discovery or coordination with other AI tools
- No cost tracking — no visibility into token usage or inference cost
- No cross-file semantic analysis — tree-sitter is syntax-only, no goto-definition across files
- Python semantic analysis only via basic heuristics, not Jedi

---

## What We'll Have After Phase 5 (Universal Orchestrator)

Phase 5 transforms AutoCode from a search/retrieval tool into a **real AI coding assistant** with multi-step planning, structured editing, quality measurement, and ecosystem integration.

### Sprint 5A0: Quick Wins
| Capability | Value |
|-----------|-------|
| Diff preview after every write | User sees exactly what changed before committing |
| Auto-commit before edits | Git safety net — every edit is recoverable |
| Per-request token counter | Cost visibility for every LLM call |
| `hc doctor` diagnostic command | One command to verify system health |

### Sprint 5A: Identity + Eval Foundation
| Capability | Value |
|-----------|-------|
| AgentCard identity system | Structured agent metadata (name, role, capabilities, model spec) |
| ProviderRegistry with lazy loading | Unified interface to Ollama, llama-cpp-python, OpenRouter |
| Adaptive context policy (4096 min / 8192 target) | VRAM-aware context window management |
| Eval harness scaffold | Systematic quality measurement from day one |

### Sprint 5B: LLMLOOP — The Core Innovation
| Capability | Value |
|-----------|-------|
| **ArchitectAgent** (L4 planner) | Multi-file planning with structured EditPlan output |
| **EditorAgent** (L3/L4 patch applier) | Applies planned edits with format compliance |
| **VerificationAgent** (L1 checker) | Deterministic verification of applied edits |
| **LLMLOOP pipeline** | Architect → Editor → Verify → retry loop (up to 3 iterations) |
| Jedi semantic analysis | Cross-file goto-definition, find-references, type inference for Python |
| `/edit` command | User-facing command that orchestrates the full LLMLOOP |

### Sprint 5C: Quality + Coordination
| Capability | Value |
|-----------|-------|
| Context quality eval suite | Measures L1/L2 retrieval quality (F1, recall, precision) |
| Routing-regret metrics | Measures how often the wrong layer handles a task |
| AgentBus message passing | Typed inter-agent communication with persistence |
| SOPRunner workflow engine | Standard Operating Procedure execution for multi-step tasks |
| PolicyRouter | Intelligent L1/L2/L3/L4 routing based on task classification |
| Cost dashboard | Real-time token usage and inference cost tracking |

### Sprint 5D: Ecosystem Integration
| Capability | Value |
|-----------|-------|
| **MCP server** | Expose AutoCode's L1/L2 tools to Claude Code, Codex, OpenCode |
| Config generator | Auto-generate MCP config for Claude Code and Codex |
| CLIBroker | Subprocess management for external tool invocation |
| Golden path integration tests | End-to-end tests with real external tools |
| ExternalToolTracker | Discover AI coding tools on PATH with health probes |

### Phase 5 Exit State

After Phase 5, AutoCode can:
1. **Plan multi-file edits** using an Architect/Editor pattern with verification
2. **Measure its own quality** via eval harness + task bank + regression suite
3. **Integrate with the AI ecosystem** as an MCP server (Claude Code, Codex, OpenCode can use its tools)
4. **Track costs** and make intelligent routing decisions (deterministic first, LLM only when needed)
5. **Discover and coordinate** with external AI tools installed on the user's machine

---

## What Phase 6 Should Deliver (Discussion — Not Yet Planned)

Phase 6 builds on the standalone MVP + MCP foundation from Phase 5. Candidates ranked by value:

### P0: Single Installable / Zero Setup

The immediate post-Phase 5 priority is making AutoCode trivially installable and usable out of the box — single command install, auto-detect hardware, auto-download models, zero manual configuration. This is the user's top-priority vision item.

### Tier 1: High Value, Clear Path

| Candidate | Description | Why Now |
|-----------|-------------|---------|
| **Multi-language LSP** | Add gopls, typescript-language-server, rust-analyzer for cross-file semantic analysis in Go, JS/TS, Rust | L1 intelligence currently Python-only via Jedi. This is the biggest gap in the "deterministic first" claim. Without it, non-Python projects fall through to L4 for basic goto-definition |
| **Cloud provider integration** | First-class Gemini CLI (free tier), Claude API, OpenAI API as ProviderRegistry adapters | Cost reduction for users. Gemini: 78% SWE-bench, 1M context, 1000 free req/day. Directly counters "why not just use Claude Code" |
| **Advanced eval + benchmarking** | SWE-bench Lite integration, competitive benchmarks vs Aider/OpenCode on identical tasks | Proves the architecture works. Without external benchmarks, quality claims are internal-only |

### Tier 2: Medium Value, Moderate Complexity

| Candidate | Description | Why Later |
|-----------|-------------|-----------|
| **Team templates + lifecycle** | Pre-built agent team configs (code review, bug fix, refactor), `/team` command, Go TUI team panel | Requires AgentBus + SOPRunner to be battle-tested first (Phase 5C) |
| **Context isolation + handoff** | Per-agent context windows (private vs shared), structured context transfer between agents | Architectural decision needed on memory model |
| **A2A protocol** | Peer-to-peer agent communication (currently WATCHLIST) | Not required for Phase 5 objectives; MCP + config surfaces already cover same-machine orchestration for Claude/Codex/OpenCode. WATCHLIST for later interoperability |

### Phase 6 Constraint: Minimum Model Contracts

Phase 6 must explicitly define minimum model contracts for any feature that depends on model quality (e.g., multi-language edit, cloud provider routing). Model optimization is deferred to Phase 7, but Phase 6 cannot assume model improvements that haven't shipped yet.

### Tier 3: Phase 7 — Model Optimization (Per User Directive)

| Candidate | Description |
|-----------|-------------|
| **Quantization tuning** | Systematic evaluation of quantization levels vs quality tradeoffs |
| **Model selection automation** | Auto-select best model for task based on hardware profile |
| **VRAM budget optimization** | Dynamic model loading/unloading based on available VRAM |
| **Fine-tuning for editor role** | Train a small model specifically for AutoCode's edit format |
| **Speculative decoding** | Use small model to draft, large model to verify |

---

## Competitive Landscape Context

| Tool | Stars | Architecture | AutoCode Differentiator |
|------|-------|-------------|---------------------------|
| Claude Code | N/A (proprietary) | Cloud LLM + MCP | AutoCode: local-first, no API costs, deterministic L1/L2 |
| Codex CLI | N/A (proprietary) | Cloud LLM + sandbox | AutoCode: runs on consumer hardware, no cloud dependency |
| OpenCode | 106k (as of 2026-02) | Go+Bubble Tea, LLM-centric | AutoCode: 4-layer architecture, LLM as last resort |
| Aider | 30k+ (as of 2026-02) | Python, LLM-first | AutoCode: deterministic context retrieval, lower token usage |
| Cursor | N/A (proprietary) | VS Code fork, cloud | AutoCode: CLI-native, editor-agnostic, open source |

**AutoCode's core differentiator:** Deterministic intelligence first. L1/L2 are designed to handle 60-70% of tasks with zero tokens (target/hypothesis — to be validated by Phase 5 eval harness with frozen task bank). LLM is only invoked when deterministic tools can't solve the problem. This means lower cost, lower latency, and higher reliability for the majority of coding tasks.

---

## Summary Timeline

```
Phase 4 (DONE)     → Agent loop, tools, sessions, Go TUI
Phase 5 (CURRENT)  → LLMLOOP, eval, MCP, ecosystem integration
Phase 6 (PLANNED)  → Multi-language LSP, cloud providers, external benchmarks
Phase 7 (PLANNED)  → Model optimization, quantization, fine-tuning
```

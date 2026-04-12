# CLAUDE.md — AI Assistant Guidelines for AutoCode

## Core Philosophy

**I am here to help, but you must always understand what's going on.**

- **Ask questions** when something is unclear
- **Challenge my suggestions** if they don't make sense
- **Don't blindly accept** any code changes without understanding them

You are the developer. I am a tool to accelerate your work, not replace your judgment.

---

## Project Overview

**AutoCode** is an edge-native AI coding assistant CLI. Local-first, deterministic-first, consumer hardware (8GB VRAM, 16GB RAM). The system uses deterministic classical AI as the primary intelligence layer, invoking LLMs only when necessary. This is the opposite of how most AI coders work.

---

## Project Invariants (User-Approved Only)

These decisions are **locked** and do NOT change unless the user explicitly approves a change. Agents must not deviate from these without user authorization.

1. **LLM as last resort** — Deterministic tools first (tree-sitter, LSP, static analysis), LLM only when they can't solve it
2. **4-Layer Architecture** — Layer 1 (deterministic) → Layer 2 (retrieval) → Layer 3 (constrained gen) → Layer 4 (full reasoning)
3. **Edge-native** — ALL intelligence runs on the user's machine. No cloud dependency by default
4. **Consumer hardware target** — 8GB VRAM, 16GB RAM, no 70B+ models required
5. **Go TUI + Python backend** — Frontend in Go (Bubble Tea), backend in Python, JSON-RPC over stdin/stdout
6. **Tech stack** — tree-sitter, Ollama (L4), llama-cpp-python + native grammar (L3), LanceDB, jina-v2-base-code embeddings
7. **Docs are the single source of truth** — If docs say X and code does Y, the docs are wrong and must be fixed before continuing

---

## Architecture: 4-Layer Intelligence Model

| Layer | Purpose | Latency | Tokens |
|-------|---------|---------|--------|
| **L1: Deterministic** | Tree-sitter parsing, LSP (types/refs/defs), static analysis, pattern matching | <50ms | 0 |
| **L2: Retrieval** | AST-aware chunking, BM25 + vector search, project rules, repo map | 100-500ms | 0 |
| **L3: Constrained Gen** | Grammar-constrained decoding, small model (1.5B-3B), structured output | 500ms-2s | 500-2000 |
| **L4: Full Reasoning** | 7B model, multi-file planning, architect/editor pattern, feedback loops | 5-30s | 2000-8000 |

---

## Technology Stack

| Component | Choice | Status |
|-----------|--------|--------|
| Backend Language | Python 3.11+ | DONE |
| TUI Frontend | Go + Bubble Tea (inline mode) | DONE |
| Frontend↔Backend | JSON-RPC over stdin/stdout | DONE |
| Package Manager | uv | DONE |
| CLI Framework | Typer + Rich | DONE |
| Parsing | tree-sitter 0.25.2 | DONE |
| Python Semantics | Jedi (cross-file goto, refs, types) | PLANNED (Phase 5) |
| LSP Client | Deferred (Jedi preferred over multilspy) | EVALUATING |
| Vector DB | LanceDB | DONE |
| Embeddings | jina-v2-base-code (768-dim, local) | DONE |
| L4 LLM Runtime | LLM Gateway (OpenAI-compatible, 9 providers, auto-failover) | DONE |
| L4 Model | `coding` alias (GPT-4.1, DeepSeek-R1, Codestral, Qwen3, etc.) | DONE |
| L3 LLM Runtime | llama-cpp-python + native grammar | PLANNED (Phase 5) |
| L3 Model | Qwen2.5-Coder-1.5B Q4_K_M (~1 GB VRAM) | PLANNED |

> L3 uses llama-cpp-python with native grammar constraints (Outlines replaced per Phase 5 plan). L4 uses the LLM Gateway (`http://localhost:4000/v1`) — an OpenAI-compatible proxy aggregating 9 free providers (OpenRouter, Google AI Studio, Cerebras, Groq, Mistral, GitHub Models, NVIDIA NIM, Cloudflare, Cohere) with automatic failover, latency-based routing, and 5-hour caching. Model aliases: `coding`, `default`, `fast`, `thinking`, `vision`, `tools`, `big`, `local`. Gateway docs: `http://localhost:4001/docs`.

---

## Key Design Principles

1. **LLM as last resort** — Always try deterministic approaches first
2. **Fail fast, fail safe** — Verify edits before applying, git commit for safety
3. **Transparent operations** — User should see what's happening
4. **Local-first** — Privacy and cost are features, not afterthoughts
5. **Incremental complexity** — Start with simple approaches, add sophistication as needed
6. **Docs track reality** — Update documentation WITH code changes, never after (see AGENT_COMMUNICATION_RULES.md "Mandatory Documentation Sync")

---

## Current Phase

Phases 0-8 complete. Post-Phase-8 frontier work active: deep-research-report Phase A+B complete (~60%), Phase C (multi-lane execution router, etc.) in design. Monorepo flattened (submodules removed 2026-04-12). All 3 frontends use `create_orchestrator()`. Current QA: 1953 passed, 0 failed, 4 skipped (artifact: `autocode/docs/qa/test-results/20260412-175034-full-suite-post-monorepo-flatten.md`). Canonical benchmark closeout: 120/120 (100%) — all 23 lanes green.

**Read `current_directives.md` for the active sprint and what to work on next.**

---

## Testing (Required)

**Always run tests after any code change.** No code is considered working until tests pass.

```bash
# Unit tests — autocode (fast, run after every change)
uv run pytest autocode/tests/unit/ -v --cov=src/autocode

# Unit tests — benchmarks
uv run pytest benchmarks/tests/ -v

# All tests (both modules)
uv run pytest autocode/tests/unit/ benchmarks/tests/ -v

# Sprint verification (run after completing a sprint)
uv run pytest autocode/tests/test_sprint_verify.py -v

# Linting + type checking (run before any review)
make lint

# Integration tests (only when testing LLM connections)
uv run pytest -m integration autocode/tests/integration/
```

**Rules:**
- **TDD is mandatory.** Every sub-sprint begins by writing all tests first. Tests are expected to fail until implementation catches up — this is the workflow, not a problem.
- All unit tests must pass before requesting review or moving to the next sprint
- New code must include tests — no exceptions
- Sprint verification tests must pass at each sprint boundary
- Integration tests are included by default but self-skip when requirements are not met (API keys, running servers)

---

## Repository Structure

Monorepo with logical folder segregation:

| Directory | Contents |
|-----------|----------|
| `autocode/` | Python backend (`src/autocode/`), Go TUI (`cmd/autocode-tui/`), product tests |
| `benchmarks/` | Benchmark harness, adapters, e2e fixtures, benchmark tests |
| `docs/` | All documentation |
| `training-data/` | Training data for models |

Root keeps: `CLAUDE.md`, `AGENTS_CONVERSATION.MD`, `pyproject.toml` (workspace), `Makefile` (delegator)

**Cross-module imports:** `uv` workspace with editable deps. `autocode` is importable from `benchmarks/` via workspace wiring.

```bash
# After cloning:
uv sync
```

---

## Where to Find What (Session Index)

| What you need | Where to find it |
|---|---|
| **Active sprint / what to do next** | **`current_directives.md`** |
| Sprint tracking (all sub-sprints) | `docs/plan/sprints/_index.md` |
| Fast session startup | `docs/session-onramp.md` |
| Testing & evaluation guide | `autocode/TESTING.md` |
| Full product roadmap | `docs/plan.md` |
| MVP acceptance checklist | `docs/plan.md` Section 1.6 |
| Feature catalog (built vs planned) | `docs/requirements_and_features.md` |
| Phase 5 plan (next) | `docs/plan/phase5-agent-teams.md` |
| Phase 4 plan (complete) | `docs/plan/phase4-agent-orchestration.md` |
| Phase 3 plan (archived) | `docs/archive/plan/phase3-final-implementation.md` |
| Phase 3 execution brief (archived) | `docs/archive/plan/phase3-execution-brief.md` |
| Benchmark protocol | `docs/qa/phase3-before-after-benchmark-protocol.md` |
| E2E benchmark guide | `docs/qa/e2e-benchmark-guide.md` |
| External benchmark runbook | `docs/plan/agentic-benchmarks/external-benchmark-runbook.md` |
| Agent communication protocol | `AGENT_COMMUNICATION_RULES.md` |
| Agent message log | `AGENTS_CONVERSATION.MD` |
| Message format examples | `docs/reference/comms-examples.md` |
| Tech research (deep dives) | `docs/claude/*.md` |
| Vendor/tool reference | `docs/codex/*.md` |
| Go TUI migration details | `docs/archive/plan/go-bubble-tea-migration.md` |
| Archived conversations | `docs/communication/old/` (read only when asked) |
| Archived/superseded docs | `docs/archive/` |

---

## Agent Communication

All agent-to-agent communication goes through `AGENTS_CONVERSATION.MD`. Protocol rules are in `AGENT_COMMUNICATION_RULES.md`. Use `/comms` to manage messages.

- **Before any action**: check `AGENTS_CONVERSATION.MD` for pending items directed to you
- **NEVER run Codex CLI directly** — write messages in `AGENTS_CONVERSATION.MD`, the user launches other agents
- **NEVER read from `docs/communication/old/`** unless the user explicitly asks — archives are off-limits by default

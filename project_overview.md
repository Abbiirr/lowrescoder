# HybridCoder — Project Overview

## What Is This?

A local-first AI coding assistant CLI that runs on consumer hardware (7-11B models, 8GB VRAM). Think Claude Code, but fully local — no cloud, no API costs, no data leaves your machine.

## Core Architecture: 4-Layer Intelligence

| Layer | What It Does | LLM? | Latency | Tokens |
|-------|-------------|------|---------|--------|
| **L1** Deterministic | tree-sitter, LSP, static analysis | No | <50ms | 0 |
| **L2** Retrieval | AST chunking, BM25 + vector search | No | 100-500ms | 0 |
| **L3** Constrained | Grammar-constrained small model (1.5-3B) | Yes | 500ms-2s | 500-2K |
| **L4** Reasoning | Full 7B model for complex edits | Yes | 5-30s | 2K-8K |

**Key insight:** 60-80% of operations use zero LLM tokens. Classical AI handles what it can; LLMs handle only what it can't.

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| Package Manager | uv |
| CLI | Typer + Rich |
| Parsing | tree-sitter |
| Inline REPL | Rich + prompt_toolkit |
| TUI (opt-in) | Textual |
| LLM (L4) | Ollama + Qwen3-8B |
| LLM (L3) | llama-cpp-python + Outlines |
| Embeddings | jina-v2-base-code |
| Vector DB | LanceDB |
| Session DB | SQLite (WAL mode) |

## Project Structure

```
src/hybridcoder/
  cli.py              # Typer CLI entry point
  config.py           # Pydantic config (env > yaml > defaults)
  core/types.py       # Request/Response/LayerResult types
  inline/
    app.py            # Inline REPL (canonical mode)
    renderer.py       # Rich terminal output
    completer.py      # Tab completion
  tui/
    app.py            # Textual TUI (opt-in)
    commands.py       # 14 slash commands + AppContext protocol
    widgets/          # Textual widgets
  agent/
    loop.py           # Agent loop (max 10 iterations)
    tools.py          # 6 built-in tools (read/write/list/search/run/ask)
    approval.py       # 3-mode approval system
  layer4/llm.py       # Provider abstraction (Ollama/OpenRouter)
  session/store.py    # SQLite session persistence
  utils/file_tools.py # Path-safe file operations
tests/
  unit/               # ~474 tests
  integration/        # 9 tests (require running servers)
  test_sprint_verify.py  # Sprint boundary verification
```

## Current State

- **Phase:** 2E (UI bug fixes + comprehensive testing)
- **Tests:** 474 passed, ruff clean, mypy clean
- **UI Modes:** Inline REPL (canonical) + Textual TUI (opt-in)
- **Commands:** 14 slash commands (/help, /model, /mode, /copy, /thinking, etc.)
- **Agent:** Working agent loop with 6 tools, 3-mode approval, session persistence

## How to Run

```bash
# Install
uv sync

# Run inline REPL (main mode)
uv run hybridcoder chat

# Run Textual TUI
uv run hybridcoder chat --tui

# Run tests
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/
```

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project setup | Done |
| 1 | CLI + LLM foundation | Done |
| 2 | Edit system + TUI + inline REPL | Done (2A-2E) |
| 3 | Code intelligence (L1: tree-sitter/LSP) | Not started |
| 4 | Context & retrieval (L2: embeddings/BM25) | Not started |
| 5 | Agentic workflow (L4: subagents) | Not started |
| 6 | Polish & benchmarking | Not started |

## Agent Communication

- `AGENTS_CONVERSATION.MD` — Active message log between agents
- `AGENT_COMMUNICATION_RULES.md` — Protocols and rules
- `docs/communication/old/` — Archived resolved threads

## Key Design Principles

1. LLM as last resort — deterministic first
2. Fail fast, fail safe — verify edits, git commit for safety
3. Transparent operations — user sees what's happening
4. Local-first — privacy and cost are features
5. Incremental complexity — simple first, sophistication later

## Known Issues

- Windows venv: `uv sync` may fail with "Access is denied" on `.venv/lib64` symlink. Fix: `rm -f .venv/lib64 && uv sync`
- Security review pending (Entries 101/102): shell injection, path traversal, async blocking
- L1/L2 not yet implemented — all requests go directly to L4

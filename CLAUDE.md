# CLAUDE.md - AI Assistant Guidelines for HybridCoder

## Core Philosophy

**I am here to help, but you must always understand what's going on.**

This project is about building an AI coding assistant that YOU control and understand. The same principle applies to our collaboration:

- **Ask questions** when something is unclear
- **Request explanations** for any code or decisions I make
- **Challenge my suggestions** if they don't make sense
- **Don't blindly accept** any code changes without understanding them

You are the developer. I am a tool to accelerate your work, not replace your judgment.

---

## Project Overview

**HybridCoder** is a local-first AI coding assistant CLI that aims to achieve Claude Code-level performance while running on consumer hardware (7-11B parameter models).

### Key Differentiator
The system uses **deterministic classical AI techniques as the primary intelligence layer**, invoking LLMs only when necessary. This is the opposite of how most AI coders work.

| Aspect | Traditional AI Coders | HybridCoder |
|--------|----------------------|-------------|
| LLM Usage | First resort | **Last resort** |
| Resource Requirement | Cloud API / 70B+ models | Local 7B model, 8GB VRAM |
| Latency (simple queries) | 2-5 seconds | <100ms |
| Privacy | Data sent to cloud | Fully local |
| Cost per task | $0.01-$0.50 | $0 (after setup) |

---

## Architecture: The 4-Layer Intelligence Model

Understanding this architecture is critical to working on this project:

### Layer 1: Deterministic Analysis (No LLM)
- Tree-sitter parsing (syntax, structure)
- LSP integration (types, references, definitions)
- Static analysis (Semgrep rules, linting)
- Pattern matching (known refactoring patterns)
- **Latency: <50ms | Tokens: 0**

### Layer 2: Retrieval & Context (No Generative LLM)
- AST-aware code chunking
- Hybrid search (BM25 + vector embeddings)
- Project rules loading (.rules/, AGENTS.md, CLAUDE.md)
- Repository map generation
- **Latency: 100-500ms | Tokens: 0** (embeddings are encoder models, not LLM calls)

### Layer 3: Constrained Generation (Efficient LLM)
- Grammar-constrained decoding (valid syntax guaranteed)
- Small model for simple completions (1.5B-3B)
- Structured output enforcement (JSON, tool calls)
- **Latency: 500ms-2s | Tokens: 500-2000**

### Layer 4: Full Reasoning (Targeted LLM)
- 7B model for complex edits
- Multi-file planning and refactoring
- Architect/Editor pattern for reliability
- Compiler feedback loops (LLMLOOP)
- **Latency: 5-30s | Tokens: 2000-8000**

---

## Target Success Metrics (MVP)

| Metric | Target |
|--------|--------|
| LLM call reduction | 60-80% vs naive approach |
| Edit success rate (first attempt) | >40% |
| Edit success rate (with retry) | >75% |
| Simple query latency | <500ms |
| Agentic task completion | >50% on custom test suite |
| Memory usage (idle) | <2GB RAM (stretch: <500MB) |
| Memory usage (inference) | <8GB VRAM |

---

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | ML ecosystem, rapid dev |
| CLI Framework | Typer + Rich | Modern, type-safe, beautiful |
| Parsing | tree-sitter | Industry standard, fast |
| Python LSP | Pyright | Best type inference |
| Java LSP | JDT-LS | Most complete |
| Vector DB | LanceDB | Embedded, hybrid search |
| Embeddings | jina-v2-base-code | Local, good quality |
| Local LLM | Ollama | Easiest setup |
| Model | Qwen2.5-Coder 7B Q4_K_M | Best 7B code model |
| Grammar | Outlines | Pydantic integration |

---

## Development Phases

1. **Phase 0**: Project Setup
2. **Phase 1**: Foundation - CLI & Basic LLM
3. **Phase 2**: Edit System
4. **Phase 3**: Code Intelligence - Layer 1
5. **Phase 4**: Context & Retrieval - Layer 2
6. **Phase 5**: Agentic Workflow - Layer 4
7. **Phase 6**: Polish & Benchmarking

See `docs/plan.md` for complete phase details and deliverables.

---

## Working With Me On This Project

### When I Write Code
- I will explain WHY I'm making certain architectural decisions
- I will reference which Layer (1-4) a component belongs to
- Ask me to clarify if anything is unclear

### When I Suggest Changes
- I will describe what the change does and why
- I will note any tradeoffs or alternatives considered
- You should understand the change before accepting it

### When Something Fails
- I will help debug, but explain the debugging process
- You should learn from the investigation, not just the fix

### Questions to Ask Me
- "Why did you structure it this way?"
- "What alternatives did you consider?"
- "What are the tradeoffs here?"
- "Can you explain this part in more detail?"
- "How does this fit into the Layer architecture?"

---

## Key Design Principles

1. **LLM as last resort** - Always try deterministic approaches first
2. **Fail fast, fail safe** - Verify edits before applying, git commit for safety
3. **Transparent operations** - User should see what's happening
4. **Local-first** - Privacy and cost are features, not afterthoughts
5. **Incremental complexity** - Start with simple approaches, add sophistication as needed

---

## Reference Documents

- `docs/plan.md` - Full product roadmap and requirements specification
- `docs/spec.md` - System specification with MVP acceptance checklist
- Project rules can be placed in `.rules/` directory

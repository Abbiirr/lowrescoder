# HybridCoder — Master Plan Index

> Edge-Native AI Coding Assistant
> Created: 2026-02-05
> Status: Planning Complete — Ready for Implementation

---

## Plan Documents

| # | Document | Description | File |
|---|----------|-------------|------|
| 00 | **This Index** | Master plan table of contents | `00-master-plan-index.md` |
| 01 | **LLM Inference Research** | Ollama, llama.cpp, Outlines, models, quantization | `01-local-llm-inference-research.md` |
| 02 | **Competitive Analysis** | Market landscape, competitors, gaps | `02-competitive-analysis.md` |
| 03 | **Code Intelligence Research** | tree-sitter, LSP, LanceDB, embeddings, benchmarks | `03-code-intelligence-research.md` |
| P1 | **Phase 1: Tech Stack** | Every component justified with versions and alternatives | `phase1-tech-stack.md` |
| P2 | **Phase 2: HLD** | System architecture, data flow, security, performance | `phase2-hld.md` |
| P3 | **Phase 3: LLD** | Data models, algorithms, APIs, schemas, test mapping | `phase3-lld.md` |
| P4 | **Phase 4: Implementation** | Sprint-by-sprint code plan with file paths and functions | `phase4-implementation.md` |
| P5 | **Phase 5: Documentation** | Docs inventory, CI/CD, quality standards, release process | `phase5-documentation.md` |
| P6 | **Phase 6: Testing & Benchmarks** | Test strategy, 10 benchmark suites, quality gates | `phase6-testing-benchmarking.md` |

---

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layer 4 Model | Qwen3-8B Q4_K_M | Best 8B model, thinking mode, fits 8GB VRAM |
| Layer 3 Model | Qwen2.5-Coder-1.5B Q4_K_M | 72% HumanEval at 1GB VRAM |
| LLM Runtime (L4) | Ollama | Easy setup, model management, streaming |
| LLM Runtime (L3) | llama-cpp-python + Outlines | Outlines requires direct model access |
| Vector DB | LanceDB | Embedded, hybrid search, zero-server |
| Embeddings | jina-v2-base-code (MVP) | 768-dim, local, proven quality |
| Parsing | tree-sitter 0.25.2 | Cross-language, <10ms parse |
| LSP Client | multilspy (Microsoft) | Multi-language, battle-tested |
| Package Manager | uv | 10-100x faster than pip |

---

## Implementation Timeline

```
Week 1      │ S0: Project Setup
Weeks 2-3   │ S1: CLI + LLM Foundation
Weeks 4-5   │ S2: Edit System + Git Safety
Weeks 6-7   │ S3: Layer 1 (tree-sitter + LSP)
Weeks 8-9   │ S4: Layer 2 (Chunking + Search)
Weeks 10-12 │ S5: Layer 4 (Agentic Workflow)
Weeks 13-14 │ S6: Benchmarks + Docs + Release
```

---

## MVP Acceptance Criteria (12 Must-Pass)

1. CLI commands work (chat, ask, edit, config, help)
2. Ollama streams with <2s first token
3. Edit success >40% pass@1
4. Edit with retry >75%
5. Zero file corruption in 100 edits
6. 100% rollback on failures
7. 100% Layer 1 accuracy
8. >60% search precision@3
9. Latency targets met (L1 <50ms, search <200ms, query <500ms)
10. Memory: idle <2GB, inference <8GB VRAM
11. Sandbox blocks disallowed commands
12. Git auto-commit + undo works

---

## Critical Architecture: Outlines + Ollama Incompatibility

**Key finding from research**: Outlines does NOT integrate with Ollama's HTTP API.

**Solution**: Two-tier LLM architecture:
- **Layer 3**: llama-cpp-python + Outlines (guaranteed structured output)
- **Layer 4**: Ollama (free-form reasoning, streaming)

This aligns perfectly with the 4-layer design and is documented in ADR-001.

---

## Edge-Native Competitive Advantage

| Metric | Cloud Tools | HybridCoder |
|--------|------------|-------------|
| Cost/task | $0.01-$0.50 | $0 |
| Latency (simple) | 2-5s | <50ms |
| Works offline | No | Yes |
| Data privacy | Code sent to cloud | 100% local |
| Min hardware | Any (cloud) | 8GB VRAM |
| LLM calls | Every query | 20-40% of queries |

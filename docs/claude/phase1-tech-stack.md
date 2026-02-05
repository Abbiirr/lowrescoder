# Phase 1: Technology Stack Deep Dive

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 2.0 | Date: 2026-02-05
> Based on: docs/plan.md, docs/spec.md, web research (Feb 2026)

---

## 1. Stack Overview

| Layer | Component | Choice | Version | Rationale |
|-------|-----------|--------|---------|-----------|
| Runtime | Python | 3.11+ | 3.11-3.13 | ML ecosystem, async, type hints |
| Packaging | uv | latest | 0.5+ | 10-100x faster than pip, lockfile support |
| CLI | Typer + Rich | Typer 0.12+, Rich 13+ | Type-safe, beautiful output |
| Parsing | tree-sitter | py-tree-sitter 0.25.2 | Industry standard, <10ms parse |
| LSP Client | multilspy | latest | Microsoft's cross-language LSP client |
| Python LSP | Pyright | latest | Best Python type inference (MIT) |
| Java LSP | Eclipse JDT-LS | latest | Most complete Java LSP (requires Java 21) |
| Static Analysis | Semgrep | latest | Pattern-based, custom rules |
| Vector DB | LanceDB | latest | Embedded, hybrid search, zero-server |
| Embeddings | jina-v2-base-code | - | 768-dim, 8K context, ~300MB, local |
| LLM Runtime (L4) | Ollama | 0.5+ | Model management, streaming, easy setup |
| LLM Runtime (L3) | llama-cpp-python | latest | Direct Outlines integration |
| LLM Model (L4) | Qwen3-8B Q4_K_M | - | Best 8B, thinking mode, 5 GB VRAM |
| LLM Model (L3) | Qwen2.5-Coder-1.5B Q4_K_M | - | ~72% HumanEval, ~1 GB VRAM |
| Grammar | Outlines | 0.1+ | Pydantic/JSON/regex/CFG constraints |
| Testing | pytest | 8+ | Standard, fixtures, parametrize |
| Linting | ruff | latest | Fastest Python linter/formatter |
| Type Checking | mypy or pyright | latest | Static type verification |
| CI | GitHub Actions | - | Free for open-source |

---

## 2. Decision Log: Why Each Choice

### 2.1 Python 3.11+
- **Why not Rust/Go**: ML ecosystem (transformers, sentence-transformers, LanceDB) is Python-native. Building in Rust would require FFI for every ML library.
- **Why 3.11+**: `TaskGroup`, `ExceptionGroup`, significant performance improvements (10-60% faster than 3.10), `tomllib` stdlib.
- **Stretch**: Support 3.13 for experimental free-threading (GIL removal) which helps concurrent LSP + LLM calls.

### 2.2 uv (Package Manager)
- **Why not pip/poetry**: uv is 10-100x faster, has built-in lockfile (`uv.lock`), resolver, and venv management.
- **Install**: `pip install uv` or standalone installer
- **Commands**: `uv sync`, `uv run pytest`, `uv add <package>`
- **Risk**: Newer tool, but backed by Astral (ruff creators), rapidly adopted

### 2.3 Typer + Rich (CLI)
- **Why not Click alone**: Typer adds type-hint-driven argument parsing with zero boilerplate
- **Why not argparse**: No color output, no streaming support, verbose
- **Rich** provides: Markdown rendering, syntax highlighting, progress bars, live updating, tables, panels
- **Prompt Toolkit** (optional): For advanced REPL with history, autocomplete, key bindings

### 2.4 tree-sitter (Parsing)
- **Why not AST module**: Python `ast` only handles Python. tree-sitter handles all languages with unified API.
- **Performance**: Parse 10K-line file in <10ms. Incremental reparsing in <1ms.
- **Pre-built wheels**: No native compilation needed for end users
- **Language grammars**: Install per-language (`tree-sitter-python`, `tree-sitter-java`)

### 2.5 multilspy (LSP Client)
- **Why not raw LSP JSON-RPC**: LSP protocol is complex (initialization, capabilities, workspace management). multilspy handles all of it.
- **Why not pylsp/jedi**: We need a CLIENT, not a server. multilspy is a client that connects to ANY language server.
- **Origin**: Microsoft Research — battle-tested in NeurIPS 2023 paper
- **Risk**: Medium — not as widely used as tree-sitter. Mitigation: tree-sitter fallback for everything.

### 2.6 LanceDB (Vector Database)
- **Why not ChromaDB**: LanceDB is truly embedded (no server process), has built-in hybrid search (BM25 + vector), and uses Apache Arrow for zero-copy.
- **Why not Qdrant**: Qdrant requires a server process (docker) — violates edge-native constraint.
- **Why not FAISS**: No built-in BM25, no metadata filtering, no incremental updates.
- **Key advantage**: Serverless, embedded, hybrid search, Pydantic schemas, incremental updates

### 2.7 Two-Tier LLM Architecture (CRITICAL DECISION)

**Problem discovered in research**: Outlines (grammar-constrained generation) does NOT work with Ollama's HTTP API. Outlines requires direct model access via transformers or llama-cpp-python.

**Solution**: Two-tier architecture:
- **Layer 4 (Full Reasoning)**: Ollama — easy setup, model management, streaming, free-form generation
- **Layer 3 (Constrained Generation)**: llama-cpp-python + Outlines — guaranteed valid structured output

This maps perfectly to our layered architecture and is cleaner than trying to force one runtime for both purposes.

### 2.8 Model Selection

#### Layer 4: Qwen3-8B (Q4_K_M)
- **Why upgrade from Qwen2.5-Coder-7B**: Qwen3 has thinking/non-thinking modes, better reasoning, same VRAM footprint
- **VRAM**: ~5 GB (weights) + ~1.5 GB (KV cache 8K) = ~6.5 GB
- **Throughput**: 30-50 tok/s on RTX 3060/3070
- **Thinking mode**: Can toggle between fast responses and deep reasoning per query
- **Fallback**: Qwen2.5-Coder-7B-Instruct if Qwen3-8B has stability issues

#### Layer 3: Qwen2.5-Coder-1.5B (Q4_K_M)
- **Why**: ~72% HumanEval, only ~1 GB VRAM, 80-120 tok/s
- **Sufficient for**: JSON tool calls, edit format generation, routing decisions, simple completions
- **Same tokenizer family**: Compatible prompting patterns
- **Note**: Check if Qwen3-1.5B exists; if yes, evaluate as replacement

#### Memory Budget (Both Models Loaded)
| Component | VRAM |
|-----------|------|
| Qwen3-8B Q4_K_M weights | ~5.0 GB |
| Qwen2.5-Coder-1.5B Q4_K_M weights | ~1.0 GB |
| KV cache (8B, 8K context) | ~1.5 GB |
| KV cache (1.5B, 4K context) | ~0.3 GB |
| **Total** | **~7.8 GB** |

Fits within 8 GB VRAM target. For 6 GB VRAM cards: swap models via Ollama (adds ~2-5s on model switch).

### 2.9 Embedding Model: jina-v2-base-code
- **Why for MVP**: Proven, 768-dim, 8K context, ~300MB, fast inference
- **Upgrade path**: jina-v3 (flexible dims, task adapters) or Nomic Embed Code (code-specialized)
- **Local inference**: sentence-transformers library, runs on CPU or GPU
- **Indexing speed**: ~100 chunks/sec on CPU, ~1000/sec on GPU

### 2.10 Outlines (Grammar Constraints)
- **Version**: 0.1.x (dottxt-ai/outlines)
- **Backend**: Uses outlines-core (Rust) for FSM computation
- **Integration**: `outlines.models.llamacpp.LlamaCpp` + `outlines.generate.json`
- **Performance overhead**: ~1-5% throughput reduction, one-time FSM build (1-30s, cached)
- **Value**: Eliminates 100% of JSON parsing failures in structured output

---

## 3. Dependency Matrix

### Core Dependencies
```toml
[project]
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "rich>=13.0",
    "prompt-toolkit>=3.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "tree-sitter>=0.25",
    "tree-sitter-python>=0.23",
    "tree-sitter-java>=0.23",
    "multilspy>=0.1",
    "lancedb>=0.10",
    "sentence-transformers>=3.0",
    "ollama>=0.4",
    "llama-cpp-python>=0.3",
    "outlines>=0.1",
    "gitpython>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "mypy>=1.10",
    "pre-commit>=3.7",
]
```

### External Tools (Not pip-installable)
| Tool | Install Method | Required For |
|------|---------------|-------------|
| Ollama | OS installer | Layer 4 LLM inference |
| Pyright | `npm install -g pyright` or `pip install pyright` | Python LSP |
| JDT-LS | Download JAR + Java 21 | Java LSP (optional) |
| Semgrep | `pip install semgrep` | Static analysis rules |
| Git | OS package | Version control |

---

## 4. Hardware Baseline

### Minimum (8GB VRAM)
- GPU: NVIDIA RTX 3060 / 4060 (8GB) or equivalent AMD
- RAM: 16 GB
- Storage: 10 GB free (models + index)
- CPU: 4+ cores
- OS: Windows 10/11, macOS 12+, Ubuntu 20.04+

### Recommended (12-16GB VRAM)
- GPU: NVIDIA RTX 3080 / 4070 (12GB)
- RAM: 32 GB
- Both models loaded simultaneously with room for larger context

### CPU-Only Mode (No GPU)
- RAM: 32 GB minimum
- Performance: 8-15 tok/s (workable but slow for Layer 4)
- Layer 1-2 unaffected (no GPU needed)
- Recommended: Use Q2_K or IQ2 quantization for smaller memory footprint

### Apple Silicon
- M1/M2/M3 with 16GB+ unified memory
- Use Ollama (Metal backend) or mlx-lm
- Performance: 25-50 tok/s (excellent for local inference)

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Outlines + llama-cpp-python version mismatch | Medium | High | Pin versions, integration test in CI |
| multilspy instability | Medium | Medium | Tree-sitter fallback for all Layer 1 queries |
| Qwen3-8B not available in Ollama | Low | Medium | Fall back to Qwen2.5-Coder-7B |
| LanceDB hybrid search limitations | Low | Medium | Implement BM25 separately (rank-bm25 library) |
| 8GB VRAM too tight for dual models | Medium | High | Model swapping via Ollama (adds 2-5s latency) |
| sentence-transformers memory spike during embedding | Low | Medium | Batch processing, limit concurrent operations |

---

## 6. Version Pinning Strategy

- **Lock file**: `uv.lock` for exact reproducibility
- **Pin strategy**: Pin major.minor, allow patch updates
- **Critical pins**: Outlines + llama-cpp-python must be tested together
- **CI matrix**: Test on Python 3.11, 3.12, 3.13

---

## 7. Install Flow (End User)

```bash
# 1. Install Ollama
# Visit https://ollama.com and install for your OS

# 2. Pull models
ollama pull qwen3:8b
# OR for Qwen2.5-Coder fallback:
# ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# 3. Install HybridCoder
pip install hybridcoder
# OR from source:
git clone https://github.com/youruser/hybridcoder
cd hybridcoder
uv sync

# 4. Verify
hybridcoder --help
hybridcoder config --check
```

# Phase 2: High-Level Design (HLD)

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 2.0 | Date: 2026-02-05

---

## 1. System Context

```
┌─────────────────────────────────────────────────────────┐
│                    USER (Developer)                       │
│  Terminal / CLI                                           │
└───────────────────────┬─────────────────────────────────┘
                        │ stdin/stdout (streaming)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   HYBRIDCODER CLI                         │
│  Commands: chat, ask, edit, config, help                  │
│  REPL: streaming output, history, Ctrl+C                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   CORE ROUTER                             │
│  Classifies request → routes to lowest-cost layer         │
│  Manages escalation: L1 → L2 → L3 → L4                  │
└──┬──────────┬──────────┬──────────┬─────────────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐
│ L1   │ │ L2   │ │ L3   │ │ L4           │
│Determ│ │Retrvl│ │Constr│ │Full Reasoning│
│ <50ms│ │<500ms│ │ <2s  │ │   <30s       │
│0 tok │ │0 tok │ │~1K   │ │  ~5K tok     │
└──┬───┘ └──┬───┘ └──┬───┘ └──────┬───────┘
   │        │        │             │
   ▼        ▼        ▼             ▼
┌──────────────────────────────────────────────────────────┐
│                 SHARED SERVICES                           │
│  File Manager │ Git Manager │ Shell Executor │ Config     │
│  Cache        │ Logging     │ Metrics                     │
└──────────────────────────────────────────────────────────┘
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
      ┌─────────┐ ┌─────────┐ ┌──────────┐
      │ Ollama  │ │llama.cpp│ │ LanceDB  │
      │ Server  │ │+Outlines│ │ (local)  │
      │ (L4)    │ │ (L3)    │ │ (L2)     │
      └─────────┘ └─────────┘ └──────────┘
      ┌─────────┐ ┌─────────┐ ┌──────────┐
      │tree-sit │ │multilspy│ │ Semgrep  │
      │ (L1)    │ │ (L1)    │ │ (L1)     │
      └─────────┘ └─────────┘ └──────────┘
```

---

## 2. Request Flow

### 2.1 Simple Query (e.g., "What type is `user_id`?")
```
User Input → CLI → Router
  → Router classifies: DETERMINISTIC_QUERY
  → Route to Layer 1
  → L1: tree-sitter parse → find symbol → LSP hover → return type info
  → CLI: Display result
  → Latency: <50ms, Tokens: 0
```

### 2.2 Code Search (e.g., "Find where authentication is handled")
```
User Input → CLI → Router
  → Router classifies: SEMANTIC_SEARCH
  → Route to Layer 2
  → L2: BM25 search + vector search → RRF fusion → top-k results
  → CLI: Display ranked results with file paths and snippets
  → Latency: <200ms, Tokens: 0
```

### 2.3 Simple Edit (e.g., "Add a docstring to this function")
```
User Input → CLI → Router
  → Router classifies: SIMPLE_EDIT
  → Route to Layer 3
  → L3: Load context (L2) → Constrained generation (Outlines) → Validate output
  → Edit System: Parse diff → Show preview → Apply → Lint → Git commit
  → Latency: <2s, Tokens: ~500-1000
```

### 2.4 Complex Task (e.g., "Refactor auth module to use JWT")
```
User Input → CLI → Router
  → Router classifies: COMPLEX_TASK
  → Route to Layer 4
  → L4 Architect: Analyze codebase (L1+L2) → Create plan → User approval
  → L4 Editor (per step):
    → Generate edit → Validate syntax → Type check → Lint → Test
    → If fail: retry (max 3) with error feedback
    → If pass: Git commit
  → CLI: Stream progress, show diffs
  → Latency: 5-30s, Tokens: ~2000-8000
```

---

## 3. Component Responsibilities

### 3.1 CLI Layer (`cli.py`)
- Parse commands (chat, ask, edit, config, help)
- REPL loop with streaming token output
- Command history (prompt-toolkit)
- Ctrl+C graceful cancellation
- Progress indicators (Rich spinners, progress bars)
- **No business logic** — pure I/O

### 3.2 Core Router (`core/router.py`)
- Accept user input + context
- Classify request type:
  - `DETERMINISTIC_QUERY` → Layer 1
  - `SEMANTIC_SEARCH` → Layer 2
  - `SIMPLE_EDIT` → Layer 3
  - `COMPLEX_TASK` → Layer 4
  - `CONFIGURATION` → Config manager
  - `HELP` → Built-in help
- Classification uses keyword matching + regex patterns (no LLM)
- Escalation logic: if Layer N fails, try Layer N+1

### 3.3 Layer 1 Engine (`layer1/`)
- **Parser** (`parser.py`): tree-sitter parsing, AST traversal, symbol extraction
- **LSP Client** (`lsp.py`): multilspy wrapper for Pyright/JDT-LS
- **Queries** (`queries.py`): Deterministic query handlers
  - `find_references(symbol, file)` → LSP
  - `find_definition(symbol, file)` → LSP
  - `get_type(symbol, file)` → LSP hover
  - `list_symbols(file)` → tree-sitter
  - `list_imports(file)` → tree-sitter
  - `get_signature(function, file)` → LSP
- **Cache**: Parse trees cached per file (invalidate on modify), LSP results cached 30s TTL

### 3.4 Layer 2 Engine (`layer2/`)
- **Chunker** (`chunker.py`): AST-aware code chunking
  - Respect function/class boundaries
  - Max 1000 tokens, min 50 tokens
  - 10-line overlap between chunks
  - Metadata: file path, language, chunk type, scope chain, imports
- **Embeddings** (`embeddings.py`): sentence-transformers wrapper
  - Batch embedding generation
  - GPU or CPU inference
- **Search** (`search.py`): Hybrid search orchestrator
  - BM25 search via LanceDB FTS
  - Vector search via LanceDB
  - RRF fusion (configurable weights: default 50/50)
  - Language/path/type filters
- **Repo Map** (`repomap.py`): Generate ranked symbol map of project
- **Index** (`index.py`): LanceDB table management, incremental updates
- **Rules** (`rules.py`): Load project rules from `.rules/`, `AGENTS.md`, `CLAUDE.md`

### 3.5 Layer 3 Engine (`layer3/`)
- **LLM Client** (`llm.py`): llama-cpp-python wrapper
  - Model loading/unloading
  - Outlines integration for constrained generation
- **Grammar** (`grammar.py`): Pydantic models for structured outputs
  - `EditInstruction`, `ToolCall`, `RoutingDecision`, `SearchQuery`
- **Output Parser** (`output.py`): Validate and extract structured output
- **Small model only**: Qwen2.5-Coder-1.5B for simple structured tasks

### 3.6 Layer 4 Engine (`layer4/`)
- **LLM Client** (`llm.py`): Ollama async client wrapper
  - Streaming generation
  - Message history management
  - Token counting
- **Planner** (`planner.py`): Architect role — analyze + create plan
- **Editor** (`editor.py`): Editor role — execute plan steps
- **Tools** (`tools.py`): Tool registry and execution
  - `read_file`, `write_file`, `search_code`, `run_command`, `find_references`, `get_diagnostics`
- **Feedback** (`feedback.py`): LLMLOOP — syntax check → type check → lint → test → retry
- **Executor** (`executor.py`): Orchestrate multi-step task execution

### 3.7 Edit System (`edit/`)
- **Formats** (`formats.py`): Parse whole-file and search/replace edit formats
- **Fuzzy** (`fuzzy.py`): Fuzzy matching for search/replace blocks
  - Exact → Normalized whitespace → Levenshtein (>80%) → Line-anchored
- **Apply** (`apply.py`): Apply edits with verification
  - Parse → Validate syntax (tree-sitter) → Show diff → Apply → Lint → Commit
- **Diff** (`diff.py`): Generate and display unified diffs (Rich formatting)

### 3.8 Git Manager (`git/manager.py`)
- Auto-commit on successful edits with `[AI]` prefix
- Undo command: revert last AI commit
- Branch management for multi-step tasks
- Diff generation for preview
- Uses GitPython library

### 3.9 Shell Executor (`shell/executor.py`)
- Sandboxed command execution
- Allowlist/blocklist enforcement
- Timeout management (default 30s, max 300s)
- Working directory restriction
- Output capture and streaming

### 3.10 Configuration (`config.py`)
- YAML-based config at `~/.hybridcoder/config.yaml`
- Pydantic models for validation
- Sensible defaults for all settings
- Runtime override via CLI flags

### 3.11 Shared Services
- **Cache** (`utils/cache.py`): LRU cache with TTL, per-file invalidation
- **Logging** (`utils/logging.py`): Structured logging with levels, per-request metrics
- **Metrics** (`utils/metrics.py`): Latency, token usage, layer hit rates

---

## 4. Data Flow Diagram

```
                    User Query
                        │
                        ▼
                 ┌──────────────┐
                 │  CLI Parser  │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Core Router  │◄── Classification Rules (regex/keyword)
                 └──┬───┬───┬──┘
                    │   │   │
         ┌──────────┘   │   └──────────┐
         ▼              ▼              ▼
    ┌─────────┐  ┌───────────┐  ┌───────────┐
    │ Layer 1 │  │ Layer 2   │  │ Layer 3/4 │
    │(Determ.)│  │(Retrieval)│  │  (LLM)    │
    └────┬────┘  └─────┬─────┘  └─────┬─────┘
         │             │              │
         │        ┌────┘              │
         │        ▼                   ▼
         │   ┌─────────┐      ┌────────────┐
         │   │ Context  │      │  Edit      │
         │   │ Assembly │─────►│  System    │
         │   └─────────┘      └──────┬─────┘
         │                           │
         │                           ▼
         │                    ┌────────────┐
         │                    │ Git Manager│
         │                    └──────┬─────┘
         │                           │
         └───────────┬───────────────┘
                     ▼
              ┌────────────┐
              │  Response   │
              │  to User    │
              └────────────┘
```

---

## 5. Configuration Architecture

### 5.1 Config Hierarchy (lowest wins)
1. Built-in defaults (in code)
2. `~/.hybridcoder/config.yaml` (user global)
3. `.hybridcoder.yaml` (project-level)
4. CLI flags (per-invocation)
5. Environment variables (`HYBRIDCODER_*`)

### 5.2 Key Config Sections
```yaml
llm:
  provider: ollama          # ollama | openai | anthropic
  model: qwen3:8b           # Ollama model name
  api_base: http://localhost:11434
  temperature: 0.2
  max_tokens: 4096
  context_length: 8192

layer3:
  enabled: true
  model_path: ~/.hybridcoder/models/qwen2.5-coder-1.5b-q4_k_m.gguf
  grammar_constrained: true

layers:
  layer1: {enabled: true, cache_ttl: 300}
  layer2:
    enabled: true
    embedding_model: jinaai/jina-embeddings-v2-base-code
    search_top_k: 10
    chunk_size: 1000
    hybrid_weight: 0.5  # 0=BM25 only, 1=vector only

edit:
  format: whole_file        # whole_file | search_replace
  fuzzy_threshold: 0.8
  auto_commit: true

git:
  auto_commit: true
  commit_prefix: "[AI]"

shell:
  timeout: 30
  max_timeout: 300
  allowed_commands: [pytest, python, pip, mvn, gradle, git]
  blocked_commands: ["rm -rf", sudo, curl, wget]
  allow_network: false

ui:
  theme: dark
  show_diff: true
  confirm_edits: true
  stream_output: true
  verbose: false
```

---

## 6. Security Architecture

### 6.1 Threat Model
- **Primary threat**: LLM generating malicious shell commands
- **Secondary**: Data exfiltration via network commands
- **Tertiary**: File corruption from bad edits

### 6.2 Mitigations
| Threat | Mitigation |
|--------|-----------|
| Malicious commands | Shell allowlist + blocklist |
| Network exfiltration | Network commands blocked by default |
| File corruption | Git auto-commit before edit, rollback on failure |
| Path traversal | Working directory restricted to project root |
| Resource exhaustion | Timeout (30s), memory limit, max retries |
| Prompt injection | System prompt isolation, tool output sanitization |

### 6.3 Sandbox Design
```
┌─────────────────────────────┐
│ Shell Executor              │
│ ┌─────────────────────────┐ │
│ │ Command Validator       │ │  ← Check allowlist/blocklist
│ │ ┌───────────────────┐   │ │
│ │ │ Subprocess         │   │ │  ← Restricted cwd, timeout
│ │ │ (isolated)         │   │ │  ← No network (default)
│ │ └───────────────────┘   │ │
│ └─────────────────────────┘ │
│ Output Capture + Truncation │  ← Limit output size
└─────────────────────────────┘
```

---

## 7. Performance Architecture

### 7.1 Latency Budgets
| Operation | Budget | Strategy |
|-----------|--------|----------|
| Router classification | <5ms | Regex/keyword rules in-memory |
| tree-sitter parse | <10ms | Cached parse trees |
| Symbol extraction | <20ms | Walk cached AST |
| LSP query | <100ms | Cached results, 30s TTL |
| BM25 search | <50ms | LanceDB FTS index |
| Vector search | <150ms | LanceDB ANN index |
| Hybrid search | <200ms | Parallel BM25 + vector + fusion |
| Embedding (single) | <100ms | GPU batch, or ~300ms CPU |
| L3 generation | <2s | 1.5B model, 500-2000 tokens |
| L4 generation | <30s | 8B model, 2000-8000 tokens |
| Full edit flow | <5s | L3 gen + parse + lint + commit |

### 7.2 Caching Strategy
| Cache | Scope | TTL | Invalidation |
|-------|-------|-----|-------------|
| Parse trees | Per-file | Until modified | File watcher / mtime check |
| Symbol tables | Per-file | Until modified | Derived from parse tree |
| LSP results | Per-query | 30s | Time-based |
| Embeddings | Per-chunk | Until modified | File hash change |
| Search results | Per-query | 10s | Time-based |
| LLM responses | None | - | Not cached (non-deterministic) |

### 7.3 Startup Optimization
- **Cold start target**: <2s
- Load config: <10ms
- Initialize CLI: <50ms
- Connect Ollama: <100ms (lazy, on first LLM call)
- Load tree-sitter: <50ms
- Open LanceDB: <100ms
- LSP server start: <1s (lazy, on first L1 query)

---

## 8. Deployment Model

### Single-Machine, Single-User
- All components run on one machine
- No server processes except Ollama (background daemon)
- LanceDB is embedded (no separate process)
- CLI is the only user interface

### Process Model
```
hybridcoder (main process)
  ├── Ollama (external daemon, HTTP on localhost:11434)
  ├── llama-cpp-python (in-process, loaded on demand)
  ├── Pyright (subprocess, managed by multilspy)
  ├── JDT-LS (subprocess, managed by multilspy, optional)
  └── Semgrep (subprocess, invoked on demand)
```

---

## 9. Module Dependency Graph

```
cli.py
  └── core/router.py
        ├── layer1/
        │     ├── parser.py      ← tree-sitter
        │     ├── lsp.py         ← multilspy (Pyright, JDT-LS)
        │     └── queries.py     ← parser + lsp
        ├── layer2/
        │     ├── chunker.py     ← parser (AST-aware)
        │     ├── embeddings.py  ← sentence-transformers
        │     ├── search.py      ← LanceDB
        │     ├── repomap.py     ← parser + search
        │     ├── index.py       ← LanceDB
        │     └── rules.py       ← file I/O
        ├── layer3/
        │     ├── llm.py         ← llama-cpp-python
        │     ├── grammar.py     ← outlines + pydantic
        │     └── output.py      ← grammar
        ├── layer4/
        │     ├── llm.py         ← ollama
        │     ├── planner.py     ← llm + layer2 (context)
        │     ├── editor.py      ← llm + edit system
        │     ├── tools.py       ← file manager + shell + layer1
        │     ├── feedback.py    ← shell (tests) + layer1 (lint)
        │     └── executor.py    ← planner + editor + feedback
        ├── edit/
        │     ├── formats.py     ← parsing edit output
        │     ├── fuzzy.py       ← string matching
        │     ├── apply.py       ← file manager + git
        │     └── diff.py        ← rich formatting
        ├── git/
        │     └── manager.py     ← gitpython
        ├── shell/
        │     └── executor.py    ← subprocess
        ├── config.py            ← pydantic + yaml
        └── utils/
              ├── cache.py
              ├── logging.py
              └── metrics.py
```

---

## 10. Edge-Native Design Checklist

Every component must pass this checklist:

- [ ] Runs 100% locally — no external network calls
- [ ] Fits within 8 GB VRAM + 16 GB RAM budget
- [ ] Has a defined latency budget
- [ ] Degrades gracefully if GPU unavailable (CPU fallback)
- [ ] Does not require Docker, cloud services, or server processes (except Ollama)
- [ ] Produces deterministic results where possible (L1, L2 search)
- [ ] Can function without internet after initial model download
- [ ] Logs performance metrics for profiling

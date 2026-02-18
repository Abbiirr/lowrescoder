# AutoCode: Low-Resource AI Coding Agent
## Product Roadmap & Requirements Specification

> Quick links for current implementation context:
> - `docs/session-onramp.md` (fast session startup)
> - `docs/plan/phase5-agent-teams.md` (Phase 5 plan — current phase, PROVISIONAL_LOCKED)
> - `docs/plan/phase5-roadmap-lock-checklist.md` (Phase 5 lock criteria)
> - `docs/plan/phase4-agent-orchestration.md` (Phase 4 plan — COMPLETE)
> - `docs/archive/plan/phase3-execution-brief.md` (Phase 3 completion summary)

**Version:** 1.1
**Last Updated:** February 17, 2026
**Target:** Solo Developer MVP
**Languages:** Python, Java
**Platform:** Local CLI Tool (Windows, macOS, Linux)

---

## 1. Vision & Objectives

### 1.1 Product Vision
A local-first AI coding assistant CLI that achieves Claude Code-level performance while running on consumer hardware (7-11B parameter models). The system uses deterministic classical AI techniques as the primary intelligence layer, invoking LLMs only when necessary.

**Performance Target Proxy**: Achieve >40% pass@1 on Aider polyglot benchmark subset (comparable to GPT-4 baseline on similar tasks) while using 60-80% fewer LLM tokens than a naive always-call-LLM approach. See Appendix D for full benchmark definition.

### 1.2 Core Differentiators
| Aspect | Traditional AI Coders | AutoCode |
|--------|----------------------|-------------|
| LLM Usage | First resort | Last resort |
| Resource Requirement | Cloud API / 70B+ models | Local 7B model, 8GB VRAM |
| Latency (simple queries) | 2-5 seconds | <100ms |
| Privacy | Data sent to cloud | Fully local |
| Cost per task | $0.01-$0.50 | $0 (after setup) |

### 1.3 Competitive Landscape (Feb 2026)

| Tool | Local? | LLM-First? | Min VRAM | Cost | Edge-Native? |
|------|--------|-----------|----------|------|-------------|
| Claude Code | No | Yes | N/A | $$$ | No |
| Cursor | No | Yes | N/A | $20/mo | No |
| Copilot CLI | No | Yes | N/A | $10/mo | No |
| Aider | Optional | Yes | 8GB+ | Free+API | No |
| Cline | Optional | Yes | 8GB+ | Free+API | No |
| **AutoCode** | **Yes** | **No** | **8GB** | **$0** | **YES** |

Additional positioning points:
- **Zero-Cost After Setup** — Once installed, every task is free. No API keys, no subscriptions, no metered billing.
- **Air-Gap Ready** — Works on laptops without internet, air-gapped corporate networks, developer machines in regions with poor connectivity, and for developers who refuse to send proprietary code to third-party servers.

### 1.4 Target Users and Use Cases

- Solo or small-team developers who want a local, privacy-preserving coding assistant.
- Common tasks:
  - Ask questions about a codebase (symbols, types, references).
  - Generate or refactor code safely with diffs and undo.
  - Run tests/lints and iterate on failures.
  - Search across large repos with hybrid lexical + semantic retrieval.

### 1.5 Success Metrics (MVP)
| Metric | Target | Verification Method |
|--------|--------|---------------------|
| LLM call reduction | 60-80% vs naive approach | Instrumentation logging |
| Edit success rate (first attempt) | >40% | Aider benchmark subset |
| Edit success rate (with retry) | >75% | Aider benchmark subset |
| Simple query latency | <500ms | Automated timing tests |
| Agentic task completion | >50% on custom test suite | Manual + automated tests |
| Memory usage (idle) | <2GB RAM (stretch: <500MB) | System monitoring |
| Memory usage (inference) | <8GB VRAM | System monitoring |

### 1.6 MVP Acceptance Checklist

The following 12 criteria must ALL pass for MVP release:

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | CLI operational | `autocode chat`, `ask`, `edit`, `config`, `--help` commands work |
| 2 | Local LLM integration | Ollama provider streams responses with <2s to first token |
| 3 | Edit success rate | >40% pass@1 on 50-task Aider benchmark subset |
| 4 | Edit with retry | >75% success after up to 3 retries |
| 5 | No data loss | 0 file corruptions across 100 edit operations |
| 6 | Rollback works | 100% of failed edits restore original file state |
| 7 | Layer 1 accuracy | 100% correct on deterministic query test suite (find refs, go-to-def, list symbols) |
| 8 | Search relevance | >60% precision@3 on custom retrieval test suite |
| 9 | Latency targets | Layer 1 <50ms, hybrid search <200ms, simple query <500ms |
| 10 | Memory limits | Idle <2GB RAM, inference <8GB VRAM |
| 11 | Sandbox enforced | Blocked commands rejected, timeout kills long-running processes |
| 12 | Git safety | Every successful edit creates commit; `/undo` reverts cleanly |

### 1.7 Scope

**In Scope (MVP)**
- Local CLI with chat, ask, edit, config, and help commands.
- Layered intelligence model (deterministic -> retrieval -> constrained generation -> full reasoning).
- Deterministic code intelligence for Python and Java (tree-sitter + LSP).
- Reliable edit system with diff preview, verification, retry, and undo.
- Local retrieval index with hybrid search (BM25 + embeddings).
- Sandboxed tool execution (tests, linting, type checks).
- Git integration with automatic commits and rollback.

**Out of Scope (MVP)**
- IDE plugins (VS Code/JetBrains) beyond LSP usage.
- Cloud-hosted SaaS or multi-tenant deployments.
- Full multi-language support beyond Python/Java.
- Automated code review or security scanning beyond basic rules.

### 1.8 Open Questions and Decisions

**Resolved:**
- Memory target: <2GB idle (stretch goal: <500MB)
- Default edit format: whole-file (search/replace deferred to Phase 2.5+)

**Open:**
- Python-only MVP vs Python+Java (recommendation: Python-only to reduce scope risk)
- Cloud fallback policy and opt-in UX

**Resolved (Feb 2026):**
- Embedding model: jina-v2-base-code (768-dim, local, proven quality)
- L4 model: Qwen3-8B Q4_K_M (supersedes Qwen2.5-Coder-7B)
- L3 model: Qwen2.5-Coder-1.5B Q4_K_M (constrained generation)
- Two-tier LLM: Ollama (L4) + llama-cpp-python with native grammar (L3)
- Python semantic intelligence: Jedi (preferred over multilspy LSP)
- Package manager: uv
- TUI Frontend: Go + Bubble Tea (inline mode, JSON-RPC over stdin/stdout to Python backend). See `docs/archive/plan/go-bubble-tea-migration.md` for full plan.

---

## 2. Architecture Overview

### 2.1 Layered Intelligence Model

> See CLAUDE.md "Architecture: 4-Layer Intelligence Model" for the canonical layer descriptions.

Request flow: User Request → Layer 1 (deterministic, <50ms, 0 tokens) → Layer 2 (retrieval, 100-500ms, 0 tokens) → Layer 3 (constrained generation, 500ms-2s) → Layer 4 (full reasoning, 5-30s). Each layer escalates only if it cannot resolve the request.

---

## 3. Development Phases

### Phase 0: Project Setup — COMPLETE

Repository structure, development environment (Python 3.11+, uv), CI/CD pipeline, and core dependency audit all complete. See `docs/requirements_and_features.md` Section 2 for the full feature catalog.

---

### Phase 1: Foundation - CLI & Basic LLM — COMPLETE

Functional CLI (chat, ask, edit, config, serve, --help), Ollama + OpenRouter LLM providers, streaming output, file read/write tools, configuration system, and command history all complete. 6 agent tools, 14 slash commands, Go TUI + Python inline REPL. See `docs/requirements_and_features.md` Sections 2.1-2.12 for details.

---

### Phase 2: Edit System — COMPLETE

Whole-file edit format, search/replace parser, fuzzy matching (>80% threshold), git auto-commit, undo command, diff preview, edit retry logic (max 3), approval system, session management, Go Bubble Tea TUI rewrite. 784+ tests passing. See `docs/requirements_and_features.md` Sections 2.1-2.12 for details.

---

### Phase 3: Code Intelligence (Layer 1 + Layer 2) — COMPLETE

Phase 3 consolidated both deterministic analysis (L1) and retrieval/context (L2) into a single phase. Implementation completed 2026-02-13. 840 Python tests passing, ruff clean, mypy clean, all Go tests passing.

#### What Was Built

| Sprint | Deliverables |
|--------|-------------|
| 3A | Tree-sitter Python parser with mtime LRU cache (500 entries), symbol extraction (functions, classes, methods, imports, variables) |
| 3B | 3-stage request router (regex → feature extraction → weighted scoring), deterministic query handlers (list_symbols, find_definition, find_references, get_imports, show_signature) |
| 3D | AST-aware chunker (function/class boundaries, 200-800 token chunks), embedding engine (jina-v2-base-code, lazy-loaded), BM25 fallback |
| 3E | LanceDB code index (file-hash invalidation, incremental updates, gitignore-aware), hybrid search (BM25 + vector + RRF fusion) |
| 3F | Repo map generator (ranked symbol summary, 600-token budget), rules loader (CLAUDE.md, .rules/, .cursorrules), context assembler (5000-token budget) |
| 3G | 5 new agent tools (11 total), L1 bypass in server, `/index` command, Go TUI layer indicator `[L1]`/`[L2]`/`[L4]`, context injection in prompts, syntax validator |

#### Deferred (Not Phase 3)
- Sprint 3C: LSP integration (multilspy/Jedi)
- `get_diagnostics` tool (requires LSP)
- Java support (Python-first approach validated)

#### Gate Results

- [x] **Gate 1 (Deterministic):** Router accuracy >= 90% on 50-query benchmark. L1 latency p95 < 50ms. 0 tokens used.
- [x] **Gate 2 (Retrieval):** Search precision@3 > 60%. Context budget <= 5000 tokens. BM25-only fallback works.
- [x] **Gate 3 (Integration):** 11 tools registered. `on_done` includes `layer_used`. TUI shows layer indicator. `/index` command works. 840 tests pass. Ruff clean. Mypy clean.

#### New Files (14 Python source + 15 test files)
- `src/autocode/layer1/`: `__init__.py`, `parser.py`, `symbols.py`, `queries.py`, `validators.py`
- `src/autocode/layer2/`: `__init__.py`, `chunker.py`, `embeddings.py`, `index.py`, `search.py`, `repomap.py`, `rules.py`
- `src/autocode/core/`: `router.py`, `context.py`

See `docs/archive/plan/phase3-final-implementation.md` for the authoritative spec and `docs/archive/plan/phase3-execution-brief.md` for completion summary.

---

### Phase 4: Agent Orchestration — COMPLETE (2026-02-14)

> Authoritative plan: `docs/plan/phase4-agent-orchestration.md` (v3.2a)
> Feature catalog: `docs/requirements_and_features.md` Section 3.1

Phase 4 implemented the agentic workflow layer: agent loop with tool calling, 19-tool registry, approval system, task management, subagent orchestration, plan mode, memory/checkpoints, and E2E evaluation framework.

**Sprints completed:**
- 4A: Core Primitives (ContextEngine, LLM scheduler, event recorder, blob store, episode store)
- 4B: Subagents + Plan Mode (SubagentLoop, SubagentManager, plan mode, task tools, subagent tools)
- 4C: Memory + Checkpoints + L2/L3 wiring + Plan Artifact + Go Task Panel

**Gate results:** 987 collected, 978 passed, 9 skipped (8 Ollama + 1 OpenRouter rate limit), 0 failed, ruff clean.

**Original Phase 4 objectives from this doc** (tool framework, feedback loops, Architect/Editor) are partially delivered and partially deferred to Phase 5:
- [x] Tool framework (19 tools, extensible registry)
- [x] Shell executor (sandboxed, timeout-enforced)
- [x] Task persistence (SQLite task store + checkpoints)
- [x] Progress reporting (Go TUI task panel, streaming indicators)
- [ ] LLMLOOP feedback loop → Phase 5 Sprint 5B
- [ ] Architect/Editor split → Phase 5 Sprint 5B
- [ ] Multi-file editing coordination → Phase 5 Sprint 5B

---

### Phase 5: Universal Orchestrator — Agent Teams & Multi-Model — PROVISIONAL_LOCKED (2026-02-17)

> Authoritative plan: `docs/plan/phase5-agent-teams.md`
> Lock checklist: `docs/plan/phase5-roadmap-lock-checklist.md`
> Strategy: **"Standalone first, then interact."**

Phase 5 transforms AutoCode from a single-agent assistant into a feature-complete standalone AI coding tool, then adds external tool integration.

**Sprint order:**
| Sprint | Focus | Gate |
|--------|-------|------|
| 5A0 | Quick Wins (diff preview, doctor, token counting) | User-visible improvements |
| 5A | Agent Identity + Eval Skeleton | AgentCard, ProviderRegistry, eval harness |
| 5B | LLMLOOP (Architect/Editor) | Edit→compile→fix cycle, tree-sitter+Jedi verification |
| 5C | Evals + AgentBus + Cost Dashboard | Context quality, reliability soak, cost tracking |
| 5D | MCP Server + External Integration | MCP server, config generator, adapter compat matrix |

> Sprint 5E (A2A) **dropped** from Phase 5 scope. Not a Phase 5 dependency; WATCHLIST for Phase 6+ re-evaluation.

**Milestone gates (from Entry 448):**
- M1+M2 (Standalone MVP): >= 75% task bank pass, p95 <= 180s, 0 hard-fail regressions
- M3 (External Integration): health probes pass, idempotent setup/uninstall

**Original "Phase 5: Testing & Benchmarking" from this doc** was largely delivered in Phases 3-4:
- [x] Benchmark suite (E2E-Calculator, E2E-BugFix, E2E-CLI)
- [x] Unit + integration test coverage (989+ tests)
- [x] Performance benchmarks (L1 latency, search relevance)
- [x] Reliability regression suite (sprint verification tests)
- [ ] External benchmark integration (SWE-bench, Terminal-Bench) → Phase 5 Sprint 5C

---

## 4. Technical Specifications

### 4.0 External Dependencies and Constraints

| Dependency | Details |
|------------|---------|
| tree-sitter | Incremental parsing to maintain syntax trees during edits |
| LSP | JSON-RPC protocol for language intelligence; spec 3.17 |
| Pyright | Python type checking CLI (npm or pip wrapper) |
| Eclipse JDT LS | Java LSP server; requires Java 21 runtime |
| Semgrep | Open-source, pattern-based static analysis rules |
| LanceDB | Local/embedded vector database with vector search and optional full-text (BM25) search |
| Embeddings | jina-embeddings-v2-base-code (768-dim, 8192 tokens, ~300MB model size) |
| LLM Runtime (L4) | Ollama local server (HTTP API at http://localhost:11434/api by default) |
| LLM Runtime (L3) | llama-cpp-python + native grammar (direct model access for constrained decoding) |
| LLM Model (L4) | Qwen3-8B Q4_K_M (~5 GB VRAM, thinking mode) |
| LLM Model (L3) | Qwen2.5-Coder-1.5B Q4_K_M (~1 GB VRAM, 72% HumanEval) |
| Constrained Decoding | llama-cpp-python native grammar (Outlines replaced — segfaults, perf penalty) |
| Python Semantics | Jedi library (cross-file goto, refs, types — preferred over multilspy LSP) |
| CLI UX | Typer (Click-based, type-hint driven CLI) with Rich for formatting |

### 4.1 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Backend Language | Python 3.11+ | ML ecosystem, rapid dev |
| TUI Frontend | Go + Bubble Tea | Single binary, inline mode, goroutines |
| Frontend↔Backend | JSON-RPC over stdin/stdout | Language-agnostic, LSP-like |
| CLI Framework | Typer + Rich | Modern, type-safe, beautiful |
| Parsing | tree-sitter | Industry standard, fast |
| Python LSP | Pyright | Best type inference |
| Java LSP | JDT-LS | Most complete |
| Vector DB | LanceDB | Embedded, hybrid search |
| Embeddings | jina-v2-base-code | Local, good quality |
| L4 LLM Runtime | Ollama | Easy setup, streaming |
| L4 Model | Qwen3-8B Q4_K_M | Best 8B, thinking mode, ~5 GB VRAM |
| L3 LLM Runtime | llama-cpp-python + native grammar | Outlines replaced — segfaults, 2-5x perf penalty |
| L3 Model | Qwen2.5-Coder-1.5B Q4_K_M | 72% HumanEval, 1GB VRAM |
| Python Semantics | Jedi | Cross-file goto/refs/types, pure Python, <100ms |
| Package Manager | uv | 10-100x faster than pip |
| Git | GitPython | Pure Python |
| Testing | pytest | Standard |

> For alternative evaluations and deep research, see `docs/claude/` research documents.

### 4.2 File Structure

```
autocode/
├── cmd/
│   └── autocode-tui/       # Go TUI frontend
│       ├── main.go            # Entry point, launch Python backend
│       ├── model.go           # Root Bubble Tea model
│       ├── view.go            # View rendering
│       ├── update.go          # Message handling
│       ├── backend.go         # Python subprocess + JSON-RPC
│       ├── approval.go        # Arrow-key approval prompt
│       ├── commands.go        # Slash command handling
│       ├── statusbar.go       # Status bar component
│       └── styles.go          # Lip Gloss styles
├── go.mod
├── go.sum
├── src/
│   └── autocode/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── config.py           # Configuration management
│       │
│       ├── core/
│       │   ├── router.py       # Request routing logic
│       │   └── context.py      # Context assembly
│       │
│       ├── layer1/             # Deterministic analysis
│       │   ├── parser.py       # Tree-sitter wrapper
│       │   ├── lsp.py          # LSP client
│       │   └── queries.py      # Tree-sitter queries
│       │
│       ├── layer2/             # Retrieval & context
│       │   ├── chunker.py      # AST-aware chunking
│       │   ├── embeddings.py   # Embedding generation
│       │   ├── search.py       # Hybrid search
│       │   └── repomap.py      # Repository map
│       │
│       ├── layer3/             # Constrained generation
│       │   ├── llm.py          # LLM client abstraction
│       │   ├── grammar.py      # Grammar constraints
│       │   └── output.py       # Output parsing
│       │
│       ├── layer4/             # Agentic workflow
│       │   ├── tools.py        # Tool definitions
│       │   ├── executor.py     # Tool execution
│       │   ├── planner.py      # Architect logic
│       │   ├── editor.py       # Editor logic
│       │   └── feedback.py     # LLMLOOP implementation
│       │
│       ├── edit/
│       │   ├── formats.py      # Edit format handlers
│       │   ├── fuzzy.py        # Fuzzy matching
│       │   └── apply.py        # Edit application
│       │
│       ├── git/
│       │   └── manager.py      # Git operations
│       │
│       └── utils/
│           ├── cache.py        # Caching utilities
│           └── logging.py      # Logging setup
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── benchmarks/
│
├── docs/
│   ├── installation.md
│   ├── usage.md
│   ├── configuration.md
│   └── architecture.md
│
├── benchmarks/
│   ├── aider_subset/
│   └── custom/
│
├── pyproject.toml
├── Makefile
└── README.md
```

### 4.3 Configuration Schema

```yaml
# ~/.autocode/config.yaml

# LLM Configuration
llm:
  provider: ollama          # ollama | openai | anthropic | llama_cpp
  model: qwen3:8b-q4_K_M           # Layer 4 model
  l3_model: qwen2.5-coder:1.5b-instruct-q4_K_M  # Layer 3 model
  api_base: http://localhost:11434  # For Ollama (L4)
  api_key: null             # For cloud providers
  temperature: 0.2
  max_tokens: 4096
  context_length: 8192

# Layer Configuration
layers:
  layer1:
    enabled: true
    cache_ttl: 300          # seconds
  layer2:
    enabled: true
    embedding_model: jinaai/jina-embeddings-v2-base-code
    search_top_k: 10
    chunk_size: 1000
  layer3:
    enabled: true
    grammar_constrained: true
  layer4:
    enabled: true
    max_retries: 3
    architect_model: null   # Use same as llm.model if null

# Edit Configuration
edit:
  format: whole_file        # whole_file | search_replace
  fuzzy_threshold: 0.8
  auto_commit: true
  branch_per_task: false

# Git Configuration
git:
  auto_commit: true
  commit_prefix: "[AI]"
  create_branch: false

# Shell Configuration
shell:
  timeout: 30
  allowed_commands:
    - pytest
    - python
    - pip
    - mvn
    - gradle
  blocked_commands:
    - rm -rf
    - sudo

# UI Configuration
ui:
  theme: dark
  show_diff: true
  confirm_edits: true
  stream_output: true
```

### 4.4 Prompt Templates

**System Prompt (Base)**
```
You are AutoCode, an expert AI coding assistant. You help developers write, edit, and understand code.

Current project: {project_name}
Working directory: {working_dir}
Languages: {detected_languages}

{project_rules}

{repository_map}
```

**Edit Prompt (Whole File)**
```
Edit the following file according to the user's request.
Return ONLY the complete updated file content, nothing else.
Do not include markdown code fences or explanations.

File: {file_path}
```python
{file_content}
```

User request: {user_request}

Updated file content:
```

**Edit Prompt (Search/Replace)**
```
Edit the file according to the user's request.
Use SEARCH/REPLACE blocks to specify changes.

Format:
<<<<<<< SEARCH
exact code to find
=======
replacement code
>>>>>>> REPLACE

File: {file_path}
```python
{file_content}
```

User request: {user_request}

Changes:
```

**Architect Prompt**
```
You are planning code changes. Create a step-by-step plan.
Do NOT write code - just describe what changes are needed.

Context:
{context}

User request: {user_request}

Create a numbered plan with specific, actionable steps:
```

### 4.5 Observability Requirements

- Per-request logs: latency, tokens, model, retries.
- Debug log with full prompts and responses (local only).

### 4.6 Sandbox Default Policy

- Default allowed: `pytest`, `python`, `pip`, `mvn`, `gradle`, `java`, `javac`, `git status`, `git diff`
- Default blocked: `rm -rf`, `sudo`, `curl`, `wget`, network commands
- Working directory: restricted to project root
- Timeout: 30s default, 300s max
- **User override**: `~/.autocode/config.yaml` allows custom `shell.allowed_commands` and `shell.blocked_commands` lists. Users can also set `shell.allow_network: true` to permit network access.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM output parsing failures | High | Medium | Fuzzy matching, retry logic, fallback formats |
| LSP integration complexity | Medium | High | Use multilspy abstraction, fallback to tree-sitter only |
| Embedding quality insufficient | Medium | Medium | Support multiple embedding models, tune retrieval |
| Context window limitations | Medium | Medium | Aggressive context management, summarization |
| Performance bottlenecks | Medium | Medium | Profiling, caching, async operations |

### 5.2 Schedule Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fuzzy matching harder than expected | High | Medium | Start with exact match, iterate |
| LSP setup complexity | Medium | High | Budget extra week, have fallback |
| Benchmark score below target | Medium | Medium | Iterate on prompts, consider model upgrade |
| Solo developer burnout | Medium | High | Maintain sustainable pace, celebrate milestones |

### 5.3 Mitigation Strategies

**If behind schedule:**
1. Cut search/replace format (use whole-file only)
2. Cut Java support (Python only MVP)
3. Cut Layer 2 sophistication (simple chunking)
4. Extend timeline by 2-4 weeks

**If LLM quality insufficient:**
1. Try larger quantization (Q5_K_M, Q6_K)
2. Try 14B model if hardware permits
3. Add cloud fallback for complex tasks
4. Improve prompts and context

---

## 6. Milestone Checklist

### MVP Milestones

- [ ] **M1 (Week 3)**: Interactive chat with local LLM works end-to-end
- [ ] **M2 (Week 5)**: Can edit Python files reliably with undo
- [ ] **M3 (Week 7)**: Deterministic queries work without LLM
- [ ] **M4 (Week 9)**: Code search finds relevant results
- [ ] **M5 (Week 12)**: Multi-step tasks complete successfully
- [ ] **M6 (Week 14)**: Benchmarks pass, ready for release

### Quality Gates

Each phase must pass before proceeding:

**Phase 1 Gate**: Manual testing of 10 conversations — PASSED
**Phase 2 Gate**: 50 edit operations with <5 failures — PASSED
**Phase 3 Gate**: 100 deterministic queries, 100% correct; search precision@3 >60% — PASSED
**Phase 4 Gate**: 987 collected, 978 passed, 0 failed, ruff clean — PASSED
**Phase 5 Gate**: >= 75% task bank pass, p95 <= 180s, 0 hard-fail regressions (see `docs/plan/phase5-agent-teams.md`)
**Phase 6 Gate**: TBD

---

## 7. Appendices

### A. Glossary

| Term | Definition |
|------|------------|
| Layer 1 | Deterministic analysis using tree-sitter and LSP |
| Layer 2 | Context retrieval using embeddings and hybrid search |
| Layer 3 | Constrained LLM generation with grammar enforcement |
| Layer 4 | Full agentic workflow with tools and feedback loops |
| LLMLOOP | Iterative refinement using compiler/test feedback |
| Architect/Editor | Pattern separating planning from code execution |
| Repo Map | Compressed summary of repository symbols |
| Hybrid Search | Combined BM25 (keyword) + vector (semantic) search |

### B. References

1. Tree-sitter documentation: https://tree-sitter.github.io/tree-sitter/
2. LSP specification: https://microsoft.github.io/language-server-protocol/
3. Pyright CLI: https://www.npmjs.com/package/pyright
4. Eclipse JDT LS: https://github.com/eclipse-jdtls/eclipse.jdt.ls
5. Semgrep: https://github.com/semgrep/semgrep
6. LanceDB docs: https://lancedb.com/documentation/overview/
7. Jina embeddings v2 base code: https://aws.amazon.com/marketplace/pp/prodview-tk7t7bz6fp5ng
8. Ollama API: https://docs.ollama.com/api/introduction
9. Qwen3-8B model card: https://huggingface.co/Qwen/Qwen3-8B
9a. Qwen2.5-Coder-1.5B model card: https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct
10. llama-cpp-python native grammar (replaced Outlines): https://llama-cpp-python.readthedocs.io/
11. Typer docs: https://typer.tiangolo.com/
12. Rich: https://github.com/Textualize/rich
13. Aider polyglot benchmark: https://github.com/Aider-AI/polyglot-benchmark
14. SWE-bench: https://www.swebench.com/

### C. Benchmark Datasets

**Aider Polyglot Subset (50 tasks)**
- Source: https://github.com/Aider-AI/polyglot-benchmark
- Languages: Python (30), Java (20)
- Difficulty: Medium (solvable by GPT-4)

**Custom Edit Test Suite (100 tasks)**
- Single function edits (40)
- Multi-function edits (30)
- Cross-file edits (20)
- Refactoring tasks (10)

**Layer 1 Verification (100 queries)**
- Find references (25)
- Go to definition (25)
- List symbols (25)
- Get type info (25)

### D. Baseline Benchmark Definition

**What "Claude Code-level performance" means (measurable proxy):**

AutoCode aims to match the utility of frontier AI coding assistants while running locally. Since direct comparison is impractical, we use the following proxy metrics:

| Proxy Metric | Target | Rationale |
|--------------|--------|-----------|
| Aider Polyglot pass@1 | >40% | GPT-4 achieves ~50-60% on similar tasks; 40% is viable for 7B model |
| Token efficiency | 60-80% reduction | Measures Layer 1-2 effectiveness vs naive always-LLM approach |
| Deterministic query accuracy | 100% | Layer 1 should never produce wrong answers for supported query types |

**Benchmark Execution Protocol:**

1. **Aider Polyglot Subset (50 tasks)**
   - Run each task with default config (Qwen3-8B, whole-file edit)
   - Record: pass/fail, retries needed, tokens used, latency
   - Success = code compiles and passes provided tests
   - Calculate: pass@1, pass@3 (with retries), avg tokens per task

2. **Token Efficiency Measurement**
   - Baseline: Send every user query directly to LLM (naive approach)
   - AutoCode: Route through Layer 1-4 system
   - Measure: (baseline_tokens - autocode_tokens) / baseline_tokens
   - Run on 100 mixed queries (50 deterministic, 50 generative)

3. **Retrieval Quality (precision@k)**
   - Ground truth: Manually labeled relevant code chunks for 50 queries
   - Measure: How many of top-k results are in ground truth set
   - Target: precision@3 > 60%, precision@10 > 40%

4. **Latency Percentiles**
   - Measure p50, p90, p99 for each operation type
   - Targets are for p50; p99 should be <3x p50

**When to Re-run Benchmarks:**
- After any change to prompts, routing logic, or model configuration
- Before each phase gate review
- Before MVP release

### E. Phased Execution Plan (Tech Stack → HLD → LLD → Code → Documentation)

This appendix organizes the same work as Phases 0-6 but by engineering lifecycle stage rather than feature area.

#### Phase A: Tech Stack Finalization
1. Confirm supported languages (Python-only vs Python+Java) using scope and resource criteria.
2. Select package/tooling stack (uv or pip/poetry, pytest, lint/format tools) and document exact commands.
3. Validate LLM runtime defaults (Ollama vs llama.cpp server) on target hardware; set baseline model and quantization.
4. Validate deterministic stack (tree-sitter, Pyright, JDT LS, Semgrep) install steps and performance budgets.
5. Validate retrieval stack (LanceDB, embedding model) for disk and RAM usage; set index size limits.
6. Define minimum hardware baseline and resource budgets per layer; document thresholds.
7. Produce dependency matrix with versions, licenses, and install steps; update roadmap docs if needed.

#### Phase B: High-Level Design (HLD)
1. Define system context diagram and request flow across layers 1-4.
2. Define component responsibilities and boundaries (CLI, router, layer engines, edit system, git, shell).
3. Define configuration schema and defaults aligned to local-first and edge-first constraints.
4. Define security model and sandbox boundaries.
5. Define persistence layout for logs, cache, indexes, and config.
6. Define performance budgets and SLAs per component; identify bottleneck risks.
7. Review HLD against "LLM as last resort" and low-resource edge requirement.

#### Phase C: Low-Level Design (LLD)
1. Specify module layout under `src/autocode/` with public interfaces and dependencies.
2. Define data models for requests, tool calls, edit results, context bundles, and metrics.
3. Detail algorithms: routing logic, chunking strategy, hybrid search scoring, fuzzy matching, retry rules.
4. Define error handling and rollback behavior; state machine for multi-step tasks.
5. Define cache keys, invalidation rules, and persistence schema (LanceDB tables, repo map).
6. Define observability (structured logs, metrics, profiling hooks).
7. Produce a test plan mapping each module to unit, integration, and benchmark coverage.

#### Phase D: Implementation (Code)

- **D0: Repo and Tooling Setup** — Project layout, packaging, dev tooling, CI scaffolding.
- **D1: CLI + LLM Foundation** — Typer CLI, config, LLM provider abstraction, file tools.
- **D2: Edit System + Git Safety** — Whole-file edit, syntax validation, git auto-commit, retry/rollback.
- **D3: Layer 1 Deterministic Engine** — Tree-sitter, LSP clients, deterministic query router.
- **D4: Layer 2 Retrieval + Context** — AST chunker, embeddings, LanceDB, hybrid search, repo map, rules loader.
- **D5: Layer 4 Agentic Workflow** — Tool registry, architect/editor pattern, feedback loop, task persistence.
- **D6: Testing + Benchmarking** — Test harnesses, benchmark runners, profiling, threshold tuning.

#### Phase E: Documentation and Release
1. Write installation, usage, configuration, and architecture docs in docs/.
2. Document performance targets, benchmarks, and reproducibility steps.
3. Provide example projects and .rules templates.
4. Finalize release checklist and packaging (PyPI/test PyPI).

---

*End of Document*

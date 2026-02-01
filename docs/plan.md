# HybridCoder: Low-Resource AI Coding Agent
## Product Roadmap & Requirements Specification

**Version:** 1.0
**Last Updated:** February 1, 2026
**Target:** Solo Developer MVP
**Languages:** Python, Java
**Platform:** Local CLI Tool (Windows, macOS, Linux)

---

## 1. Vision & Objectives

### 1.1 Product Vision
A local-first AI coding assistant CLI that achieves Claude Code-level performance while running on consumer hardware (7-11B parameter models). The system uses deterministic classical AI techniques as the primary intelligence layer, invoking LLMs only when necessary.

**Performance Target Proxy**: Achieve >40% pass@1 on Aider polyglot benchmark subset (comparable to GPT-4 baseline on similar tasks) while using 60-80% fewer LLM tokens than a naive always-call-LLM approach. See Appendix D for full benchmark definition.

### 1.2 Core Differentiators
| Aspect | Traditional AI Coders | HybridCoder |
|--------|----------------------|-------------|
| LLM Usage | First resort | Last resort |
| Resource Requirement | Cloud API / 70B+ models | Local 7B model, 8GB VRAM |
| Latency (simple queries) | 2-5 seconds | <100ms |
| Privacy | Data sent to cloud | Fully local |
| Cost per task | $0.01-$0.50 | $0 (after setup) |

### 1.3 Success Metrics (MVP)
| Metric | Target | Verification Method |
|--------|--------|---------------------|
| LLM call reduction | 60-80% vs naive approach | Instrumentation logging |
| Edit success rate (first attempt) | >40% | Aider benchmark subset |
| Edit success rate (with retry) | >75% | Aider benchmark subset |
| Simple query latency | <500ms | Automated timing tests |
| Agentic task completion | >50% on custom test suite | Manual + automated tests |
| Memory usage (idle) | <2GB RAM (stretch: <500MB) | System monitoring |
| Memory usage (inference) | <8GB VRAM | System monitoring |

### 1.4 Scope

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

### 1.5 Open Questions and Decisions

**Resolved:**
- Memory target: <2GB idle (stretch goal: <500MB)
- Default edit format: whole-file (search/replace deferred to Phase 2.5+)

**Open:**
- Python-only MVP vs Python+Java (recommendation: Python-only to reduce scope risk)
- Default embedding model and index size limits
- Cloud fallback policy and opt-in UX

---

## 2. Architecture Overview

### 2.1 Layered Intelligence Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: DETERMINISTIC ANALYSIS (No LLM)                       │
│  ├─ Tree-sitter parsing (syntax, structure)                     │
│  ├─ LSP integration (types, references, definitions)            │
│  ├─ Static analysis (Semgrep rules, linting)                    │
│  └─ Pattern matching (known refactoring patterns)               │
│  Latency: <50ms | Tokens: 0                                     │
└─────────────────────────────────────────────────────────────────┘
                                │ (if unresolved)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: RETRIEVAL & CONTEXT (No Generative LLM)               │
│  ├─ AST-aware code chunking                                     │
│  ├─ Hybrid search (BM25 + vector embeddings)                    │
│  ├─ Project rules loading (.rules/, AGENTS.md)                  │
│  └─ Repository map generation                                   │
│  Latency: 100-500ms | Tokens: 0 (embeddings are not LLM calls)  │
└─────────────────────────────────────────────────────────────────┘
                                │ (if generation needed)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: CONSTRAINED GENERATION (Efficient LLM)                │
│  ├─ Grammar-constrained decoding (valid syntax guaranteed)      │
│  ├─ Small model for simple completions (1.5B-3B)                │
│  └─ Structured output enforcement (JSON, tool calls)            │
│  Latency: 500ms-2s | Tokens: 500-2000                           │
└─────────────────────────────────────────────────────────────────┘
                                │ (if complex reasoning needed)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: FULL REASONING (Targeted LLM)                         │
│  ├─ 7B model for complex edits                                  │
│  ├─ Multi-file planning and refactoring                         │
│  ├─ Architect/Editor pattern for reliability                    │
│  └─ Compiler feedback loops (LLMLOOP)                           │
│  Latency: 5-30s | Tokens: 2000-8000                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Dependency Graph

```
CLI Interface
    │
    ├── Request Router (decides which layer handles request)
    │       │
    │       ├── Layer 1: Deterministic Engine
    │       │       ├── Tree-sitter Parser
    │       │       ├── LSP Client (Pyright, JDT)
    │       │       └── Semgrep Runner
    │       │
    │       ├── Layer 2: Context Engine
    │       │       ├── Code Chunker
    │       │       ├── Embedding Generator
    │       │       ├── Vector Store (LanceDB)
    │       │       └── Repo Map Generator
    │       │
    │       ├── Layer 3: Generation Engine
    │       │       ├── LLM Client (Ollama/llama.cpp)
    │       │       ├── Grammar Constraints (Outlines)
    │       │       └── Output Parser
    │       │
    │       └── Layer 4: Agentic Engine
    │               ├── Planner (Architect)
    │               ├── Editor (code modifications)
    │               ├── Tool Executor
    │               └── Feedback Loop Manager
    │
    ├── File Manager
    │       ├── Read/Write operations
    │       └── Diff generation
    │
    ├── Git Manager
    │       ├── Auto-commit
    │       ├── Branch management
    │       └── Undo/revert
    │
    └── Shell Executor (sandboxed)
            ├── Test runner
            └── Build commands
```

---

## 3. Development Phases

### Phase 0: Project Setup (Week 1)

#### Objectives
- Repository structure established
- Development environment configured
- CI/CD pipeline operational
- Core dependencies selected and tested

#### Deliverables
| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| D0.1 | Repository with standard structure | Has src/, tests/, docs/, configs |
| D0.2 | Development environment | Python 3.11+, all deps install cleanly |
| D0.3 | CI pipeline | Tests run on every push |
| D0.4 | Dependency audit | All core libs tested in isolation |

#### Technical Decisions Required
- [ ] Primary language: Python (recommended) vs TypeScript
- [ ] Package manager: uv (recommended) vs pip vs poetry
- [ ] Test framework: pytest (recommended) vs unittest
- [ ] CLI framework: Typer (recommended) vs Click vs argparse

#### Exit Criteria
- [ ] `make setup` creates working environment
- [ ] `make test` runs (even with no tests)
- [ ] `make lint` passes
- [ ] README documents setup process

---

### Phase 1: Foundation - CLI & Basic LLM (Weeks 2-3)

#### Objectives
- Functional CLI with REPL interface
- LLM integration working (local + cloud fallback)
- Basic file operations
- Streaming output to terminal

#### Deliverables
| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| D1.1 | CLI entry point | `hybridcoder` command available after install |
| D1.2 | Interactive REPL | Can type messages, see responses |
| D1.3 | LLM client abstraction | Supports Ollama, OpenAI API, llama.cpp server |
| D1.4 | Streaming output | Tokens appear as generated, not all at once |
| D1.5 | File read tool | Can read files, partial reads (line ranges) |
| D1.6 | File write tool | Can write/overwrite files |
| D1.7 | Configuration system | Config file for model, API keys, preferences |
| D1.8 | Command history | Up/down arrows recall previous commands |

#### Functional Requirements

**FR1.1: CLI Commands**
```
hybridcoder chat              # Start interactive session
hybridcoder ask "question"    # One-shot question
hybridcoder edit file.py      # Edit mode for specific file
hybridcoder config            # Show/edit configuration
hybridcoder --help            # Show all commands
```

**FR1.2: LLM Provider Support**
- Must support: Ollama (local)
- Must support: OpenAI-compatible API (for llama.cpp server)
- Should support: Anthropic API (cloud fallback)
- Configuration via environment variables or config file

**FR1.3: Streaming Requirements**
- First token must appear within 2 seconds of request
- Terminal must show tokens as they arrive
- Support for cancellation (Ctrl+C)

#### Technical Requirements

**TR1.1: Model Configuration**
```yaml
# ~/.hybridcoder/config.yaml
llm:
  provider: ollama  # ollama | openai | anthropic
  model: qwen2.5-coder:7b-instruct-q4_K_M
  temperature: 0.2
  max_tokens: 4096
  context_length: 8192
```

**TR1.2: Response Format**
- All LLM responses logged to debug file
- Token count tracked per request
- Latency measured and logged

#### Verification Tests
- [ ] VT1.1: Start REPL, send "Hello", receive response
- [ ] VT1.2: Stream response shows character-by-character output
- [ ] VT1.3: Read a file via chat command
- [ ] VT1.4: Write a file via chat command
- [ ] VT1.5: Switch between Ollama and OpenAI provider
- [ ] VT1.6: Config file changes reflected without restart

#### Exit Criteria
- [ ] Can have multi-turn conversation with local LLM
- [ ] File read/write works reliably
- [ ] Latency under 3 seconds for first token (local model)

---

### Phase 2: Edit System (Weeks 4-5)

#### Objectives
- Reliable code editing via LLM
- Multiple edit format support
- Git integration for safety
- Edit verification and retry

#### Deliverables
| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| D2.1 | Whole-file edit format | LLM can rewrite entire files |
| D2.2 | Search/Replace parser | Parse <<<<<<< SEARCH blocks |
| D2.3 | Fuzzy matching | 80%+ similarity threshold matching |
| D2.4 | Git auto-commit | Every edit creates commit |
| D2.5 | Undo command | `/undo` reverts last AI change |
| D2.6 | Diff preview | Show diff before applying |
| D2.7 | Edit retry logic | Auto-retry on parse failure (max 3) |

#### Functional Requirements

**FR2.1: Edit Formats**
```
Format 1: Whole File (default for MVP)
- LLM outputs complete file content
- Simplest, most reliable for small models
- Higher token cost, but fewer failures

Format 2: Search/Replace (Phase 2.5+)
<<<<<<< SEARCH
original code here
=======
replacement code here
>>>>>>> REPLACE
```

**FR2.2: Edit Verification Pipeline**
1. Parse LLM output for edit instructions
2. Validate syntax of proposed code (tree-sitter)
3. Show diff to user (unless auto-apply mode)
4. Apply edit to file
5. Run linter on modified file
6. If lint fails, offer to fix or revert
7. Create git commit

**FR2.3: Fuzzy Matching Requirements**
- Exact match: Try first, fastest
- Whitespace-normalized match: Ignore leading/trailing whitespace
- Fuzzy match: Levenshtein distance, >80% similarity
- Line-anchored match: Find by surrounding context
- Report match confidence to user

#### Technical Requirements

**TR2.1: Edit Success Metrics**
```python
class EditResult:
    success: bool
    match_type: str  # exact | normalized | fuzzy | failed
    match_confidence: float  # 0.0 - 1.0
    lines_changed: int
    tokens_used: int
    retry_count: int
```

**TR2.2: Git Commit Format**
```
[AI] <action>: <brief description>

Files modified:
- path/to/file.py

Prompt: <truncated user prompt>
Model: qwen2.5-coder:7b
Tokens: 1234
```

#### Verification Tests
- [ ] VT2.1: Edit a function, verify syntax valid after
- [ ] VT2.2: Fuzzy match succeeds when LLM adds extra whitespace
- [ ] VT2.3: Undo reverts to pre-edit state
- [ ] VT2.4: Failed edit does not corrupt file
- [ ] VT2.5: Git commit created for each successful edit
- [ ] VT2.6: Multi-file edit creates single commit

#### Exit Criteria
- [ ] Edit success rate >60% on simple single-file edits
- [ ] No data loss (file corruption) in 100 test edits
- [ ] Git history clean and informative
- [ ] Failure budget: <5% of edits require manual intervention after retries
- [ ] Rollback success rate: 100% of failed edits restore original file state

---

### Phase 3: Code Intelligence - Layer 1 (Weeks 6-7)

#### Objectives
- Tree-sitter parsing for Python and Java
- LSP integration for type information
- Deterministic query handling
- Latency under 50ms for Layer 1 queries

#### Deliverables
| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| D3.1 | Tree-sitter Python parser | Parse any valid Python file |
| D3.2 | Tree-sitter Java parser | Parse any valid Java file |
| D3.3 | Symbol extraction | Extract functions, classes, methods |
| D3.4 | Pyright integration | Get type info for Python symbols |
| D3.5 | JDT integration | Get type info for Java symbols |
| D3.6 | Reference finder | Find all usages of a symbol |
| D3.7 | Definition jumper | Go to definition of a symbol |
| D3.8 | Query router | Route deterministic queries to Layer 1 |

#### Functional Requirements

**FR3.1: Deterministic Query Types**
These queries MUST be handled without LLM:
- "Find all usages of X"
- "Go to definition of X"
- "What type is X?"
- "List all functions in file Y"
- "Show signature of function X"
- "Find all imports in file Y"

**FR3.2: Tree-sitter Queries Required**
```scheme
# Functions (Python)
(function_definition name: (identifier) @name)

# Classes (Python)
(class_definition name: (identifier) @name)

# Methods (Python)
(class_definition 
  body: (block 
    (function_definition name: (identifier) @method)))

# Imports (Python)
(import_statement) @import
(import_from_statement) @import

# Similar for Java...
```

**FR3.3: LSP Operations Required**
- textDocument/hover → Type information
- textDocument/definition → Jump to definition
- textDocument/references → Find all usages
- textDocument/documentSymbol → List all symbols
- textDocument/diagnostic → Get errors/warnings

#### Technical Requirements

**TR3.1: Latency Budgets**
| Operation | Target | Maximum |
|-----------|--------|---------|
| Parse single file | <10ms | 50ms |
| Extract symbols | <20ms | 100ms |
| Find references (LSP) | <100ms | 500ms |
| Query routing decision | <5ms | 20ms |

**TR3.2: Caching Strategy**
- Parse tree cached per file, invalidated on change
- Symbol table cached per project, incremental update
- LSP results cached with 30-second TTL

#### Verification Tests
- [ ] VT3.1: Parse 100 Python files without error
- [ ] VT3.2: Parse 100 Java files without error
- [ ] VT3.3: Extract all functions from Django codebase
- [ ] VT3.4: "Find usages of X" returns correct results
- [ ] VT3.5: Latency under 50ms for symbol extraction
- [ ] VT3.6: Query "what functions are in this file" uses no LLM tokens

#### Exit Criteria
- [ ] 100% of deterministic queries handled without LLM
- [ ] Parsing works on real-world codebases (Django, Spring)
- [ ] LSP integration stable for 1-hour session

---

### Phase 4: Context & Retrieval - Layer 2 (Weeks 8-9)

#### Objectives
- AST-aware code chunking
- Vector store with hybrid search
- Repository map generation
- Project rules system

#### Deliverables
| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| D4.1 | AST-aware chunker | Chunks respect function/class boundaries |
| D4.2 | Embedding generator | Generate embeddings for code chunks |
| D4.3 | LanceDB integration | Store and query embeddings |
| D4.4 | Hybrid search | Combined BM25 + vector search |
| D4.5 | Repository map | Generate ranked symbol summary |
| D4.6 | Project rules loader | Load .rules/, AGENTS.md, CLAUDE.md |
| D4.7 | Context assembler | Build optimal context for LLM |
| D4.8 | Index management | Create, update, rebuild index |

#### Functional Requirements

**FR4.1: Chunking Requirements**
- Chunk at function/class boundaries (never mid-function)
- Maximum chunk size: 1000 tokens
- Minimum chunk size: 50 tokens
- Include metadata: file path, scope chain, imports
- Overlap: 10 lines for context continuity

**FR4.2: Chunk Metadata Schema**
```yaml
chunk:
  id: unique_hash
  file_path: src/auth/service.py
  language: python
  chunk_type: function | class | module
  name: authenticate_user
  start_line: 45
  end_line: 78
  scope: AuthService.authenticate_user
  imports: [jwt, datetime, User]
  content: <actual code>
  embedding: <vector>
```

**FR4.3: Search Requirements**
- Hybrid search: 50% BM25 + 50% vector (configurable)
- Return top-k results (default k=10)
- Include relevance score
- Support filters: language, file path pattern, chunk type

**FR4.4: Repository Map Format**
```
Repository Map (ranked by importance):

src/auth/service.py:
  class AuthService:
    def authenticate(user_id: str) -> User
    def refresh_token(token: str) -> str
    def revoke_token(token: str) -> bool

src/models/user.py:
  class User:
    id: str
    email: str
    def validate() -> bool
...
```

**FR4.5: Project Rules**
- Load from: `.rules/*.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`
- Rules injected into system prompt
- Support for language-specific rules
- Support for directory-specific rules

#### Technical Requirements

**TR4.1: Embedding Model Options**
| Model | Dimensions | Local | Quality | Speed |
|-------|------------|-------|---------|-------|
| voyage-code-3 | 1024 | No (API) | Best | Fast |
| jina-v2-base-code | 768 | Yes | Good | Fast |
| CodeSage-large-v2 | 2048 | Yes | Very Good | Slow |
| all-MiniLM-L6-v2 | 384 | Yes | Okay | Very Fast |

Default: jina-v2-base-code (local, good quality)

**TR4.2: Index Performance**
| Operation | Target | Maximum |
|-----------|--------|---------|
| Index 1000 files | <60s | 180s |
| Single file update | <1s | 3s |
| Hybrid search query | <200ms | 500ms |
| Repo map generation | <2s | 5s |

**TR4.3: Context Budget**
- Total context budget: 6000 tokens (leaves room for response)
- Repository map: 500-1000 tokens
- Retrieved chunks: 2000-3000 tokens
- Project rules: 500-1000 tokens
- User message + history: 1000-2000 tokens

#### Verification Tests
- [ ] VT4.1: Chunk Django codebase, no mid-function chunks
- [ ] VT4.2: Search "authentication" returns auth-related code
- [ ] VT4.3: BM25 finds exact function name matches
- [ ] VT4.4: Vector search finds semantically similar code
- [ ] VT4.5: Repo map fits in 1000 tokens for 50-file project
- [ ] VT4.6: Project rules loaded and present in prompts
- [ ] VT4.7: Index survives restart (persistence)

#### Exit Criteria
- [ ] Search relevance: correct result in top-3 for 80% of queries
- [ ] Indexing completes for 10,000 file project
- [ ] Context assembly under 500ms

---

### Phase 5: Agentic Workflow - Layer 4 (Weeks 10-12)

#### Objectives
- Multi-step task execution
- Tool use framework
- Compiler feedback loops
- Architect/Editor pattern

#### Deliverables
| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| D5.1 | Tool framework | Extensible tool registration and execution |
| D5.2 | Shell executor | Sandboxed command execution |
| D5.3 | Test runner integration | Run pytest, junit, report results |
| D5.4 | Compiler feedback loop | Fix errors iteratively |
| D5.5 | Architect/Editor split | Planning vs execution separation |
| D5.6 | Multi-file editing | Coordinate edits across files |
| D5.7 | Task persistence | Resume interrupted tasks |
| D5.8 | Progress reporting | Show what agent is doing |

#### Functional Requirements

**FR5.1: Tool Definitions**
```yaml
tools:
  - name: read_file
    description: Read contents of a file
    parameters:
      path: string (required)
      start_line: int (optional)
      end_line: int (optional)
    
  - name: write_file
    description: Write content to a file
    parameters:
      path: string (required)
      content: string (required)
    
  - name: search_code
    description: Search codebase for relevant code
    parameters:
      query: string (required)
      limit: int (default: 10)
    
  - name: run_command
    description: Execute shell command
    parameters:
      command: string (required)
      timeout: int (default: 30)
    
  - name: find_references
    description: Find all usages of a symbol
    parameters:
      symbol: string (required)
      file: string (optional)
    
  - name: get_diagnostics
    description: Get errors/warnings for a file
    parameters:
      path: string (required)
```

**FR5.2: Feedback Loop (LLMLOOP)**
```
1. Generate code
2. Parse for syntax errors (tree-sitter)
   → If errors: feed back to LLM, goto 1
3. Run type checker (Pyright/JDT)
   → If type errors: feed back to LLM, goto 1
4. Run linter (flake8/checkstyle)
   → If warnings: optionally fix, continue
5. Run tests (if available)
   → If failures: feed back to LLM, goto 1
6. Success - commit changes
```

**FR5.3: Architect/Editor Pattern**
```
Phase 1 - Architect (planning):
  Input: User request + context
  Output: Plain-text plan with specific steps
  Model: Can use larger/smarter model
  
Phase 2 - Editor (execution):
  Input: Single step from plan
  Output: Code changes (search/replace)
  Model: Can use smaller/faster model
```

**FR5.4: Multi-file Edit Coordination**
- Detect cross-file dependencies
- Order edits to avoid breaking changes
- Atomic commit for related changes
- Rollback all if any edit fails

#### Technical Requirements

**TR5.1: Sandbox Requirements**
- Shell commands run in subprocess
- Timeout enforced (default 30s, max 300s)
- Working directory restricted to project
- No network access by default (configurable)
- Resource limits: 1GB memory, 1 CPU

**TR5.2: Retry Limits**
| Operation | Max Retries | Backoff |
|-----------|-------------|---------|
| Syntax fix | 3 | None |
| Type error fix | 2 | None |
| Test failure fix | 3 | None |
| Tool call parse | 2 | None |

**TR5.3: State Management**
- Save state after each successful step
- State includes: plan, completed steps, file versions
- Resume from last successful step on restart

#### Verification Tests
- [ ] VT5.1: "Add parameter to function" modifies function + callers
- [ ] VT5.2: Syntax error auto-fixed without user intervention
- [ ] VT5.3: Test failure triggers fix attempt
- [ ] VT5.4: Complex refactor uses Architect/Editor pattern
- [ ] VT5.5: Shell command timeout enforced
- [ ] VT5.6: Interrupted task resumes correctly

#### Exit Criteria
- [ ] Can complete multi-file refactoring tasks
- [ ] Feedback loop catches and fixes 70%+ of syntax errors
- [ ] No sandbox escapes in security testing

---

### Phase 6: Polish & Benchmarking (Weeks 13-14)

#### Objectives
- Comprehensive benchmarking
- Performance optimization
- Documentation
- Release preparation

#### Deliverables
| ID | Deliverable | Acceptance Criteria |
|----|-------------|---------------------|
| D6.1 | Benchmark suite | Automated tests against Aider benchmark |
| D6.2 | Performance profiling | Identify and fix bottlenecks |
| D6.3 | User documentation | Installation, usage, configuration docs |
| D6.4 | Developer documentation | Architecture, contribution guide |
| D6.5 | Release packaging | pip installable package |
| D6.6 | Demo project | Example project with .rules/ |

#### Benchmark Requirements

**BR6.1: Core Benchmarks**
| Benchmark | Source | Target Score | Purpose |
|-----------|--------|--------------|---------|
| Aider Polyglot (subset) | aider.chat | >40% pass@1 | Edit quality |
| SWE-bench Lite/Verified | swebench.com | TBD | Real-world issue resolution |
| HumanEval (subset) | OpenAI | >80% pass@1 | Generation quality |
| Custom retrieval test | Internal | >70% precision@3 | Search quality |
| Custom Layer-1 test | Internal | 100% correct | Deterministic ops |

**BR6.2: Performance Benchmarks**
| Metric | Target | Test Method |
|--------|--------|-------------|
| Startup time | <2s | Time to first prompt |
| Layer 1 query | <50ms | 100 symbol lookups |
| Layer 2 search | <200ms | 100 search queries |
| Simple edit | <5s | Single function edit |
| Complex edit | <30s | Multi-file refactor |
| Memory (idle) | <2GB (stretch: <500MB) | After startup |
| Memory (inference) | <8GB VRAM | During LLM inference |

**BR6.3: Reliability Benchmarks**
| Metric | Target | Test Method |
|--------|--------|-------------|
| Edit success (no retry) | >40% | 100 edit tasks |
| Edit success (with retry) | >75% | 100 edit tasks |
| No data loss | 100% | 1000 edit operations |
| Crash recovery | 100% | Kill during edit, verify state |
| Failure budget | <5% manual intervention | After all retries exhausted |
| Rollback success | 100% | Failed edits restore original |

#### Verification Tests
- [ ] VT6.1: Benchmark suite runs in CI
- [ ] VT6.2: Performance regression detected automatically
- [ ] VT6.3: Documentation builds without errors
- [ ] VT6.4: Package installs from PyPI (test.pypi.org)
- [ ] VT6.5: Demo project works end-to-end

#### Exit Criteria
- [ ] All benchmark targets met
- [ ] Documentation complete and reviewed
- [ ] Package published to PyPI
- [ ] Demo video/walkthrough created

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
| LLM Runtime | Ollama local server (HTTP API at http://localhost:11434/api by default) |
| LLM Model | Qwen2.5-Coder 7B Instruct (32k default context; longer via YaRN in supported runtimes) |
| Constrained Decoding | Outlines for JSON/Pydantic/grammar outputs |
| CLI UX | Typer (Click-based, type-hint driven CLI) with Rich for formatting |

### 4.1 Technology Stack

| Component | Choice | Rationale | Alternatives |
|-----------|--------|-----------|--------------|
| Language | Python 3.11+ | ML ecosystem, rapid dev | TypeScript |
| CLI Framework | Typer + Rich | Modern, type-safe, beautiful | Click |
| Parsing | tree-sitter | Industry standard, fast | - |
| Python LSP | Pyright | Best type inference | pylsp |
| Java LSP | JDT-LS | Most complete | - |
| Vector DB | LanceDB | Embedded, hybrid search | Chroma |
| Embeddings | jina-v2-base-code | Local, good quality | voyage-code-3 |
| Local LLM | Ollama | Easiest setup | llama.cpp |
| Model | Qwen2.5-Coder 7B Q4_K_M | Best 7B code model | DeepSeek |
| Grammar | Outlines | Pydantic integration | SynCode |
| Git | GitPython | Pure Python | subprocess |
| Testing | pytest | Standard | - |

### 4.2 File Structure

```
hybridcoder/
├── src/
│   └── hybridcoder/
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
# ~/.hybridcoder/config.yaml

# LLM Configuration
llm:
  provider: ollama          # ollama | openai | anthropic | llama_cpp
  model: qwen2.5-coder:7b-instruct-q4_K_M
  api_base: http://localhost:11434  # For Ollama
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
You are HybridCoder, an expert AI coding assistant. You help developers write, edit, and understand code.

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

**Phase 1 Gate**: Manual testing of 10 conversations
**Phase 2 Gate**: 50 edit operations with <5 failures
**Phase 3 Gate**: 100 deterministic queries, 100% correct
**Phase 4 Gate**: Search relevance >60% precision@3
**Phase 5 Gate**: 20 multi-step tasks, >50% success
**Phase 6 Gate**: All benchmarks meet targets

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
9. Qwen2.5-Coder model card: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
10. Outlines structured generation: https://dottxt-ai.github.io/outlines/reference/generation/json/
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

HybridCoder aims to match the utility of frontier AI coding assistants while running locally. Since direct comparison is impractical, we use the following proxy metrics:

| Proxy Metric | Target | Rationale |
|--------------|--------|-----------|
| Aider Polyglot pass@1 | >40% | GPT-4 achieves ~50-60% on similar tasks; 40% is viable for 7B model |
| Token efficiency | 60-80% reduction | Measures Layer 1-2 effectiveness vs naive always-LLM approach |
| Deterministic query accuracy | 100% | Layer 1 should never produce wrong answers for supported query types |

**Benchmark Execution Protocol:**

1. **Aider Polyglot Subset (50 tasks)**
   - Run each task with default config (Qwen2.5-Coder 7B, whole-file edit)
   - Record: pass/fail, retries needed, tokens used, latency
   - Success = code compiles and passes provided tests
   - Calculate: pass@1, pass@3 (with retries), avg tokens per task

2. **Token Efficiency Measurement**
   - Baseline: Send every user query directly to LLM (naive approach)
   - HybridCoder: Route through Layer 1-4 system
   - Measure: (baseline_tokens - hybridcoder_tokens) / baseline_tokens
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

---

*End of Document*
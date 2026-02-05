# Phase 4: Implementation Plan (Code)

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 2.0 | Date: 2026-02-05

---

## Sprint Overview

| Sprint | Duration | Phase | Deliverables |
|--------|----------|-------|-------------|
| S0 | Week 1 | Setup | Repo structure, tooling, CI |
| S1 | Weeks 2-3 | Foundation | CLI + LLM + Config |
| S2 | Weeks 4-5 | Edit System | Edit + Git + Retry |
| S3 | Weeks 6-7 | Layer 1 | tree-sitter + LSP + Queries |
| S4 | Weeks 8-9 | Layer 2 | Chunking + Embeddings + Search |
| S5 | Weeks 10-12 | Layer 4 | Agentic + Tools + Feedback |
| S6 | Weeks 13-14 | Polish | Benchmarks + Docs + Release |

---

## Sprint 0: Project Setup (Week 1)

### S0.1 Create Project Structure
**Files to create:**
```
pyproject.toml          # uv/pip project config
Makefile                # setup, test, lint, format commands
src/hybridcoder/__init__.py
src/hybridcoder/__main__.py
src/hybridcoder/cli.py  # stub
src/hybridcoder/config.py  # stub
tests/conftest.py
tests/unit/__init__.py
tests/integration/__init__.py
.gitignore              # update with Python patterns
```

**pyproject.toml skeleton:**
```toml
[project]
name = "hybridcoder"
version = "0.1.0"
description = "Edge-native AI coding assistant"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "typer>=0.12",
    "rich>=13.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
]

[project.scripts]
hybridcoder = "hybridcoder.cli:app"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0", "ruff>=0.5", "mypy>=1.10"]
layer1 = ["tree-sitter>=0.25", "tree-sitter-python>=0.23"]
layer2 = ["lancedb>=0.10", "sentence-transformers>=3.0"]
layer3 = ["llama-cpp-python>=0.3", "outlines>=0.1"]
layer4 = ["ollama>=0.4"]
all = ["hybridcoder[layer1,layer2,layer3,layer4]"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Makefile:**
```makefile
.PHONY: setup test lint format clean

setup:
	uv sync --all-extras

test:
	uv run pytest tests/ -v --cov=src/hybridcoder

lint:
	uv run ruff check src/ tests/
	uv run mypy src/hybridcoder/

format:
	uv run ruff format src/ tests/

clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache
```

### S0.2 CI/CD Setup
**File:** `.github/workflows/ci.yml`
- Trigger: push, PR to main
- Matrix: Python 3.11, 3.12, 3.13 × ubuntu-latest
- Steps: install uv, sync deps, ruff check, mypy, pytest

### S0.3 Git Configuration
- Update `.gitignore` with full Python patterns
- Verify all existing docs are tracked

**Exit Criteria:**
- [ ] `make setup` installs all deps
- [ ] `make test` runs (even with 0 tests)
- [ ] `make lint` passes
- [ ] CI runs on push

---

## Sprint 1: CLI + LLM Foundation (Weeks 2-3)

### S1.1 Configuration System
**File:** `src/hybridcoder/config.py`
- Pydantic config models (from LLD Phase 3)
- YAML loader: `~/.hybridcoder/config.yaml`
- Project-level override: `.hybridcoder.yaml`
- CLI flag overrides
- `config` command: show, set, check

**Functions:**
```python
def load_config() -> HybridCoderConfig: ...
def save_config(config: HybridCoderConfig) -> None: ...
def get_config_path() -> Path: ...
def check_config() -> list[str]:  # Returns list of warnings/errors
```

### S1.2 CLI Framework
**File:** `src/hybridcoder/cli.py`
- Typer app with commands: `chat`, `ask`, `edit`, `config`, `--help`
- REPL loop with Rich console
- Streaming token output via Rich Live
- Ctrl+C handling
- Command history (prompt-toolkit integration)

**Functions:**
```python
app = typer.Typer()

@app.command()
def chat(verbose: bool = False): ...

@app.command()
def ask(question: str, file: Optional[str] = None): ...

@app.command()
def edit(file: str, instruction: str): ...

@app.command()
def config(action: str = "show"): ...
```

### S1.3 LLM Provider Abstraction
**File:** `src/hybridcoder/layer4/llm.py`
- Abstract base: `LLMProvider` protocol
- Ollama implementation with async streaming
- Message history management
- Token counting (approximate)

**Protocol:**
```python
class LLMProvider(Protocol):
    async def generate(self, messages: list[dict],
                       stream: bool = True) -> AsyncIterator[str]: ...
    async def generate_json(self, messages: list[dict],
                            schema: type[BaseModel]) -> BaseModel: ...
    def count_tokens(self, text: str) -> int: ...
```

### S1.4 File Tools
**File:** `src/hybridcoder/utils/file_tools.py`
- `read_file(path, start_line?, end_line?) -> str`
- `write_file(path, content) -> None`
- `list_files(directory, pattern?) -> list[str]`
- Path validation (no traversal above project root)

### S1.5 Core Types
**File:** `src/hybridcoder/core/types.py`
- All dataclasses from LLD: `Request`, `Response`, `FileRange`, `Symbol`, etc.

**Tests for S1:**
- `tests/unit/test_config.py` — config load/save/validate
- `tests/unit/test_cli.py` — command parsing (mocked LLM)
- `tests/integration/test_ollama.py` — real Ollama connection

**Exit Criteria:**
- [ ] `hybridcoder chat` starts REPL and streams from Ollama
- [ ] `hybridcoder ask "hello"` returns streamed response
- [ ] `hybridcoder config show` displays config
- [ ] Multi-turn conversation works (history preserved)
- [ ] Latency: first token <2s

---

## Sprint 2: Edit System + Git Safety (Weeks 4-5)

### S2.1 Edit Format Parsers
**File:** `src/hybridcoder/edit/formats.py`
- Parse whole-file edit output (strip markdown fences, validate)
- Parse search/replace blocks (SEARCH/REPLACE format)
- Validate edit output structure

### S2.2 Fuzzy Matching
**File:** `src/hybridcoder/edit/fuzzy.py`
- Exact match
- Normalized whitespace match
- Levenshtein sliding window
- Line-anchored match
- Confidence scoring

### S2.3 Edit Application Pipeline
**File:** `src/hybridcoder/edit/apply.py`
- Full pipeline: Parse → Match → Validate Syntax → Show Diff → Apply → Lint

```python
async def apply_edit(edit_output: str, file_path: str,
                     config: EditConfig) -> EditResult:
    # 1. Parse edit format
    parsed = parse_edit(edit_output, config.format)

    # 2. Find match (fuzzy if needed)
    match = find_match(parsed, file_path, config.fuzzy_threshold)

    # 3. Generate new content
    new_content = apply_replacement(match, parsed)

    # 4. Validate syntax
    syntax_ok = validate_syntax(new_content, file_path)

    # 5. Show diff (if ui.show_diff)
    diff = generate_diff(original, new_content)

    # 6. Apply (if ui.confirm_edits → prompt user)
    if confirmed:
        write_file(file_path, new_content)

    return EditResult(...)
```

### S2.4 Diff Display
**File:** `src/hybridcoder/edit/diff.py`
- Unified diff generation
- Rich-formatted colored diff display
- Line numbers, additions (green), deletions (red)

### S2.5 Git Manager
**File:** `src/hybridcoder/git/manager.py`
```python
class GitManager:
    def __init__(self, project_root: str): ...
    def is_repo(self) -> bool: ...
    def checkpoint(self, file_path: str) -> str: ...  # Returns commit SHA
    def commit(self, files: list[str], message: str) -> str: ...
    def rollback(self, commit_sha: str) -> None: ...
    def undo_last_ai_commit(self) -> bool: ...
    def get_diff(self, file_path: str) -> str: ...
```

### S2.6 Retry Logic
**File:** integrated into `edit/apply.py` and `layer4/feedback.py`
- Retry with error feedback
- Max retries from config (default 3)
- Exponential backoff for LLM calls

**Tests for S2:**
- `tests/unit/test_formats.py` — parse whole-file, search/replace
- `tests/unit/test_fuzzy.py` — all fuzzy matching strategies
- `tests/unit/test_git.py` — commit, rollback, undo
- `tests/integration/test_edit_flow.py` — full edit pipeline with real files

**Exit Criteria:**
- [ ] Whole-file edit works end-to-end
- [ ] Diff preview shows correctly
- [ ] Git auto-commit creates `[AI]` prefixed commits
- [ ] Undo reverts last AI commit
- [ ] 0 file corruptions in 100 edit operations
- [ ] Edit success >40% on simple Python edits

---

## Sprint 3: Layer 1 — Deterministic Engine (Weeks 6-7)

### S3.1 Tree-sitter Parser
**File:** `src/hybridcoder/layer1/parser.py`
```python
class CodeParser:
    def __init__(self): ...
    def parse(self, source: str, language: str) -> Tree: ...
    def extract_symbols(self, source: str, language: str) -> list[Symbol]: ...
    def get_node_at_position(self, tree: Tree, line: int, col: int) -> Node: ...
    def get_scope_chain(self, node: Node) -> list[str]: ...
```

### S3.2 Symbol Extraction
**File:** `src/hybridcoder/layer1/symbols.py`
- Extract functions, classes, methods, imports from AST
- Build symbol table with types, scopes, line ranges
- Cache per-file with mtime invalidation

### S3.3 LSP Client
**File:** `src/hybridcoder/layer1/lsp.py`
```python
class LSPClient:
    def __init__(self, language: str, project_root: str): ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def find_definition(self, file: str, line: int, col: int) -> Location: ...
    async def find_references(self, file: str, line: int, col: int) -> list[Location]: ...
    async def get_hover(self, file: str, line: int, col: int) -> str: ...
    async def get_completions(self, file: str, line: int, col: int) -> list[str]: ...
    async def get_diagnostics(self, file: str) -> list[Diagnostic]: ...
```
- Uses multilspy under the hood
- Manages lifecycle (start/stop/restart)
- Caches results with 30s TTL

### S3.4 Deterministic Queries
**File:** `src/hybridcoder/layer1/queries.py`
```python
class DeterministicQueries:
    def find_references(self, symbol: str, file: str) -> list[Location]: ...
    def find_definition(self, symbol: str, file: str) -> Location: ...
    def get_type(self, symbol: str, file: str) -> str: ...
    def list_functions(self, file: str) -> list[Symbol]: ...
    def list_classes(self, file: str) -> list[Symbol]: ...
    def list_imports(self, file: str) -> list[str]: ...
    def get_signature(self, function: str, file: str) -> str: ...
```

### S3.5 Core Router (Initial)
**File:** `src/hybridcoder/core/router.py`
- Classify requests using regex patterns
- Route deterministic queries to Layer 1
- Route everything else to Layer 4 (Layer 2/3 come in next sprints)

**Tests for S3:**
- `tests/unit/test_parser.py` — parse Python/Java, extract symbols
- `tests/unit/test_router.py` — classification accuracy
- `tests/integration/test_lsp.py` — Pyright integration
- `tests/benchmarks/bench_layer1.py` — latency (<50ms per query)

**Exit Criteria:**
- [ ] `find_references`, `find_definition`, `get_type` work for Python
- [ ] `list_functions`, `list_imports` work from tree-sitter
- [ ] All deterministic queries return in <50ms
- [ ] 100% accuracy on deterministic query test suite
- [ ] LSP server stable for 1-hour session

---

## Sprint 4: Layer 2 — Retrieval + Context (Weeks 8-9)

### S4.1 AST-Aware Chunker
**File:** `src/hybridcoder/layer2/chunker.py`
- Chunk files respecting function/class boundaries
- Metadata extraction (scope chain, imports, symbol name)
- Max 1000 tokens, min 50 tokens, 10-line overlap

### S4.2 Embedding Generator
**File:** `src/hybridcoder/layer2/embeddings.py`
```python
class EmbeddingGenerator:
    def __init__(self, model_name: str = "jinaai/jina-embeddings-v2-base-code"): ...
    def embed_text(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...
```

### S4.3 LanceDB Index Manager
**File:** `src/hybridcoder/layer2/index.py`
```python
class IndexManager:
    def __init__(self, db_path: str): ...
    def create_index(self) -> None: ...
    def add_chunks(self, chunks: list[CodeChunk]) -> None: ...
    def remove_file(self, file_path: str) -> None: ...
    def update_file(self, file_path: str, chunks: list[CodeChunk]) -> None: ...
    def reindex_project(self, project_root: str) -> None: ...
    def get_stats(self) -> dict: ...
```

### S4.4 Hybrid Search
**File:** `src/hybridcoder/layer2/search.py`
```python
class HybridSearch:
    def __init__(self, index: IndexManager, embeddings: EmbeddingGenerator): ...
    def search(self, query: str, top_k: int = 10,
               filters: dict = None) -> list[SearchResult]: ...
    def bm25_search(self, query: str, top_k: int) -> list[SearchResult]: ...
    def vector_search(self, query: str, top_k: int) -> list[SearchResult]: ...
    def rrf_fusion(self, bm25: list, vector: list, weight: float) -> list: ...
```

### S4.5 Repository Map
**File:** `src/hybridcoder/layer2/repomap.py`
- Generate ranked list of symbols in project
- Prioritize: recently modified, highly connected, frequently referenced
- Output format: `file:line symbol_name (type)`
- Budget: 500-1000 tokens

### S4.6 Project Rules Loader
**File:** `src/hybridcoder/layer2/rules.py`
- Load from: `.rules/*.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`
- Concatenate and truncate to token budget

### S4.7 Context Assembler
**File:** `src/hybridcoder/core/context.py`
- Combine repo map + rules + search results + history
- Respect 6000 token budget
- Priority-based allocation

**Tests for S4:**
- `tests/unit/test_chunker.py` — chunking boundaries, metadata
- `tests/unit/test_search.py` — BM25, vector, hybrid
- `tests/integration/test_lancedb.py` — full index lifecycle
- `tests/benchmarks/bench_search.py` — latency + precision@3

**Exit Criteria:**
- [ ] Index 10K files in <5 minutes
- [ ] Hybrid search returns relevant results in top-3 for 80% of queries
- [ ] Search latency <200ms
- [ ] Context assembly <500ms
- [ ] Repo map correctly reflects project structure

---

## Sprint 5: Layer 4 — Agentic Workflow (Weeks 10-12)

### S5.1 Layer 3 Engine (Constrained Generation)
**File:** `src/hybridcoder/layer3/llm.py`
```python
class ConstrainedGenerator:
    def __init__(self, model_path: str): ...
    def generate_json(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...
    def generate_text(self, prompt: str, max_tokens: int) -> str: ...
```
- llama-cpp-python model loading
- Outlines integration for JSON/Pydantic schemas

### S5.2 Grammar Schemas
**File:** `src/hybridcoder/layer3/grammar.py`
- All Pydantic models from LLD: `ToolCall`, `EditInstruction`, `RoutingDecision`, etc.

### S5.3 Tool Registry
**File:** `src/hybridcoder/layer4/tools.py`
```python
class ToolRegistry:
    def register(self, name: str, fn: Callable, schema: type[BaseModel]): ...
    def execute(self, tool_call: ToolCall) -> str: ...
    def get_tool_descriptions(self) -> str: ...

# Built-in tools
registry.register("read_file", read_file_tool, ReadFileArgs)
registry.register("write_file", write_file_tool, WriteFileArgs)
registry.register("search_code", search_code_tool, SearchCodeArgs)
registry.register("run_command", run_command_tool, RunCommandArgs)
registry.register("find_references", find_refs_tool, FindRefsArgs)
registry.register("get_diagnostics", get_diagnostics_tool, DiagnosticsArgs)
```

### S5.4 Shell Executor (Sandboxed)
**File:** `src/hybridcoder/shell/executor.py`
```python
class ShellExecutor:
    def __init__(self, config: ShellConfig, project_root: str): ...
    def validate_command(self, command: str) -> bool: ...
    async def execute(self, command: str, timeout: int = 30) -> ShellResult: ...
```
- Allowlist/blocklist enforcement
- Timeout handling with process kill
- Working directory restriction
- Output capture and truncation

### S5.5 Architect/Editor Pattern
**File:** `src/hybridcoder/layer4/planner.py`
```python
class Architect:
    async def create_plan(self, task: str, context: str) -> ArchitectPlan: ...
    async def refine_plan(self, plan: ArchitectPlan, feedback: str) -> ArchitectPlan: ...
```

**File:** `src/hybridcoder/layer4/editor.py`
```python
class Editor:
    async def execute_step(self, step: str, context: str,
                          file_path: str) -> EditResult: ...
```

### S5.6 Feedback Loop (LLMLOOP)
**File:** `src/hybridcoder/layer4/feedback.py`
- Full loop: Generate → Syntax check → Type check → Lint → Test → Commit
- Error feedback injection on retry
- Max retries configurable

### S5.7 Multi-Step Executor
**File:** `src/hybridcoder/layer4/executor.py`
```python
class TaskExecutor:
    async def execute_task(self, task: str) -> TaskResult:
        # 1. Architect creates plan
        plan = await self.architect.create_plan(task, context)

        # 2. Show plan to user, get approval
        approved = await self.confirm_plan(plan)

        # 3. Execute each step
        for step in plan.steps:
            result = await self.editor.execute_step(step, context, file)
            if not result.success:
                # Retry or rollback
                ...

        # 4. Final verification
        return TaskResult(...)
```

### S5.8 Router Update
- Add Layer 2 and Layer 3 routing
- Full escalation chain: L1 → L2 → L3 → L4

**Tests for S5:**
- `tests/unit/test_shell.py` — sandbox enforcement
- `tests/unit/test_grammar.py` — Pydantic schema validation
- `tests/integration/test_agentic.py` — full agentic task
- `tests/benchmarks/bench_edit.py` — edit success rate

**Exit Criteria:**
- [ ] Multi-file refactoring works end-to-end
- [ ] Architect creates reasonable plans
- [ ] LLMLOOP fixes 70%+ of syntax errors automatically
- [ ] Sandbox blocks all disallowed commands
- [ ] No sandbox escapes
- [ ] Tool calls work correctly

---

## Sprint 6: Polish + Benchmarking (Weeks 13-14)

See **Phase 6: Testing & Benchmarking** document for full details.

### S6.1 Benchmark Suite
- Aider polyglot subset (50 tasks)
- Custom edit test (100 tasks)
- Layer 1 verification (100 queries)
- Custom retrieval (precision@3)

### S6.2 Performance Profiling
- CPU/RAM/VRAM profiling
- Identify and optimize hot paths
- Caching tuning

### S6.3 Documentation
See **Phase 5: Documentation** document.

### S6.4 Release Packaging
- PyPI package
- README with quickstart
- Example projects

**Exit Criteria:**
- [ ] All 12 MVP acceptance criteria pass
- [ ] Benchmarks documented with reproducible results
- [ ] Documentation complete
- [ ] `pip install hybridcoder` works

---

## Dependency Graph Between Sprints

```
S0 (Setup)
 └── S1 (CLI + LLM)
      ├── S2 (Edit System)
      │    └── S5 (Agentic) ──── S6 (Polish)
      └── S3 (Layer 1)
           └── S4 (Layer 2)
                └── S5 (Agentic)
```

**Critical Path:** S0 → S1 → S3 → S4 → S5 → S6
**Parallel Track:** S2 can run parallel with S3 after S1 completes.

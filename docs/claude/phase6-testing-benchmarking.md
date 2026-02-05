# Phase 6: Testing & Benchmarking Plan

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 2.0 | Date: 2026-02-05

---

## 1. Testing Strategy Overview

```
┌─────────────────────────────────────────────┐
│           Testing Pyramid                    │
│                                              │
│              ╱╲ Benchmarks                   │
│             ╱  ╲ (10 suites)                │
│            ╱────╲                            │
│           ╱ Integ ╲                          │
│          ╱  Tests  ╲ (15-20 tests)          │
│         ╱────────────╲                       │
│        ╱  Unit Tests  ╲ (100+ tests)        │
│       ╱────────────────╲                     │
│      ╱  Static Analysis  ╲ (ruff, mypy)     │
│     ╱────────────────────╲                   │
└─────────────────────────────────────────────┘
```

| Level | Count | Runtime | When |
|-------|-------|---------|------|
| Static Analysis | N/A | <10s | Every commit (pre-commit) |
| Unit Tests | 100+ | <30s | Every commit (CI) |
| Integration Tests | 15-20 | <5min | Every PR (CI, requires Ollama) |
| Benchmarks | 10 suites | 30-60min | Weekly / pre-release |

---

## 2. Unit Testing

### 2.1 Framework & Conventions
- **Framework**: pytest 8+
- **Fixtures**: `conftest.py` at each test directory level
- **Naming**: `test_<module>.py` → `test_<function_name>()`
- **Mocking**: `unittest.mock` for external dependencies (Ollama, LLM, LSP)
- **Parametrize**: Use `@pytest.mark.parametrize` for edge cases

### 2.2 Unit Test Plan by Module

#### Router (`tests/unit/test_router.py`)
```python
# Test cases:
# - Deterministic queries classified correctly
@pytest.mark.parametrize("input,expected", [
    ("what type is user_id", RequestType.DETERMINISTIC_QUERY),
    ("find references of calculate_total", RequestType.DETERMINISTIC_QUERY),
    ("list all functions in main.py", RequestType.DETERMINISTIC_QUERY),
    ("where is authentication handled", RequestType.SEMANTIC_SEARCH),
    ("search for database connection code", RequestType.SEMANTIC_SEARCH),
    ("add a docstring to this function", RequestType.SIMPLE_EDIT),
    ("refactor the auth module to use JWT", RequestType.COMPLEX_TASK),
    ("hello, how are you?", RequestType.CHAT),
])
def test_classify_request(input, expected): ...

# - Edge cases: ambiguous queries, empty input, very long input
# - Escalation logic works correctly
```

#### Parser (`tests/unit/test_parser.py`)
```python
# Test cases:
# - Parse valid Python file → correct AST
# - Parse valid Java file → correct AST
# - Extract functions from Python class
# - Extract imports from Python module
# - Extract classes with methods
# - Handle syntax errors gracefully
# - Parse empty file
# - Parse file with only comments
# - Incremental parse after edit
```

#### Chunker (`tests/unit/test_chunker.py`)
```python
# Test cases:
# - Single function → single chunk
# - Large class → multiple method-level chunks
# - Module-level code between functions
# - Chunk size within bounds (50-1000 tokens)
# - Overlap between adjacent chunks
# - Metadata correct (scope chain, imports)
# - Empty file → no chunks
# - File with only imports → module chunk
```

#### Fuzzy Matching (`tests/unit/test_fuzzy.py`)
```python
# Test cases:
# - Exact match returns correct range
# - Normalized whitespace match (tabs vs spaces)
# - Levenshtein match above threshold
# - Levenshtein match below threshold returns None
# - Line-anchored match finds correct range
# - No match in completely different content
# - Match with extra trailing newlines
# - Match in multi-occurrence file (returns first/best)
```

#### Edit Formats (`tests/unit/test_formats.py`)
```python
# Test cases:
# - Parse whole-file output (clean)
# - Parse whole-file output (strip markdown fences)
# - Parse search/replace blocks (single)
# - Parse search/replace blocks (multiple)
# - Handle malformed edit output gracefully
# - Empty output → error
```

#### Git Manager (`tests/unit/test_git.py`)
```python
# Test cases (using tmp_path fixture with git init):
# - commit creates [AI] prefixed commit
# - rollback restores file content
# - undo_last_ai_commit works
# - undo does nothing if no AI commits
# - checkpoint creates savepoint
# - is_repo returns correct value
```

#### Shell Executor (`tests/unit/test_shell.py`)
```python
# Test cases:
# - Allowed command executes successfully
# - Blocked command raises SecurityError
# - Timeout kills long-running process
# - Working directory is restricted
# - Output is captured correctly
# - Command with arguments parsed correctly
# - Empty command raises ValueError
```

#### Search (`tests/unit/test_search.py`)
```python
# Test cases:
# - BM25 search returns keyword matches
# - Vector search returns semantic matches
# - RRF fusion combines rankings correctly
# - Filters by language work
# - Filters by file path work
# - Empty query returns empty results
# - Top-k limit respected
```

#### Grammar (`tests/unit/test_grammar.py`)
```python
# Test cases:
# - ToolCall schema validates correctly
# - EditInstruction schema validates
# - RoutingDecision schema validates
# - Invalid data rejected by Pydantic
# - All Literal types have correct values
```

---

## 3. Integration Testing

### 3.1 Test Environment Requirements
- Ollama running with `qwen3:8b` model
- Python 3.11+ installed
- Git initialized test repo
- ~100MB test corpus of Python files

### 3.2 Integration Test Plan

#### Ollama Integration (`tests/integration/test_ollama.py`)
```python
@pytest.mark.integration
@pytest.mark.requires_ollama
class TestOllamaIntegration:
    def test_connection(self): ...          # Ollama is reachable
    def test_streaming(self): ...           # Stream tokens arrive
    def test_json_mode(self): ...           # JSON output is valid
    def test_first_token_latency(self): ... # <2s to first token
    def test_cancellation(self): ...        # Ctrl+C stops generation
```

#### LSP Integration (`tests/integration/test_lsp.py`)
```python
@pytest.mark.integration
@pytest.mark.requires_pyright
class TestLSPIntegration:
    def test_find_definition(self): ...     # Finds correct location
    def test_find_references(self): ...     # Finds all usages
    def test_hover_type(self): ...          # Returns type info
    def test_diagnostics(self): ...         # Returns lint errors
    def test_stability(self): ...           # No crashes in 100 queries
```

#### LanceDB Integration (`tests/integration/test_lancedb.py`)
```python
@pytest.mark.integration
class TestLanceDBIntegration:
    def test_create_index(self): ...        # Table created
    def test_add_chunks(self): ...          # Chunks stored
    def test_bm25_search(self): ...         # FTS works
    def test_vector_search(self): ...       # ANN works
    def test_hybrid_search(self): ...       # Combined works
    def test_incremental_update(self): ...  # Add/remove chunks
    def test_reindex(self): ...             # Full reindex
```

#### Edit Flow Integration (`tests/integration/test_edit_flow.py`)
```python
@pytest.mark.integration
@pytest.mark.requires_ollama
class TestEditFlow:
    def test_whole_file_edit(self): ...     # Complete edit pipeline
    def test_diff_preview(self): ...        # Diff is correct
    def test_git_commit(self): ...          # Commit created
    def test_undo(self): ...                # Rollback works
    def test_syntax_validation(self): ...   # Bad edits rejected
    def test_no_corruption(self): ...       # 100 edits, 0 corruption
```

#### Agentic Integration (`tests/integration/test_agentic.py`)
```python
@pytest.mark.integration
@pytest.mark.requires_ollama
@pytest.mark.slow
class TestAgenticWorkflow:
    def test_simple_task(self): ...         # Single-file edit via L4
    def test_multi_file_task(self): ...     # Multi-file refactoring
    def test_architect_plan(self): ...      # Plan generation
    def test_feedback_loop(self): ...       # LLMLOOP retry works
    def test_tool_calls(self): ...          # Tools execute correctly
```

---

## 4. Benchmark Suites

### 4.1 Benchmark Framework

```python
# benchmarks/runner.py
@dataclass
class BenchmarkResult:
    suite: str
    total_tasks: int
    passed: int
    failed: int
    pass_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_tokens: int
    llm_calls: int

def run_benchmark(suite: str) -> BenchmarkResult: ...
def save_results(results: list[BenchmarkResult], path: str) -> None: ...
def compare_results(baseline: str, current: str) -> dict: ...
```

### 4.2 Benchmark Suite Details

#### Suite 1: Layer 1 Accuracy (`benchmarks/bench_layer1.py`)
- **Tasks**: 100 deterministic queries on real Python codebases
- **Types**: find_references, find_definition, get_type, list_functions, list_imports
- **Target**: 100% accuracy, <50ms median latency
- **No LLM calls** should be made

```python
LAYER1_TEST_CASES = [
    {"query": "find references of calculate_total", "file": "billing.py",
     "expected_count": 5, "expected_files": ["billing.py", "orders.py"]},
    {"query": "what type is user_id", "file": "models.py",
     "expected_type": "int"},
    # ... 98 more cases
]
```

#### Suite 2: Search Relevance (`benchmarks/bench_search.py`)
- **Tasks**: 50 code search queries with known relevant results
- **Metric**: precision@3 (correct result in top 3)
- **Target**: >60% precision@3
- **Corpus**: 10K-file Python project (e.g., Flask, Django subset)

```python
SEARCH_TEST_CASES = [
    {"query": "authentication middleware", "relevant_files": ["auth.py", "middleware.py"]},
    {"query": "database connection pool", "relevant_files": ["db.py", "pool.py"]},
    # ... 48 more cases
]
```

#### Suite 3: Edit Success Rate (`benchmarks/bench_edit.py`)
- **Tasks**: 100 edit operations on Python files
- **Categories**: add docstring, rename variable, add import, fix bug, add function
- **Metrics**: pass@1 (no retry), pass@3 (with retry)
- **Targets**: >40% pass@1, >75% pass@3

```python
EDIT_TEST_CASES = [
    {"file": "calculator.py", "instruction": "Add type hints to all functions",
     "validation": lambda content: "def add(a: int" in content},
    {"file": "utils.py", "instruction": "Add docstrings to all public functions",
     "validation": lambda content: '"""' in content},
    # ... 98 more cases
]
```

#### Suite 4: Aider Polyglot Subset (`benchmarks/bench_aider.py`)
- **Tasks**: 50 Exercism problems (Python-focused subset)
- **Evaluation**: Run unit tests after edit
- **Metrics**: pass@1 percentage
- **Target**: >40% pass@1
- **Source**: github.com/Aider-AI/polyglot-benchmark

#### Suite 5: Latency Profiling (`benchmarks/bench_latency.py`)
- **Operations**: Router, parse, LSP, search, embed, L3 gen, L4 gen
- **Metric**: median and p95 latency
- **Targets**: Per performance architecture document

| Operation | Median Target | P95 Target |
|-----------|--------------|------------|
| Router | <5ms | <10ms |
| tree-sitter parse | <10ms | <50ms |
| LSP query | <100ms | <500ms |
| BM25 search | <50ms | <100ms |
| Vector search | <150ms | <300ms |
| Hybrid search | <200ms | <500ms |
| L3 generation (500 tok) | <1s | <2s |
| L4 generation (2K tok) | <15s | <30s |

#### Suite 6: Memory Profiling (`benchmarks/bench_memory.py`)
- **Idle**: Process memory with no active inference
- **Inference**: Memory during L3 and L4 generation
- **Index**: Memory during 10K-file indexing
- **Targets**: Idle <2GB, Inference <8GB VRAM

#### Suite 7: Token Efficiency (`benchmarks/bench_tokens.py`)
- **Comparison**: Same 50 tasks, measure tokens used
- **Baseline**: Naive always-call-LLM approach (every query goes to L4)
- **Metric**: Token reduction percentage
- **Target**: 60-80% reduction

#### Suite 8: Stress Test (`benchmarks/bench_stress.py`)
- **100 sequential edits** — 0 file corruptions
- **1-hour LSP session** — no crashes or memory leaks
- **10K file indexing** — completes without OOM
- **Rapid query burst** — 100 queries in 10 seconds

#### Suite 9: Reliability (`benchmarks/bench_reliability.py`)
- **Rollback**: 100% of failed edits restore original
- **Crash recovery**: Simulated kills → state recoverable
- **Git safety**: Every edit creates commit, undo works

#### Suite 10: End-to-End (`benchmarks/bench_e2e.py`)
- **Real-world scenarios**: 10 multi-step tasks
- **Full pipeline**: chat → search → edit → test → commit
- **Measure**: Task completion rate, total time, tokens used

---

## 5. Benchmark Execution

### 5.1 Running Benchmarks
```bash
# Run all benchmarks
make benchmark

# Run specific suite
uv run pytest benchmarks/bench_layer1.py -v

# Run with profiling
uv run pytest benchmarks/ --benchmark-json=results.json

# Compare with baseline
python benchmarks/compare.py baseline.json results.json
```

### 5.2 CI Integration
- **Unit tests**: Every push
- **Integration tests**: Every PR (requires Ollama GitHub Action)
- **Benchmarks**: Weekly scheduled run + pre-release
- **Results**: Stored in `benchmarks/results/` as JSON

### 5.3 Benchmark Environment
- **Standardized hardware**: Document exact GPU/CPU/RAM
- **Model versions**: Pin model files by hash
- **Ollama version**: Pin in CI
- **Reproducibility**: Seed random, fix temperature=0 for deterministic comparison

---

## 6. Test Data Management

### 6.1 Test Fixtures
```
tests/
├── fixtures/
│   ├── python/
│   │   ├── simple_function.py      # Single function
│   │   ├── class_with_methods.py   # Class with methods
│   │   ├── complex_module.py       # Multi-class, imports
│   │   ├── syntax_error.py         # Intentionally broken
│   │   └── large_file.py           # 1000+ lines
│   ├── java/
│   │   ├── Calculator.java
│   │   └── UserService.java
│   └── projects/
│       └── mini_flask/             # Small but real project
│           ├── app.py
│           ├── models.py
│           ├── routes.py
│           └── tests/
```

### 6.2 Test Corpus for Benchmarks
- **Small corpus**: 100 files (in `tests/fixtures/`)
- **Medium corpus**: 1K files (generated or subset of open-source project)
- **Large corpus**: 10K files (Flask/Django subset — downloaded by benchmark setup script)

---

## 7. Quality Gates

### 7.1 PR Merge Requirements
- [ ] All unit tests pass
- [ ] Lint clean (ruff + mypy)
- [ ] Coverage >= target for modified modules
- [ ] No new security vulnerabilities
- [ ] Integration tests pass (if touching L1-L4)

### 7.2 Release Requirements (MVP)
All 12 acceptance criteria from spec.md:

| # | Criterion | Test Suite |
|---|-----------|-----------|
| 1 | CLI operational | Integration: test_cli.py |
| 2 | Local LLM integration | Integration: test_ollama.py |
| 3 | Edit success rate >40% | Benchmark: bench_edit.py |
| 4 | Edit with retry >75% | Benchmark: bench_edit.py |
| 5 | No data loss | Benchmark: bench_stress.py |
| 6 | Rollback works | Benchmark: bench_reliability.py |
| 7 | Layer 1 accuracy 100% | Benchmark: bench_layer1.py |
| 8 | Search relevance >60% | Benchmark: bench_search.py |
| 9 | Latency targets met | Benchmark: bench_latency.py |
| 10 | Memory limits met | Benchmark: bench_memory.py |
| 11 | Sandbox enforced | Unit: test_shell.py |
| 12 | Git safety | Integration: test_edit_flow.py |

---

## 8. Profiling & Optimization Strategy

### 8.1 Profiling Tools
- **CPU**: `py-spy` (sampling profiler, attach to running process)
- **Memory**: `memray` (Python memory profiler)
- **GPU/VRAM**: `nvidia-smi` monitoring during inference
- **Line-level**: `scalene` (CPU + memory + GPU in one)

### 8.2 Optimization Priority
1. **Hot paths first**: Router, parser, search (called on every request)
2. **Cache effectiveness**: Measure hit rates, tune TTLs
3. **Model loading**: Lazy loading, keep-alive between requests
4. **Embedding batching**: Batch chunking + embedding for indexing
5. **Async I/O**: Use asyncio for concurrent LSP + search + LLM calls

### 8.3 Performance Regression Prevention
- Benchmark results stored as JSON baselines
- CI compares against baseline on each run
- Alert if any metric degrades by >10%

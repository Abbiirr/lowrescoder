# Phase 3: Low-Level Design (LLD)

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 2.0 | Date: 2026-02-05

---

## 1. Project Structure

```
hybridcoder/
├── src/
│   └── hybridcoder/
│       ├── __init__.py              # Package version, metadata
│       ├── __main__.py              # python -m hybridcoder entry
│       ├── cli.py                   # Typer app, commands, REPL
│       ├── config.py                # Pydantic config models, loader
│       ├── core/
│       │   ├── __init__.py
│       │   ├── router.py            # Request classifier + layer dispatcher
│       │   ├── context.py           # Context assembly (combine L1+L2 results)
│       │   └── types.py             # Shared enums, dataclasses, protocols
│       ├── layer1/
│       │   ├── __init__.py
│       │   ├── parser.py            # tree-sitter wrapper
│       │   ├── lsp.py               # multilspy wrapper
│       │   ├── queries.py           # Deterministic query handlers
│       │   └── symbols.py           # Symbol table extraction
│       ├── layer2/
│       │   ├── __init__.py
│       │   ├── chunker.py           # AST-aware code chunking
│       │   ├── embeddings.py        # Embedding model wrapper
│       │   ├── search.py            # Hybrid search (BM25 + vector)
│       │   ├── repomap.py           # Repository map generator
│       │   ├── index.py             # LanceDB index management
│       │   └── rules.py             # Project rules loader
│       ├── layer3/
│       │   ├── __init__.py
│       │   ├── llm.py               # llama-cpp-python + Outlines wrapper
│       │   ├── grammar.py           # Pydantic schemas for structured output
│       │   └── output.py            # Output validation and extraction
│       ├── layer4/
│       │   ├── __init__.py
│       │   ├── llm.py               # Ollama async client wrapper
│       │   ├── planner.py           # Architect role
│       │   ├── editor.py            # Editor role (execute edits)
│       │   ├── tools.py             # Tool registry + definitions
│       │   ├── feedback.py          # LLMLOOP (syntax→type→lint→test)
│       │   └── executor.py          # Multi-step task orchestrator
│       ├── edit/
│       │   ├── __init__.py
│       │   ├── formats.py           # Parse edit output (whole-file, search/replace)
│       │   ├── fuzzy.py             # Fuzzy matching for search/replace
│       │   ├── apply.py             # Apply edits with verification pipeline
│       │   └── diff.py              # Diff generation and display
│       ├── git/
│       │   ├── __init__.py
│       │   └── manager.py           # Git operations (commit, undo, branch)
│       ├── shell/
│       │   ├── __init__.py
│       │   └── executor.py          # Sandboxed command execution
│       └── utils/
│           ├── __init__.py
│           ├── cache.py             # LRU cache with TTL
│           ├── logging.py           # Structured logging
│           └── metrics.py           # Performance metrics collection
├── tests/
│   ├── unit/
│   │   ├── test_router.py
│   │   ├── test_parser.py
│   │   ├── test_chunker.py
│   │   ├── test_fuzzy.py
│   │   ├── test_formats.py
│   │   ├── test_search.py
│   │   ├── test_grammar.py
│   │   ├── test_git.py
│   │   └── test_shell.py
│   ├── integration/
│   │   ├── test_lsp.py
│   │   ├── test_ollama.py
│   │   ├── test_lancedb.py
│   │   ├── test_edit_flow.py
│   │   └── test_agentic.py
│   ├── benchmarks/
│   │   ├── bench_layer1.py
│   │   ├── bench_search.py
│   │   ├── bench_edit.py
│   │   └── bench_aider.py
│   └── conftest.py                  # Shared fixtures
├── docs/
│   ├── plan.md
│   ├── spec.md
│   └── claude/                      # Research & plan documents
├── pyproject.toml
├── Makefile
├── CLAUDE.md
├── AGENTS.md
└── README.md
```

---

## 2. Data Models

### 2.1 Core Types (`core/types.py`)

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class RequestType(Enum):
    DETERMINISTIC_QUERY = "deterministic"   # → Layer 1
    SEMANTIC_SEARCH = "search"              # → Layer 2
    SIMPLE_EDIT = "simple_edit"             # → Layer 3
    COMPLEX_TASK = "complex_task"           # → Layer 4
    CHAT = "chat"                           # → Layer 4
    CONFIGURATION = "config"                # → Config
    HELP = "help"                           # → Built-in

class LayerResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ESCALATE = "escalate"       # Try next layer

@dataclass
class Request:
    raw_input: str
    request_type: RequestType
    file_context: Optional[str] = None
    symbol: Optional[str] = None
    conversation_history: list[dict] = field(default_factory=list)

@dataclass
class Response:
    content: str
    layer_used: int             # 1-4
    tokens_used: int = 0
    latency_ms: float = 0.0
    files_modified: list[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

@dataclass
class FileRange:
    path: str
    start_line: int = 1
    end_line: Optional[int] = None

@dataclass
class Symbol:
    name: str
    kind: str           # function, class, variable, import, method
    file: str
    line: int
    end_line: int
    scope: Optional[str] = None     # parent class/function
    type_annotation: Optional[str] = None

@dataclass
class CodeChunk:
    content: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    chunk_type: str         # function, class, module, block
    scope_chain: list[str]  # e.g., ["MyClass", "my_method"]
    imports: list[str]
    embedding: Optional[list[float]] = None

@dataclass
class SearchResult:
    chunk: CodeChunk
    score: float
    match_type: str     # bm25, vector, hybrid

@dataclass
class EditResult:
    file_path: str
    original_content: str
    new_content: str
    diff: str
    syntax_valid: bool
    lint_passed: bool
    type_check_passed: bool
    commit_sha: Optional[str] = None
```

### 2.2 Tool Call Schema (`layer3/grammar.py`)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class ToolCall(BaseModel):
    """Schema for LLM tool calls — constrained by Outlines."""
    tool: Literal[
        "read_file", "write_file", "search_code",
        "run_command", "find_references", "get_diagnostics"
    ]
    arguments: dict

class ReadFileArgs(BaseModel):
    path: str
    start_line: int = 1
    end_line: Optional[int] = None

class WriteFileArgs(BaseModel):
    path: str
    content: str

class SearchCodeArgs(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)

class RunCommandArgs(BaseModel):
    command: str
    timeout: int = Field(default=30, ge=1, le=300)

class EditInstruction(BaseModel):
    """Schema for constrained edit generation."""
    file_path: str
    search_block: str
    replace_block: str
    explanation: str

class RoutingDecision(BaseModel):
    """Schema for query routing (used by L3 when router is uncertain)."""
    request_type: Literal["deterministic", "search", "simple_edit", "complex_task", "chat"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

class ArchitectPlan(BaseModel):
    """Schema for L4 architect planning output."""
    summary: str
    steps: list[str]
    files_to_modify: list[str]
    files_to_read: list[str]
    estimated_complexity: Literal["low", "medium", "high"]
```

### 2.3 Configuration Model (`config.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class LLMConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    model: str = "qwen3:8b"
    api_base: str = "http://localhost:11434"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = 4096
    context_length: int = 8192

class Layer3Config(BaseModel):
    enabled: bool = True
    model_path: str = "~/.hybridcoder/models/qwen2.5-coder-1.5b-q4_k_m.gguf"
    grammar_constrained: bool = True

class Layer1Config(BaseModel):
    enabled: bool = True
    cache_ttl: int = 300

class Layer2Config(BaseModel):
    enabled: bool = True
    embedding_model: str = "jinaai/jina-embeddings-v2-base-code"
    search_top_k: int = 10
    chunk_size: int = 1000
    hybrid_weight: float = Field(default=0.5, ge=0.0, le=1.0)

class Layer4Config(BaseModel):
    enabled: bool = True
    max_retries: int = 3

class EditConfig(BaseModel):
    format: Literal["whole_file", "search_replace"] = "whole_file"
    fuzzy_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    auto_commit: bool = True

class GitConfig(BaseModel):
    auto_commit: bool = True
    commit_prefix: str = "[AI]"

class ShellConfig(BaseModel):
    timeout: int = 30
    max_timeout: int = 300
    allowed_commands: list[str] = ["pytest", "python", "pip", "mvn", "gradle", "git"]
    blocked_commands: list[str] = ["rm -rf", "sudo", "curl", "wget"]
    allow_network: bool = False

class UIConfig(BaseModel):
    theme: Literal["dark", "light", "auto"] = "dark"
    show_diff: bool = True
    confirm_edits: bool = True
    stream_output: bool = True
    verbose: bool = False

class HybridCoderConfig(BaseModel):
    llm: LLMConfig = LLMConfig()
    layer1: Layer1Config = Layer1Config()
    layer2: Layer2Config = Layer2Config()
    layer3: Layer3Config = Layer3Config()
    layer4: Layer4Config = Layer4Config()
    edit: EditConfig = EditConfig()
    git: GitConfig = GitConfig()
    shell: ShellConfig = ShellConfig()
    ui: UIConfig = UIConfig()
```

---

## 3. Key Algorithms

### 3.1 Router Classification Algorithm

```python
def classify_request(user_input: str, context: dict) -> RequestType:
    """
    Classify request to lowest-cost layer. No LLM involved.

    Priority order (cheapest first):
    1. Keyword/regex patterns for deterministic queries
    2. Search intent detection
    3. Simple edit patterns
    4. Default: complex task / chat
    """
    input_lower = user_input.lower().strip()

    # Layer 1: Deterministic queries
    DETERMINISTIC_PATTERNS = [
        r"(what|find|show|get|list)\s+(type|definition|references|usages|callers|signature|imports|functions|classes|symbols)",
        r"(go\s+to|jump\s+to)\s+(definition|declaration)",
        r"where\s+is\s+\w+\s+(defined|declared|used)",
        r"(type|typeof)\s+(of\s+)?\w+",
        r"list\s+(all\s+)?(functions|classes|methods|imports)",
    ]
    for pattern in DETERMINISTIC_PATTERNS:
        if re.search(pattern, input_lower):
            return RequestType.DETERMINISTIC_QUERY

    # Layer 2: Search intent
    SEARCH_PATTERNS = [
        r"(search|find|look\s+for|grep|where)\s+.*(code|function|class|file|module)",
        r"(how|where)\s+(does|is)\s+\w+\s+(implemented|handled|used|called)",
    ]
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, input_lower):
            return RequestType.SEMANTIC_SEARCH

    # Layer 3: Simple edit
    SIMPLE_EDIT_PATTERNS = [
        r"(add|write|create|insert)\s+(a\s+)?(docstring|comment|type\s+hint|import)",
        r"(rename|change)\s+\w+\s+to\s+\w+",
        r"(fix|correct)\s+(the\s+)?(typo|spelling|indentation)",
    ]
    for pattern in SIMPLE_EDIT_PATTERNS:
        if re.search(pattern, input_lower):
            return RequestType.SIMPLE_EDIT

    # Check for explicit edit intent
    if any(word in input_lower for word in ["edit", "modify", "refactor", "rewrite", "implement", "add feature"]):
        return RequestType.COMPLEX_TASK

    # Default: chat/complex
    return RequestType.CHAT
```

### 3.2 AST-Aware Chunking Algorithm

```python
def chunk_file(source: str, file_path: str, language: str,
               max_tokens: int = 1000, min_tokens: int = 50) -> list[CodeChunk]:
    """
    Split file into chunks respecting AST boundaries.

    Strategy:
    1. Parse with tree-sitter
    2. Extract top-level definitions (functions, classes)
    3. Each definition = one chunk (split if > max_tokens)
    4. Module-level code between definitions = one chunk
    5. Classes: each method is a sub-chunk
    """
    tree = parse(source, language)
    root = tree.root_node
    chunks = []
    current_module_lines = []

    for child in root.children:
        if child.type in ('function_definition', 'class_definition',
                          'method_declaration', 'class_declaration'):
            # Flush any accumulated module-level code
            if current_module_lines:
                chunks.append(make_chunk(current_module_lines, "module", ...))
                current_module_lines = []

            node_text = source[child.start_byte:child.end_byte]
            token_count = estimate_tokens(node_text)

            if token_count <= max_tokens:
                chunks.append(make_chunk(node_text, child.type, ...))
            else:
                # Split large classes into method-level chunks
                chunks.extend(split_large_node(child, source, max_tokens))
        else:
            current_module_lines.append(child)

    if current_module_lines:
        chunks.append(make_chunk(current_module_lines, "module", ...))

    return [c for c in chunks if estimate_tokens(c.content) >= min_tokens]
```

### 3.3 Hybrid Search Scoring

```python
def hybrid_search(query: str, table, embedding_fn, top_k: int = 10,
                  weight: float = 0.5) -> list[SearchResult]:
    """
    Reciprocal Rank Fusion of BM25 + vector search.

    weight: 0.0 = pure BM25, 1.0 = pure vector, 0.5 = balanced
    """
    k = 60  # RRF constant

    # BM25 search
    bm25_results = table.search(query, query_type="fts").limit(top_k * 2).to_list()

    # Vector search
    query_embedding = embedding_fn(query)
    vector_results = table.search(query_embedding).limit(top_k * 2).to_list()

    # RRF fusion
    scores = {}
    for rank, result in enumerate(bm25_results):
        doc_id = result["_rowid"]
        scores[doc_id] = scores.get(doc_id, 0) + (1 - weight) / (k + rank + 1)

    for rank, result in enumerate(vector_results):
        doc_id = result["_rowid"]
        scores[doc_id] = scores.get(doc_id, 0) + weight / (k + rank + 1)

    # Sort by fused score, return top_k
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [make_search_result(doc_id, score) for doc_id, score in ranked]
```

### 3.4 Fuzzy Matching Algorithm

```python
def fuzzy_match(search_block: str, file_content: str,
                threshold: float = 0.8) -> Optional[tuple[int, int]]:
    """
    Find the best match for search_block in file_content.

    Strategy (in order of preference):
    1. Exact match
    2. Normalized whitespace match
    3. Levenshtein similarity (>threshold)
    4. Line-anchored match (first/last lines exact)
    """
    # 1. Exact match
    idx = file_content.find(search_block)
    if idx >= 0:
        return (idx, idx + len(search_block))

    # 2. Normalize whitespace
    normalized_search = normalize_whitespace(search_block)
    normalized_file = normalize_whitespace(file_content)
    idx = normalized_file.find(normalized_search)
    if idx >= 0:
        return map_back_to_original(idx, file_content, normalized_file)

    # 3. Levenshtein sliding window
    search_lines = search_block.splitlines()
    file_lines = file_content.splitlines()
    window_size = len(search_lines)

    best_score = 0.0
    best_range = None
    for i in range(len(file_lines) - window_size + 1):
        window = "\n".join(file_lines[i:i + window_size])
        score = levenshtein_ratio(search_block, window)
        if score > best_score:
            best_score = score
            best_range = (i, i + window_size)

    if best_score >= threshold:
        return line_range_to_byte_range(best_range, file_content)

    # 4. Line-anchored match
    first_line = search_lines[0].strip()
    last_line = search_lines[-1].strip()
    for i, line in enumerate(file_lines):
        if line.strip() == first_line:
            for j in range(i + 1, min(i + window_size * 2, len(file_lines))):
                if file_lines[j].strip() == last_line:
                    return line_range_to_byte_range((i, j + 1), file_content)

    return None  # No match found
```

### 3.5 LLMLOOP Feedback Algorithm

```python
async def llmloop(task: str, context: str, file_path: str,
                  max_retries: int = 3) -> EditResult:
    """
    Generate → Validate → Fix → Commit feedback loop.

    Steps per iteration:
    1. Generate edit (L3 or L4)
    2. Parse syntax (tree-sitter) — retry up to 3x
    3. Type check (Pyright) — retry up to 2x
    4. Lint (ruff) — auto-fix where possible
    5. Run tests — retry up to 3x with test output feedback
    6. Commit on success, rollback on exhausted retries
    """
    original_content = read_file(file_path)
    git_manager.checkpoint(file_path)  # Save state

    for attempt in range(max_retries):
        # Generate
        edit = await generate_edit(task, context, file_path,
                                   error_feedback=error_feedback if attempt > 0 else None)

        # Validate syntax
        new_content = apply_edit(edit, original_content)
        syntax_ok = check_syntax(new_content, file_path)
        if not syntax_ok:
            error_feedback = f"Syntax error: {syntax_ok.error}"
            continue

        # Type check
        write_file(file_path, new_content)
        type_errors = run_type_check(file_path)
        if type_errors:
            error_feedback = f"Type errors:\n{type_errors}"
            write_file(file_path, original_content)  # Restore
            continue

        # Lint (auto-fix)
        lint_result = run_lint(file_path, autofix=True)
        new_content = read_file(file_path)  # Re-read after autofix

        # Tests
        test_result = run_tests(file_path)
        if not test_result.passed:
            error_feedback = f"Test failures:\n{test_result.output}"
            write_file(file_path, original_content)  # Restore
            continue

        # Success!
        commit_sha = git_manager.commit(file_path, f"[AI] {task}")
        return EditResult(
            file_path=file_path,
            original_content=original_content,
            new_content=new_content,
            syntax_valid=True,
            lint_passed=True,
            type_check_passed=True,
            commit_sha=commit_sha,
        )

    # All retries exhausted
    git_manager.rollback(file_path)
    return EditResult(file_path=file_path, success=False,
                      error=f"Failed after {max_retries} attempts: {error_feedback}")
```

---

## 4. Error Handling Strategy

### 4.1 Error Categories

| Category | Example | Strategy |
|----------|---------|----------|
| **Recoverable** | LLM timeout, parse failure | Retry with backoff |
| **Degradable** | LSP unavailable | Fall back to tree-sitter |
| **User-visible** | Invalid edit, test failure | Show error, offer retry |
| **Fatal** | Config corrupt, Ollama down | Clear error message, exit |

### 4.2 Retry Policy

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base: float = 1.0   # seconds
    backoff_factor: float = 2.0
    retryable_errors: tuple = (TimeoutError, ConnectionError, LLMParseError)
```

### 4.3 Graceful Degradation Chain

```
LSP unavailable → Fall back to tree-sitter symbol extraction
Ollama unavailable → Show error: "Start Ollama with: ollama serve"
Embedding model unavailable → Use BM25-only search
Layer 3 model unavailable → Route to Layer 4 for all generation
LanceDB corrupt → Re-index on next query
Git not initialized → Warn user, disable auto-commit
```

---

## 5. LanceDB Index Schema

```python
import lancedb
from pydantic import BaseModel
from typing import Optional

class ChunkRecord(BaseModel):
    """Schema for LanceDB code chunk table."""
    id: str                     # Hash of file_path + start_line
    file_path: str
    language: str               # python, java, etc.
    chunk_type: str             # function, class, module, method
    symbol_name: Optional[str]  # Name of function/class if applicable
    scope_chain: str            # JSON-encoded list
    start_line: int
    end_line: int
    content: str                # Raw code text
    imports: str                # JSON-encoded list
    file_hash: str              # For invalidation
    embedding: list[float]      # 768-dim vector (jina-v2)

# Table creation
db = lancedb.connect("~/.hybridcoder/index")
table = db.create_table("code_chunks", schema=ChunkRecord)

# FTS index for BM25
table.create_fts_index("content")

# Vector index for ANN search
table.create_index("embedding", index_type="IVF_PQ", num_partitions=32)
```

---

## 6. Prompt Templates

### 6.1 System Prompt (Layer 4)

```
You are HybridCoder, an AI coding assistant. You help edit code in {project_name}.
Working directory: {working_dir}
Languages: {languages}

Project rules:
{project_rules}

Repository map (top symbols):
{repo_map}

You have access to these tools:
- read_file(path, start_line?, end_line?) — Read file contents
- write_file(path, content) — Write complete file
- search_code(query, limit?) — Search codebase
- run_command(command, timeout?) — Run shell command (sandboxed)
- find_references(symbol, file) — Find all usages of symbol
- get_diagnostics(path) — Get lint/type errors

Always explain your reasoning before making changes.
Verify changes compile and pass tests when possible.
```

### 6.2 Edit Prompt (Whole File)

```
Edit the file {file_path} to {task_description}.

Current file content:
```{language}
{file_content}
```

Context from codebase:
{context_chunks}

Return ONLY the complete updated file content.
Do NOT include markdown fences, explanations, or anything else.
Just the raw file content.
```

### 6.3 Edit Prompt (Search/Replace)

```
Edit {file_path} to {task_description}.

Current file content:
```{language}
{file_content}
```

Return your edits as SEARCH/REPLACE blocks:

<<<<<<< SEARCH
exact code to find
=======
replacement code
>>>>>>> REPLACE

Rules:
- SEARCH block must match EXACTLY (including whitespace)
- Include enough context lines for unique matching
- Multiple SEARCH/REPLACE blocks for multiple changes
```

### 6.4 Architect Prompt

```
You are the Architect. Analyze the codebase and create a step-by-step plan.

Task: {task_description}

Available context:
{context_chunks}

Repository structure:
{repo_map}

Create a numbered plan. For each step specify:
1. What file to modify
2. What change to make
3. Why this change is needed

Do NOT write code yet. Only plan.
```

---

## 7. Context Budget Management

```python
def assemble_context(request: Request, budget: int = 6000) -> str:
    """
    Assemble context within token budget.

    Allocation:
    - Repo map: 500-1000 tokens (priority 1)
    - Project rules: 500-1000 tokens (priority 2)
    - Relevant code chunks: 2000-3000 tokens (priority 3)
    - User history: 1000-2000 tokens (priority 4)
    """
    context_parts = []
    remaining = budget

    # 1. Repo map (always included, truncated to budget)
    repo_map = generate_repo_map(max_tokens=min(1000, remaining // 4))
    context_parts.append(f"## Repository Map\n{repo_map}")
    remaining -= count_tokens(repo_map)

    # 2. Project rules
    rules = load_project_rules(max_tokens=min(1000, remaining // 4))
    if rules:
        context_parts.append(f"## Project Rules\n{rules}")
        remaining -= count_tokens(rules)

    # 3. Relevant chunks (from L2 search)
    if request.raw_input:
        chunks = search(request.raw_input, top_k=10)
        for chunk in chunks:
            chunk_text = format_chunk(chunk)
            chunk_tokens = count_tokens(chunk_text)
            if chunk_tokens <= remaining:
                context_parts.append(chunk_text)
                remaining -= chunk_tokens
            else:
                break

    # 4. Conversation history (truncated from end)
    for msg in reversed(request.conversation_history):
        msg_tokens = count_tokens(msg["content"])
        if msg_tokens <= remaining:
            context_parts.insert(0, f"[{msg['role']}]: {msg['content']}")
            remaining -= msg_tokens
        else:
            break

    return "\n\n".join(context_parts)
```

---

## 8. Observability Design

### 8.1 Structured Log Format

```python
@dataclass
class RequestLog:
    timestamp: str
    request_id: str
    request_type: str
    layer_used: int
    latency_ms: float
    tokens_input: int
    tokens_output: int
    model: Optional[str]
    success: bool
    retries: int
    files_modified: list[str]
    error: Optional[str]
```

### 8.2 Metrics Collected

| Metric | Type | Purpose |
|--------|------|---------|
| `layer_hits` | Counter | How often each layer is used |
| `request_latency` | Histogram | End-to-end response time |
| `tokens_used` | Counter | Total tokens consumed |
| `edit_success_rate` | Gauge | % of edits that succeed |
| `cache_hit_rate` | Gauge | Parse tree / LSP cache effectiveness |
| `search_precision` | Gauge | Retrieval quality tracking |
| `llm_call_rate` | Counter | How often LLM is invoked (should be <40%) |

### 8.3 Debug Mode

```bash
hybridcoder chat --verbose  # Show layer routing decisions
hybridcoder chat --debug    # Show full prompts and responses (local log file)
```

---

## 9. Module-to-Test Mapping

| Module | Unit Tests | Integration Tests | Benchmarks |
|--------|-----------|-------------------|------------|
| `core/router.py` | test_router.py | - | - |
| `layer1/parser.py` | test_parser.py | - | bench_layer1.py |
| `layer1/lsp.py` | - | test_lsp.py | bench_layer1.py |
| `layer1/queries.py` | test_queries.py | test_lsp.py | bench_layer1.py |
| `layer2/chunker.py` | test_chunker.py | - | - |
| `layer2/search.py` | test_search.py | test_lancedb.py | bench_search.py |
| `layer2/embeddings.py` | - | test_lancedb.py | bench_search.py |
| `layer3/grammar.py` | test_grammar.py | - | - |
| `layer3/llm.py` | - | test_outlines.py | - |
| `layer4/llm.py` | - | test_ollama.py | - |
| `layer4/executor.py` | - | test_agentic.py | bench_edit.py |
| `edit/formats.py` | test_formats.py | - | - |
| `edit/fuzzy.py` | test_fuzzy.py | - | bench_edit.py |
| `edit/apply.py` | test_apply.py | test_edit_flow.py | bench_edit.py |
| `git/manager.py` | test_git.py | test_edit_flow.py | - |
| `shell/executor.py` | test_shell.py | - | - |

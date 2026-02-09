# Phase 3: Code Intelligence

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 1.0 | Date: 2026-02-06
> Depends on: Phase 2 (TUI Prototype) — COMPLETE
> Consensus: Reached via agent comms

---

## 1. Goal

Implement Layer 1 (deterministic analysis) and Layer 2 (retrieval & context) to transform HybridCoder from a thin LLM wrapper into a **truly hybrid** coding assistant. By the end of Phase 3:

- Tree-sitter parsing extracts symbols, scopes, and imports in <10ms per file
- A request router classifies queries and sends 60-80% of deterministic questions to Layer 1 with **zero LLM tokens**
- LSP integration (Jedi via multilspy) provides type info, definitions, and references — with tree-sitter fallback when unavailable
- AST-aware chunking splits code at function/class boundaries for semantic search
- LanceDB-backed hybrid search (BM25 + vector + RRF) retrieves relevant code
- Repository map and context assembler build optimized LLM prompts within a 6000-token budget
- 6 new tools and 1 new slash command integrated into the Python backend + Go TUI
- Go TUI status bar shows which layer handled each response [L1/L4]

**Implementation status:** Not started. *(Document updated 2026-02-08 to reflect Go Bubble Tea migration and dependency version updates.)*

---

## 2. Competitor Analysis

### How Competitors Handle Code Intelligence

| Feature | Aider | Continue.dev | Cursor | Claude Code |
|---------|-------|-------------|--------|-------------|
| Parsing | tree-sitter repo-map | Tree-sitter + LSP | Custom AST | None (tool-based) |
| Indexing | Tag-based ranking | Embeddings + re-rank | Proprietary index | On-demand search |
| Search | Grep + repo-map | BM25 + vector | Custom hybrid | ripgrep |
| Context | Repo-map in prompt | @codebase provider | Auto-context | Tool results |
| Deterministic bypass | None | None | None | None |

### HybridCoder's Advantage

None of the major competitors route deterministic queries away from the LLM. They all send every query through the language model, even simple lookups like "list functions in X" or "find usages of Y". This is HybridCoder's core differentiator:

- **60-80% of queries** handled deterministically in <50ms with 0 tokens
- **20-40% of queries** use LLM with curated context (repo map + search results)
- Zero cost for structural queries, zero latency, zero cloud dependency

---

## 3. Scope

### In Scope

- Tree-sitter parser for Python with mtime-based caching (<10ms parse)
- Symbol extraction: functions, classes, methods, imports, variables with scope chains
- Request router: regex + heuristic scoring, no LLM involved
- Deterministic query handlers: list symbols, find references (grep fallback), get imports, get signatures
- LSP client wrapper (multilspy + Jedi) with lazy server start and 30s cache TTL
- Graceful LSP degradation to tree-sitter + grep when server unavailable
- AST-aware code chunker splitting at function/class boundaries
- Embedding engine (jina-v2-base-code, CPU-only, lazy-loaded)
- Graceful embedding degradation to BM25-only when model unavailable
- LanceDB code index with file-hash invalidation and incremental updates
- Hybrid search: BM25 + vector + Reciprocal Rank Fusion
- On-demand indexing (first search triggers build), mtime-based refresh
- gitignore-aware file discovery with 50K file cap
- Repository map generator (ranked symbol summary, 800-token budget)
- Rules loader (CLAUDE.md, AGENTS.md, .rules/*.md, .cursorrules)
- Context assembler with priority-based 6000-token budget allocation
- 6 new agent tools: find_references, find_definition, get_type_info, list_symbols, search_code, get_diagnostics
- `/index` slash command for manual index rebuild
- Layer indicator [L1/L2/L4] in status bar
- Import validation and syntax validation via tree-sitter
- Sprint verification tests for Phase 3

### Out of Scope (Deferred)

- Multi-language support beyond Python (Java, TypeScript, etc.)
- Real-time file watching (use mtime-based refresh instead)
- Layer 3 constrained generation (Outlines + llama-cpp-python)
- Edit system (apply_diff, search_replace, fuzzy matching)
- Git integration (auto-commit, undo, rollback)
- Multi-step planner and architect/editor split
- Go TUI enhancements beyond layer indicator (inline mode already complete)

---

## 4. Architecture

### 4.1 Data Flow

```
User Input (Go TUI — cmd/hybridcoder-tui/)
    │
    ├─ Slash command? → Go handles locally (/exit, /clear, /thinking)
    │                   or delegates to Python (/index, /model, /mode, etc.)
    │                   via JSON-RPC "command" request
    │
    └─ Chat message → JSON-RPC "chat" request
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Python Backend (backend/server.py — handle_chat)                │
│                                                                   │
│  1. CommandRouter (slash commands via "command" RPC)              │
│     ├─ /index  → triggers manual index rebuild                   │
│     └─ /help, /model, /mode, etc. → existing handlers           │
│                                                                   │
│  2. RequestRouter (NEW — core/router.py, BEFORE agent loop)      │
│     ├─ Stage 1: Regex pattern matching                           │
│     ├─ Stage 2: Feature extraction (has file ref? symbol name?)  │
│     └─ Stage 3: Weighted scoring → RequestType                  │
│                                                                   │
│     Routes to:                                                    │
│     ├─ DETERMINISTIC_QUERY → Layer 1 (direct, no LLM)           │
│     ├─ SEMANTIC_SEARCH     → Layer 2 context → Layer 4 LLM      │
│     └─ COMPLEX_TASK/CHAT   → Layer 4 LLM (with L2 context)      │
└──────┬──────────┬──────────┬─────────────────────────────────────┘
       │          │          │
       ▼          │          │
┌────────────┐    │          │
│  Layer 1   │    │          │
│ (parser.py │    │          │
│  symbols.py│    │          │
│  queries.py│    │          │
│  lsp.py)   │    │          │
│            │    │          │
│ <50ms      │    │          │
│ 0 tokens   │    │          │
└─────┬──────┘    │          │
      │           ▼          │
      │    ┌────────────┐    │
      │    │  Layer 2   │    │
      │    │ (chunker   │    │
      │    │  embeddings│    │
      │    │  index     │    │
      │    │  search    │    │
      │    │  repomap   │    │
      │    │  context)  │    │
      │    │            │    │
      │    │ 100-500ms  │    │
      │    │ 0 LLM tkns │    │
      │    └─────┬──────┘    │
      │          │           │
      │          ▼           ▼
      │    ┌──────────────────────┐
      │    │  Layer 4 (AgentLoop) │
      │    │  LLM with context    │
      │    │  5-30s, 2K-8K tokens │
      │    └──────────┬───────────┘
      │               │
      ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│  on_token + on_done (JSON-RPC notifications)                     │
│  ├─ on_done includes layer_used=1 (L1) or layer_used=4 (L4)    │
│  └─ Go TUI renders response + status bar shows [L1]/[L4]       │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Router location | Pre-processor BEFORE AgentLoop | L1 queries should never touch LLM |
| L1 bypass | Returns Response directly, no AgentLoop | Sub-50ms, no async LLM overhead |
| Embedding loading | Lazy (first search), CPU-only | Preserves GPU VRAM for LLM, <2s startup |
| LSP availability | Optional with tree-sitter fallback | multilspy may be unstable; tree-sitter handles 80% |
| Indexing trigger | On-demand (first search), mtime refresh | No file watcher complexity, no idle overhead |
| Python-first | Python MVP, Java/TS deferred | Reduce scope risk, validate approach first |
| Token budget | 6000 total, priority-allocated | Matches 8192 context with room for response |
| Search fusion | BM25 + vector + RRF | Best quality per LanceDB docs and research |

### 4.3 Module Dependencies

```
core/router.py     → core/types.py, layer1/*, layer2/*
core/context.py    → layer2/search.py, layer2/repomap.py, layer2/rules.py

layer1/__init__.py → (empty, package marker)
layer1/parser.py   → tree-sitter, tree-sitter-python
layer1/symbols.py  → layer1/parser.py, core/types.py
layer1/lsp.py      → multilspy (optional)
layer1/queries.py  → layer1/symbols.py, layer1/lsp.py, layer1/parser.py
layer1/validators.py → layer1/parser.py

layer2/__init__.py → (empty, package marker)
layer2/chunker.py  → layer1/parser.py, layer1/symbols.py, core/types.py
layer2/embeddings.py → sentence-transformers (optional)
layer2/index.py    → layer2/chunker.py, layer2/embeddings.py, lancedb
layer2/search.py   → layer2/index.py
layer2/repomap.py  → layer1/symbols.py
layer2/rules.py    → (standalone, reads files)

agent/tools.py     → layer1/queries.py, layer1/lsp.py (new tools)
agent/prompts.py   → core/context.py (context injection)
backend/server.py  → core/router.py, layer1/queries.py, core/context.py (L1 bypass before agent loop)
tui/commands.py    → layer2/index.py (/index command)
```

Go TUI module integration (minimal — consumes JSON-RPC only):
```
cmd/hybridcoder-tui/protocol.go   → LayerUsed in DoneParams
cmd/hybridcoder-tui/messages.go   → LayerUsed in backendDoneMsg
cmd/hybridcoder-tui/backend.go    → Pass LayerUsed in on_done dispatch
cmd/hybridcoder-tui/statusbar.go  → Layer field, render [L1]/[L4] in View()
cmd/hybridcoder-tui/update.go     → Set m.statusBar.Layer in handleDone()
cmd/hybridcoder-tui/commands.go   → Add "/index" to knownCommands
```

---

## 5. Sprint Plan

### Sprint 3A: Tree-sitter Parser + Symbol Extraction (2-3 days)

**Goal:** Parse Python files, extract all symbols with scope chains, cache with mtime.

#### New Files

**`src/hybridcoder/layer1/__init__.py`**
```
Empty package marker.
```

**`src/hybridcoder/layer1/parser.py`** — `TreeSitterParser` class
- Constructor: initialize tree-sitter Parser with Python language
- `parse(source: str | bytes) -> tree_sitter.Tree`: parse source code
- `parse_file(path: Path) -> tree_sitter.Tree`: parse from file with mtime cache
- `invalidate(path: Path)`: remove file from cache
- `clear_cache()`: clear all cached parses
- Cache implementation: `dict[Path, tuple[float, Tree]]` keyed by (path → mtime, tree)
- Cache eviction: LRU with max 500 entries
- Performance target: <10ms per file for files up to 5000 lines
- Dependencies: `tree-sitter>=0.25.2`, `tree-sitter-python>=0.25.0`
- tree-sitter 0.25.x API: `Language(tspython.language())` capsule-based constructor, `Parser(PY_LANGUAGE)` constructor

**`src/hybridcoder/layer1/symbols.py`** — `SymbolExtractor` class
- Constructor: takes `TreeSitterParser` instance
- `extract_symbols(source: str, file_path: str = "") -> list[Symbol]`: extract all symbols from source
- `extract_from_file(path: Path) -> list[Symbol]`: extract from file (uses parser cache)
- `extract_imports(source: str) -> list[str]`: extract import statements
- `get_scope_chain(node: tree_sitter.Node) -> list[str]`: walk up tree to build scope
- Symbol kinds: `function`, `class`, `method`, `variable`, `import`
- Uses tree-sitter queries (S-expressions) via **QueryCursor API** (0.25.x):
  - Functions: `(function_definition name: (identifier) @name)`
  - Classes: `(class_definition name: (identifier) @name)`
  - Methods: `(class_definition body: (block (function_definition name: (identifier) @name)))`
  - Imports: `(import_statement)`, `(import_from_statement)`
  - Variables: `(assignment left: (identifier) @name)` (module-level only)
- **QueryCursor pattern**: `QueryCursor(query).captures(node)` returns `dict[str, list[Node]]` (not the old `Query.captures(node)` returning `list[(Node, str)]`)
- Populates: `Symbol.name`, `kind`, `file`, `line`, `end_line`, `scope`, `type_annotation`

#### Modified Files

**`src/hybridcoder/core/types.py`** — add `ParseResult` dataclass:
```python
@dataclass
class ParseResult:
    """Result from tree-sitter parsing."""
    symbols: list[Symbol]
    imports: list[str]
    file_path: str
    language: str = "python"
    parse_time_ms: float = 0.0
    from_cache: bool = False
```

#### Tests: `tests/unit/test_parser.py` (~20 tests)

```
TestTreeSitterParser:
  test_parse_simple_function
  test_parse_class_with_methods
  test_parse_empty_file
  test_parse_syntax_error_returns_tree
  test_parse_file_caches_by_mtime
  test_parse_file_invalidates_on_change
  test_cache_clear
  test_cache_lru_eviction
  test_parse_performance_under_10ms (benchmark)

TestSymbolExtractor:
  test_extract_function
  test_extract_class
  test_extract_method_with_scope
  test_extract_nested_class
  test_extract_imports
  test_extract_from_imports
  test_extract_module_variable
  test_extract_typed_variable
  test_scope_chain_nested
  test_extract_from_file
  test_empty_file_returns_empty
```

---

### Sprint 3B: Request Router + Deterministic Query Handlers (2-3 days)

**Goal:** Classify user queries by type and handle deterministic queries without LLM.

#### New Files

**`src/hybridcoder/core/router.py`** — `RequestRouter` class

3-stage classification pipeline (all deterministic, no LLM):

**Stage 1: Regex Pattern Matching**
```python
DETERMINISTIC_PATTERNS = [
    (r"(?:list|show|what)\s+(?:functions?|methods?|classes?|symbols?)\s+(?:in|from)\s+", 0.9),
    (r"(?:find|show)\s+(?:usages?|references?|callers?)\s+(?:of|for|to)\s+", 0.85),
    (r"(?:what|show)\s+(?:type|signature)\s+(?:of|is|for)\s+", 0.8),
    (r"(?:list|show|get)\s+imports?\s+(?:in|from|for)\s+", 0.9),
    (r"(?:where|how)\s+is\s+\w+\s+(?:defined|declared)", 0.85),
    (r"(?:go to|jump to|find)\s+(?:definition|declaration)\s+(?:of)\s+", 0.9),
    (r"(?:get|show)\s+diagnostics?\s+(?:for|in)\s+", 0.8),
]

SEARCH_PATTERNS = [
    (r"(?:search|find|look)\s+(?:for|up)\s+", 0.6),
    (r"(?:how|what|why|explain|describe)\s+(?:does|is|are)\s+", 0.3),  # might be search or chat
]
```

**Stage 2: Feature Extraction**
- `has_file_reference`: check for file paths in query (`.py`, `/`, `src/`, etc.)
- `has_symbol_reference`: check for `CamelCase` or `snake_case` identifiers
- `is_structural_question`: words like "list", "show", "find", "where", "type"
- `is_explanation_question`: words like "how", "why", "explain", "describe"
- `word_count`: short queries (<8 words) more likely deterministic

**Stage 3: Weighted Scoring**
```python
score = pattern_score * 0.5 + feature_score * 0.3 + structural_bonus * 0.2

if score > 0.7:  → DETERMINISTIC_QUERY
elif score > 0.4: → SEMANTIC_SEARCH
else:              → COMPLEX_TASK or CHAT
```

Methods:
- `classify(query: str, file_context: str | None = None) -> Request`: classify and return Request
- `_extract_file_path(query: str) -> str | None`: extract file path from query
- `_extract_symbol_name(query: str) -> str | None`: extract symbol name from query

**`src/hybridcoder/layer1/queries.py`** — `DeterministicQueryHandler` class

Handles deterministic queries using Layer 1 tools:
- `handle(request: Request) -> Response | None`: dispatch to appropriate handler
- `_list_symbols(file_path: str, kind_filter: str | None = None) -> Response`
- `_find_references(symbol_name: str, directory: str = ".") -> Response`
- `_get_imports(file_path: str) -> Response`
- `_get_signature(symbol_name: str, file_path: str) -> Response`
- `_find_definition(symbol_name: str, file_path: str | None = None) -> Response`
- `_get_type_info(symbol_name: str, file_path: str) -> Response` (LSP if available, else type annotation from AST)

Dependencies: `SymbolExtractor`, `TreeSitterParser`, `LSPClient` (optional)

Return format: `Response(content=formatted_text, layer_used=1, tokens_used=0)`

#### Tests: `tests/unit/test_router.py` (~25 tests)

```
TestRequestRouter:
  # Stage 1: regex matching
  test_classify_list_functions
  test_classify_find_references
  test_classify_show_type
  test_classify_list_imports
  test_classify_find_definition
  test_classify_get_diagnostics

  # Stage 2: feature extraction
  test_extract_file_path_py
  test_extract_file_path_slash
  test_extract_symbol_camelcase
  test_extract_symbol_snake_case
  test_no_file_or_symbol

  # Stage 3: scoring
  test_score_deterministic_high
  test_score_search_medium
  test_score_chat_low
  test_score_complex_task
  test_explain_routes_to_l4
  test_short_structural_query_deterministic
  test_long_open_ended_query_chat

  # Edge cases
  test_empty_query
  test_slash_command_not_routed
  test_ambiguous_query_defaults_chat
  test_file_context_boosts_deterministic

TestDeterministicQueryHandler:
  test_list_symbols_returns_response
  test_find_references_grep_fallback
  test_get_imports
  test_response_has_layer_1
  test_response_has_zero_tokens
```

---

### Sprint 3C: LSP Client Integration (2-3 days)

**Goal:** Wrap multilspy for Jedi (Python's LSP backend in multilspy) with lazy start, caching, and graceful degradation.

#### New File

**`src/hybridcoder/layer1/lsp.py`** — `LSPClient` class
- `__init__(project_root: Path, language: str = "python")`: store config, don't start server yet
- `_ensure_server() -> bool`: lazy-start LSP server via multilspy; returns False if unavailable
- `shutdown()`: stop the LSP server
- `get_definition(file: str, line: int, col: int) -> list[Symbol] | None`
- `get_references(file: str, line: int, col: int) -> list[Symbol] | None`
- `get_hover(file: str, line: int, col: int) -> str | None`
- `get_document_symbols(file: str) -> list[Symbol] | None`
- `get_diagnostics(file: str) -> list[dict] | None`
- Cache: `TTLCache` with 30-second TTL (dictionary with timestamps)
- Graceful degradation: if multilspy import fails or server won't start, all methods return `None`
- Timeout: 5 seconds per LSP operation
- Error handling: catch all exceptions from multilspy, log warning, return `None`

Implementation notes:
```python
class LSPClient:
    def __init__(self, project_root: Path, language: str = "python"):
        self._project_root = project_root
        self._language = language
        self._server = None
        self._available: bool | None = None  # None = untested
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 30.0

    def _ensure_server(self) -> bool:
        if self._available is False:
            return False
        if self._server is not None:
            return True
        try:
            from multilspy import SyncLanguageServer
            from multilspy.multilspy_config import MultilspyConfig
            config = MultilspyConfig(code_language=self._language)
            self._server = SyncLanguageServer.create(config, str(self._project_root))
            self._server.start_server()
            self._available = True
            return True
        except Exception:
            self._available = False
            return False
```

#### Tests: `tests/unit/test_lsp.py` (~12 mocked tests)

```
TestLSPClient:
  test_construction_does_not_start_server
  test_ensure_server_success (mock multilspy)
  test_ensure_server_failure_graceful
  test_get_definition_with_cache
  test_get_references_returns_symbols
  test_get_hover_returns_string
  test_get_document_symbols
  test_get_diagnostics
  test_cache_ttl_expires
  test_unavailable_returns_none
  test_timeout_returns_none
  test_shutdown_stops_server
```

#### Integration Tests: `tests/integration/test_lsp_integration.py` (~6 tests, require multilspy + Jedi)
```
@pytest.mark.integration
TestLSPIntegration:
  test_jedi_lsp_starts
  test_definition_in_project
  test_references_in_project
  test_hover_info
  test_document_symbols
  test_diagnostics
```

---

### Sprint 3D: AST-Aware Chunker + Embedding Engine (2-3 days)

**Goal:** Split code files into semantic chunks at function/class boundaries and embed them.

#### New Files

**`src/hybridcoder/layer2/__init__.py`**
```
Empty package marker.
```

**`src/hybridcoder/layer2/chunker.py`** — `ASTChunker` class
- `__init__(parser: TreeSitterParser, extractor: SymbolExtractor)`: takes L1 dependencies
- `chunk_file(path: Path) -> list[CodeChunk]`: split a file into chunks
- `chunk_source(source: str, file_path: str = "", language: str = "python") -> list[CodeChunk]`: split source string
- `_split_at_boundaries(tree: Tree, source: str) -> list[tuple[int, int, str, list[str]]]`: identify split points

Chunking strategy:
1. Parse with tree-sitter to get AST
2. Identify top-level nodes: function_definition, class_definition, import blocks
3. For classes: each method becomes a separate chunk, with class docstring as preamble
4. For large functions (>100 lines): split at logical boundaries (if/for/while blocks)
5. Module-level code between definitions → "module" chunk
6. Each chunk includes:
   - `content`: the actual code text
   - `file_path`, `language`, `start_line`, `end_line`
   - `chunk_type`: function, class, method, module, block
   - `scope_chain`: e.g., `["MyClass", "my_method"]`
   - `imports`: imports visible to this chunk (module-level imports)
7. Target chunk size: 500-1500 tokens (roughly 150-450 lines)
8. Minimum chunk size: 3 lines (skip trivial chunks like `pass` functions)

**`src/hybridcoder/layer2/embeddings.py`** — `EmbeddingEngine` class
- `__init__(model_name: str = "jinaai/jina-embeddings-v2-base-code")`: store config, don't load yet
- `_ensure_model() -> bool`: lazy-load model on first use, CPU-only
- `embed(texts: list[str]) -> list[list[float]] | None`: batch embed texts
- `embed_single(text: str) -> list[float] | None`: embed a single text
- `available` property: whether model is loaded
- `dimension` property: embedding dimension (768 for jina-v2)

Implementation notes:
- Uses `sentence-transformers` library
- Forces CPU device: `model = SentenceTransformer(name, device="cpu")`
- Batch size: 32 (balance memory vs throughput)
- Graceful degradation: if model fails to load, `embed()` returns `None`
- First-load latency: ~2-5 seconds (download ~300MB on first run, then cached)
- Inference latency: ~20ms per chunk on CPU

#### Tests: `tests/unit/test_chunker.py` (~18 tests)

```
TestASTChunker:
  test_chunk_single_function
  test_chunk_single_class
  test_chunk_class_methods_separate
  test_chunk_module_level_code
  test_chunk_imports_block
  test_chunk_preserves_scope_chain
  test_chunk_includes_imports
  test_chunk_type_correct
  test_chunk_lines_correct
  test_large_function_split
  test_small_function_not_split
  test_empty_file
  test_syntax_error_fallback (whole file as one chunk)
  test_multiple_classes
  test_nested_functions
  test_decorators_included
  test_chunk_from_file
  test_minimum_chunk_size
```

#### Tests: `tests/unit/test_embeddings.py` (~8 mocked tests)

```
TestEmbeddingEngine:
  test_construction_does_not_load
  test_ensure_model_lazy_load (mock SentenceTransformer)
  test_embed_batch_returns_vectors
  test_embed_single_returns_vector
  test_dimension_is_768
  test_unavailable_returns_none
  test_cpu_only_device
  test_empty_text_handled
```

---

### Sprint 3E: LanceDB Index + Hybrid Search (2-3 days)

**Goal:** Build and query a code index with hybrid BM25 + vector search.

#### New Files

**`src/hybridcoder/layer2/index.py`** — `CodeIndex` class
- `__init__(db_path: Path, chunker: ASTChunker, embeddings: EmbeddingEngine)`: connect to LanceDB
- `build(project_root: Path, force: bool = False)`: full index build
- `update(changed_files: list[Path])`: incremental update for changed files
- `_discover_files(root: Path) -> list[Path]`: gitignore-aware file discovery
- `_compute_file_hash(path: Path) -> str`: SHA256 of file content
- `is_stale(path: Path) -> bool`: check if file has changed since last index
- `stats() -> dict`: index statistics (total chunks, files, etc.)

LanceDB schema (Pydantic `LanceModel` — replaces PyArrow schema):
```python
from lancedb.pydantic import LanceModel, Vector

class CodeChunkRecord(LanceModel):
    id: str                    # chunk unique ID
    content: str               # code text (FTS-indexed)
    file_path: str             # relative file path
    language: str              # "python"
    start_line: int            # first line
    end_line: int              # last line
    chunk_type: str            # function/class/method/module
    scope_chain: str           # JSON-encoded list
    imports: str               # JSON-encoded list
    file_hash: str             # for invalidation
    vector: Vector(768)        # jina-v2-base-code embedding
```

File discovery:
- Walk project root recursively
- Respect `.gitignore` patterns (use `pathspec` library or simple pattern matching)
- Skip common dirs: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.tox`
- File extensions: `.py` (Python-first MVP)
- Max files: 50,000 (cap for large monorepos)
- File size limit: 1MB per file (skip larger files)

Indexing flow:
1. Discover files (gitignore-aware)
2. For each file: check hash vs stored hash → skip if unchanged
3. For changed files: re-chunk → re-embed → upsert into LanceDB
4. Remove chunks for deleted files
5. Create Tantivy FTS index: `table.create_fts_index("content", use_tantivy=True)` for BM25

**`src/hybridcoder/layer2/search.py`** — `HybridSearch` class
- `__init__(index: CodeIndex)`: takes index reference
- `search(query: str, top_k: int = 10, file_filter: str | None = None) -> list[SearchResult]`

Uses LanceDB built-in hybrid search + RRF (replaces manual BM25/vector/fusion):
```python
from lancedb.rerankers import RRFReranker

results = (
    table
    .search(query, query_type="hybrid")
    .rerank(reranker=RRFReranker())
    .limit(top_k)
    .to_pandas()
)
```

LanceDB handles BM25 (Tantivy FTS), vector search, and Reciprocal Rank Fusion internally. No manual RRF formula needed.

Search behavior:
- If embeddings unavailable: `query_type="fts"` for BM25-only mode
- If index empty: return empty results
- Relevance threshold: 0.3 (filter out low-quality results)
- File filter: optional, restrict to files matching a glob via `.where()` clause
- Symbol affinity boost: if query mentions a symbol, boost chunks containing that symbol

#### Tests: `tests/unit/test_index.py` (~12 tests)

```
TestCodeIndex:
  test_build_creates_table
  test_build_indexes_python_files
  test_incremental_update
  test_file_hash_invalidation
  test_skip_unchanged_files
  test_gitignore_respected
  test_skip_large_files
  test_max_file_cap
  test_stats_returns_counts
  test_discover_files_skips_hidden
  test_remove_deleted_files
  test_empty_project
```

#### Tests: `tests/unit/test_search.py` (~12 tests)

```
TestHybridSearch:
  test_bm25_search_finds_keyword
  test_vector_search_finds_semantic
  test_hybrid_fuses_results
  test_rrf_scoring
  test_relevance_threshold_filters
  test_file_filter
  test_empty_index_returns_empty
  test_bm25_only_when_no_embeddings
  test_top_k_limits_results
  test_symbol_affinity_boost
  test_dedup_results
  test_search_returns_search_result_type
```

#### Integration Tests: `tests/integration/test_lancedb.py` (~8 tests, require LanceDB)
```
@pytest.mark.integration
TestLanceDBIntegration:
  test_create_table
  test_insert_and_query
  test_fts_index
  test_vector_search
  test_hybrid_search
  test_incremental_update
  test_delete_by_file
  test_large_batch_insert
```

---

### Sprint 3F: Repository Map + Context Assembler (2 days)

**Goal:** Build ranked symbol summaries and assemble optimal LLM context within token budget.

#### New Files

**`src/hybridcoder/layer2/repomap.py`** — `RepoMapGenerator` class
- `__init__(extractor: SymbolExtractor)`: takes L1 dependency
- `generate(project_root: Path, query: str | None = None, budget: int = 800) -> str`: generate repo map
- `_rank_symbols(symbols: list[Symbol], query: str | None) -> list[Symbol]`: rank by relevance
- `_format_map(symbols: list[Symbol], budget: int) -> str`: format as compact text

Repo map format (inspired by Aider):
```
src/hybridcoder/agent/loop.py:
  class AgentLoop
    def run(user_message, ...)
    def cancel()

src/hybridcoder/agent/tools.py:
  class ToolRegistry
    def register(tool)
    def get(name)
    def get_all()
  def create_default_registry()

src/hybridcoder/core/types.py:
  class RequestType(Enum)
  class Response
  class Symbol
```

Ranking heuristics:
- Query-aware boosting: if query mentions "agent", boost agent/ symbols
- Recency: recently modified files rank higher (mtime)
- Centrality: files imported by many others rank higher
- Symbol type: classes > functions > variables
- Scope: public symbols (no underscore prefix) rank higher

Token counting: approximate at 4 chars/token. Truncate map to fit budget.

**`src/hybridcoder/layer2/rules.py`** — `RulesLoader` class
- `__init__(project_root: Path)`: store root
- `load() -> str`: concatenate all rules files
- `_find_rules_files() -> list[Path]`: discover rules files

Rules file search order:
1. `CLAUDE.md` (project root)
2. `AGENTS.md` (project root)
3. `.rules/*.md` (all .md files in .rules directory)
4. `.cursorrules` (project root, for compatibility)
5. `.hybridcoder/memory.md` (project memory)

Max rules budget: 500 tokens. Truncate if needed, prioritizing CLAUDE.md.

**`src/hybridcoder/core/context.py`** — `ContextAssembler` class
- `__init__(search: HybridSearch, repomap: RepoMapGenerator, rules: RulesLoader)`: dependencies
- `assemble(query: str, conversation_history: list[dict], file_context: str | None = None) -> str`: build context
- `_allocate_budget(total: int = 6000) -> dict[str, int]`: priority-based allocation

Budget allocation (6000 tokens total):
```
┌──────────────────────────┬────────┬──────────────┐
│ Section                  │ Budget │ Priority     │
├──────────────────────────┼────────┼──────────────┤
│ Project rules            │  ~500  │ 1 (highest)  │
│ Repo map                 │  ~800  │ 2            │
│ Retrieved chunks         │ ~2500  │ 3            │
│ File context (@file)     │  ~900  │ 4            │
│ Conversation history     │ ~1000  │ 5 (lowest)   │
│ Buffer (for system msg)  │  ~300  │ —            │
└──────────────────────────┴────────┴──────────────┘
```

Context format:
```
## Project Context

### Rules
{rules_content}

### Repository Map
{repo_map}

### Relevant Code
{retrieved_chunks with file:line headers}

### Current File
{file_context if provided}

### Conversation
{recent messages}
```

Relevance thresholding:
- Only include chunks with search score > 0.3
- Symbol affinity: boost chunks that contain symbols mentioned in the query
- File affinity: boost chunks from files referenced with @file

#### Tests: `tests/unit/test_repomap.py` (~8 tests)

```
TestRepoMapGenerator:
  test_generate_basic_map
  test_map_fits_budget
  test_query_aware_ranking
  test_empty_project
  test_format_compact
  test_public_symbols_ranked_higher
  test_classes_before_functions
  test_truncation_at_budget
```

#### Tests: `tests/unit/test_context.py` (~8 tests)

```
TestContextAssembler:
  test_assemble_includes_all_sections
  test_budget_allocation
  test_rules_section_present
  test_repo_map_section_present
  test_search_results_section
  test_file_context_included
  test_history_included
  test_total_under_budget
```

---

### Sprint 3G: TUI Integration + New Tools + Verification (3 days)

**Goal:** Wire everything together, add new tools, update TUI, run full verification.

#### Modified Files

**`src/hybridcoder/agent/tools.py`** — add 6 new tools

New tools (all `requires_approval=False`):

| Tool | Description | Parameters | Handler |
|------|-------------|-----------|---------|
| `find_references` | Find all usages of a symbol | symbol: str, directory?: str | grep + LSP fallback |
| `find_definition` | Find where a symbol is defined | symbol: str, file?: str | LSP + tree-sitter fallback |
| `get_type_info` | Get type information for a symbol | symbol: str, file: str | LSP hover + AST annotation |
| `list_symbols` | List all symbols in a file | file: str, kind?: str | tree-sitter extraction |
| `search_code` | Semantic code search | query: str, top_k?: int | hybrid search (L2) |
| `get_diagnostics` | Get errors/warnings for a file | file: str | LSP diagnostics |

Total tools after Phase 3: **12** (6 original + 6 new)

**`src/hybridcoder/backend/server.py`** — router integration in `handle_chat()` (line 329-368)

Add L1 bypass **before** the agent loop in `handle_chat()`:
```python
async def handle_chat(self, message: str, session_id: str | None, request_id: int) -> None:
    # ... existing session/title logic ...

    # NEW: Request router — try L1 deterministic first
    if self.config.layer1.enabled:
        router = self._ensure_request_router()
        request = router.classify(message)
        if request.request_type == RequestType.DETERMINISTIC_QUERY:
            response = self._handle_deterministic(request)
            if response is not None:
                # Emit result directly — bypasses agent loop entirely
                self.emit_notification("on_token", {"text": response.content})
                self.emit_notification("on_done", {
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "layer_used": 1,
                })
                return

    # Existing agent loop path (L4)
    try:
        agent_loop = self._ensure_agent_loop()
        # ... existing agent loop code ...

    self.emit_notification("on_done", {
        "tokens_in": 0,
        "tokens_out": 0,
        "layer_used": 4,
    })
```

New methods on `BackendServer`:
- `_ensure_request_router() -> RequestRouter`: lazy-init router
- `_handle_deterministic(request: Request) -> Response | None`: run L1 handler

**`src/hybridcoder/tui/commands.py`** — add `/index` command

```python
async def _handle_index(app: AppContext, args: str) -> None:
    app.add_system_message("Building code index...")
    try:
        index = _ensure_code_index(app)
        await asyncio.to_thread(index.build, app.project_root, force="--force" in args)
        stats = index.stats()
        app.add_system_message(
            f"Index built: {stats['files']} files, {stats['chunks']} chunks"
        )
    except Exception as e:
        app.add_system_message(f"Index build failed: {e}")
```

**Go TUI changes (~20 lines total across 5 files):**

**`cmd/hybridcoder-tui/protocol.go`** — Add `LayerUsed` to `DoneParams`:
```go
type DoneParams struct {
	TokensIn  int  `json:"tokens_in"`
	TokensOut int  `json:"tokens_out"`
	Cancelled bool `json:"cancelled,omitempty"`
	LayerUsed int  `json:"layer_used,omitempty"` // 1=L1 deterministic, 4=L4 LLM
}
```

**`cmd/hybridcoder-tui/messages.go`** — Add `LayerUsed` to `backendDoneMsg`:
```go
type backendDoneMsg struct {
	TokensIn  int
	TokensOut int
	Cancelled bool
	LayerUsed int
}
```

**`cmd/hybridcoder-tui/backend.go`** — Pass `LayerUsed` in `on_done` dispatch:
```go
case "on_done":
	var params DoneParams
	// ... unmarshal ...
	b.program.Send(backendDoneMsg{
		TokensIn:  params.TokensIn,
		TokensOut: params.TokensOut,
		Cancelled: params.Cancelled,
		LayerUsed: params.LayerUsed,
	})
```

**`cmd/hybridcoder-tui/statusbar.go`** — Add `Layer` field, render `[L1]`/`[L4]`:
```go
type statusBarModel struct {
	// ... existing fields ...
	Layer string // "L1", "L4", or ""
}

func (s statusBarModel) View() string {
	parts := []string{}
	if s.Layer != "" {
		parts = append(parts, fmt.Sprintf("[%s]", s.Layer))
	}
	// ... existing parts ...
}
```

**`cmd/hybridcoder-tui/update.go`** — Set `m.statusBar.Layer` in `handleDone()`:
```go
func (m model) handleDone(msg backendDoneMsg) (tea.Model, tea.Cmd) {
	// ... existing flush logic ...
	switch msg.LayerUsed {
	case 1:
		m.statusBar.Layer = "L1"
	case 4:
		m.statusBar.Layer = "L4"
	default:
		m.statusBar.Layer = ""
	}
	// ... rest of existing handleDone ...
}
```

**`cmd/hybridcoder-tui/commands.go`** — Add `"/index"` to `knownCommands`:
```go
var knownCommands = []string{
	// ... existing commands ...
	"/index",
}
```

**`src/hybridcoder/agent/prompts.py`** — context injection

Update `build_system_prompt()` to accept and inject:
- Repository map
- Project rules
- Citation grounding instruction

```python
def build_system_prompt(
    memory_content: str | None = None,
    *,
    shell_enabled: bool = False,
    approval_mode: str = "suggest",
    repo_map: str | None = None,
    project_rules: str | None = None,
) -> str:
    prompt = SYSTEM_PROMPT

    # ... existing env section ...

    if project_rules:
        prompt += f"\n## Project Rules\n{project_rules}\n"

    if repo_map:
        prompt += f"\n## Repository Map\n{repo_map}\n"

    # Citation grounding instruction
    prompt += (
        "\n## Code References\n"
        "When referring to code, cite the file path and line number "
        "(e.g., `src/foo.py:42`). Use the repository map and search "
        "results to ground your answers in actual code.\n"
    )

    if memory_content:
        prompt += f"\n## Project Memory\n{memory_content}\n"

    return prompt
```

**`src/hybridcoder/core/types.py`** — add `ParseResult` (from Sprint 3A)

**`src/hybridcoder/config.py`** — extend Layer1Config and Layer2Config

```python
class Layer1Config(BaseModel):
    enabled: bool = True
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
    cache_max_entries: int = Field(default=500, description="Max cached parse trees")
    lsp_timeout: float = Field(default=5.0, description="LSP operation timeout in seconds")
    lsp_cache_ttl: float = Field(default=30.0, description="LSP result cache TTL in seconds")

class Layer2Config(BaseModel):
    enabled: bool = True
    embedding_model: str = Field(default="jinaai/jina-embeddings-v2-base-code")
    search_top_k: int = Field(default=10, ge=1)
    chunk_size: int = Field(default=1000, gt=0)
    hybrid_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    db_path: str = Field(default="~/.hybridcoder/index.lancedb", description="LanceDB path")
    relevance_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    max_files: int = Field(default=50000, description="Max files to index")
    repomap_budget: int = Field(default=800, description="Repo map token budget")
    context_budget: int = Field(default=6000, description="Total context token budget")
```

#### New File

**`src/hybridcoder/layer1/validators.py`** — Validation helpers

- `validate_syntax(source: str, language: str = "python") -> tuple[bool, list[str]]`: parse with tree-sitter, return (valid, errors)
- `validate_imports(source: str, project_root: Path) -> list[str]`: check imports resolve to files/packages
- `has_syntax_errors(tree: Tree) -> bool`: check tree for ERROR nodes

#### Tests

**`tests/unit/test_new_tools.py`** (~12 tests)
```
TestNewTools:
  test_find_references_tool_registered
  test_find_definition_tool_registered
  test_get_type_info_tool_registered
  test_list_symbols_tool_registered
  test_search_code_tool_registered
  test_get_diagnostics_tool_registered
  test_total_tools_is_twelve
  test_new_tools_no_approval_required
  test_find_references_handler
  test_list_symbols_handler
  test_search_code_handler
  test_schemas_openai_format
```

**`tests/unit/test_integration_router_agent.py`** (~8 tests)
```
TestRouterBackendIntegration:
  test_handle_chat_deterministic_bypasses_agent_loop
  test_handle_chat_search_goes_to_agent_with_context
  test_handle_chat_chat_goes_to_agent
  test_on_done_includes_layer_used_1
  test_on_done_includes_layer_used_4
  test_l1_response_shows_zero_tokens
  test_l1_response_under_50ms
  test_fallback_to_l4_on_l1_failure
```

**Go tests (in `cmd/hybridcoder-tui/`):**

`protocol_test.go` — add:
```
TestDoneParamsLayerUsed:
  test_unmarshal_done_params_with_layer_used
  test_unmarshal_done_params_without_layer_used_defaults_zero
```

`statusbar_test.go` — add:
```
TestStatusBarLayerIndicator:
  test_view_renders_l1_indicator
  test_view_renders_l4_indicator
  test_view_renders_no_indicator_when_empty
```

**`tests/test_sprint_verify.py`** — add Sprint 3 verification tests

```python
# ============================================================
# Sprint 3: Phase 3 — Code Intelligence
# ============================================================

class TestSprint3Parser:
    """S3.1: Tree-sitter parser works."""

    def test_parser_imports(self) -> None:
        from hybridcoder.layer1.parser import TreeSitterParser
        assert TreeSitterParser is not None

    def test_parse_python_source(self) -> None:
        from hybridcoder.layer1.parser import TreeSitterParser
        parser = TreeSitterParser()
        tree = parser.parse("def foo(): pass")
        assert tree.root_node.type == "module"

class TestSprint3Symbols:
    """S3.2: Symbol extraction works."""

    def test_extract_function(self) -> None:
        from hybridcoder.layer1.parser import TreeSitterParser
        from hybridcoder.layer1.symbols import SymbolExtractor
        parser = TreeSitterParser()
        extractor = SymbolExtractor(parser)
        symbols = extractor.extract_symbols("def foo(): pass")
        assert any(s.name == "foo" and s.kind == "function" for s in symbols)

class TestSprint3Router:
    """S3.3: Request router classifies correctly."""

    def test_deterministic_classification(self) -> None:
        from hybridcoder.core.router import RequestRouter
        from hybridcoder.core.types import RequestType
        router = RequestRouter()
        req = router.classify("list functions in src/hybridcoder/agent/tools.py")
        assert req.request_type == RequestType.DETERMINISTIC_QUERY

class TestSprint3Tools:
    """S3.4: 12 tools registered."""

    def test_twelve_tools(self) -> None:
        from hybridcoder.agent.tools import create_default_registry
        registry = create_default_registry()
        assert len(registry.get_all()) == 12

class TestSprint3Index:
    """S3.5: Code index and search work."""

    def test_chunker_imports(self) -> None:
        from hybridcoder.layer2.chunker import ASTChunker
        assert ASTChunker is not None

    def test_search_imports(self) -> None:
        from hybridcoder.layer2.search import HybridSearch
        assert HybridSearch is not None

class TestSprint3Context:
    """S3.6: Context assembler works."""

    def test_context_imports(self) -> None:
        from hybridcoder.core.context import ContextAssembler
        assert ContextAssembler is not None

    def test_repomap_imports(self) -> None:
        from hybridcoder.layer2.repomap import RepoMapGenerator
        assert RepoMapGenerator is not None

    def test_rules_imports(self) -> None:
        from hybridcoder.layer2.rules import RulesLoader
        assert RulesLoader is not None

class TestSprint3Integration:
    """S3.7: Router integrated into backend server."""

    def test_backend_server_emits_layer_used(self) -> None:
        """BackendServer.handle_chat() emits layer_used in on_done."""
        from hybridcoder.backend.server import BackendServer
        assert hasattr(BackendServer, 'handle_chat')

    def test_index_command_registered(self) -> None:
        from hybridcoder.tui.commands import create_default_router
        router = create_default_router()
        commands = router.get_all()
        names = {c.name for c in commands}
        assert "index" in names
```

---

## 6. New Files Summary (15 create + 5 modify Python + 6 modify Go)

### Create

| File | Sprint | Purpose |
|------|--------|---------|
| `src/hybridcoder/layer1/__init__.py` | 3A | Package marker |
| `src/hybridcoder/layer1/parser.py` | 3A | Tree-sitter parser with mtime cache |
| `src/hybridcoder/layer1/symbols.py` | 3A | Symbol extraction via tree-sitter queries |
| `src/hybridcoder/layer1/queries.py` | 3B | Deterministic query handlers |
| `src/hybridcoder/layer1/lsp.py` | 3C | LSP client wrapper (multilspy) |
| `src/hybridcoder/layer1/validators.py` | 3G | Syntax + import validation |
| `src/hybridcoder/layer2/__init__.py` | 3D | Package marker |
| `src/hybridcoder/layer2/chunker.py` | 3D | AST-aware code chunker |
| `src/hybridcoder/layer2/embeddings.py` | 3D | Embedding engine (jina-v2, CPU) |
| `src/hybridcoder/layer2/index.py` | 3E | LanceDB code index |
| `src/hybridcoder/layer2/search.py` | 3E | Hybrid BM25 + vector search |
| `src/hybridcoder/layer2/repomap.py` | 3F | Repository map generator |
| `src/hybridcoder/layer2/rules.py` | 3F | Project rules loader |
| `src/hybridcoder/core/context.py` | 3F | Context assembler |
| `src/hybridcoder/core/router.py` | 3B | Request router |

### Modify (Python)

| File | Sprint | Changes |
|------|--------|---------|
| `src/hybridcoder/core/types.py` | 3A | Add `ParseResult` dataclass |
| `src/hybridcoder/config.py` | 3G | Extend `Layer1Config`, `Layer2Config` |
| `src/hybridcoder/agent/tools.py` | 3G | Add 6 new tools |
| `src/hybridcoder/agent/prompts.py` | 3G | Add repo map + rules + grounding |
| `src/hybridcoder/backend/server.py` | 3G | Router integration in `handle_chat()` — L1 bypass before agent loop, `layer_used` field in `on_done` |
| `src/hybridcoder/tui/commands.py` | 3G | Add `/index` command |

### Modify (Go TUI)

| File | Sprint | Changes |
|------|--------|---------|
| `cmd/hybridcoder-tui/protocol.go` | 3G | Add `LayerUsed int` to `DoneParams` struct |
| `cmd/hybridcoder-tui/messages.go` | 3G | Add `LayerUsed int` to `backendDoneMsg` |
| `cmd/hybridcoder-tui/backend.go` | 3G | Pass `LayerUsed` in `on_done` dispatch |
| `cmd/hybridcoder-tui/statusbar.go` | 3G | Add `Layer string` field, render `[L1]`/`[L4]` in `View()` |
| `cmd/hybridcoder-tui/update.go` | 3G | Set `m.statusBar.Layer` in `handleDone()` based on `msg.LayerUsed` |
| `cmd/hybridcoder-tui/commands.go` | 3G | Add `"/index"` to `knownCommands` for autocomplete |

### New Test Files

| File | Sprint | Test Count |
|------|--------|-----------|
| `tests/unit/test_parser.py` | 3A | ~20 |
| `tests/unit/test_router.py` | 3B | ~25 |
| `tests/unit/test_lsp.py` | 3C | ~12 |
| `tests/unit/test_chunker.py` | 3D | ~18 |
| `tests/unit/test_embeddings.py` | 3D | ~8 |
| `tests/unit/test_index.py` | 3E | ~12 |
| `tests/unit/test_search.py` | 3E | ~12 |
| `tests/unit/test_repomap.py` | 3F | ~8 |
| `tests/unit/test_context.py` | 3F | ~8 |
| `tests/unit/test_new_tools.py` | 3G | ~12 |
| `tests/unit/test_integration_router_agent.py` | 3G | ~8 |
| `tests/integration/test_lsp_integration.py` | 3C | ~6 |
| `tests/integration/test_lancedb.py` | 3E | ~8 |

Go test additions (in existing test files):

| File | Sprint | Test Count |
|------|--------|-----------|
| `cmd/hybridcoder-tui/protocol_test.go` | 3G | ~2 |
| `cmd/hybridcoder-tui/statusbar_test.go` (new) | 3G | ~3 |

**Total new Python tests: ~157**
**Total new Go tests: ~5**
**Expected total: 307 (existing Python) + 157 + 202 (existing Go) + 5 = ~671 tests**

---

## 7. Dependencies

### New Required Dependencies

```toml
# In pyproject.toml [project.optional-dependencies]
layer1 = [
    "tree-sitter>=0.25.2",        # QueryCursor API (breaking change from 0.25.0)
    "tree-sitter-python>=0.25.0", # Capsule-based Language() constructor
]
layer2 = [
    "lancedb>=0.29",              # Pydantic LanceModel, built-in RRF, Tantivy FTS
    "sentence-transformers>=5.0", # v5 backward-compatible, sparse encoder support
]
```

Note: `tree-sitter` and `tree-sitter-python` are already declared in pyproject.toml optional deps but need version bumps. `lancedb` and `sentence-transformers` are also already declared but need version bumps. `pyarrow` is no longer needed as a direct dependency — `LanceModel` (Pydantic) handles schema definition internally.

### Optional Dependencies

```toml
lsp = [
    "multilspy>=0.0.15",  # Microsoft's LSP client (now on PyPI)
]
```

Note: multilspy is now available on PyPI as of v0.0.15:
```
uv add multilspy>=0.0.15
```

---

## 8. Configuration Changes

### Layer1Config additions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cache_max_entries` | int | 500 | Max cached parse trees |
| `lsp_timeout` | float | 5.0 | LSP operation timeout (seconds) |
| `lsp_cache_ttl` | float | 30.0 | LSP result cache TTL (seconds) |

### Layer2Config additions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `db_path` | str | ~/.hybridcoder/index.lancedb | LanceDB storage path |
| `relevance_threshold` | float | 0.3 | Minimum search relevance score |
| `max_files` | int | 50000 | Max files to index |
| `repomap_budget` | int | 800 | Repo map token budget |
| `context_budget` | int | 6000 | Total context token budget |

---

## 9. Exit Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | 12 tools registered (6 original + 6 new) | `test_twelve_tools` in sprint verify |
| 2 | Router classifies 90%+ of test queries correctly | `test_router.py` — 25 test cases |
| 3 | Deterministic queries return in <50ms with 0 LLM tokens | `test_l1_response_under_50ms`, `test_l1_response_shows_zero_tokens` |
| 4 | Hybrid search returns relevant results (precision@3 >60%) | `test_search.py` with known-answer queries |
| 5 | Context assembler stays within 6000 token budget | `test_total_under_budget` |
| 6 | LSP degrades gracefully when unavailable | `test_unavailable_returns_none` |
| 7 | Embedding engine degrades to BM25-only when unavailable | `test_bm25_only_when_no_embeddings` |
| 8 | Go TUI status bar shows layer indicator for each response | `TestStatusBarLayerIndicator` (Go), `test_on_done_includes_layer_used_1` (Python) |
| 9 | All unit tests pass (target: 400+ total) | `uv run pytest tests/ -v` |
| 10 | Sprint verification tests pass | `uv run pytest tests/test_sprint_verify.py -v` |
| 11 | `/index` command works | `test_index_command_registered` |
| 12 | `make lint` passes | `uv run ruff check && uv run mypy` |

---

## 10. Timeline

| Sprint | Duration | Parallelizable With | Dependencies |
|--------|----------|-------------------|-------------|
| 3A: Parser + Symbols | 2-3 days | — | None |
| 3B: Router + Queries | 2-3 days | 3D | 3A (needs SymbolExtractor) |
| 3C: LSP Client | 2-3 days | 3D, 3E | 3A (needs Symbol type) |
| 3D: Chunker + Embeddings | 2-3 days | 3B, 3C | 3A (needs TreeSitterParser) |
| 3E: Index + Search | 2-3 days | 3C | 3D (needs ASTChunker, EmbeddingEngine) |
| 3F: Repo Map + Context | 2 days | — | 3A, 3E (needs SymbolExtractor, HybridSearch) |
| 3G: Integration + Verify | 3 days | — | All above |
| **Total** | **15-20 days** | | **10-14 days with parallelization** |

### Dependency Graph

```
3A ──┬──→ 3B ──┐
     ├──→ 3C ──┤
     └──→ 3D ──→ 3E ──→ 3F ──→ 3G
```

Sprint 3B, 3C, and 3D can run in parallel once 3A is complete.
Sprint 3E depends on 3D.
Sprint 3F depends on 3A and 3E.
Sprint 3G depends on all.

---

## 11. Verification Plan

### Automated

1. `uv run pytest tests/ -v --cov=src/hybridcoder` — all tests pass, coverage target >70%
2. `uv run pytest tests/test_sprint_verify.py -v` — sprint 3 criteria pass
3. `make lint` — ruff + mypy pass

### Manual

1. Ask "list functions in src/hybridcoder/agent/tools.py"
   - Expected: L1 result in <50ms, shows function names with line numbers, 0 tokens used
2. Ask "how does the agent loop work?"
   - Expected: L2 context assembled → L4 answers with citations to `agent/loop.py`
3. Ask "find usages of ToolRegistry"
   - Expected: L1 result showing all files/lines where ToolRegistry is referenced
4. Run `/index` command
   - Expected: Index built, shows file/chunk counts
5. Ask "search for approval handling code"
   - Expected: L2 hybrid search returns relevant chunks from approval.py, app.py

---

## 12. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| multilspy unstable on Windows | L1 LSP features unavailable | All LSP methods return None; tree-sitter fallback covers 80% |
| jina-v2-base-code large download (~300MB) | Slow first search | Lazy load; BM25-only fallback until downloaded |
| LanceDB version compatibility | Index build fails | Pin version; integration tests catch early |
| Tree-sitter QueryCursor API changes | Parser breaks | Pin tree-sitter>=0.25.2; use QueryCursor pattern; test queries in CI |
| Router misclassifies queries | Wrong layer handles request | Conservative thresholds (default to L4 on ambiguity) |
| Large monorepo performance | Index build too slow | 50K file cap; incremental updates; mtime-based skip |

---

## 13. Research Reference

See `docs/claude/04-code-intelligence-deep-research.md` for detailed research on:
- Tree-sitter parsing and query language
- LSP protocol capabilities
- Embedding model comparisons
- LanceDB hybrid search architecture
- Competitor approaches (Aider repo-map, Continue.dev, Cursor)
- Context engineering patterns

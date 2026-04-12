# Code Intelligence Deep Research

## Phase 3 Technical Reference for HybridCoder

**Document Version:** 1.0
**Date:** 2026-02-06
**Scope:** Layer 1 (Deterministic Analysis) + Layer 2 (Retrieval & Context)

This document provides deep technical research for implementing HybridCoder's code intelligence layers. Every section concludes with concrete implementation implications.

---

## Table of Contents

1. [IDE Intelligence Architecture](#1-ide-intelligence-architecture)
2. [Tree-sitter Deep Dive](#2-tree-sitter-deep-dive)
3. [LSP Protocol Capabilities (3.18)](#3-lsp-protocol-capabilities-318)
4. [How Competitors Do It](#4-how-competitors-do-it)
5. [Embedding Models for Code](#5-embedding-models-for-code)
6. [LanceDB Architecture](#6-lancedb-architecture)
7. [Hybrid Classical + LLM Approaches](#7-hybrid-classical--llm-approaches)
8. [AST-Aware Code Chunking](#8-ast-aware-code-chunking)

---

## 1. IDE Intelligence Architecture

Modern IDE intelligence is **primarily deterministic, not AI-driven**. Understanding how IntelliJ and VS Code achieve their intelligence informs HybridCoder's Layer 1 design.

### 1.1 IntelliJ PSI (Program Structure Interface)

IntelliJ's intelligence is built on a layered architecture centered around the PSI -- a read/write, language-aware syntax tree that backs nearly all IDE features.

**Three-Layer Parsing Model:**

```
+--------------------------------------------------+
|  Layer 3: PSI Elements (Semantic)                |
|  PsiClass, PsiMethod, PsiField, PsiVariable     |
|  Language-specific, carries semantic meaning      |
+--------------------------------------------------+
|  Layer 2: AST Nodes (Syntactic)                  |
|  ASTNode instances via PsiBuilderImpl            |
|  Language-neutral tree structure                  |
+--------------------------------------------------+
|  Layer 1: Lexer Tokens (Lexical)                 |
|  IElementType tokens from FlexLexer              |
|  Raw character stream tokenization               |
+--------------------------------------------------+
```

**Parsing is a two-step process:**
1. An Abstract Syntax Tree (AST) is built defining program structure, with nodes represented by `ASTNode` instances.
2. PSI elements are created on top of the AST, providing language-specific semantics. A `PsiFile` is the root of the hierarchy.

**Virtual File System (VFS):**
IntelliJ uses a VFS abstraction layer that decouples file access from the physical filesystem. The VFS provides snapshot-based file access, change notifications via `VirtualFileListener`, and content caching with lazy loading. This means the IDE never reads files directly -- it always goes through the VFS, which enables incremental processing.

**Index Infrastructure:**
IntelliJ uses two types of indexes to avoid full AST construction for common queries:

- **File-based indexes**: Map/Reduce architecture where each index has key-value pairs. The word index, for instance, maps words to bitmasks indicating occurrence context. Querying returns a *set of files* matching a condition.
- **Stub indexes**: Built over serialized *stub trees* -- compact binary representations of externally visible declarations (names, modifier flags, etc.). Querying returns *PSI elements* directly, without parsing the full file.

The stub tree is a critical optimization: it stores only the subset of PSI needed for navigation (class names, method signatures, field declarations) in a compact binary format. When navigation is needed, the stub is deserialized. When editing, the full AST is parsed. Switching between the two is transparent.

**Reference:** [PSI Documentation](https://plugins.jetbrains.com/docs/intellij/psi.html) | [Indexing and PSI Stubs](https://plugins.jetbrains.com/docs/intellij/indexing-and-psi-stubs.html)

### 1.2 VS Code Language Intelligence

VS Code uses a fundamentally different architecture -- a thin editor core with intelligence delegated to extensions via protocols.

**Three Intelligence Tiers:**

```
+--------------------------------------------------+
|  Tier 3: Language Server Protocol (LSP)          |
|  Separate process, full semantic analysis        |
|  Go-to-definition, references, diagnostics       |
|  Latency: 50ms-2s (server dependent)            |
+--------------------------------------------------+
|  Tier 2: Programmatic Language Features          |
|  In-process extension APIs                       |
|  CompletionItemProvider, HoverProvider            |
|  Latency: 10-100ms                              |
+--------------------------------------------------+
|  Tier 1: TextMate Grammars (Declarative)         |
|  Regex-based tokenization, .tmLanguage files     |
|  Syntax highlighting, bracket matching           |
|  Latency: <5ms (runs in renderer process)        |
+--------------------------------------------------+
```

**TextMate Grammars** provide syntax highlighting via regex-based tokenization. They run in the same process as the renderer and update tokens as the user types. While fast, they cannot provide semantic understanding -- they only see patterns in text.

**Semantic Token Highlighting** (added later) layers on top of TextMate, providing tokens enriched with type information from the language server. This appears with a short delay after TextMate highlighting.

**Language Server Protocol** separates the language intelligence into a standalone process that communicates via JSON-RPC. The server can be implemented in any language and provides features like completions, diagnostics, hover, go-to-definition, and references.

**Reference:** [VS Code Language Extensions](https://code.visualstudio.com/api/language-extensions/overview) | [Language Server Extension Guide](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide)

### 1.3 Key Insight: Intelligence is Deterministic

Both IDEs achieve their intelligence through **deterministic analysis**:

| Feature | Technique | LLM Needed? |
|---------|-----------|-------------|
| Syntax highlighting | Regex/grammar tokenization | No |
| Go-to-definition | Symbol table + index lookup | No |
| Find references | Reverse index scan | No |
| Type inference | Constraint solving (Hindley-Milner variants) | No |
| Rename refactoring | Symbol resolution + text replacement | No |
| Error diagnostics | Type checking + static analysis | No |
| Code completion (basic) | Scope analysis + type filtering | No |
| Code completion (AI) | Neural model prediction | Yes |

The *only* IDE feature that genuinely requires an LLM is AI-powered code completion (Copilot-style). Everything else is deterministic.

### HybridCoder Implications

- **Adopt the stub index pattern**: Build a lightweight index of externally visible declarations (function names, class names, signatures) that can be queried without full parsing. This is HybridCoder's equivalent of IntelliJ's stub tree.
- **Layer 1 should mirror VS Code's tiered approach**: fast syntactic analysis (tree-sitter) first, then LSP for semantic queries, then LLM only for generation.
- **VFS-like caching**: Cache parsed ASTs and invalidate on file change. Tree-sitter's incremental parsing makes this efficient.

---

## 2. Tree-sitter Deep Dive

Tree-sitter is the foundation of HybridCoder's Layer 1. It provides fast, incremental, error-tolerant parsing across languages.

### 2.1 Incremental Parsing Algorithm

Tree-sitter uses a **sentential-form incremental LR parsing algorithm**, based on the work of Tim Wagner and Susan Graham ("Efficient and Flexible Incremental Parsing" and "Incremental Analysis of Real Programming Languages").

**How Incremental Parsing Works:**

```
Original Parse:
  Source: "def foo():\n    return 1\n"
  Tree:   [module [function_def name:[identifier "foo"] body:[return [integer "1"]]]]

Edit: Change "1" to "42"
  tree.edit(start_byte=25, old_end_byte=26, new_end_byte=27, ...)

Incremental Reparse:
  - Parser receives old tree + edit description
  - Identifies which subtrees are invalidated by the edit
  - Reuses all unchanged subtrees (shared structure)
  - Only reparses the minimal affected region
  - New tree shares most nodes with old tree
```

**Key properties:**
1. **Structural sharing**: The new tree shares unmodified subtrees with the old tree. Memory consumption is proportional to the size of the change, not the file.
2. **Edit locality**: Only the subtrees affected by the edit are reparsed. For a typical single-character edit in a 10,000-line file, this means reparsing a handful of nodes rather than the entire file.
3. **GLR for ambiguity**: Tree-sitter handles ambiguous grammars using the Generalized LR algorithm at runtime, and precedence annotations to resolve conflicts at compile time.
4. **Error recovery**: The parser produces a valid tree even for syntactically incorrect input, inserting ERROR and MISSING nodes where needed. This is critical for real-time editing.

**Performance Characteristics:**

| File Size | Initial Parse | Incremental Reparse (single edit) |
|-----------|--------------|-----------------------------------|
| 100 lines | ~1ms | <0.1ms |
| 1,000 lines | ~5-10ms | <0.5ms |
| 6,000 lines | ~30-80ms | <1ms |
| 20,000 lines | ~100-150ms | <2ms |

These are approximate benchmarks observed across various grammar implementations. The actual numbers depend heavily on the grammar complexity -- Python grammars are generally fast, while Haskell and C++ grammars can be slower due to language complexity.

Tree-sitter also supports **asynchronous parsing** with configurable time budgets (e.g., 3ms increments) to prevent blocking the UI thread.

**Reference:** [Tree-sitter GitHub](https://github.com/tree-sitter/tree-sitter) | [Incremental Parsing Using Tree-sitter](https://tomassetti.me/incremental-parsing-using-tree-sitter/) | [Tree-sitter Architecture Analysis](https://mgx.dev/insights/tree-sitter-an-in-depth-analysis-of-its-architecture-applications-and-ecosystem/e60ae923e4424f87bb114373f2243fa7)

### 2.2 Query Language: S-Expression Patterns

Tree-sitter provides a powerful query language for pattern matching against syntax trees. Queries use S-expressions with captures and predicates.

**Basic Syntax:**

A query consists of one or more patterns. Each pattern is an S-expression matching nodes:

```scheme
; Match any function definition
(function_definition)

; Match function definition and capture the name
(function_definition
  name: (identifier) @function.name)

; Match class with its body
(class_definition
  name: (identifier) @class.name
  body: (block) @class.body)
```

**Captures** (prefixed with `@`) bind matched nodes to names for extraction:

```scheme
; Capture all import statements
(import_statement
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.from
  name: (dotted_name) @import.name)
```

**Predicates** (prefixed with `#`) filter matches:

```scheme
; Match functions named "test_*"
(function_definition
  name: (identifier) @test.name
  (#match? @test.name "^test_"))

; Match string literals containing "TODO"
(string) @todo.string
  (#match? @todo.string "TODO")

; Match identifiers that equal a specific name
(identifier) @name
  (#eq? @name "self")

; Negation
(identifier) @name
  (#not-eq? @name "__init__")
```

**Alternations and Wildcards:**

```scheme
; Match either function or method definition
[
  (function_definition name: (identifier) @def.name)
  (class_definition name: (identifier) @def.name)
]

; Match any node (wildcard)
(_) @any.node

; Anchored child (first child must match)
(block . (expression_statement) @first.stmt)
```

**Reference:** [Tree-sitter Query Syntax](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html) | [Predicates](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/3-predicates-and-directives.html)

### 2.3 Multi-Language Support

Tree-sitter grammars are defined in JavaScript DSL files (`grammar.js`) that compile to C parsers. Language bindings for Python are distributed as separate packages:

| Language | Package | Grammar Maturity |
|----------|---------|-----------------|
| Python | `tree-sitter-python` | Excellent |
| JavaScript | `tree-sitter-javascript` | Excellent |
| TypeScript | `tree-sitter-typescript` | Excellent |
| Java | `tree-sitter-java` | Good |
| Rust | `tree-sitter-rust` | Good |
| Go | `tree-sitter-go` | Good |
| C/C++ | `tree-sitter-c` / `tree-sitter-cpp` | Good |
| Ruby | `tree-sitter-ruby` | Good |

Each grammar package provides a compiled shared library and a `language()` function to load it. As of tree-sitter 0.25.x, grammars are installed as Python packages and loaded directly:

```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
```

### 2.4 Python Bindings (py-tree-sitter 0.25.x API)

The 0.25.x API is a significant improvement over earlier versions. Here are the core APIs:

**Parsing:**

```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# Create language and parser
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

# Parse source code (must be bytes)
source = b"""
def greet(name: str) -> str:
    return f"Hello, {name}!"

class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
"""
tree = parser.parse(source)
```

**Tree and Node Navigation:**

```python
root = tree.root_node

# Basic properties
print(root.type)           # "module"
print(root.start_point)    # (row, column) tuple
print(root.end_point)      # (row, column) tuple
print(root.start_byte)     # byte offset
print(root.end_byte)       # byte offset
print(root.child_count)    # number of children
print(root.text)           # source text as bytes

# Navigate children
for child in root.children:
    print(child.type)  # "function_definition", "class_definition", etc.

# Named children (skip anonymous nodes like punctuation)
for child in root.named_children:
    print(child.type)

# Field-based access
func_node = root.children[0]
name_node = func_node.child_by_field_name("name")
params_node = func_node.child_by_field_name("parameters")
body_node = func_node.child_by_field_name("body")
print(name_node.text)  # b"greet"
```

**TreeCursor for Efficient Traversal:**

```python
cursor = tree.walk()

def traverse(cursor, depth=0):
    print("  " * depth + cursor.node.type)
    if cursor.goto_first_child():
        traverse(cursor, depth + 1)
        while cursor.goto_next_sibling():
            traverse(cursor, depth + 1)
        cursor.goto_parent()

traverse(cursor)
```

**Query API:**

```python
# Define queries
query = PY_LANGUAGE.query("""
(function_definition
  name: (identifier) @function.name
  parameters: (parameters) @function.params
  return_type: (type) @function.return_type)

(class_definition
  name: (identifier) @class.name
  body: (block) @class.body)

(import_statement
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.module
  name: (dotted_name) @import.name)

(decorator
  (identifier) @decorator.name)
""")

# Execute query - captures returns dict[str, list[Node]]
captures = query.captures(root)
for name, nodes in captures.items():
    for node in nodes:
        print(f"  {name}: {node.text.decode()}")

# Matches returns list[tuple[pattern_index, dict[str, list[Node]]]]
matches = query.matches(root)
for pattern_idx, match_captures in matches:
    print(f"Pattern {pattern_idx}: {match_captures}")
```

**Incremental Parsing:**

```python
# Initial parse
tree = parser.parse(source)

# Simulate editing: change "greet" to "hello"
# old text at bytes 5..10 is "greet", new text is "hello"
tree.edit(
    start_byte=5,
    old_end_byte=10,
    new_end_byte=10,
    start_point=(1, 4),
    old_end_point=(1, 9),
    new_end_point=(1, 9),
)

# Re-parse with old tree -- only changed regions are reparsed
new_source = source.replace(b"greet", b"hello")
new_tree = parser.parse(new_source, tree)

# Find what changed
for range_ in tree.changed_ranges(new_tree):
    print(f"Changed: bytes {range_.start_byte}-{range_.end_byte}")
```

**Concrete Query Examples for Python:**

```python
# 1. All function/method definitions with full signatures
FUNCTION_QUERY = """
(function_definition
  name: (identifier) @name
  parameters: (parameters) @params
  return_type: (type)? @return_type
  body: (block) @body)
"""

# 2. All class definitions with bases
CLASS_QUERY = """
(class_definition
  name: (identifier) @name
  superclasses: (argument_list)? @bases
  body: (block) @body)
"""

# 3. All imports (both styles)
IMPORT_QUERY = """
[
  (import_statement name: (dotted_name) @module)
  (import_from_statement
    module_name: (dotted_name) @module
    name: [(dotted_name) (aliased_import name: (dotted_name))] @name)
]
"""

# 4. Decorated definitions
DECORATED_QUERY = """
(decorated_definition
  (decorator (identifier) @decorator.name)
  definition: [
    (function_definition name: (identifier) @def.name)
    (class_definition name: (identifier) @def.name)
  ])
"""

# 5. All assignments at module level (global variables)
GLOBAL_ASSIGNMENT_QUERY = """
(module
  (expression_statement
    (assignment
      left: (identifier) @var.name
      right: (_) @var.value)))
"""

# 6. All string literals (for docstring extraction)
DOCSTRING_QUERY = """
(function_definition
  body: (block
    . (expression_statement (string) @docstring)))
(class_definition
  body: (block
    . (expression_statement (string) @docstring)))
"""
```

**Reference:** [py-tree-sitter 0.25.2 Documentation](https://tree-sitter.github.io/py-tree-sitter/) | [py-tree-sitter GitHub](https://github.com/tree-sitter/py-tree-sitter)

### HybridCoder Implications

- **Use tree-sitter as the primary Layer 1 engine**. It provides sub-millisecond incremental parsing, error tolerance, and multi-language support.
- **Build a query library**: Pre-define queries for each supported language (functions, classes, imports, decorators, type annotations). Store these as `.scm` files or Python constants.
- **Cache parse trees**: Store `Tree` objects in memory keyed by file path. On file change, use `tree.edit()` + incremental reparse. This gives effectively free re-parsing for editor integrations.
- **Start with Python support** via `tree-sitter-python`, then add JavaScript/TypeScript and Java.
- **Extract "tags"** (definition + reference pairs) for the repository map, following Aider's pattern (see Section 4.1).

---

## 3. LSP Protocol Capabilities (3.18)

The Language Server Protocol provides semantic analysis capabilities that complement tree-sitter's syntactic analysis. LSP 3.18 is the latest specification.

### 3.1 Full Operation Catalog with Latency Profiles

**Document Operations:**

| Operation | Method | Returns | Typical Latency |
|-----------|--------|---------|-----------------|
| Go to Definition | `textDocument/definition` | Location(s) | 10-100ms |
| Find References | `textDocument/references` | Location[] | 50-500ms |
| Hover Information | `textDocument/hover` | Markup content | 10-50ms |
| Document Symbols | `textDocument/documentSymbol` | SymbolInformation[] | 20-100ms |
| Diagnostics | `textDocument/publishDiagnostics` | Diagnostic[] | 100ms-5s |
| Completion | `textDocument/completion` | CompletionItem[] | 50-300ms |
| Signature Help | `textDocument/signatureHelp` | SignatureInformation | 10-50ms |
| Code Actions | `textDocument/codeAction` | CodeAction[] | 50-200ms |
| Rename | `textDocument/rename` | WorkspaceEdit | 100-500ms |
| Formatting | `textDocument/formatting` | TextEdit[] | 50-200ms |
| Folding Range | `textDocument/foldingRange` | FoldingRange[] | 20-50ms |
| Selection Range | `textDocument/selectionRange` | SelectionRange | 10-30ms |
| Semantic Tokens | `textDocument/semanticTokens` | SemanticTokens | 50-200ms |
| Inline Completion | `textDocument/inlineCompletion` | InlineCompletionItem[] | 50-200ms (new in 3.18) |
| Call Hierarchy | `textDocument/prepareCallHierarchy` | CallHierarchyItem[] | 50-300ms |
| Type Hierarchy | `textDocument/prepareTypeHierarchy` | TypeHierarchyItem[] | 50-200ms |

**Workspace Operations:**

| Operation | Method | Returns | Typical Latency |
|-----------|--------|---------|-----------------|
| Workspace Symbols | `workspace/symbol` | SymbolInformation[] | 100ms-2s |
| File Watching | `workspace/didChangeWatchedFiles` | (notification) | N/A |
| Configuration | `workspace/configuration` | any[] | <10ms |
| Execute Command | `workspace/executeCommand` | any | varies |
| Workspace Edit | `workspace/applyEdit` | ApplyWorkspaceEditResponse | 50-200ms |

**New in LSP 3.18:**
- Inline completions support
- Dynamic text document content support
- Refresh support for folding ranges
- Multi-range formatting
- Snippet support in workspace edits
- Code action kind documentation
- Command tooltips

**Reference:** [LSP 3.18 Specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/)

### 3.2 Pyright Capabilities

Pyright is the recommended Python LSP server for HybridCoder. Written in TypeScript/Node.js, it provides:

**Type Inference Engine:**
- **Bidirectional type inference**: If the left-hand side of an assignment has a declared type, it influences the inferred type of the right-hand side.
- **Flow-sensitive type narrowing**: Tracks variable types through `if`, `isinstance`, `assert`, and pattern matching branches.
- **Generic type resolution**: Full support for `TypeVar`, `ParamSpec`, `TypeVarTuple`, and generic protocols.
- **Overload resolution**: Handles `@overload` decorated functions with multiple signatures.
- **Stub file support**: Reads `.pyi` stub files for type information on untyped libraries.

**Workspace Analysis:**
- **Incremental analysis**: Only rechecks modified files and their transitive dependents, not the entire workspace.
- **Multi-root workspace support**: Each root can have its own `pyrightconfig.json`.
- **Watch mode**: Real-time type checking as files change.
- **Parallel processing**: Uses multiple CPU cores for analysis.

**Performance:**
- Initial workspace analysis: 2-10s for medium projects (1000 files)
- Incremental updates: 100-500ms after file changes
- Memory: 200-800MB depending on project size

**Configuration Modes:**
- `basic`: Default, catches common errors
- `standard`: Stricter, catches more potential issues
- `strict`: All type-checking rules enabled; requires complete type annotations

**Reference:** [Pyright GitHub](https://github.com/microsoft/pyright) | [Pyright Type Inference Docs](https://github.com/microsoft/pyright/blob/main/docs/type-inference.md)

### 3.3 JDT-LS for Java (Deferred)

Eclipse JDT Language Server provides comprehensive Java support:
- Full Java 21+ syntax support
- Project model (Maven/Gradle) integration
- Refactoring support (extract method, rename, move)
- Code generation (constructors, getters/setters, equals/hashCode)
- Debug adapter protocol integration

JDT-LS is heavier than Pyright (~500MB-1GB memory) but provides the most complete Java analysis available. HybridCoder will defer Java support to a later phase but the architecture should accommodate it.

### 3.4 multilspy (Microsoft)

multilspy is HybridCoder's LSP client library. It wraps multiple language servers behind a unified Python API.

**Supported Languages:** Python (Pyright), Rust (rust-analyzer), Java (JDT-LS), Go (gopls), JavaScript/TypeScript (tsserver), Ruby, C# (OmniSharp), Dart

**Lifecycle Management:**
multilspy handles the complete language server lifecycle:
1. **Download**: Automatically downloads platform-specific server binaries
2. **Startup**: Launches the server process with correct arguments
3. **Initialization**: Sends `initialize` request with capabilities
4. **Communication**: Handles JSON-RPC message passing
5. **Teardown**: Graceful shutdown on context exit

**API Usage:**

```python
from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger

# Configuration
config = MultilspyConfig.from_dict({"code_language": "python"})
logger = MultilspyLogger()

# Create server and use within context manager
lsp = SyncLanguageServer.create(config, logger, project_root="/path/to/project")

with lsp.start_server():
    # Go to definition
    result = lsp.request_definition(
        file_path="src/main.py",
        line=10,
        column=15
    )
    # result: [{"uri": "file:///path/to/module.py", "range": {...}}]

    # Find references
    refs = lsp.request_references(
        file_path="src/main.py",
        line=10,
        column=15
    )
    # refs: [{"uri": "...", "range": {...}}, ...]

    # Get hover information (type info, docstrings)
    hover = lsp.request_hover(
        file_path="src/main.py",
        line=10,
        column=15
    )

    # Get document symbols (outline)
    symbols = lsp.request_document_symbols(
        file_path="src/main.py"
    )

    # Get completions
    completions = lsp.request_completions(
        file_path="src/main.py",
        line=10,
        column=15
    )
```

**Origin:** multilspy was created for the NeurIPS 2023 paper "Monitor-Guided Decoding of Code LMs with Static Analysis of Repository Context" (originally part of `monitors4codegen`). It was later extracted into a standalone library by Microsoft.

**Reference:** [multilspy GitHub](https://github.com/microsoft/multilspy) | [multilspy PyPI](https://pypi.org/project/multilspy/)

### HybridCoder Implications

- **Use multilspy as the unified LSP client**. It handles server lifecycle, binary downloads, and provides a clean Python API.
- **Layer 1 decision tree**: tree-sitter for syntax queries (<50ms), LSP for semantic queries (50-500ms), LLM for generation (5-30s).
- **Start with Pyright** for Python. Its incremental analysis and type inference are excellent for HybridCoder's use cases.
- **Pre-warm the LSP server** at project open. Initial analysis takes 2-10s, but subsequent queries are fast.
- **Key LSP operations for HybridCoder**:
  - `textDocument/definition` -- resolving imports, understanding call chains
  - `textDocument/references` -- impact analysis for edits
  - `textDocument/documentSymbol` -- building file outlines for context
  - `textDocument/hover` -- extracting type information for context
  - `textDocument/publishDiagnostics` -- error checking after edits (LLMLOOP pattern)

---

## 4. How Competitors Do It

### 4.1 Aider: Repository Map

Aider's repository map is the most well-documented and effective approach to giving LLMs codebase awareness. It achieves **4.3-6.5% context window utilization** versus 54-70% for agents using iterative search.

**Architecture:**

```
+-------------------+     +------------------+     +------------------+
| Source Files      | --> | Tree-sitter      | --> | Tag Extraction   |
| (all repo files)  |     | Parsing          |     | (defs + refs)    |
+-------------------+     +------------------+     +------------------+
                                                          |
                                                          v
+-------------------+     +------------------+     +------------------+
| Ranked Map        | <-- | PageRank         | <-- | File Graph       |
| (token-budgeted)  |     | Algorithm        |     | Construction     |
+-------------------+     +------------------+     +------------------+
```

**Step 1: Tag Extraction**

Aider uses tree-sitter to parse every file in the repository and extract "tags" -- pairs of (definition, reference). A tag is either:
- A **definition**: where a symbol (function, class, variable) is declared
- A **reference**: where a symbol is used

For each file, tree-sitter queries extract:
- Function/method names and their locations
- Class names
- Variable assignments at module level
- Import statements

**Step 2: Graph Construction**

Files become nodes in a directed graph. Edges connect files based on cross-file references: if file A references a symbol defined in file B, there is an edge from A to B. The weight of the edge corresponds to the number of cross-references.

**Step 3: PageRank Ranking**

Aider runs a **Personalized PageRank** algorithm on this graph:
- Files currently being edited (`chat_fnames`) receive a higher initial rank (personalization vector)
- The PageRank computation propagates importance from these "active" files through the dependency graph
- Files with many incoming references from active files rank higher
- The algorithm uses scipy's sparse matrix operations for efficiency

**Step 4: Token-Budgeted Output**

The `get_ranked_tags_map` function uses **binary search** to find the maximum number of tags that fit within the token budget (default: 1024 tokens, configurable via `--map-tokens`). The map dynamically expands when no files are in the chat.

**Output Format:**

```
src/main.py:
  class Application
    def __init__(self, config)
    def run(self)
    def shutdown(self)

src/config.py:
  class Config
    def load(cls, path)
    def validate(self)

src/utils/logging.py:
  def setup_logging(level, format)
```

**Reference:** [Building a better repository map with tree-sitter](https://aider.chat/2023/10/22/repomap.html) | [Repository map documentation](https://aider.chat/docs/repomap.html)

### 4.2 Continue.dev: Embeddings + Tree-sitter

Continue.dev uses a combination of embeddings and AST-aware chunking for codebase retrieval.

**Indexing Pipeline:**
1. **Crawl**: Scan all files in the workspace
2. **Chunk**: Use tree-sitter to parse files and split at function/class boundaries. If a file fits within the chunk size, use the whole file. Otherwise, extract top-level functions and classes as individual chunks.
3. **Embed**: Generate vector embeddings for each chunk (default: `all-MiniLM-L6-v2` with 384 dimensions; recommended: Voyage AI code embedding models)
4. **Store**: Save embeddings in **LanceDB** (embedded TypeScript library, disk-based, stored in `~/.continue/`)

**Retrieval:**
- Codebase retrieval combines **semantic search** (vector similarity) with **keyword search** (ripgrep)
- The `@codebase` context provider triggers this search
- Results are re-ranked and fed to the LLM as context

**Key Design Choices:**
- Tree-sitter for structure-aware chunking (not naive line-based)
- LanceDB for local, embedded vector storage
- Incremental indexing (only re-index changed files via Merkle tree comparison)
- Default chunk strategy: ~10-line blocks, but respects AST boundaries

**Reference:** [Continue Codebase Retrieval](https://docs.continue.dev/features/codebase-embeddings) | [Continue + LanceDB](https://lancedb.com/blog/the-future-of-ai-native-development-is-local-inside-continues-lancedb-powered-evolution/)

### 4.3 Cursor: Cloud-Native Indexing

Cursor takes a fundamentally different approach -- cloud-based indexing with aggressive optimization.

**Indexing Pipeline:**
1. **Chunk**: Split code into function-level chunks
2. **Encrypt**: Encrypt chunks locally
3. **Upload**: Send to Cursor's server (only changed files, identified via Merkle tree)
4. **Embed**: Server computes embeddings
5. **Store**: Embeddings stored in **Turbopuffer** (Cursor's vector database)
6. **PR Indexing**: Automatically indexes merged PR summaries for repository history awareness

**Retrieval:**
- User query is embedded
- Nearest-neighbor search against Turbopuffer
- Semantically similar code chunks returned
- Agent harness manages context selection efficiency

**Custom Models:**
- Cursor 2.0 introduced **Composer** -- a custom model trained for agentic coding
- Optimized for low latency, long context, and tool use
- Most turns complete in under 30 seconds

**Key Difference from HybridCoder:** Cursor's approach requires cloud infrastructure and sends code to external servers. HybridCoder's edge-first philosophy means all indexing and retrieval must happen locally. However, Cursor's Merkle tree approach for incremental sync is a good pattern for local incremental indexing.

**Reference:** [Cursor Codebase Indexing](https://docs.cursor.com/context/codebase-indexing) | [How Cursor Indexes Codebases Fast](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast)

### 4.4 Claude Code: Tool-Based Exploration

Claude Code uses a **tool-based, on-demand approach** rather than pre-indexing.

**Available Tools:**
- `Grep` / `search_files` -- ripgrep-based content search
- `Glob` / `list_files` -- file pattern matching
- `Read` -- read file contents
- `Edit` -- modify files
- `Bash` -- run shell commands

**Context Assembly:**
- No pre-built codebase index
- Claude explores the codebase iteratively using tools
- Context is assembled on-demand per task
- Automatic context management: clears older tool outputs first, then summarizes if needed

**Tool Search Optimization:**
- Deferred tool loading: tools marked `defer_loading: true` are not loaded into context initially
- Claude discovers tools on-demand via the Tool Search Tool
- This saves ~191,300 tokens versus loading all tools upfront (85% reduction)

**Trade-off:** Claude Code's approach is flexible but uses more tokens per task due to iterative exploration. HybridCoder can beat this by pre-indexing the repository, so the LLM receives relevant context immediately.

**Reference:** [How Claude Code Works](https://code.claude.com/docs/en/how-claude-code-works)

### 4.5 Cline / Roo Code: Mode-Based Architecture

**Cline** and **Roo Code** (originally a Cline fork) use mode-based approaches:

**Roo Code Modes:**
- **Architect**: Plans changes without modifying code
- **Code**: Applies precise diffs across modules
- **Debug**: Runs terminals and inspects logs
- **Ask**: Quick reference queries
- **Custom**: User-defined modes with approved tools and guardrails

Each mode activates a specific subset of tools, keeping the context window clearer. This is similar to HybridCoder's approval mode concept.

**Cline's Dual Mode:**
- **Plan Mode**: Gathers context, discusses architecture, drafts solutions (no code changes)
- **Act Mode**: Implements the agreed plan

Both tools use VS Code's APIs for file access and terminal interaction rather than building their own code intelligence. They rely primarily on the LLM's reasoning capabilities with file content as context.

**Reference:** [Roo Code vs Cline Comparison](https://www.qodo.ai/blog/roo-code-vs-cline/)

### Competitor Summary Table

| Tool | Index Strategy | Storage | Context Size | Latency | Local? |
|------|---------------|---------|-------------|---------|--------|
| Aider | Tree-sitter + PageRank | In-memory | 1-4K tokens | <1s | Yes |
| Continue.dev | Embeddings + tree-sitter | LanceDB | 2-8K tokens | 1-3s | Yes |
| Cursor | Embeddings (cloud) | Turbopuffer | 4-16K tokens | 2-5s | No |
| Claude Code | On-demand tools | None | Variable | 5-30s | No |
| Cline/Roo | File reading | None | Variable | 5-20s | No |

### HybridCoder Implications

- **Adopt Aider's repository map as the baseline Layer 2 strategy**. It is proven, efficient (1K tokens default), and runs entirely locally.
- **Add embeddings-based search on top** (Continue.dev pattern) for semantic queries.
- **Use LanceDB for vector storage** (proven by Continue.dev at scale, local-first).
- **Incremental indexing via Merkle tree or file hash comparison** (Cursor pattern adapted for local).
- **Tool-based exploration as fallback** when pre-indexed context is insufficient.
- **Mode-based tool scoping** (Roo Code pattern) aligns with HybridCoder's approval modes.

---

## 5. Embedding Models for Code

HybridCoder needs a code embedding model that runs on CPU (GPU is reserved for the LLM). This section compares the options.

### 5.1 jina-embeddings-v2-base-code

**The current default choice for HybridCoder.**

| Property | Value |
|----------|-------|
| Parameters | 161M |
| Dimensions | 768 |
| Context Length | 8,192 tokens |
| Model Size | 307 MB (unquantized) |
| Languages | 30 programming languages |
| Architecture | BERT-based with ALiBi positional encoding |
| Training Data | 150M+ coding Q&A pairs + docstring-code pairs |

**Strengths:**
- Leads in 9 of 15 CodeSearchNet benchmarks
- 8K context window via ALiBi extrapolation (handles large functions)
- Compact model size enables efficient CPU inference
- Specifically trained for code + natural language queries

**CPU Performance:**
- Estimated ~50-100ms per chunk on modern CPU (based on model size class)
- ONNX Runtime + INT8 quantization can bring this to ~20-40ms
- Batch processing: 50-200 chunks/second on CPU

**Reference:** [jina-embeddings-v2-base-code HuggingFace](https://huggingface.co/jinaai/jina-embeddings-v2-base-code) | [Jina Models](https://jina.ai/models/jina-embeddings-v2-base-code/)

### 5.2 jina-embeddings-v3

**Improved successor with task-specific LoRA adapters.**

| Property | Value |
|----------|-------|
| Parameters | 570M |
| Dimensions | 1024 (truncatable to 256 via Matryoshka) |
| Context Length | 8,192 tokens |
| Model Size | ~1.1 GB |
| Task Adapters | 5: retrieval.query, retrieval.passage, separation, classification, text-matching |

**Improvements over v2:**
- Task-specific LoRA adapters add <3% parameters but significantly improve task performance
- Matryoshka embeddings allow dimension truncation (1024 -> 512 -> 256) with minimal quality loss
- Outperforms OpenAI and Cohere embeddings on English tasks
- Multilingual support

**Trade-off for HybridCoder:** 3.6x larger than v2-base-code. At 570M parameters, CPU inference is slower (~150-300ms per chunk). The task adapters are valuable for asymmetric retrieval (different embeddings for query vs. passage), but the size increase may not be justified for our resource-constrained target.

**Reference:** [jina-embeddings-v3](https://jina.ai/models/jina-embeddings-v3/) | [arXiv paper](https://arxiv.org/abs/2409.10173)

### 5.3 Jina Code Embeddings (0.5B / 1.5B) -- NEW (2025)

**Purpose-built code embedding models derived from code generation LLMs.**

| Property | 0.5B | 1.5B |
|----------|------|------|
| Parameters | 500M | 1.5B |
| Avg Score (25 benchmarks) | 78.41% | 79.04% |
| CodeSearchNet | 86.45% | ~87% |
| Cross-language Search | 99.44% | ~99.5% |
| Training | 8.3 hours on 4x A100 | 12 hours on 4x A100 |

**Key Results:**
- 0.5B outperforms Qwen3-Embedding-0.6B by 5 percentage points despite being 20% smaller
- 1.5B matches voyage-code-3 (79.23%) -- a proprietary model
- Exceeds gemini-embedding-001 (77.38%)
- Built using contrastive learning with InfoNCE loss

**Trade-off for HybridCoder:** These are excellent models but large (0.5B-1.5B parameters). CPU inference would be 200-500ms+ per chunk. Best suited if HybridCoder later supports offloading embeddings to GPU during idle periods.

**Reference:** [Jina Code Embeddings Blog](https://jina.ai/news/jina-code-embeddings-sota-code-retrieval-at-0-5b-and-1-5b/) | [HuggingFace 0.5B](https://huggingface.co/jinaai/jina-code-embeddings-0.5b)

### 5.4 Nomic Embed Text v2

**Open-source MoE model with Matryoshka support.**

| Property | Value |
|----------|-------|
| Architecture | Mixture-of-Experts (MoE) |
| Dimensions | 768 (truncatable to 256) |
| Matryoshka | Yes |
| Training Data | 1.6B high-quality pairs |
| License | Fully open source |

**Strengths:**
- MoE architecture: activates only a subset of parameters per inference (faster than dense models of same quality)
- Matryoshka: truncate from 768 to 256 dimensions with minimal quality loss (3x storage reduction)
- State-of-the-art on BEIR and MIRACL benchmarks
- Fully open-source with transparent training

**Note:** This is a *text* embedding model, not code-specific. It would need evaluation on code retrieval tasks before adoption. Good for documentation and natural language queries about code, less proven for code-to-code similarity.

**Reference:** [Nomic Embed Text v2](https://www.nomic.ai/blog/posts/nomic-embed-text-v2) | [HuggingFace](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)

### 5.5 CodeSage (Amazon)

**Code-specific embeddings trained with consistency filtering.**

| Property | Small | Base | Large |
|----------|-------|------|-------|
| Parameters | 130M | 356M | 1.3B |
| Languages | 9 (c, c#, go, java, js, ts, php, python, ruby) |
| Training | Stage 1: MLM + deobfuscation, Stage 2: Contrastive learning |
| Dataset | The Stack |

**Key Innovation:** Consistency filtering removes 40% of contrastive training data while yielding 10%+ absolute improvement in Code2Code search and 3%+ in NL2Code search. This means cleaner training data is more important than more data.

**Trade-off:** CodeSage-small (130M) is the most CPU-friendly option but supports fewer languages than Jina. CodeSage-large (1.3B) is too big for CPU. CodeSage V2 (December 2024) adds flexible embedding dimensions.

**Reference:** [CodeSage GitHub](https://github.com/amazon-science/CodeSage) | [CodeSage V2](https://code-representation-learning.github.io/codesage-v2.html)

### 5.6 Comparison Table

| Model | Params | Dims | Context | Code-Specific | CPU Friendly | Quality |
|-------|--------|------|---------|---------------|-------------|---------|
| jina-v2-base-code | 161M | 768 | 8K | Yes | **Best** | Good |
| jina-v3 | 570M | 1024 | 8K | Partial | Fair | Very Good |
| jina-code-0.5b | 500M | - | 8K+ | Yes | Fair | Excellent |
| jina-code-1.5b | 1.5B | - | 8K+ | Yes | Poor | Excellent |
| Nomic Embed v2 | MoE | 768 | 8K | No | Good | Very Good |
| CodeSage-small | 130M | - | 1K | Yes | **Best** | Fair |
| CodeSage-base | 356M | - | 1K | Yes | Fair | Good |
| voyage-code-3 | Unknown | 2048 | 32K | Yes | N/A (API) | Excellent |

### 5.7 CPU Inference Optimization

Since HybridCoder reserves GPU for LLM inference, embeddings must run on CPU:

**Optimization Strategies:**
1. **ONNX Runtime**: Convert PyTorch model to ONNX for 2-3x speedup
2. **INT8 Quantization**: Reduce model precision for ~2x speedup with minimal quality loss
3. **Batch Processing**: Embed multiple chunks in parallel (exploit CPU parallelism)
4. **Background Indexing**: Run embedding generation during idle time, not on the critical path
5. **Caching**: Cache embeddings indexed by file content hash; only re-embed changed files

**Expected Performance (jina-v2-base-code + ONNX + INT8):**

| Operation | Latency |
|-----------|---------|
| Single chunk embedding | 20-40ms |
| Batch of 32 chunks | 200-400ms |
| 1000-file project initial index | 30-60 seconds |
| Incremental re-index (10 files) | 2-5 seconds |

**Reference:** [CPU Optimized Embeddings with Optimum Intel](https://huggingface.co/blog/intel-fast-embedding) | [CPU-Optimized Models with fastRAG](https://haystack.deepset.ai/blog/cpu-optimized-models-with-fastrag)

### HybridCoder Implications

- **Stick with jina-v2-base-code as the default**. It offers the best balance of quality, size, and CPU inference speed for our resource constraints.
- **Plan for ONNX + INT8 quantization** from day one. This is essential for acceptable CPU performance.
- **Consider jina-code-0.5b as a future upgrade** when the architecture supports optional GPU embedding.
- **Background indexing** is mandatory -- never block the user waiting for embeddings.
- **768 dimensions is a good balance** -- large enough for quality, small enough for fast similarity search.

---

## 6. LanceDB Architecture

LanceDB is HybridCoder's vector database, chosen for its embedded architecture, native hybrid search, and proven use in Continue.dev.

### 6.1 Lance Columnar Storage Format

LanceDB stores data in the **Lance** format, a modern columnar format optimized for ML workloads.

**Key Properties:**
- **Arrow-native**: Zero-copy reads in Python, DuckDB, and Polars
- **Fragment-based**: Data stored in small columnar chunks optimized for random reads and concurrent access
- **Versioned**: Every write creates a new version via an append-only transaction log (like Delta/Iceberg but lighter)
- **Adaptive encodings**: Alternates between structural encodings based on data width for optimal random access
- **100x random access** vs Parquet without sacrificing scan performance

**Architecture:**

```
+------------------------------------------+
|  LanceDB Python API                      |
|  (sync + async)                          |
+------------------------------------------+
|  Lance Format Layer                      |
|  Fragments | Versions | Indexes          |
+------------------------------------------+
|  Storage Layer                           |
|  Local Disk | S3 | GCS | Azure Blob     |
+------------------------------------------+
```

**Reference:** [Lance Format Paper](https://arxiv.org/abs/2504.15247) | [Beyond Parquet: Lance](https://koushik-dutta.medium.com/beyond-parquet-lance-the-ml-native-data-format-03740f12eb86)

### 6.2 Vector Search with IVF-PQ

LanceDB uses **IVF-PQ** (Inverted File Index with Product Quantization) for approximate nearest neighbor search.

**How IVF-PQ Works:**

```
1. Partition: Divide vector space into num_partitions clusters (IVF)
2. Quantize: Compress vectors within each partition using PQ
   - Split vector into num_sub_vectors segments
   - Each segment quantized to nearest centroid (8 bits)
3. Search: At query time, probe nprobes nearest partitions
   - Compute distances using quantized representations
   - Fast approximate distance computation
```

**Configuration Parameters:**

```python
import lancedb

db = lancedb.connect("data/hybridcoder-index")

# Create table with data
table = db.create_table("code_chunks", data=[
    {
        "vector": [0.1, 0.2, ...],  # 768-dim embedding
        "text": "def calculate_total(items):\n    ...",
        "file_path": "src/billing.py",
        "chunk_type": "function",
        "symbol_name": "calculate_total",
        "start_line": 42,
        "end_line": 55,
    },
    # ...
])

# Create IVF-PQ index
table.create_index(
    metric="cosine",                    # distance metric
    num_partitions=256,                 # IVF partitions (heuristic: num_rows / 8192)
    num_sub_vectors=96,                 # PQ sub-vectors (higher = better recall, slower)
    index_type="IVF_PQ",
)
```

**Tuning Guidelines:**
- `num_partitions`: `num_rows / 8192` is a common heuristic. For 10K chunks, use 1-2 partitions (or skip index entirely -- brute force is fine at this scale).
- `num_sub_vectors`: Must divide the vector dimensions evenly. For 768-dim, use 96 (8 bytes per sub-vector) or 48 (16 bytes).
- `nprobes`: Set at query time. 5-10% of partitions gives good recall with low latency.

**Performance at Scale:**

| Scale | Index Needed? | Build Time | Query Latency | Memory |
|-------|--------------|-----------|--------------|--------|
| 1K chunks | No (brute force) | N/A | <5ms | <10MB |
| 10K chunks | Optional | <5s | 5-20ms | 50-100MB |
| 100K chunks | Yes (IVF-PQ) | 30-60s | 10-50ms | 200-500MB |
| 1M chunks | Required | 3-5min | 20-100ms | 1-2GB |

For HybridCoder's target (small to medium projects), brute-force search is likely sufficient. Index creation is recommended only for large monorepos.

### 6.3 Native BM25 Full-Text Search

LanceDB provides native full-text search using Tantivy (Rust-based, Lucene-equivalent).

```python
# Create FTS index
table.create_fts_index("text", tokenizer_name="en_stem")

# Search
results = table.search("calculate total billing", query_type="fts").limit(10).to_list()
```

**Features:**
- Tantivy tokenizer with language-specific stemming
- Multiple columns can be indexed
- Index creation is asynchronous (returns immediately, builds in background)
- BM25 scoring for relevance ranking

**Note:** Install `tantivy-py` dependency for FTS support.

### 6.4 Hybrid Search with Reciprocal Rank Fusion (RRF)

The core value proposition: combining vector search (semantic similarity) with BM25 (keyword matching) in a single query.

```python
# Hybrid search combining vector + FTS
results = (
    table.search(query_type="hybrid")
    .text("calculate total billing")       # BM25 query
    .vector(query_embedding)               # Vector query (768-dim)
    .limit(10)
    .to_list()
)
```

**RRF Scoring:**

```
RRF_score = 1/(k + BM25_rank) + 1/(k + semantic_rank)
```

Where `k` is typically 60 (default). Higher `k` gives more weight to highly-ranked results from either method.

**Alternative Rerankers:**
- `RRFReranker()` -- default, no external dependency
- `CohereReranker()` -- uses Cohere's reranking API (cloud)
- `CrossEncoderReranker()` -- uses a local cross-encoder model
- `ColbertReranker()` -- uses ColBERT for token-level similarity

For HybridCoder (local-first), use `RRFReranker()` by default. Consider `CrossEncoderReranker()` with a small model for improved quality.

**Performance:** Hybrid search with RRF adds ~5-10ms overhead versus vector-only search. Studies show **35% performance improvement** over pure semantic retrieval when using hybrid search.

**Reference:** [LanceDB Hybrid Search](https://docs.lancedb.com/search/hybrid-search) | [LanceDB Vector Indexes](https://docs.lancedb.com/indexing/vector-index) | [LanceDB FTS](https://docs.lancedb.com/search/full-text-search)

### 6.5 Incremental Updates

LanceDB supports efficient incremental operations:

```python
# Add new chunks (append)
table.add([new_chunk_1, new_chunk_2])

# Update existing chunks (merge insert)
table.merge_insert("file_path") \
    .when_matched_update_all() \
    .when_not_matched_insert_all() \
    .execute(updated_chunks)

# Delete chunks for removed/changed files
table.delete('file_path = "src/old_module.py"')
```

**Incremental vs Full Rebuild:**
- For <100 file changes: incremental update (add/delete changed chunks)
- For major refactors (>30% files changed): full rebuild is simpler and often faster
- FTS index may need rebuild after significant changes (Tantivy limitation)
- Vector index (IVF-PQ) may need rebuild if data distribution shifts significantly

### 6.6 Python API Quick Reference

```python
import lancedb
import pyarrow as pa

# Connect (creates if not exists)
db = lancedb.connect("data/hybridcoder-index")

# Create table with schema
schema = pa.schema([
    pa.field("vector", pa.list_(pa.float32(), 768)),
    pa.field("text", pa.string()),
    pa.field("file_path", pa.string()),
    pa.field("chunk_type", pa.string()),
    pa.field("symbol_name", pa.string()),
    pa.field("start_line", pa.int32()),
    pa.field("end_line", pa.int32()),
    pa.field("language", pa.string()),
    pa.field("scope_chain", pa.string()),  # e.g., "module.ClassName.method_name"
    pa.field("imports", pa.list_(pa.string())),
])

table = db.create_table("code_chunks", schema=schema)

# Add data
table.add(chunks)

# Vector search
results = table.search(query_vector).metric("cosine").limit(5).to_list()

# FTS search
results = table.search("search query", query_type="fts").limit(5).to_list()

# Hybrid search
results = (
    table.search(query_type="hybrid")
    .text("search query")
    .vector(query_vector)
    .limit(5)
    .to_list()
)

# List tables
db.table_names()

# Drop table
db.drop_table("code_chunks")
```

### HybridCoder Implications

- **LanceDB fits perfectly** for local-first embedded vector search. No server process, disk-based, Arrow-compatible.
- **Skip IVF-PQ indexing initially** -- brute force is fine for projects under 10K chunks (most projects).
- **Use hybrid search (BM25 + vector + RRF)** as the default retrieval strategy. This gives the best of both worlds.
- **Schema design**: Store rich metadata per chunk (file_path, chunk_type, symbol_name, scope_chain, imports) to enable filtered queries.
- **Incremental updates**: Track file hashes, only re-embed changed files. Use `merge_insert` for atomic updates.
- **Storage location**: `~/.hybridcoder/index/` or `.hybridcoder/` in project root.

---

## 7. Hybrid Classical + LLM Approaches

This section covers the emerging discipline of **context engineering** and frameworks for combining deterministic analysis with LLM reasoning.

### 7.1 Context Engineering: The Central Pattern (2025-2026)

Context engineering has emerged as the successor to "prompt engineering" -- recognized by Gartner in July 2025 as the critical discipline for production AI systems.

**Definition:** Context engineering is the systematic design and management of ALL information provided to an LLM during inference -- including prompts, retrieved documents, memory, tool descriptions, state information, and environmental signals.

**Four Patterns of Context Engineering:**

```
+---------------------------------------------------+
|              Context Engineering                   |
|                                                    |
|  +----------+  +---------+  +----------+  +------+|
|  |  WRITE   |  | SELECT  |  | COMPRESS |  |ISOLATE|
|  |          |  |         |  |          |  |      ||
|  | What to  |  | What to |  | How to   |  | How  ||
|  | save for |  | retrieve|  | fit more |  | to   ||
|  | later    |  | now     |  | in less  |  |scope ||
|  +----------+  +---------+  +----------+  +------+|
+---------------------------------------------------+
```

1. **WRITE**: What context gets saved for later use
   - Session memory, conversation history, tool outputs
   - HybridCoder: session store, compaction summaries
2. **SELECT**: What context gets retrieved for the current task
   - RAG, repository map, file content
   - HybridCoder: hybrid search, tree-sitter analysis
3. **COMPRESS**: How to fit more information in less space
   - Summarization, token budgeting, map compression
   - HybridCoder: Aider-style ranked map, chunk selection
4. **ISOLATE**: How to scope context to specific sub-tasks
   - Agent specialization, tool-specific prompts
   - HybridCoder: architect/editor split, mode-based tools

**Reference:** [Context Engineering Guide (LangChain)](https://blog.langchain.com/context-engineering-for-agents/) | [Context Engineering for Multi-Agent LLM Code Assistants](https://arxiv.org/abs/2508.08322)

### 7.2 Citation-Grounded Code Comprehension

When an LLM explains or modifies code, it should ground its reasoning in specific code locations. This pattern works as follows:

```
Input to LLM:
  [FILE: src/billing.py, LINES: 42-55]
  def calculate_total(items):
      subtotal = sum(item.price for item in items)
      tax = subtotal * TAX_RATE
      return subtotal + tax

  [FILE: src/constants.py, LINES: 3-3]
  TAX_RATE = 0.08

Output from LLM:
  The calculate_total function [src/billing.py:42-55] computes the
  sum of item prices, then applies the tax rate defined in
  [src/constants.py:3] (currently 8%). To change the tax rate,
  modify TAX_RATE in src/constants.py.
```

**Implementation:**
- Include file paths and line numbers in all code context
- Instruct the LLM to cite specific locations in its responses
- Validate citations against actual file content
- Use tree-sitter to extract exact symbol locations for accurate citations

### 7.3 LLMLOOP: Compiler-in-the-Loop

LLMLOOP (ICSME 2025) is a framework that uses automated iterative feedback loops to improve LLM-generated code.

**Five Feedback Loops:**

```
+-------+     +--------+     +--------+     +--------+     +---------+
| Loop 1| --> | Loop 2 | --> | Loop 3 | --> | Loop 4 | --> | Loop 5  |
| Compile|    | Static |     | Test   |     | Mutation|     | Quality |
| Errors |    | Analysis|    | Failures|    | Testing |     | Metrics |
+-------+     +--------+     +--------+     +--------+     +---------+
```

1. **Compilation Loop**: Ensure generated code compiles. Feed compiler errors back to LLM.
2. **Static Analysis Loop**: Run linting/analysis tools (e.g., PMD, ruff). Feed violations back.
3. **Test Execution Loop**: Run test suite. Feed failures back.
4. **Mutation Testing Loop**: Assess test quality via mutation analysis. Feed surviving mutants back.
5. **Quality Loop**: Check code quality metrics. Feed issues back.

**Results:** LLMLOOP achieves pass@10 of 90.24% vs 76.22% baseline on HumanEval-X.

**HybridCoder Application:**
- Loop 1 maps directly to our Layer 1 (compiler/type checker feedback via Pyright)
- Loop 2 maps to Layer 1 (ruff, tree-sitter-based analysis)
- Loop 3 maps to Layer 4 (test execution via run_command tool)
- This is the architecture for HybridCoder's edit retry mechanism

**Reference:** [LLMLOOP Paper (ICSME 2025)](https://valerio-terragni.github.io/assets/pdf/ravi-icsme-2025.pdf) | [LLMLOOP on ResearchGate](https://www.researchgate.net/publication/394085087_LLMLOOP_Improving_LLM-Generated_Code_and_Tests_through_Automated_Iterative_Feedback_Loops)

### 7.4 Retrieval-Augmented Generation for Code

Code RAG differs from document RAG in several important ways:

**Code-Specific RAG Challenges:**
1. **Structure matters**: Code has hierarchical structure (modules > classes > methods) that naive RAG ignores
2. **Dependencies matter**: A function is meaningless without its imports and type definitions
3. **Context spans files**: Understanding a method often requires reading the class definition, base classes, and called methods across files
4. **Freshness**: Code changes frequently; stale embeddings lead to incorrect suggestions

**Best Practices for Code RAG (2025):**

1. **Hybrid retrieval**: Always combine keyword (BM25) and semantic (vector) search. BM25 catches exact identifiers; vectors catch semantic similarity.
2. **AST-aware chunking**: Split at function/class boundaries, not line counts (see Section 8).
3. **Dependency-aware expansion**: When retrieving a function, also retrieve its imports, type definitions, and called functions.
4. **Hierarchical context**: Include file-level context (module docstring, imports) alongside function-level chunks.
5. **Re-ranking**: Use a cross-encoder or LLM-based reranker to filter the top candidates.
6. **Query augmentation**: Expand natural language queries with extracted identifiers and type information.

**Reference:** [Enhancing RAG: A Study of Best Practices (arXiv)](https://arxiv.org/abs/2501.07391) | [RAG Best Practices Guide 2025](https://www.edenai.co/post/the-2025-guide-to-retrieval-augmented-generation-rag)

### 7.5 Decision Framework: When to Use LLM vs. Deterministic

This is the core decision tree for HybridCoder's 4-layer architecture:

```
User Query / Task
        |
        v
+------------------+
| Can tree-sitter   |--YES--> Layer 1: Return AST result (<50ms)
| answer this?      |         (symbol lookup, structure query,
+------------------+          syntax validation)
        | NO
        v
+------------------+
| Can LSP answer    |--YES--> Layer 1: Return LSP result (50-500ms)
| this?             |         (type info, definitions, references,
+------------------+          diagnostics)
        | NO
        v
+------------------+
| Is this a search  |--YES--> Layer 2: Retrieval (<500ms)
| / context query?  |         (hybrid search, repo map,
+------------------+          embeddings lookup)
        | NO
        v
+------------------+
| Is this a simple  |--YES--> Layer 3: Constrained generation (1-2s)
| completion/fill?  |         (grammar-constrained, small model)
+------------------+
        | NO
        v
+------------------+
| Complex reasoning |-------> Layer 4: Full LLM (5-30s)
| / multi-file edit |         (Qwen3-8B, planning, editing)
+------------------+
```

**Examples by Layer:**

| Query Type | Layer | Technique | Latency |
|-----------|-------|-----------|---------|
| "What functions are in this file?" | L1 | tree-sitter documentSymbol | <50ms |
| "What type does this variable have?" | L1 | LSP hover | 50-100ms |
| "Where is this function defined?" | L1 | LSP definition | 50-100ms |
| "Find all files related to billing" | L2 | Hybrid search | 200-500ms |
| "Show me the project structure" | L2 | tree-sitter + repo map | 200-500ms |
| "Complete this function signature" | L3 | Constrained generation | 1-2s |
| "Refactor this class to use composition" | L4 | Full LLM reasoning | 5-30s |
| "Add error handling to all API endpoints" | L4 | Multi-file LLM edit | 10-60s |

### HybridCoder Implications

- **Implement the decision tree as a query router** in the agent loop. Before sending any query to the LLM, check if Layers 1-2 can answer it.
- **LLMLOOP pattern for edit verification**: After every LLM-generated edit, run Pyright diagnostics + ruff. If errors, feed back to LLM automatically.
- **Context engineering over prompt engineering**: The quality of HybridCoder's output depends on the quality of context assembled, not just the prompt. Invest heavily in Layers 1-2.
- **Track token savings**: Log every query and whether it was resolved at L1, L2, L3, or L4. This metric directly measures HybridCoder's core value proposition (60-80% LLM call reduction).

---

## 8. AST-Aware Code Chunking

Chunking strategy directly impacts retrieval quality. Naive approaches destroy code structure; AST-aware approaches preserve it.

### 8.1 Why Naive Chunking Fails for Code

**Line-based chunking** (e.g., 50 lines per chunk) creates arbitrary boundaries:

```python
# Chunk boundary falls here ---v
class PaymentProcessor:
    def __init__(self, gateway):
        self.gateway = gateway
        self.logger = logging.getLogger(__name__)
# --- CHUNK BOUNDARY ---
    def process_payment(self, amount, card):
        """Process a credit card payment."""
        try:
            result = self.gateway.charge(card, amount)
            self.logger.info(f"Payment processed: {amount}")
            return result
        except GatewayError as e:
            self.logger.error(f"Payment failed: {e}")
            raise PaymentError(str(e))
```

Problems:
1. `process_payment` is separated from its class context
2. The method cannot be understood without knowing `self.gateway` and `self.logger`
3. The import of `logging` is in a completely different chunk
4. A search for "payment processing" might find the method chunk but miss the class definition

### 8.2 AST-Aware Chunking Strategy

The recommended approach uses tree-sitter to identify natural code boundaries:

**Algorithm:**

```python
def chunk_file(source: bytes, language: Language, max_chars: int = 1500) -> list[Chunk]:
    """Chunk a file respecting AST boundaries."""
    parser = Parser(language)
    tree = parser.parse(source)
    root = tree.root_node

    # If file fits in one chunk, return as-is
    if len(source) <= max_chars:
        return [Chunk(text=source, type="file", ...)]

    chunks = []
    for child in root.named_children:
        if child.type in ("function_definition", "class_definition"):
            node_text = source[child.start_byte:child.end_byte]

            if len(node_text) <= max_chars:
                # Function/class fits in one chunk
                chunks.append(Chunk(
                    text=node_text,
                    type=child.type,
                    symbol_name=get_name(child),
                    start_line=child.start_point[0],
                    end_line=child.end_point[0],
                ))
            else:
                # Large class: chunk by methods
                chunks.extend(chunk_large_node(child, source, max_chars))
        else:
            # Imports, assignments, etc. -- group into header chunk
            pass  # accumulate into a "module_header" chunk

    return chunks
```

**Handling Large Classes:**

```python
def chunk_large_node(node, source, max_chars):
    """Recursively chunk a large class or nested structure."""
    chunks = []
    # Extract class header (name, bases, docstring)
    header = extract_header(node, source)

    for child in node.named_children:
        if child.type == "function_definition":
            method_text = source[child.start_byte:child.end_byte]
            # Prepend class context
            chunk_text = f"# In class {get_name(node)}:\n{method_text.decode()}"
            chunks.append(Chunk(
                text=chunk_text.encode(),
                type="method",
                symbol_name=f"{get_name(node)}.{get_name(child)}",
                scope_chain=get_scope_chain(child),
                ...
            ))

    return chunks
```

### 8.3 Metadata Extraction Per Chunk

Each chunk should carry rich metadata for filtered retrieval:

```python
@dataclass
class CodeChunk:
    # Content
    text: str                    # The actual code text
    language: str                # "python", "javascript", etc.

    # Location
    file_path: str               # Relative path from project root
    start_line: int              # 0-indexed
    end_line: int                # 0-indexed

    # Structure
    chunk_type: str              # "function", "class", "method", "module_header"
    symbol_name: str             # "calculate_total" or "PaymentProcessor.process"
    scope_chain: str             # "module.PaymentProcessor.process_payment"

    # Dependencies
    imports: list[str]           # ["logging", "gateway.GatewayError"]
    referenced_symbols: list[str] # ["self.gateway.charge", "PaymentError"]

    # Type info (from LSP, if available)
    signature: str | None        # "def process(self, amount: float, card: Card) -> Result"
    return_type: str | None      # "Result"
    parameter_types: dict | None # {"amount": "float", "card": "Card"}

    # Content hash for incremental updates
    content_hash: str            # SHA256 of text content
```

### 8.4 Optimal Chunk Sizes

Research and practice converge on these guidelines:

| Metric | Recommendation | Rationale |
|--------|---------------|-----------|
| Characters (non-whitespace) | 500-1500 | Dense enough for meaning, fits in embedding context |
| Tokens | 200-600 | Fits within most embedding model contexts |
| Lines | 20-80 | Typical function size |
| Max characters | 2000 | Beyond this, split at method boundaries |
| Min characters | 100 | Below this, merge with adjacent chunk |

**Language-Specific Defaults:**

| Language | Default Max Chars | Rationale |
|----------|------------------|-----------|
| Python | 1500 | Functions tend to be moderate size |
| Java | 2000 | More verbose, larger boilerplate |
| TypeScript | 1800 | Between Python and Java |
| Go | 1500 | Compact, function-oriented |

**Key Insight:** Use non-whitespace character count, not line count. A file full of blank lines and comments should not count the same as dense logic. Two chunks with the same line count can have wildly different amounts of actual code.

**Research Validation:** The cAST paper (EMNLP 2025 Findings) validates that AST-based chunking improves Recall@5 by 4.3 points on RepoEval retrieval and Pass@1 by 2.67 points on SWE-bench generation, compared to fixed-size chunking.

**Reference:** [Building code-chunk: AST-Aware Chunking](https://supermemory.ai/blog/building-code-chunk-ast-aware-code-chunking/) | [cAST: Enhancing Code RAG with AST Chunking](https://arxiv.org/abs/2506.15655) | [ASTChunk GitHub](https://github.com/yilinjz/astchunk)

### 8.5 Complete Chunking Pipeline

```
+-------------+     +---------------+     +------------------+
| Source File  | --> | Tree-sitter   | --> | Node Extraction  |
|              |     | Parse         |     | (functions,      |
|              |     |               |     |  classes, etc.)  |
+-------------+     +---------------+     +------------------+
                                                   |
                                                   v
+-------------+     +---------------+     +------------------+
| Enriched    | <-- | Metadata      | <-- | Size Check &     |
| CodeChunks  |     | Extraction    |     | Split/Merge      |
|             |     | (imports,     |     | (respect AST     |
|             |     |  types, scope)|     |  boundaries)     |
+-------------+     +---------------+     +------------------+
       |
       v
+------------------+     +------------------+
| Embed (jina-v2)  | --> | Store (LanceDB)  |
| CPU, background  |     | with metadata    |
+------------------+     +------------------+
```

### HybridCoder Implications

- **Implement tree-sitter-based chunking** from day one. Never use naive line-based splitting.
- **Non-whitespace character count** as the size metric, not lines.
- **Default chunk size: 1500 characters** for Python, adjustable per language.
- **Rich metadata per chunk** enables powerful filtered queries (e.g., "find all methods in PaymentProcessor", "find functions that import logging").
- **Module header chunk**: Always create a separate chunk for file-level imports, globals, and module docstrings. This provides context when individual functions are retrieved.
- **Scope chain**: Track the full scope chain (e.g., `module.ClassName.method_name`) for hierarchical navigation.
- **Incremental updates**: Hash each chunk's content. Only re-embed chunks whose hash changes on file modification.

---

## Appendix A: Implementation Priority Matrix

Based on this research, the recommended implementation order for Phase 3:

| Priority | Component | Layer | Dependencies | Effort |
|----------|-----------|-------|-------------|--------|
| P0 | Tree-sitter parsing + query library | L1 | tree-sitter-python | 2 days |
| P0 | AST-aware code chunking | L2 | Tree-sitter | 2 days |
| P0 | Repository map (Aider-style) | L2 | Tree-sitter | 3 days |
| P1 | LanceDB integration + schema | L2 | LanceDB | 2 days |
| P1 | Embedding pipeline (jina-v2 + ONNX) | L2 | jina-v2-base-code | 2 days |
| P1 | Hybrid search (BM25 + vector + RRF) | L2 | LanceDB + embeddings | 1 day |
| P1 | Incremental indexing | L2 | All above | 2 days |
| P2 | multilspy / LSP integration | L1 | multilspy + Pyright | 3 days |
| P2 | Query router (L1/L2/L3/L4 dispatch) | All | All above | 2 days |
| P2 | LLMLOOP feedback (diagnostics loop) | L1+L4 | LSP + Agent loop | 2 days |
| P3 | Background index worker | L2 | Indexing pipeline | 1 day |
| P3 | Scope-aware context expansion | L2 | Tree-sitter + LSP | 2 days |

**Total estimated effort: ~24 developer-days**

## Appendix B: Key Dependencies

```toml
# pyproject.toml additions for Phase 3
[project]
dependencies = [
    # Tree-sitter
    "tree-sitter>=0.25.2",
    "tree-sitter-python>=0.23.0",
    # LSP
    "multilspy>=0.2.0",
    # Vector DB
    "lancedb>=0.15.0",
    "tantivy>=0.22.0",  # for FTS
    # Embeddings
    "sentence-transformers>=3.0.0",  # or direct HuggingFace
    "onnxruntime>=1.18.0",  # CPU optimization
    # Utilities
    "pyarrow>=15.0.0",
    "networkx>=3.0",  # for PageRank computation
]
```

## Appendix C: References

### Papers
- Wagner, T. & Graham, S. "Efficient and Flexible Incremental Parsing." ACM TOPLAS, 1998.
- Wagner, T. & Graham, S. "Incremental Analysis of Real Programming Languages." ACM PLDI, 1997.
- Ravi et al. "LLMLOOP: Improving LLM-Generated Code and Tests through Automated Iterative Feedback Loops." ICSME 2025.
- "cAST: Enhancing Code RAG with Structural Chunking via Abstract Syntax Tree." EMNLP 2025 Findings. [arXiv:2506.15655](https://arxiv.org/abs/2506.15655)
- "Lance: Efficient Random Access in Columnar Storage through Adaptive Structural Encodings." [arXiv:2504.15247](https://arxiv.org/abs/2504.15247)
- "jina-embeddings-v3: Multilingual Embeddings With Task LoRA." [arXiv:2409.10173](https://arxiv.org/abs/2409.10173)
- "Enhancing RAG: A Study of Best Practices." [arXiv:2501.07391](https://arxiv.org/abs/2501.07391)
- "Context Engineering for Multi-Agent LLM Code Assistants." [arXiv:2508.08322](https://arxiv.org/abs/2508.08322)

### Documentation
- [Tree-sitter Official Documentation](https://tree-sitter.github.io/tree-sitter/)
- [py-tree-sitter 0.25.2 Documentation](https://tree-sitter.github.io/py-tree-sitter/)
- [LSP 3.18 Specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/)
- [IntelliJ PSI Documentation](https://plugins.jetbrains.com/docs/intellij/psi.html)
- [IntelliJ Indexing and PSI Stubs](https://plugins.jetbrains.com/docs/intellij/indexing-and-psi-stubs.html)
- [VS Code Language Extensions](https://code.visualstudio.com/api/language-extensions/overview)
- [Pyright GitHub](https://github.com/microsoft/pyright)
- [multilspy GitHub](https://github.com/microsoft/multilspy)
- [LanceDB Documentation](https://docs.lancedb.com/)
- [LanceDB Hybrid Search](https://docs.lancedb.com/search/hybrid-search)
- [LanceDB Vector Indexes](https://docs.lancedb.com/indexing/vector-index)

### Tool Documentation
- [Aider Repository Map](https://aider.chat/2023/10/22/repomap.html)
- [Continue.dev Codebase Retrieval](https://docs.continue.dev/features/codebase-embeddings)
- [Cursor Codebase Indexing](https://docs.cursor.com/context/codebase-indexing)
- [How Claude Code Works](https://code.claude.com/docs/en/how-claude-code-works)
- [jina-embeddings-v2-base-code](https://huggingface.co/jinaai/jina-embeddings-v2-base-code)
- [Jina Code Embeddings](https://jina.ai/news/jina-code-embeddings-sota-code-retrieval-at-0-5b-and-1-5b/)
- [CodeSage GitHub](https://github.com/amazon-science/CodeSage)
- [Nomic Embed Text v2](https://www.nomic.ai/blog/posts/nomic-embed-text-v2)

### Blog Posts and Analysis
- [Context Engineering for Agents (LangChain)](https://blog.langchain.com/context-engineering-for-agents/)
- [Continue + LanceDB Evolution](https://lancedb.com/blog/the-future-of-ai-native-development-is-local-inside-continues-lancedb-powered-evolution/)
- [How Cursor Indexes Codebases Fast](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast)
- [CPU Optimized Embeddings (HuggingFace)](https://huggingface.co/blog/intel-fast-embedding)
- [6 Best Code Embedding Models Compared (Modal)](https://modal.com/blog/6-best-code-embedding-models-compared)
- [Scaling LanceDB: 700M Vectors in Production](https://sprytnyk.dev/posts/running-lancedb-in-production/)
- [AST-Aware Code Chunking (Supermemory)](https://supermemory.ai/blog/building-code-chunk-ast-aware-code-chunking/)
- [Tree-sitter Architecture Analysis](https://www.deusinmachina.net/p/tree-sitter-revolutionizing-parsing)

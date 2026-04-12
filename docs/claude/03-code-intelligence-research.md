# Research: Code Intelligence & Retrieval Tools (Feb 2026)

> Generated from web research for HybridCoder project planning

---

## 1. Tree-sitter Python Bindings (py-tree-sitter)

- **Latest Version**: 0.25.2 (September 2025)
- **Install**: `pip install tree-sitter`
- **Python Support**: 3.11, 3.12, 3.13, 3.14
- **Platforms**: Windows, macOS, Linux (x86_64, ARM64) — pre-compiled wheels
- **No native dependencies** — pure Python bindings with pre-built C extensions

### Language Grammars
Each language has a separate package:
- `pip install tree-sitter-python`
- `pip install tree-sitter-java`
- `pip install tree-sitter-javascript`
- `pip install tree-sitter-typescript`

### API Pattern
```python
from tree_sitter import Language, Parser
import tree_sitter_python as tspython

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)
tree = parser.parse(bytes(source_code, "utf8"))
root_node = tree.root_node
# Walk tree, query nodes, extract symbols
```

### Alternative: tree-sitter-languages
- Single package with ALL language grammars bundled
- `pip install tree-sitter-languages`
- Convenient but heavier; may not track latest grammar versions

---

## 2. multilspy — Microsoft's LSP Client

- **Source**: github.com/microsoft/multilspy
- **Origin**: Microsoft Research (NeurIPS 2023 paper "Monitor-Guided Decoding")
- **License**: MIT
- **Languages**: Python (Pyright), Rust, Java (JDT-LS), Go, JavaScript, Ruby, C#, Dart

### Key Capabilities
- Find definitions
- Find references/callers
- Type-based completions
- Hover information
- Document symbols (list all symbols in file)

### API Pattern
```python
from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig

config = MultilspyConfig(code_language="python")
lsp = SyncLanguageServer.create(config, project_root="/path/to/project")

with lsp.start_server():
    result = lsp.request_definition(file_path, line, character)
    refs = lsp.request_references(file_path, line, character)
    symbols = lsp.request_document_symbols(file_path)
    hover = lsp.request_hover(file_path, line, character)
```

### Why Use This Over Raw LSP
- Handles LSP lifecycle (start/stop/restart)
- Manages workspace initialization
- Normalizes responses across different language servers
- Already tested with Pyright and JDT-LS
- Used in production by Microsoft Research

### Considerations
- Actively maintained (activity on GitHub as of 2025)
- Community discussions highlight it as viable for programmatic LSP usage
- Pyright (MIT license) is the Python backend — same engine as Pylance but open-source

---

## 3. Embedding Models for Code

### jina-embeddings-v3 (Recommended)
- **Dimensions**: Flexible 32-1024 (default 1024)
- **Context**: 8,192 tokens
- **Languages**: 89+ natural languages, 30+ programming languages
- **Features**: Task-specific adapters (retrieval, classification, code)
- **Local**: Available via sentence-transformers, ~500MB model
- **Advantage**: Multi-task adapters eliminate need for separate models

### Nomic Embed Code
- **Specialized**: Code-only embedding model
- **Training**: Pre-trained on code repositories
- **Languages**: 30+ programming languages
- **Advantage**: Purpose-built for code retrieval, understands syntax/logic
- **Open-source**: Fully open weights and training data

### jina-embeddings-v2-base-code (Original Plan Choice)
- **Dimensions**: 768
- **Context**: 8,192 tokens
- **Size**: ~300MB
- **Still valid**: Good quality, smaller footprint
- **Consideration**: v3 supersedes it with better quality and flexibility

### Comparison
| Model | Dims | Context | Size | Code-Specific | Local |
|-------|------|---------|------|---------------|-------|
| jina-v3 | 32-1024 | 8K | ~500MB | Adapter | Yes |
| jina-v2-base-code | 768 | 8K | ~300MB | Yes | Yes |
| Nomic Embed Code | 768 | 8K | ~300MB | Yes | Yes |
| voyage-code-3 | 1024 | 16K | API-only | Yes | **No** |
| CodeSage-large-v2 | 1024 | 1K | ~1.3GB | Yes | Yes (slow) |

**Recommendation**: jina-v2-base-code for MVP (smaller, proven), upgrade to jina-v3 or Nomic Embed Code in Phase 6.

---

## 4. LanceDB Hybrid Search

- **Latest**: LanceDB is free, open-source, serverless vector database
- **Install**: `pip install lancedb`
- **Storage**: Local files (no server process)
- **Integration**: pandas, Arrow, Pydantic

### Hybrid Search Architecture
LanceDB supports hybrid search combining:
1. **BM25 (keyword search)** — finds exact term matches
2. **Vector search (semantic)** — finds conceptually similar code
3. **Reciprocal Rank Fusion (RRF)** — combines rankings from both

### Implementation Pattern
```python
import lancedb
from lancedb.embeddings import get_registry

db = lancedb.connect("./lance_index")

# Create table with embeddings
table = db.create_table("code_chunks", data=[
    {"text": chunk, "file": path, "language": "python", ...}
])

# Vector search
results = table.search(query_embedding).limit(10).to_list()

# Full-text search (BM25)
results = table.search(query_text, query_type="fts").limit(10).to_list()

# Hybrid search
results = table.search(query_text, query_type="hybrid").limit(10).to_list()
```

### Key Features for HybridCoder
- Zero-server architecture (aligns with edge-native design)
- Built-in BM25 + vector fusion
- Incremental updates (add/delete chunks without full reindex)
- Pydantic schema support for structured metadata
- DuckDB integration for SQL queries over results

---

## 5. Semgrep Integration

- **Install**: `pip install semgrep`
- **Usage**: Pattern-based static analysis
- **Custom Rules**: YAML-based rule definitions

### Integration Pattern
```python
import subprocess
import json

# Run Semgrep with custom rules
result = subprocess.run(
    ["semgrep", "--config", ".rules/", "--json", "src/"],
    capture_output=True, text=True
)
findings = json.loads(result.stdout)
```

### Custom Rule Example
```yaml
rules:
  - id: unused-import
    pattern: import $X
    message: "Potentially unused import: $X"
    languages: [python]
    severity: WARNING
```

---

## 6. Aider Polyglot Benchmark Details

- **Problems**: 225 Exercism challenges across 6 languages (C++, Go, Java, JS, Python, Rust)
- **Evaluation**: Model edits existing code, run unit tests, 2 attempts (retry with test output)
- **Scoring**: pass@1 percentage
- **Top scores**: ~76% with Claude 4.5 Opus + agentic scaffolding
- **7B local models**: ~30-40%
- **Benchmark repo**: github.com/Aider-AI/polyglot-benchmark

### What It Tests
- Code editing ability (not just generation)
- Format compliance (must produce valid edit blocks)
- Multi-language understanding
- Error recovery (second attempt with test feedback)

---

## 7. SWE-bench Verified

- **Problems**: 500 real GitHub issues, verified solvable by human engineers
- **Evaluation**: Agent must navigate repo, understand issue, write fix, pass tests
- **Top scores (Feb 2026)**: ~70% (Qwen3-Coder-Next, high-end cloud models)
- **Small model results**: Limited — most entries use 70B+ or cloud models
- **Relevant variant**: SWE-bench Lite (300 problems, easier subset)

---

## Sources
- [py-tree-sitter 0.25.2 docs](https://tree-sitter.github.io/py-tree-sitter/)
- [py-tree-sitter releases](https://github.com/tree-sitter/py-tree-sitter/releases)
- [multilspy GitHub](https://github.com/microsoft/multilspy)
- [multilspy HN discussion](https://news.ycombinator.com/item?id=42438918)
- [LanceDB hybrid search docs](https://docs.lancedb.com/search/hybrid-search)
- [LanceDB hybrid search tutorial](https://lancedb.com/blog/hybrid-search-combining-bm25-and-semantic-search-for-better-results-with-lan-1358038fe7e6/)
- [Best embedding models 2026 - Elephas](https://elephas.app/blog/best-embedding-models)
- [6 Best Code Embedding Models - Modal](https://modal.com/blog/6-best-code-embedding-models-compared)
- [jina-embeddings-v3](https://jina.ai/models/jina-embeddings-v3/)
- [Aider polyglot benchmark](https://github.com/Aider-AI/polyglot-benchmark)
- [SWE-bench Verified](https://epoch.ai/benchmarks/swe-bench-verified)

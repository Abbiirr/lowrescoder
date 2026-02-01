# HybridCoder Specification
Version: 1.0 (Draft)
Date: 2026-02-01
Derived from: CLAUDE.md, docs/plan.md

## 1. Purpose
HybridCoder is a local-first AI coding assistant CLI that prioritizes deterministic analysis and uses LLMs only when necessary. The goal is Claude Code-level utility on consumer hardware, with strong transparency and user control.

**Performance Target Proxy**: Achieve >40% pass@1 on Aider polyglot benchmark subset (comparable to GPT-4 baseline on similar tasks) while using 60-80% fewer LLM tokens than a naive always-call-LLM approach.

## 2. Scope
### 2.1 In Scope (MVP)
- Local CLI with chat, ask, edit, config, and help commands.
- Layered intelligence model (deterministic -> retrieval -> constrained generation -> full reasoning).
- Deterministic code intelligence for Python and Java (tree-sitter + LSP).
- Reliable edit system with diff preview, verification, retry, and undo.
- Local retrieval index with hybrid search (BM25 + embeddings).
- Sandboxed tool execution (tests, linting, type checks).
- Git integration with automatic commits and rollback.

### 2.2 Out of Scope (MVP)
- IDE plugins (VS Code/JetBrains) beyond LSP usage.
- Cloud-hosted SaaS or multi-tenant deployments.
- Full multi-language support beyond Python/Java.
- Automated code review or security scanning beyond basic rules.

## 3. Target Users and Use Cases
- Solo or small-team developers who want a local, privacy-preserving coding assistant.
- Common tasks:
  - Ask questions about a codebase (symbols, types, references).
  - Generate or refactor code safely with diffs and undo.
  - Run tests/lints and iterate on failures.
  - Search across large repos with hybrid lexical + semantic retrieval.

## 4. Guiding Principles
- LLM as last resort; deterministic tools first.
- Transparent operations (show diffs, logs, and reasoning steps).
- Local-first privacy (no network by default for tools).
- Fail-safe editing (verify syntax, revert on failure).
- Incremental complexity with measurable performance targets.

## 5. System Overview
### 5.1 Layered Intelligence Model
- Layer 1: Deterministic Analysis (no LLM)
  - tree-sitter parsing for syntax/structure.
  - LSP for types, definitions, references.
  - Static analysis rules (Semgrep).
- Layer 2: Retrieval and Context (no generative LLM)
  - AST-aware chunking.
  - Hybrid search (BM25 + vector embeddings).
  - Repo map generation and project rules injection.
  - Note: Embeddings are encoder models, not generative LLM calls.
- Layer 3: Constrained Generation (efficient LLM)
  - Grammar/JSON constrained decoding (Outlines).
  - Small model for simple tasks.
- Layer 4: Full Reasoning (targeted LLM)
  - 7B model for complex edits.
  - Architect/Editor split for reliability.
  - Feedback loop with compiler/linter/test signals.

### 5.2 Request Routing
- Route to lowest-cost layer that can satisfy the request.
- Escalate only on unresolved queries or when edits are required.

### 5.3 Major Components
- CLI: command routing, REPL, streaming output.
- Core router: decides layer and tool usage.
- File manager: read/write with line range support.
- Git manager: auto-commit, undo/revert, branch control.
- Shell executor: sandboxed command runner.
- Layer 1 engine: tree-sitter + LSP + Semgrep.
- Layer 2 engine: chunking, embeddings, LanceDB, repo map.
- Layer 3 engine: constrained generation and output parsing.
- Layer 4 engine: plan/execute loop with retries.

## 6. External Dependencies and Constraints
- tree-sitter: incremental parsing to maintain syntax trees during edits.
- LSP: JSON-RPC protocol for language intelligence; spec 3.17.
- Pyright: Python type checking CLI (npm or pip wrapper).
- Eclipse JDT LS: Java LSP server; requires Java 21 runtime.
- Semgrep: open-source, pattern-based static analysis rules.
- LanceDB: local/embedded vector database with vector search and optional full-text (BM25) search.
- Embeddings: jina-embeddings-v2-base-code (768-dim, 8192 tokens, ~300MB model size).
- LLM runtime: Ollama local server (HTTP API at http://localhost:11434/api by default).
- LLM model: Qwen2.5-Coder 7B Instruct (32k default context; longer via YaRN in supported runtimes).
- Constrained decoding: Outlines for JSON/Pydantic/grammar outputs.
- CLI UX: Typer (Click-based, type-hint driven CLI) with Rich for formatting.

## 7. Functional Requirements
### 7.1 CLI
- Commands:
  - `hybridcoder chat`
  - `hybridcoder ask "..."`
  - `hybridcoder edit <file>`
  - `hybridcoder config`
  - `hybridcoder --help`
- REPL with streaming tokens and Ctrl+C cancellation.
- Command history with arrow-key navigation.

### 7.2 Edit System
- Whole-file edit (default MVP).
- Search/replace blocks (Phase 2.5+).
- Fuzzy matching with confidence scoring.
- Diff preview before applying edits.
- Lint/type check after edits (optional auto-fix).
- Auto-commit on success; undo command to revert.

### 7.3 Deterministic Queries (Layer 1)
Handled without LLM:
- Find references, definitions, types, signatures.
- List functions/classes/imports in a file.

### 7.4 Retrieval and Context (Layer 2)
- Chunking aligned to AST boundaries.
- Hybrid search with tunable BM25/embedding weights.
- Repo map generation with ranked symbols.
- Load project rules from `.rules/`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`.

### 7.5 Constrained Generation (Layer 3)
- JSON outputs validated against Pydantic models.
- Grammar constraints for edit formats.
- Small model routing for cheap completions.

### 7.6 Agentic Workflow (Layer 4)
- Architect/Editor pattern.
- Feedback loop: parse -> type check -> lint -> tests -> retry.
- Tool registry (read/write/search/run/find refs/diagnostics).
- Multi-file edits with atomic commit or rollback.

### 7.7 Configuration
- YAML config in `~/.hybridcoder/config.yaml`.
- Key sections: llm, layers, edit, git, shell, ui.

### 7.8 Observability
- Per-request logs: latency, tokens, model, retries.
- Debug log with full prompts and responses (local only).

## 8. Non-Functional Requirements
### 8.1 Performance Targets
- Simple query latency: <500ms end-to-end.
- Layer 1 queries: <50ms median.
- Hybrid search: <200ms median.
- First token streaming: <2s.

### 8.2 Resource Targets
- Idle memory: <2GB (stretch: <500MB).
- Inference memory: <8GB VRAM or equivalent.

### 8.3 Reliability and Safety
- No file corruption across 100+ edits.
- Auto-commit on success; auto-revert on failure.
- Max retries per step: 3 (configurable).
- **Failure budget**: <5% of edit operations should require manual intervention after retries.
- **Rollback success rate**: 100% of failed edits must restore original file state.

### 8.4 Privacy and Security
- Local-first: no external calls unless user enables.
- Shell sandbox with allowlist and timeouts.
- No hidden network access during tool runs.

**Sandbox Default Policy**:
- Default allowed: `pytest`, `python`, `pip`, `mvn`, `gradle`, `java`, `javac`, `git status`, `git diff`
- Default blocked: `rm -rf`, `sudo`, `curl`, `wget`, network commands
- Working directory: restricted to project root
- Timeout: 30s default, 300s max
- **User override**: `~/.hybridcoder/config.yaml` allows custom `shell.allowed_commands` and `shell.blocked_commands` lists. Users can also set `shell.allow_network: true` to permit network access.

### 8.5 Portability
- Windows, macOS, Linux support.
- Python 3.11+ runtime.

## 9. Data and Storage
### 9.1 Index Schema
- Per-chunk metadata: file path, language, symbol, start/end lines.
- Stored content plus embedding vector and BM25 index.

### 9.2 Persistence
- LanceDB local files under project cache directory.
- Incremental updates on file changes.

## 10. Interfaces
### 10.1 LLM Provider Interface
- Providers: Ollama (local), OpenAI-compatible server, optional cloud fallback.
- Must support streaming and token usage metrics.

### 10.2 Tool API
- read_file(path, start_line, end_line)
- write_file(path, content)
- search_code(query, limit)
- run_command(command, timeout)
- find_references(symbol, file)
- get_diagnostics(path)

### 10.3 Config Schema (Key Fields)
- llm.provider, llm.model, llm.temperature, llm.max_tokens
- layers.*.enabled
- edit.format, edit.fuzzy_threshold
- git.auto_commit, git.commit_prefix
- shell.timeout, shell.allowed_commands, shell.blocked_commands
- ui.theme, ui.show_diff, ui.stream_output

## 11. Verification and Benchmarks
- Unit tests for parsers, chunking, edit application.
- Integration tests for LSP, Ollama, LanceDB.
- Benchmarks:
  - Aider polyglot benchmark subset.
  - SWE-bench Lite or Verified subset.
  - Custom retrieval precision@k tests.

## 12. Risks and Mitigations
- LLM edit errors: use diff preview, retries, and undo.
- LSP setup complexity: fallback to tree-sitter only.
- Embedding quality: allow multiple models and tunable fusion.
- Performance regressions: continuous profiling and caching.
- Solo dev risk: staged milestones, cut scope if behind.

## 13. Open Questions and Decisions

**Resolved:**
- Memory target: <2GB idle (stretch goal: <500MB)
- Default edit format: whole-file (search/replace deferred to Phase 2.5+)

**Open:**
- Python-only MVP vs Python+Java (recommendation: Python-only to reduce scope risk)
- Default embedding model and index size limits
- Cloud fallback policy and opt-in UX

## 14. MVP Acceptance Checklist

The following 12 criteria must ALL pass for MVP release:

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| 1 | CLI operational | `hybridcoder chat`, `ask`, `edit`, `config`, `--help` commands work |
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

---

## 15. Roadmap Summary
- Phase 0: Project setup and CI.
- Phase 1: CLI + local LLM.
- Phase 2: Edit system + Git safety.
- Phase 3: Deterministic Layer 1.
- Phase 4: Retrieval Layer 2.
- Phase 5: Agentic workflow Layer 4.
- Phase 6: Benchmarking and release.

---

## 16. References
- Tree-sitter documentation: https://tree-sitter.github.io/tree-sitter/
- LSP specification: https://microsoft.github.io/language-server-protocol/
- Pyright CLI: https://www.npmjs.com/package/pyright
- Eclipse JDT LS: https://github.com/eclipse-jdtls/eclipse.jdt.ls
- Semgrep: https://github.com/semgrep/semgrep
- LanceDB docs: https://lancedb.com/documentation/overview/
- Jina embeddings v2 base code: https://aws.amazon.com/marketplace/pp/prodview-tk7t7bz6fp5ng
- Ollama API: https://docs.ollama.com/api/introduction
- Qwen2.5-Coder model card: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
- Outlines structured generation: https://dottxt-ai.github.io/outlines/reference/generation/json/
- Typer docs: https://typer.tiangolo.com/
- Rich: https://github.com/Textualize/rich
- Aider polyglot benchmark: https://github.com/Aider-AI/polyglot-benchmark
- SWE-bench: https://www.swebench.com/

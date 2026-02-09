# Phase 3: Code Intelligence — Final Implementation Plan

> **This is the definitive implementation plan.** It defines scope, decisions, gates, exit criteria, and benchmarks. For implementation-level detail (class pseudocode, method signatures, regex patterns, full test names), see [`phase3-code-intelligence.md`](phase3-code-intelligence.md) — the original plan remains the implementation reference, but this document overrides it on all decisions listed below.
>
> **Related documents:**
> - [`phase3-code-intelligence.md`](phase3-code-intelligence.md) — Implementation detail (pseudocode, class specs, method signatures, test lists)
> - [`phase3-review-notes.md`](phase3-review-notes.md) — Review history (concerns, recommendations, review rounds)
> - [`benchmark-testing-strategy.md`](benchmark-testing-strategy.md) — Full benchmark framework (9 industry benchmarks, 6 tiers, competitor comparison)
>
> Version: 2.0 | Date: 2026-02-09
> Status: READY FOR REVIEW — pending Codex APPROVE before implementation begins

---

## What Changed From the Original Plan

| Change | Source | Impact |
|--------|--------|--------|
| **Sprint 3C (LSP) deferred** to post-Phase 3 | Review notes R2, Codex Entry 174/179 | Tools: 12 → 11, `get_diagnostics` removed |
| **Pyright → Jedi** throughout | Codex Entry 174 | multilspy's Python backend is Jedi, not Pyright |
| **`get_diagnostics` tool removed** | Codex Entry 179 (no multilspy public API) | One fewer tool, simpler scope |
| **Context budget: 6000 → 5000 tokens** | Review notes R4 | More response room for Qwen3-8B |
| **3 gated sub-phases** (Alpha/Beta/Gamma) | Review notes R5, user direction | Independent validation at each gate |
| **Concern 2.8 resolved** (Pyright→Jedi was historical) | Codex Entry 179, Concern 4 | Plan now says Jedi everywhere |
| **Layer indicator: L1/L2/L4** (not just L1/L4) | Codex Entry 179, Concern 5 | Protocol emits `layer_used=2` for retrieval path |

---

## 1. Goal

Transform HybridCoder from a thin LLM wrapper into a **truly hybrid** coding assistant where 60-80% of queries use zero LLM tokens.

### North Star Outcomes

| Outcome | Metric | Target |
|---------|--------|--------|
| Reduced token cost | % of queries using 0 tokens | 60-80% |
| Reduced latency | p95 for deterministic queries | <50ms |
| Fewer tool calls | L1 queries bypassing agent loop | 100% of L1 |
| Better codebase understanding | Symbol extraction accuracy | 100% for Python |
| Better search/RAG | Search precision@3 | >60% |
| Better intellisense | Definition/reference lookup | Works without LLM |
| Improved accuracy | LLM gets curated context | Context budget compliant |

---

## 2. Architecture

```
User Input (Go TUI)
    │
    ├─ Slash command? → /index delegates to Python, others handled locally
    │
    └─ Chat message → JSON-RPC "chat" request
                       │
                       ▼
    ┌──────────────────────────────────────────────────┐
    │  Python Backend (server.py → handle_chat)         │
    │                                                    │
    │  RequestRouter (BEFORE agent loop)                 │
    │    ├─ Regex pattern matching                       │
    │    ├─ Feature extraction                           │
    │    └─ Weighted scoring → RequestType               │
    │                                                    │
    │  Routes to:                                        │
    │    ├─ DETERMINISTIC_QUERY → Layer 1 (no LLM)      │
    │    ├─ SEMANTIC_SEARCH    → L2 context → L4 LLM    │
    │    └─ COMPLEX_TASK/CHAT  → L4 LLM (with L2 ctx)   │
    └──────┬──────────┬──────────┬───────────────────────┘
           │          │          │
           ▼          ▼          ▼
      Layer 1     Layer 2     Layer 4
      <50ms       100-500ms   5-30s
      0 tokens    0 tokens    2K-8K tokens
           │          │          │
           ▼          ▼          ▼
    on_done notification (layer_used=1/2/4)
    Go TUI renders response + status bar [L1]/[L2]/[L4]
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Router location | Before AgentLoop | L1 queries never touch LLM |
| L1 bypass | Returns Response directly | Sub-50ms, no async overhead |
| LSP (Sprint 3C) | **Deferred** to post-Phase 3 | multilspy v0.0.15 unstable, Jedi not Pyright, `get_diagnostics` has no API |
| Embedding loading | Lazy (first search), CPU-only | Preserves GPU VRAM for LLM |
| Indexing trigger | On-demand, mtime refresh | No file watcher complexity |
| Token budget | **5000 tokens** (was 6000) | More response room in 8192 context |
| Search fusion | BM25 + vector + RRF | Best quality per research |
| Layer indicator | L1/L2/L4 (not just L1/L4) | Retrieval path gets its own indicator |

---

## 3. Gated Sprint Structure

### Phase 3-Alpha: Deterministic Intelligence

**Sprints 3A + 3B | ~5 days**

The core differentiator. Proves that HybridCoder can answer structural queries 100x faster than any competitor, at zero cost.

#### Sprint 3A: Tree-sitter Parser + Symbol Extraction (2-3 days)

**New files:**
- `src/hybridcoder/layer1/__init__.py` — package marker
- `src/hybridcoder/layer1/parser.py` — `TreeSitterParser` with mtime cache, LRU eviction (500 entries)
- `src/hybridcoder/layer1/symbols.py` — `SymbolExtractor` using QueryCursor API (0.25.x)

**Modified files:**
- `src/hybridcoder/core/types.py` — add `ParseResult`, `Symbol`, `RequestType` dataclasses

**Tests:** `tests/unit/test_parser.py` (~20 tests)

**Dependencies:** `tree-sitter>=0.25.2`, `tree-sitter-python>=0.25.0`

**First task (validation spike):** Parse a function, extract a symbol via QueryCursor. If 0.25.x API works, proceed. If not, fall back to 0.24.x pattern.

#### Sprint 3B: Request Router + Deterministic Query Handlers (2-3 days)

**New files:**
- `src/hybridcoder/core/router.py` — `RequestRouter` (3-stage: regex → features → weighted scoring)
- `src/hybridcoder/layer1/queries.py` — `DeterministicQueryHandler` (list symbols, find refs, get imports, signatures, definitions)

**Tests:** `tests/unit/test_router.py` (~25 tests)

#### Gate 1 Exit Criteria

| Criterion | Test | Target |
|-----------|------|--------|
| "list functions in X.py" works end-to-end | Manual + `test_l1_latency.py` | <50ms, 0 tokens |
| Router accuracy | `test_router.py` (25 queries) | 90%+ correct |
| Parser reliability | Parse all project .py files | 100% success |
| Symbol extraction | Known-answer tests | Exact match |

**If Gate 1 fails:** Stop. Fix the foundation before building retrieval on top.
**If Gate 1 passes:** This alone is a shippable demo. Proceed to Beta.

---

### Phase 3-Beta: Retrieval Intelligence

**Sprints 3D + 3E + 3F | ~7 days**

Adds search, indexing, and context assembly. Makes LLM responses smarter by giving them curated code context.

#### Sprint 3D: AST-Aware Chunker + Embedding Engine (2-3 days)

**New files:**
- `src/hybridcoder/layer2/__init__.py` — package marker
- `src/hybridcoder/layer2/chunker.py` — `ASTChunker` (splits at function/class boundaries, 200-800 token chunks)
- `src/hybridcoder/layer2/embeddings.py` — `EmbeddingEngine` (jina-v2-base-code, CPU-only, lazy-loaded, BM25 fallback)

**Tests:** `tests/unit/test_chunker.py` (~18), `tests/unit/test_embeddings.py` (~8)

**Dependencies:** `sentence-transformers>=5.0`

#### Sprint 3E: LanceDB Index + Hybrid Search (2-3 days)

**New files:**
- `src/hybridcoder/layer2/index.py` — `CodeIndex` (LanceDB, file-hash invalidation, incremental updates, 50K file cap, gitignore-aware)
- `src/hybridcoder/layer2/search.py` — `HybridSearch` (BM25 + vector + Reciprocal Rank Fusion)

**Tests:** `tests/unit/test_index.py` (~12), `tests/unit/test_search.py` (~12), `tests/integration/test_lancedb.py` (~8)

**Dependencies:** `lancedb>=0.29`

#### Sprint 3F: Repo Map + Context Assembler (2 days)

**New files:**
- `src/hybridcoder/layer2/repomap.py` — `RepoMapGenerator` (ranked symbol summary, 600-token budget)
- `src/hybridcoder/layer2/rules.py` — `RulesLoader` (CLAUDE.md, AGENTS.md, .rules/*.md, .cursorrules)
- `src/hybridcoder/core/context.py` — `ContextAssembler` (priority-based 5000-token budget)

**Context budget allocation (5000 tokens):**
```
Rules:       ~300
Repo map:    ~600
Chunks:     ~2200
File:        ~800
History:     ~800
Buffer:      ~300
Total:       5000
```

**Tests:** `tests/unit/test_repomap.py` (~8), `tests/unit/test_context.py` (~8)

#### Gate 2 Exit Criteria

| Criterion | Test | Target |
|-----------|------|--------|
| Search precision | `test_search_relevance.py` (10 known-answer queries) | precision@3 > 60% |
| Token budget compliance | `test_context_budget.py` (20 queries) | 100% under 5000 tokens |
| Index build time | Integration test | <30s for project-sized codebases |
| Embedding fallback | `test_bm25_only_when_no_embeddings` | BM25-only works when model unavailable |

**If Gate 2 fails:** The deterministic path (Alpha) still works standalone. Fix retrieval before proceeding.
**If Gate 2 passes:** Both L1 and L2 work. Proceed to Gamma.

---

### Phase 3-Gamma: Integration + Polish

**Sprint 3G | ~3 days**

Wire everything together. Add tools, update TUI, run full verification.

#### Sprint 3G: TUI Integration + New Tools + Verification (3 days)

**Modified Python files:**
- `src/hybridcoder/agent/tools.py` — add 5 new tools (was 6, minus `get_diagnostics`)
- `src/hybridcoder/backend/server.py` — router integration in `handle_chat()`, L1 bypass before agent loop, `layer_used` field in `on_done`
- `src/hybridcoder/agent/prompts.py` — context injection (repo map + rules + grounding)
- `src/hybridcoder/tui/commands.py` — add `/index` command
- `src/hybridcoder/config.py` — extend `Layer1Config`, `Layer2Config`

**New Python files:**
- `src/hybridcoder/layer1/validators.py` — syntax + import validation via tree-sitter

**Modified Go files (~20 lines total):**
- `protocol.go` — add `LayerUsed int` to `DoneParams`
- `messages.go` — add `LayerUsed int` to `backendDoneMsg`
- `backend.go` — pass `LayerUsed` in `on_done` dispatch
- `statusbar.go` — add `Layer` field, render `[L1]`/`[L2]`/`[L4]`
- `update.go` — set `m.statusBar.Layer` in `handleDone()`
- `commands.go` — add `"/index"` to `knownCommands`

**Tests:** `tests/unit/test_new_tools.py` (~12), `tests/unit/test_integration_router_agent.py` (~8), Go tests (~5)

### Tools After Phase 3: 11 Total

| # | Tool | Source | Layer |
|---|------|--------|-------|
| 1 | `read_file` | Phase 2 (existing) | — |
| 2 | `write_file` | Phase 2 (existing) | — |
| 3 | `apply_diff` | Phase 2 (existing) | — |
| 4 | `search_replace` | Phase 2 (existing) | — |
| 5 | `run_command` | Phase 2 (existing) | — |
| 6 | `list_directory` | Phase 2 (existing) | — |
| 7 | `find_references` | **Phase 3 (new)** | L1 — grep + tree-sitter |
| 8 | `find_definition` | **Phase 3 (new)** | L1 — tree-sitter + grep |
| 9 | `get_type_info` | **Phase 3 (new)** | L1 — AST type annotation only |
| 10 | `list_symbols` | **Phase 3 (new)** | L1 — tree-sitter extraction |
| 11 | `search_code` | **Phase 3 (new)** | L2 — hybrid search |

**Deferred:** `get_diagnostics` (no multilspy public API, no tree-sitter equivalent)

#### Gate 3 Exit Criteria

All Phase 3 exit criteria pass (see Section 5 below).

---

## 4. What's Deferred (NOT in Phase 3)

| Item | Reason | When |
|------|--------|------|
| Sprint 3C (LSP via multilspy) | multilspy v0.0.15 unstable, Jedi not Pyright, API issues (Codex Entry 179) | Post-Phase 3 |
| `get_diagnostics` tool | No multilspy public API for diagnostics (Codex Entry 179) | With Sprint 3C |
| Exit criterion #6 (LSP graceful degradation) | No LSP to degrade | With Sprint 3C |
| Multi-language support (Java, TypeScript) | Python-first, reduce scope | Phase 5+ |
| Semgrep integration | Not needed for MVP | Phase 5+ |
| Pattern matching (refactoring patterns) | Not needed for MVP | Phase 5+ |
| Layer 3 constrained generation | Separate architecture | Phase 4 (renumbered) |

---

## 5. Exit Criteria (11 total)

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | **11 tools registered** (6 original + 5 new) | `test_sprint_verify.py::test_eleven_tools` — `assert len(registry.get_all()) == 11` |
| 2 | **Router classifies 90%+ correctly** | `test_router.py` (25 cases) + `test_deterministic_routing.py` (50 queries) — `assert accuracy >= 0.90` |
| 3 | **L1 queries: <50ms, 0 tokens** | `test_l1_latency.py` — `assert latency_p95 < 50 and tokens_used == 0` |
| 4 | **Search precision@3 > 60%** | `test_search_relevance.py` (10 known-answer queries) — `assert precision_at_3 > 0.60` |
| 5 | **Context within 5000 token budget** | `test_context.py::test_total_under_budget` — `assert total_tokens <= 5000` |
| 6 | **Embeddings degrade to BM25-only** | `test_search.py::test_bm25_only_when_no_embeddings` |
| 7 | **Go TUI shows layer indicator** | Go: `TestStatusBarLayerIndicator`, Python: `test_on_done_includes_layer_used` |
| 8 | **All unit tests pass (target: 600+)** | `uv run pytest tests/ -v` — exit code 0 |
| 9 | **Sprint verification tests pass** | `uv run pytest tests/test_sprint_verify.py -v` — all TestSprint3* pass |
| 10 | **`/index` command works** | `test_index_command_registered` |
| 11 | **`make lint` passes** | `uv run ruff check && uv run mypy` — exit code 0 |

---

## 6. Benchmarks

### Tier 0: Deterministic Layer Validation (Gate 1)

File: `tests/benchmark/test_deterministic_routing.py` (50 queries)

| Test | Target |
|------|--------|
| Router classifies 90%+ of test queries | 45/50 correct |
| L1 returns results in <50ms | p95 < 50ms |
| L1 uses 0 LLM tokens | 0 tokens asserted |
| Parser parses all project .py files | 100% success |
| Router defaults to L4 on ambiguous queries | 100% safe fallback |

File: `tests/benchmark/test_l1_latency.py`

| Test | Target |
|------|--------|
| Single file parse | <10ms |
| Symbol extraction (cached) | <5ms |
| Router classification | <1ms |
| Full L1 query (router → parse → format) | <50ms |
| 100 sequential L1 queries | <5s total |
| Cached parse (same file) | <1ms |

### Tier 1: Code Intelligence (Gate 2)

File: `tests/benchmark/test_search_relevance.py` (10 known-answer queries)

| Test | Target |
|------|--------|
| Precision@3 across all queries | >60% |
| Known-answer recall | Relevant file in top 3 |

File: `tests/benchmark/test_context_budget.py` (20 queries)

| Test | Target |
|------|--------|
| All contexts under token budget | 100% ≤ 5000 tokens |
| Empty project doesn't crash | Graceful handling |

### Manual Verification (Gate 3)

| # | Query | Expected Result |
|---|-------|----------------|
| 1 | "list functions in src/hybridcoder/agent/tools.py" | L1, <50ms, function names + lines, 0 tokens |
| 2 | "how does the agent loop work?" | L2→L4, cites agent/loop.py |
| 3 | "find usages of ToolRegistry" | L1, all files/lines with references |
| 4 | `/index` command | Index built, file/chunk counts shown |
| 5 | "search for approval handling code" | L2, relevant chunks from approval.py |

---

## 7. Files Summary

### New Files (14 Python + 0 Go)

| File | Sprint | Purpose |
|------|--------|---------|
| `src/hybridcoder/layer1/__init__.py` | 3A | Package marker |
| `src/hybridcoder/layer1/parser.py` | 3A | Tree-sitter parser with mtime cache |
| `src/hybridcoder/layer1/symbols.py` | 3A | Symbol extraction via QueryCursor |
| `src/hybridcoder/core/router.py` | 3B | Request router (regex + heuristic) |
| `src/hybridcoder/layer1/queries.py` | 3B | Deterministic query handlers |
| `src/hybridcoder/layer2/__init__.py` | 3D | Package marker |
| `src/hybridcoder/layer2/chunker.py` | 3D | AST-aware code chunker |
| `src/hybridcoder/layer2/embeddings.py` | 3D | Embedding engine (jina-v2, CPU) |
| `src/hybridcoder/layer2/index.py` | 3E | LanceDB code index |
| `src/hybridcoder/layer2/search.py` | 3E | Hybrid BM25 + vector search |
| `src/hybridcoder/layer2/repomap.py` | 3F | Repository map generator |
| `src/hybridcoder/layer2/rules.py` | 3F | Project rules loader |
| `src/hybridcoder/core/context.py` | 3F | Context assembler (5000 token budget) |
| `src/hybridcoder/layer1/validators.py` | 3G | Syntax + import validation |

### Modified Files (6 Python + 6 Go)

| File | Sprint | Changes |
|------|--------|---------|
| `src/hybridcoder/core/types.py` | 3A | Add `ParseResult`, `Symbol`, `RequestType` |
| `src/hybridcoder/agent/tools.py` | 3G | Add 5 new tools |
| `src/hybridcoder/agent/prompts.py` | 3G | Context injection (repo map + rules) |
| `src/hybridcoder/backend/server.py` | 3G | Router integration, L1 bypass, `layer_used` |
| `src/hybridcoder/tui/commands.py` | 3G | `/index` command |
| `src/hybridcoder/config.py` | 3G | Layer1Config, Layer2Config |
| `cmd/hybridcoder-tui/protocol.go` | 3G | `LayerUsed` in DoneParams |
| `cmd/hybridcoder-tui/messages.go` | 3G | `LayerUsed` in backendDoneMsg |
| `cmd/hybridcoder-tui/backend.go` | 3G | Pass `LayerUsed` in dispatch |
| `cmd/hybridcoder-tui/statusbar.go` | 3G | Render `[L1]`/`[L2]`/`[L4]` |
| `cmd/hybridcoder-tui/update.go` | 3G | Set Layer in handleDone |
| `cmd/hybridcoder-tui/commands.go` | 3G | Add "/index" to knownCommands |

### New Test Files (11 Python + 1 Go)

| File | Sprint | Tests |
|------|--------|-------|
| `tests/unit/test_parser.py` | 3A | ~20 |
| `tests/unit/test_router.py` | 3B | ~25 |
| `tests/unit/test_chunker.py` | 3D | ~18 |
| `tests/unit/test_embeddings.py` | 3D | ~8 |
| `tests/unit/test_index.py` | 3E | ~12 |
| `tests/unit/test_search.py` | 3E | ~12 |
| `tests/unit/test_repomap.py` | 3F | ~8 |
| `tests/unit/test_context.py` | 3F | ~8 |
| `tests/unit/test_new_tools.py` | 3G | ~12 |
| `tests/unit/test_integration_router_agent.py` | 3G | ~8 |
| `tests/integration/test_lancedb.py` | 3E | ~8 |
| `cmd/hybridcoder-tui/statusbar_test.go` | 3G | ~5 |

**New test total: ~144 Python + ~5 Go = ~149**
**Expected project total: ~509 (existing Python) + 144 + ~275 (existing Go) + 5 = ~933 tests**

### Benchmark Test Files (4 new)

| File | Tests | Gate |
|------|-------|------|
| `tests/benchmark/test_deterministic_routing.py` | 50 query classifications | Gate 1 |
| `tests/benchmark/test_l1_latency.py` | 6 performance benchmarks | Gate 1 |
| `tests/benchmark/test_search_relevance.py` | 10 known-answer queries | Gate 2 |
| `tests/benchmark/test_context_budget.py` | 20 budget compliance tests | Gate 2 |

---

## 8. Dependencies

### Required

```toml
[project.optional-dependencies]
layer1 = [
    "tree-sitter>=0.25.2",
    "tree-sitter-python>=0.25.0",
]
layer2 = [
    "lancedb>=0.29",
    "sentence-transformers>=5.0",
]
```

### Deferred (Not installed in Phase 3)

```toml
lsp = [
    "multilspy>=0.0.15",  # Deferred — Sprint 3C post-Phase 3
]
```

---

## 9. Configuration

### Layer1Config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | True | Enable L1 deterministic routing |
| `cache_max_entries` | int | 500 | Max cached parse trees |

### Layer2Config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `db_path` | str | ~/.hybridcoder/index.lancedb | LanceDB storage path |
| `relevance_threshold` | float | 0.3 | Minimum search relevance score |
| `max_files` | int | 50000 | Max files to index |
| `repomap_budget` | int | 600 | Repo map token budget |
| `context_budget` | int | 5000 | Total context token budget |

---

## 10. Timeline

| Sprint | Gate | Duration | Dependencies |
|--------|------|----------|-------------|
| 3A: Parser + Symbols | Alpha | 2-3 days | None |
| 3B: Router + Queries | Alpha | 2-3 days | 3A |
| **Gate 1 checkpoint** | | | |
| 3D: Chunker + Embeddings | Beta | 2-3 days | 3A |
| 3E: Index + Search | Beta | 2-3 days | 3D |
| 3F: Repo Map + Context | Beta | 2 days | 3A, 3E |
| **Gate 2 checkpoint** | | | |
| 3G: Integration + Verify | Gamma | 3 days | All above |
| **Gate 3 checkpoint** | | | |
| **Total** | | **~15 days** | |

### Dependency Graph (without 3C)

```
3A ──┬──→ 3B ──────────────────┐
     │                          │
     └──→ 3D ──→ 3E ──→ 3F ──→ 3G
```

3B and 3D can run in parallel after 3A. Critical path: 3A → 3D → 3E → 3F → 3G (~12 days).

---

## 11. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Tree-sitter 0.25.x QueryCursor API changed | Parser breaks, blocks everything | Pin exact versions; validation spike as 3A first task; 0.24.x fallback |
| LanceDB LanceModel API unstable | Index build fails | Pin exact version; PyArrow schema fallback; integration tests |
| Router misclassifies queries | Wrong layer handles request | Conservative thresholds (default to L4 on ambiguity); confusion matrix |
| jina-v2-base-code large download (~300MB) | Slow first search | Lazy load; BM25-only fallback; status messaging |
| Large monorepo performance | Index build too slow | 50K file cap; incremental updates; mtime skip |
| Qwen3-8B response truncation | Context too large | 5000-token budget (was 6000); configurable; users with VRAM can increase `num_ctx` |

**Note on context budget:** Qwen3-8B supports up to 40960 tokens natively (`max_position_embeddings`). The 8192 limit is our Ollama runtime config for 8GB VRAM. Users with more VRAM can increase `num_ctx` and the budget constraint relaxes.

---

## 12. Decision Log

| # | Decision | Entry | Status |
|---|----------|-------|--------|
| 1 | Defer Sprint 3C (LSP) to post-Phase 3 | Review notes R2, Codex 174/179 | **Proposed — needs Codex APPROVE** |
| 2 | Pyright → Jedi in all plan references | Codex Entry 174 | **Done** |
| 3 | `get_diagnostics` deferred (no multilspy API) | Codex Entry 179 | **Proposed — needs Codex APPROVE** |
| 4 | 3 gated sub-phases (Alpha/Beta/Gamma) | Review notes R5, user direction | **Proposed — needs Codex APPROVE** |
| 5 | Context budget 6000 → 5000 tokens | Review notes R4, Codex 174 | **Proposed — needs Codex APPROVE** |
| 6 | Layer indicator L1/L2/L4 (not just L1/L4) | Codex Entry 179 | **Proposed — needs Codex APPROVE** |
| 7 | Tool count 12 → 11 | Follows from decisions 1, 3 | **Proposed — needs Codex APPROVE** |

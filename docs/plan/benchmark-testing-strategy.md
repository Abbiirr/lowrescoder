# Benchmark & Testing Strategy

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 1.0 | Date: 2026-02-09
> Purpose: Comprehensive evaluation framework for all project phases

---

## 1. Industry Benchmarks Overview

### Code Generation Benchmarks

| Benchmark | What it Tests | Problems | Metrics | Language | Suitable Phase |
|-----------|--------------|----------|---------|----------|----------------|
| **HumanEval+** (OpenAI + EvalPlus) | Function-level code completion | 164 Python | pass@k | Python | Phase 3-4 |
| **MBPP+** (Google + EvalPlus) | Basic Python programming | 378 Python | pass@k | Python | Phase 3-4 |
| **LiveCodeBench** | Fresh competitive programming (live-updated, no contamination) | 600+ | pass@1 | Multi | Phase 4-5 |
| **BigCodeBench** | Complex multi-library tasks across 7 domains | 1140 tasks | pass@1 | Python | Phase 5+ |

### Code Editing & Refactoring Benchmarks

| Benchmark | What it Tests | Problems | Metrics | Suitable Phase |
|-----------|--------------|----------|---------|----------------|
| **Aider Code Editing** | Multi-turn code editing via CLI | 133 Exercism | completion % | Phase 4 |
| **Aider Polyglot** | Multi-language editing (6 languages) | 225 exercises | pass@1 | Phase 5+ |
| **Aider Refactoring** | Large method restructuring | 89 methods | pass@1 | Phase 5+ |

### Agentic / End-to-End Benchmarks

| Benchmark | What it Tests | Problems | Metrics | Suitable Phase |
|-----------|--------------|----------|---------|----------------|
| **SWE-Bench Verified** | Real GitHub issue resolution (human-verified subset) | 500 issues | resolved % | Phase 5+ |
| **CodeArena** | Full application building, collective evaluation | ~400 challenges | collective score | Phase 6 |

### Benchmark Selection Rationale

**Why these 9 benchmarks?**

1. **HumanEval+ / MBPP+**: Industry standard for code generation. EvalPlus versions add edge-case tests to catch false passes. Essential for baseline measurement.

2. **LiveCodeBench**: Fresh problems (added monthly) — prevents training data contamination, which is a real concern with static benchmarks for fine-tuned models. If Qwen3-8B was trained on HumanEval/MBPP data, LiveCodeBench provides a contamination-free alternative.

3. **Aider benchmarks**: Directly comparable to the most popular open-source coding CLI. Aider publishes leaderboards — we can position HybridCoder against known baselines.

4. **SWE-Bench Verified**: The gold standard for agentic coding evaluation. Tests real-world bug fixing on popular open-source repos. The "Verified" subset (500 issues) is human-validated for solvability.

5. **BigCodeBench / CodeArena**: Stretch goals for Phase 5+. Tests complex, multi-library, real-world tasks beyond simple function completion.

**What we're NOT using and why:**

- **APPS / CodeContests**: Competitive programming focus — not representative of real coding agent tasks.
- **DS-1000**: Data science specific — outside our initial scope (Python-first, not data-science-first).
- **CrossCodeEval**: Cross-file completion — relevant but Phase 5+ only. Revisit later.

---

## 2. HybridCoder-Specific Test Tiers

### Tier 0: Deterministic Layer Validation (Phase 3)

Tests the core differentiator: **does the deterministic path work correctly?**

| Test | Target | Method |
|------|--------|--------|
| Router correctly classifies 90%+ of test queries | >90% accuracy | 50 labeled test queries |
| L1 returns results in <50ms | p95 < 50ms | Benchmark timing over 100 queries |
| L1 uses 0 LLM tokens | 0 tokens | Assert token counter unchanged |
| tree-sitter parses all project Python files | 100% parse success | Parse every .py file in src/ |
| Symbol extraction matches expected output | Exact match | Known-answer tests on sample files |
| Router defaults to L4 on ambiguous queries | 100% safe fallback | 10 ambiguous query test cases |

**Why Tier 0 is critical:** If the deterministic layer doesn't work, HybridCoder has no competitive advantage. This tier validates the fundamental value proposition before measuring anything else.

### Tier 1: Basic Code Intelligence (Phase 3-4)

Tests Layer 1 and Layer 2 capabilities individually.

| Test | Target | Method |
|------|--------|--------|
| "List functions in X.py" returns correct names | 100% recall | Compare against tree-sitter ground truth |
| "Find usages of ClassName" finds all references | >80% recall | Compare against grep ground truth |
| "What type is variable X" returns type info | Correct when annotation is explicit | Compare against AST annotation fixtures (LSP deferred in Phase 3) |
| Hybrid search returns relevant code chunks | precision@3 > 60% | Known-answer search queries |
| Context assembler stays within token budget | 100% under 5000 tokens | Assert on 20 diverse queries |
| Repo map includes key project symbols | Top-10 symbols present | Manual verification |
| Rules loader finds CLAUDE.md | Always found when present | Test with/without file |

### Tier 2: Code Generation Quality (Phase 4)

Measures whether HybridCoder's context pipeline **helps** the LLM generate better code.

| Test | Baseline (Raw Qwen3-8B) | Target (HybridCoder) | Method |
|------|--------------------------|----------------------|--------|
| HumanEval+ pass@1 | ~45% (estimated) | >= baseline | Run 164 problems through both |
| MBPP+ pass@1 | ~50% (estimated) | >= baseline | Run 378 problems through both |
| Code with context vs without | N/A | Measurable improvement | A/B test on 20 complex problems |

**Key insight:** HybridCoder should **match or exceed** raw model performance. The context pipeline adds relevant code, repo maps, and rules — this should help, not hurt. If HybridCoder performs *worse* than raw Qwen3-8B, the context is confusing the model, not helping it.

### Tier 3: Edit & Refactoring (Phase 4-5)

| Test | Target | Method |
|------|--------|--------|
| Aider-style editing (133 Exercism problems) | >40% first attempt, >75% with retry | Run Aider benchmark suite |
| Multi-file edit success rate | >30% first attempt | 10 custom multi-file scenarios |
| Edit verification (does code compile/pass tests?) | 100% verification runs | Automated compile + test after each edit |
| Rollback safety (can we undo failed edits?) | 100% undoable | Git-based rollback on every failure |

### Tier 4: Agentic Task Completion (Phase 4-5)

| Test | Target | Method |
|------|--------|--------|
| SWE-Bench Verified subset (50-100 issues) | >15% resolved | Run against curated subset |
| Multi-step tool usage chains | >50% complete | 20 custom multi-step scenarios |
| React calculator app (see separate doc) | >60 points / 100 | Full build + evaluation rubric |
| Token efficiency vs naive approach | 60-80% fewer tokens | Compare token logs for same tasks |

### Tier 5: Real-World Stress Tests (Phase 5+)

| Test | Target | Method |
|------|--------|--------|
| Large codebase indexing (10K+ files) | Completes in <60s | Clone Django/Flask, run index |
| Concurrent query handling | No crashes | 10 parallel queries via test harness |
| Memory usage (idle) | <2GB RAM | Monitor with psutil |
| Memory usage (inference) | <8GB VRAM | Monitor with nvidia-smi |
| Cold start time | <5s to first query | Time from launch to ready |
| Index rebuild time (incremental) | <5s for 10 changed files | Modify 10 files, re-index |

---

## 3. Custom Test Suite Design

### Directory Structure

```
tests/benchmark/
  conftest.py                      — Shared fixtures (parser, router, search instances)
  test_deterministic_routing.py    — 50 query classification tests (Tier 0)
  test_l1_latency.py               — Performance benchmarks, <50ms target (Tier 0)
  test_search_relevance.py         — Known-answer search queries (Tier 1)
  test_context_budget.py           — Token budget compliance (Tier 1)
  test_humaneval_subset.py         — 20 HumanEval problems, quick smoke test (Tier 2)
  test_edit_scenarios.py           — 10 edit/refactor scenarios (Tier 3)
  test_project_creation.py         — React calculator app test, automated (Tier 4)
```

### Test File Specifications

#### `test_deterministic_routing.py` — 50 Query Classification Tests

```python
# Categories of test queries:

# DETERMINISTIC_QUERY (should route to L1)
DETERMINISTIC_QUERIES = [
    "list functions in src/hybridcoder/agent/tools.py",
    "show methods in TreeSitterParser",
    "what functions are in core/types.py",
    "find usages of SymbolExtractor",
    "find references to RequestRouter",
    "where is AgentLoop defined",
    "go to definition of create_default_registry",
    "show type of response in handler.py",
    "get signature of parse_file",
    "list imports in agent/loop.py",
    "show classes in layer1/parser.py",
    "what variables are in config.py",
    "find callers of emit_notification",
    "list imports in backend/server.py",
    "list symbols in context.py",
    # ... (25 total)
]

# SEMANTIC_SEARCH (should route to L2 + L4)
SEARCH_QUERIES = [
    "search for approval handling code",
    "find code related to token streaming",
    "look for error handling patterns",
    # ... (10 total)
]

# COMPLEX_TASK / CHAT (should route to L4)
COMPLEX_QUERIES = [
    "how does the agent loop work?",
    "explain the request routing architecture",
    "why did we choose LanceDB over FAISS?",
    "refactor the approval handler to use a state machine",
    "write a test for the backend server",
    "help me debug this error in the parser",
    "what are the tradeoffs of tree-sitter vs LSP?",
    # ... (15 total)
]
```

**Acceptance criterion:** 90%+ of queries classified correctly (45/50 minimum).

#### `test_l1_latency.py` — Performance Benchmarks

```python
# Tests:
# 1. Parse single file: <10ms
# 2. Extract symbols from cached file: <5ms
# 3. Router classification: <1ms
# 4. Full L1 query (router → parse → extract → format): <50ms
# 5. 100 sequential L1 queries: <5s total (50ms avg)
# 6. Cached parse (same file, no changes): <1ms

# Uses pytest-benchmark or manual timing with time.perf_counter_ns()
```

#### `test_search_relevance.py` — Known-Answer Search Queries

```python
# 10 known-answer queries with expected top-3 results:
KNOWN_ANSWER_QUERIES = [
    {
        "query": "approval handling",
        "expected_files": ["approval.py", "update.go", "server.py"],
        "min_precision_at_3": 0.66,  # at least 2/3 correct
    },
    {
        "query": "JSON-RPC protocol",
        "expected_files": ["protocol.go", "backend.go", "server.py"],
        "min_precision_at_3": 0.66,
    },
    # ... (10 total)
]
```

**Acceptance criterion:** precision@3 > 60% across all queries.

#### `test_context_budget.py` — Token Budget Compliance

```python
# 20 queries of varying complexity:
# - Simple (list functions): context should be minimal
# - Medium (search + context): context should use budget
# - Complex (multi-file question): context should approach but not exceed budget
# - Edge case (empty project, no rules file, no index)

# Assert: assembled context is ALWAYS under 5000 tokens (or configured budget)
# Token counting: approximate at 4 chars/token (same heuristic as context assembler)
```

#### `test_humaneval_subset.py` — Quick Smoke Test (20 Problems)

```python
# 20 hand-picked HumanEval problems covering:
# - String manipulation (3)
# - Math/arithmetic (3)
# - List/array operations (4)
# - Control flow (3)
# - Data structures (3)
# - Edge cases (4)

# Run through HybridCoder's L4 agent with context
# Compare: raw Ollama (Qwen3-8B) vs HybridCoder (same model + context)
# Target: HybridCoder >= raw model performance
```

#### `test_edit_scenarios.py` — Edit & Refactor Tests

```python
# 10 edit scenarios with known correct outcomes:
# 1. Add a parameter to an existing function
# 2. Rename a variable across a file
# 3. Extract a function from a code block
# 4. Add error handling to an existing function
# 5. Convert a class to use dataclasses
# 6. Add type annotations to a function
# 7. Fix a simple bug (off-by-one)
# 8. Add a method to an existing class
# 9. Move a function to a different module
# 10. Add a test for an existing function

# Evaluation: does the edit compile? Does it pass tests? Is it correct?
```

#### `test_project_creation.py` — React Calculator App

See `docs/plan/react-calculator-benchmark.md` for full specification. This test automates:

1. Run HybridCoder with the project creation prompt
2. Verify `npm install` succeeds
3. Verify `npm run build` succeeds
4. Run basic Playwright tests for each calculator
5. Score against the 100-point rubric

---

## 4. Metrics & Reporting

### Primary Metrics

| Metric | Target | Test File | Phase |
|--------|--------|-----------|-------|
| L1 classification accuracy | >90% | `test_deterministic_routing.py` | 3 |
| L1 query latency (p95) | <50ms | `test_l1_latency.py` | 3 |
| Search precision@3 | >60% | `test_search_relevance.py` | 3-4 |
| Context budget compliance | 100% under budget | `test_context_budget.py` | 3 |
| HumanEval+ pass@1 | Match raw Qwen3-8B | `test_humaneval_subset.py` | 4 |
| Edit success (first attempt) | >40% | `test_edit_scenarios.py` | 4-5 |
| Edit success (with retry) | >75% | `test_edit_scenarios.py` | 4-5 |
| Project creation score | >60/100 | `test_project_creation.py` | 5-6 |

### Efficiency Metrics (HybridCoder Differentiator)

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Tokens per deterministic query | 0 | Assert in L1 handler |
| Tokens per search-augmented query | <3000 | Log token usage in L4 path |
| % queries handled deterministically | 60-80% | Router classification logs |
| L1 latency vs L4 latency | 100x faster | Compare timings |
| Memory idle | <2GB RAM | psutil monitoring |
| Memory inference | <8GB VRAM | nvidia-smi monitoring |

### Reporting Format

After each phase, generate a benchmark report:

```
# HybridCoder Benchmark Report — Phase X

## Summary
- Total tests: N
- Passing: N (N%)
- Failing: N

## Tier Results
| Tier | Tests | Pass | Fail | Target Met? |
|------|-------|------|------|------------|
| T0   | 50    | 48   | 2    | YES (96%)  |
| T1   | 30    | 25   | 5    | YES (83%)  |
| ...  | ...   | ...  | ...  | ...        |

## Key Metrics
| Metric              | Target  | Actual  | Status |
|---------------------|---------|---------|--------|
| L1 accuracy         | >90%    | 96%     | PASS   |
| L1 latency (p95)    | <50ms   | 12ms    | PASS   |
| Search precision@3  | >60%    | 67%     | PASS   |
| ...                 | ...     | ...     | ...    |

## Token Efficiency
| Query Type     | Avg Tokens | vs Naive | Savings |
|----------------|-----------|----------|---------|
| Deterministic  | 0         | ~2000    | 100%    |
| Search-augmented | 2500    | ~5000    | 50%     |
| Complex/Chat   | 5000     | ~8000    | 37.5%   |

## Regressions
(List any metrics that got worse since last report)

## Action Items
(List fixes needed for failing tests)
```

---

## 5. Competitor Comparison Framework

### Direct Comparisons

#### vs Aider (Open-source, Local, CLI)

Aider is the closest competitor: open-source, CLI-based, supports local models.

| Metric | Aider | HybridCoder | How to Compare |
|--------|-------|-------------|---------------|
| HumanEval pass@1 | Published on leaderboard | Run same benchmark | EvalPlus framework |
| MBPP pass@1 | Published on leaderboard | Run same benchmark | EvalPlus framework |
| Aider Edit benchmark | Published on leaderboard | Run same benchmark | Aider's benchmark suite |
| Tokens per edit | Not published | Measure | Token logging |
| Deterministic query handling | None (all LLM) | 60-80% zero-token | Unique metric |
| Cold start time | ~3-5s | Target <5s | Measure both |
| Memory usage | ~500MB-1GB | Target <2GB | Measure both |

**Key differentiator to highlight:** Tokens per task. Aider sends everything through the LLM. HybridCoder handles 60-80% of queries deterministically. This means:
- Lower cost (for cloud models)
- Lower latency (for local models)
- Works without LLM for structural queries

#### vs Continue.dev (Open-source, IDE Extension)

| Metric | Continue.dev | HybridCoder | Notes |
|--------|-------------|-------------|-------|
| Retrieval accuracy | Embeddings + re-rank | BM25 + vector + RRF | Compare search precision |
| Context quality | @codebase provider | Priority-budgeted context | Compare on same queries |
| Deterministic bypass | None | 60-80% | Unique to HybridCoder |
| Deployment | IDE extension (VS Code) | CLI + Go TUI | Different targets |

**Comparison method:** For retrieval accuracy, run the same known-answer queries through both systems and compare precision@3.

#### vs Claude Code (Cloud, CLI)

| Metric | Claude Code | HybridCoder | Notes |
|--------|-----------|-------------|-------|
| SWE-Bench Verified | ~50%+ resolved | Target >15% | Different model class |
| Privacy | Data sent to cloud | Fully local | Qualitative |
| Cost per task | $0.01-$0.50 | $0 | Quantitative |
| Latency (simple) | 2-5s (network) | <50ms (L1) | Quantitative |
| Model quality | Opus/Sonnet | Qwen3-8B | Different class |

**Note:** Claude Code uses Claude Opus/Sonnet (100B+ parameter cloud models). Direct benchmark comparison is unfair — different resource class entirely. The comparison that matters is:
- **Cost:** $0 vs $0.01-$0.50 per task
- **Privacy:** Fully local vs cloud
- **Latency for structural queries:** <50ms vs 2-5s
- **Token efficiency:** 60-80% savings

#### vs Cursor (Cloud, IDE)

Not directly comparable (different model tier, IDE vs CLI). Include only for market positioning:
- Cursor targets premium developers willing to pay $20/month
- HybridCoder targets developers who want free, private, local-first tooling
- No shared benchmarks — different product categories

### Competitor Comparison Report Template

```
# Competitor Comparison — HybridCoder vs {Competitor}

## Shared Benchmarks
| Benchmark | Competitor | HybridCoder | Delta |
|-----------|-----------|-------------|-------|
| ...       | ...       | ...         | ...   |

## Unique HybridCoder Advantages
| Metric | Value | Competitor Equivalent |
|--------|-------|----------------------|
| Deterministic queries (% zero-token) | 65% | 0% |
| L1 latency | 12ms p95 | N/A (all LLM) |
| Cost per 1000 tasks | $0 | ${X} |

## Areas Where Competitor Excels
| Metric | Competitor | HybridCoder | Notes |
|--------|-----------|-------------|-------|
| ...    | ...       | ...         | ...   |
```

---

## 6. Implementation Timeline

| Phase | Benchmark Tiers | Key Tests | When |
|-------|----------------|-----------|------|
| Phase 3 | Tier 0, Tier 1 | Routing, latency, search, budget | During Phase 3 sprints |
| Phase 4 | Tier 2, Tier 3 | HumanEval, MBPP, Aider edit | After Phase 4 agentic workflow baseline |
| Phase 5 | Tier 4, Tier 5 | SWE-Bench subset, React calculator, stress tests | During polish + benchmarking |

### Phase 3 Benchmark Checklist

- [ ] Create `tests/benchmark/conftest.py` with shared fixtures
- [ ] Implement `test_deterministic_routing.py` (50 queries)
- [ ] Implement `test_l1_latency.py` (performance benchmarks)
- [ ] Implement `test_search_relevance.py` (10 known-answer queries)
- [ ] Implement `test_context_budget.py` (20 budget compliance tests)
- [ ] Run first benchmark report after Sprint 3G
- [ ] Establish baselines for all Tier 0 and Tier 1 metrics

### Phase 4 Benchmark Checklist

- [ ] Set up EvalPlus framework for HumanEval+ / MBPP+
- [ ] Implement `test_humaneval_subset.py` (20 problems)
- [ ] Implement `test_edit_scenarios.py` (10 scenarios)
- [ ] Run Aider Code Editing benchmark (133 problems)
- [ ] Compare raw Qwen3-8B vs HybridCoder on all benchmarks
- [ ] Publish first competitor comparison (vs Aider)

---

## 7. Running Benchmarks

### Quick Run (Tier 0 only, ~30 seconds)

```bash
uv run pytest tests/benchmark/test_deterministic_routing.py tests/benchmark/test_l1_latency.py -v
```

### Full Benchmark Suite (~5 minutes)

```bash
uv run pytest tests/benchmark/ -v --tb=short
```

### With Performance Reporting

```bash
uv run pytest tests/benchmark/ -v --benchmark-json=benchmark_results.json
```

### CI Integration

```yaml
# In CI pipeline (GitHub Actions / local)
- name: Run benchmarks
  run: |
    uv run pytest tests/benchmark/ -v --tb=short
    # Fail CI if Tier 0 metrics drop below targets
```

Benchmark tests should be marked with `@pytest.mark.benchmark` so they can be run separately from unit tests. They should NOT be included in the default `make test` run (they're slower and may require additional setup).

## 8. Before/After Phase 3 Benchmark Protocol

Run benchmark snapshots twice:
- **Before Phase 3 implementation** (baseline)
- **After Phase 3 implementation** (verification)

Use:

```bash
./scripts/run_phase3_benchmark_snapshot.sh before
./scripts/run_phase3_benchmark_snapshot.sh after
```

This generates timestamped reports and raw logs in `docs/qa/phase3-benchmarks/`.

Comparison rule:
- Keep command set identical between before/after runs.
- Compare Tier 0/Tier 1 metrics first (routing, latency, budget, search).
- Treat any regression in deterministic latency or accuracy as release-blocking.

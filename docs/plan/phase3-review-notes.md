# Phase 3 Plan Review Notes

> Reviewer: Claude (Architect) | Date: 2026-02-09
> Document reviewed: `docs/plan/phase3-code-intelligence.md` (~1400 lines)
> Status: Review complete — strengths, concerns, and recommendations below

---

## 1. Strengths

### Comprehensive Sprint Breakdown
The 7-sprint plan (3A-3G) has clear dependencies, deliverables, and test counts per sprint. The dependency graph (`3A → 3B/3C/3D → 3E → 3F → 3G`) enables parallelization of 3B, 3C, and 3D — a genuine time savings if multiple developers (or agents) can work in parallel.

### Well-Defined Exit Criteria
12 measurable exit criteria (Section 9) cover every major component: tool count, router accuracy, latency targets, search quality, token budget compliance, graceful degradation, TUI integration, test counts, and lint pass. Each criterion has a specific test that verifies it.

### Smart Graceful Degradation
The plan doesn't assume perfect conditions. Three independent fallback paths:
- **LSP unavailable** → tree-sitter + grep fallback (Sprint 3C)
- **Embeddings unavailable** → BM25-only search (Sprint 3E)
- **Router uncertain** → defaults to L4 LLM (Sprint 3B)

This means the system works at some level even if multilspy, jina-v2, or the router fails. Real-world resilience.

### Zero-Token Deterministic Routing (Core Differentiator)
Section 2 (Competitor Analysis) correctly identifies that **no major competitor routes deterministic queries away from the LLM**. Aider, Continue.dev, Cursor, and Claude Code all send every query through the language model. The plan's request router (Sprint 3B) is the implementation of HybridCoder's primary competitive advantage.

### Good Risk Mitigation Table
Section 12 identifies 6 concrete risks with mitigations. Each risk has a clear fallback. The "conservative thresholds (default to L4 on ambiguity)" strategy for the router is the right call.

### Clear Module Dependency Graph
Section 4.3 maps every module dependency explicitly. This is invaluable for understanding the build order and for testing in isolation (mock boundaries are obvious).

---

## 2. Concerns

### 2.1 tree-sitter API Version Risk (HIGH)

**The Problem:** The plan specifies `QueryCursor` pattern from tree-sitter 0.25.x (Sprint 3A, line 249):
```python
QueryCursor(query).captures(node)  # returns dict[str, list[Node]]
```

The tree-sitter Python bindings API changed significantly between 0.24 and 0.25:
- 0.24.x: `Query.captures(node)` returns `list[(Node, str)]`
- 0.25.x: `QueryCursor(query).captures(node)` returns `dict[str, list[Node]]`
- `Language()` constructor changed from file-path to capsule-based API

**Risk:** If the exact 0.25.x API is subtly different from what's documented, or if `tree-sitter-python` doesn't ship compatible capsules, Sprint 3A will block everything downstream.

**Recommendation:**
- Pin exact versions in CI: `tree-sitter==0.25.2`, `tree-sitter-python==0.25.0`
- Write a 5-line smoke test as the very first task of Sprint 3A — parse a function, extract a symbol via QueryCursor. If this works, proceed. If not, investigate before writing more code.
- Keep a fallback plan: the old `Query.captures()` API (0.24.x style) still works if we downgrade.

### 2.2 LanceDB Pydantic `LanceModel` Stability (MEDIUM)

**The Problem:** Sprint 3E uses `LanceModel` (Pydantic-based schema):
```python
from lancedb.pydantic import LanceModel, Vector

class CodeChunkRecord(LanceModel):
    vector: Vector(768)
    ...
```

This is a relatively new API in LanceDB (introduced around 0.25-0.29). The older `pa.schema()` (PyArrow) approach is more battle-tested.

**Risk:** If `LanceModel` has bugs or API changes in future versions, the index code breaks.

**Recommendation:**
- Verify `LanceModel` + `Vector(768)` works with the exact version pinned (`>=0.29`). Write an integration test early.
- Keep the PyArrow schema approach as a documented fallback in case `LanceModel` proves unstable.
- Consider pinning to an exact LanceDB version (e.g., `lancedb==0.29.0`) rather than `>=0.29`.

### 2.3 Router Accuracy Claims (MEDIUM)

**The Problem:** The plan claims "60-80% deterministic" classification. The router uses regex + heuristic scoring (Sprint 3B):
```python
score = pattern_score * 0.5 + feature_score * 0.3 + structural_bonus * 0.2
if score > 0.7: → DETERMINISTIC_QUERY
```

**Risk:** Regex + heuristic scoring may misclassify complex queries:
- "What functions in tools.py handle file operations?" — deterministic or semantic?
- "How does the agent loop call tools?" — search or chat?
- "Show me the type of response in context.py" — deterministic or needs code reading?

Ambiguous queries at the threshold (score ~0.5-0.7) will be the most common failure mode.

**Recommendation:**
- The plan already says "default to L4 on ambiguity" (Section 12, router risk), which is correct.
- But also: log every router decision with its score during development. Build a confusion matrix from the 25 test cases + real usage. The 60-80% target should be validated empirically, not assumed.
- Consider adding a "confidence" field to the router response. If confidence is below a threshold, always fall through to L4 even if the score says DETERMINISTIC.

### 2.4 Embedding Model Size and First-Use Latency (LOW-MEDIUM)

**The Problem:** jina-v2-base-code is ~300MB. First search triggers a download (if not cached) and model load, with 2-5 second latency (Sprint 3D, line 531).

**Risk:** Users may think the system is frozen on first search. This is a UX problem, not a technical one.

**Recommendation:**
- Add clear status messaging during first load: "Downloading code search model (300MB, one-time)..." and "Loading search model..."
- Consider offering a CLI command to pre-download: `hybridcoder setup` or `hybridcoder index --download-model`
- The BM25-only fallback is already in the plan — good. But document that BM25-only is the *default* until the user explicitly triggers model download or first search.

### 2.5 multilspy Availability and Windows Stability (LOW-MEDIUM)

**The Problem:** The plan says "multilspy is now available on PyPI as of v0.0.15" (Section 7, line 1296). But:
- v0.0.15 is very early-stage. API may be unstable.
- Windows support for LSP subprocess management may have issues.
- **Critical:** multilspy's Python backend is jedi-language-server, NOT Pyright (see Concern 2.8). All plan references to "Pyright via multilspy" are incorrect.
- The plan correctly makes LSP optional (Sprint 3C is the most "deferrable" sprint).

**Recommendation:**
- Verify `pip install multilspy>=0.0.15` works on Windows before Sprint 3C starts.
- If multilspy is problematic, Sprint 3C can be deferred entirely. Tree-sitter + grep covers ~80% of use cases (definition lookup, symbol listing, import extraction). The only things lost are: cross-file type inference, live diagnostics, and go-to-definition across packages.
- Consider making Sprint 3C a stretch goal rather than a hard requirement.

### 2.6 6000-Token Context Budget Tightness (MEDIUM)

**The Problem:** The context assembler (Sprint 3F) allocates 6000 tokens out of an 8192 context window:
```
Rules:       ~500
Repo map:    ~800
Chunks:     ~2500
File:        ~900
History:    ~1000
Buffer:      ~300
Total:       6000
```

This leaves ~2192 tokens for system prompt + model response. With a typical system prompt (~500 tokens) and the new grounding instructions, that's potentially only ~1500 tokens for the response.

**Risk:** Complex answers (multi-file explanations, code generation) may be truncated. The model may also generate lower-quality responses when it senses its output space is constrained.

**Recommendation:**
- Consider reducing the context budget to **5000 tokens** and allocating the saved 1000 tokens to response space.
- Alternatively, reduce the repo map budget (800 → 500) and rules budget (500 → 300) — these are summaries that can be more compact.
- Make the budget configurable (it already is via `context_budget` config) but lower the default.
- Document the tradeoff: more context = less response room.
- **Important distinction (per Codex Entry 174):** Qwen3-8B natively supports up to
  40960 tokens (`max_position_embeddings` in model config). The 8192 limit is a
  *runtime configuration choice* in our Ollama setup, chosen to keep VRAM usage under
  8GB and maintain acceptable latency. This is a deployment constraint, not a model
  limitation. If users have more VRAM, they could increase `num_ctx` and the context
  budget would no longer be tight. The 5000-token recommendation remains valid for the
  default 8192 runtime config.

### 2.7 Sprint Timeline Aggressiveness (LOW)

**The Problem:** 15-20 days estimated, 10-14 with parallelization (Section 10). This covers:
- 15 new Python files + 5 modified Python + 6 modified Go files
- 157 new Python tests + 5 new Go tests
- 2 new integration test suites
- New dependency setup and validation

**Risk:** The timeline is tight but not unreasonable. The main risk is Sprint 3A (tree-sitter API) blocking everything. If Sprint 3A takes longer than expected due to API issues, the parallel sprints (3B, 3C, 3D) are all blocked.

**Recommendation:**
- Start Sprint 3A as a standalone validation. If the tree-sitter 0.25.x `QueryCursor` API works correctly with the first smoke test, the rest can proceed on schedule.
- Build 1-2 buffer days into the timeline (not in the document, just in practice).

### 2.8 multilspy Python Backend Is Jedi, Not Pyright (HIGH)

**The Problem:** The Phase 3 plan assumes "Pyright via multilspy" in multiple places
(lines 16, 57, 407). However, multilspy's README lists Python support as
`jedi-language-server`, not Pyright. Pyright is not a supported backend.

**Source:** https://github.com/microsoft/multilspy — Python backend is Jedi.

**Risk:** All LSP behavior expectations in the plan (type inference quality,
diagnostic output format, definition resolution) are based on Pyright's capabilities.
Jedi provides different (generally less complete) type inference and diagnostics.
Test plans and fallback semantics may be incorrect.

**Recommendation:**
- Accept Jedi as the LSP backend for Python. Jedi still provides: go-to-definition,
  find-references, hover info, document symbols, and basic diagnostics.
- Update Phase 3 plan to say "Jedi via multilspy" instead of "Pyright via multilspy".
- Adjust type inference expectations downward — Jedi is weaker than Pyright at complex
  type narrowing. This further strengthens the case for tree-sitter fallback (R2).
- If Pyright-level type inference is needed later, investigate using Pyright directly
  via its own LSP transport (not multilspy) as a Phase 5+ enhancement.

**Credit:** Identified by Codex in Entry 174.

---

## 3. Recommendations

### R1: Start with Sprint 3A as a Standalone Validation
Before committing to the full Phase 3 timeline, validate the tree-sitter 0.25.x API in a focused 2-hour spike:
1. `uv add tree-sitter>=0.25.2 tree-sitter-python>=0.25.0`
2. Parse a Python file
3. Run a `QueryCursor` capture query
4. If it works → proceed with full Sprint 3A
5. If it doesn't → investigate API differences, potentially downgrade to 0.24.x pattern

### R2: Consider Deferring Sprint 3C (LSP)
Sprint 3C (LSP via multilspy) is the highest-risk, lowest-reward sprint:
- **Risk:** multilspy is v0.0.15, may be unstable on Windows. Additionally, the Python
  backend is Jedi, not Pyright (see Concern 2.8) — type inference will be weaker than
  the plan assumes.
- **Reward:** Type inference and cross-package definitions (nice-to-have)
- **Without it:** tree-sitter handles symbol extraction, scope chains, and import
  parsing. Grep handles reference finding. This covers 80%+ of deterministic queries.

Recommendation: Make Sprint 3C a post-Phase 3 enhancement. Focus Phase 3 on the core
path (tree-sitter → router → search → context → tools).

**If 3C is deferred, the following Phase 3 deliverables must be re-scoped
(per Codex Entry 174, Concern 2):**

| Deliverable | Current Scope | Re-scoped (without LSP) |
|-------------|--------------|------------------------|
| `get_type_info` tool | LSP hover + AST annotation | AST type annotation only (tree-sitter) |
| `find_definition` tool | LSP + tree-sitter fallback | Tree-sitter + grep only |
| `get_diagnostics` tool | LSP diagnostics | **Deferred entirely** (no tree-sitter equivalent) |
| Exit criterion #6 (LSP degrades gracefully) | Test LSP fallback | **Deferred** (no LSP to degrade) |
| Exit criterion #1 (12 tools) | 6 original + 6 new = 12 | 6 original + 5 new = **11** (no `get_diagnostics`) |
| Tool count in sprint verify test | `assert len(...) == 12` | `assert len(...) == 11` |

### R3: Add a Smoke Test Milestone After Sprint 3B
After Sprint 3A (parser) and Sprint 3B (router), the core deterministic path should work end-to-end:
- User asks "list functions in foo.py"
- Router classifies as DETERMINISTIC_QUERY
- Parser extracts symbols
- Response returned in <50ms with 0 tokens

This is the minimum viable proof of concept. Validate it works before investing in L2 (search, embeddings, indexing). If the router + parser path works, the rest is "just" adding more capabilities. If it doesn't, we need to fix the foundation before building on it.

### R4: Lower Default Context Budget to 5000 Tokens
Reduce from 6000 to 5000 tokens to give the 8192-context Qwen3-8B more breathing room for responses. Specific allocation:
```
Rules:       ~300  (was ~500)
Repo map:    ~600  (was ~800)
Chunks:     ~2200  (was ~2500)
File:        ~800  (was ~900)
History:     ~800  (was ~1000)
Buffer:      ~300  (unchanged)
Total:       5000  (was 6000)
```

This trades 1000 tokens of context for 1000 tokens of response capacity. For a 7B model that generates shorter, more focused responses anyway, the context reduction is acceptable.

### R5: Split Phase 3 Into Gated Sub-Phases (Intellisense-First)

The core product philosophy is **deterministic intelligence first, LLM second**. The
sprint structure should reflect this by validating the classical AI path as a standalone
deliverable before investing in retrieval/LLM integration.

**Phase 3-Alpha: Deterministic Intelligence (Sprints 3A + 3B)**
- Sprint 3A: tree-sitter parser + symbol extraction
- Sprint 3B: request router + deterministic query handlers
- **Gate 1 exit criteria:**
  - "list functions in X.py" returns correct results in <50ms, 0 tokens
  - Router classifies 90%+ of 25 test queries correctly
  - Parser parses all project .py files without errors
- **Why gate here:** This alone proves the core differentiator. If it works,
  HybridCoder can already answer structural queries 100x faster than any competitor,
  at zero cost. Ship this as an early demo.

**Phase 3-Beta: Retrieval Intelligence (Sprints 3D + 3E + 3F)**
- Sprint 3D: AST-aware chunker + embedding engine
- Sprint 3E: LanceDB index + hybrid search
- Sprint 3F: repo map + context assembler
- **Gate 2 exit criteria:**
  - Hybrid search returns relevant results (precision@3 > 60%)
  - Context assembler stays within token budget
  - Index builds in <30s for project-sized codebases
- **Why gate here:** L2 retrieval is independent from L1. If Gate 1 passed but
  Gate 2 fails, the deterministic path still works — users get value while
  retrieval is fixed.

**Phase 3-Gamma: Integration + Polish (Sprint 3G)**
- Wire L1 + L2 into backend server, add tools, update TUI
- **Gate 3 exit criteria:** All Phase 3 exit criteria pass

**Deferred entirely: Sprint 3C (LSP via multilspy)**
- Moved to post-Phase 3 (see R2 and Concern 2.8)
- Jedi-based LSP adds value but is not required for the core product

This 3-gate structure minimizes risk: each gate validates independently, and
failure at any gate doesn't invalidate work from previous gates.

---

## 4. Summary

| Area | Assessment |
|------|-----------|
| Overall plan quality | **Strong** — comprehensive, well-structured, measurable |
| Sprint breakdown | **Needs restructure** — split into 3 gated sub-phases (R5) |
| Risk mitigation | **Good** — graceful degradation, but needs multilspy/Jedi correction (Concern 2.8) |
| Timeline | **Tight but achievable** — gates reduce blast radius of delays |
| Key risk | **tree-sitter 0.25.x API + multilspy is Jedi not Pyright** |
| Biggest opportunity | **Gate 1 (3A+3B) is a shippable demo** of core differentiator |
| Budget concern | **5000 tokens for 8192 runtime config** (model supports 40960) |

**Verdict:** Proceed with Phase 3, starting with Sprint 3A validation spike. Restructure into 3 gated sub-phases (R5). Address concerns during implementation.

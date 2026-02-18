# How to Test Coding Agents: Research & Strategy

> Last updated: 2026-02-18
> Sources: SWE-bench (Princeton), Aider benchmarks, Terminal-Bench (Laude), SWE-PolyBench, SWE-Lancer (OpenAI), SWT-Bench, BaxBench, LiveCodeBench, EvalPlus, MAST taxonomy (UC Berkeley), Codex Entry 500 deep research

---

## 1. The Benchmark Pyramid

No single benchmark is sufficient. A coding agent needs a **pyramid of evaluations** at different levels:

```
                    /\
                   /  \  Tier 6: Security/Adversarial (BaxBench)
                  /    \
                 /------\  Tier 5: Test-Writing Quality (SWT-Bench)
                /        \
               /----------\  Tier 4: Full System Engineering (SWE-Lancer)
              /            \
             /--------------\  Tier 3: Multi-Language (SWE-PolyBench)
            /                \
           /------------------\  Tier 2: Terminal Workflows (Terminal-Bench)
          /                    \
         /----------------------\  Tier 1: Real Repo Issues (SWE-bench Verified)
        /                        \
       /--------------------------\  Foundation: Unit/Format/Edit Tests
```

---

## 2. Industry Benchmarks — Detailed Breakdown

### 2.1 SWE-bench (Primary Issue-Fix Benchmark)

**What it is:** 2,294 real GitHub issues from 12 popular Python repos (Django, Flask, scikit-learn, sympy, etc.). Each task is: given a repo at a specific commit + an issue description, produce a patch.

**Variants:**
| Variant | Tasks | Purpose |
|---------|-------|---------|
| SWE-bench Full | 2,294 | Complete dataset — very noisy |
| SWE-bench Lite | 300 | Curated subset — less noise |
| SWE-bench Verified | 500 | Human-verified solvable — gold standard |

**Evaluation method:** Fully automated. Apply the agent's patch to the repo, run the repo's test suite. Pass = all relevant tests pass. No LLM-as-judge.

**Current scores (2026):**
| Agent | SWE-bench Verified |
|-------|-------------------|
| Claude Code (Claude 4) | ~72% |
| Codex CLI | ~70% |
| Devin | ~55% |
| OpenCode + Claude | ~45% |
| Aider + Claude 3.5 | ~28% |
| Vanilla Qwen3-8B | ~3.4% |

**Can it run locally?** Yes — open source harness at github.com/princeton-nlp/SWE-bench. BUT: requires Docker for sandboxed execution, and running 500 tasks takes hours even with fast models. Each task clones a real repo and runs real tests.

**Relevance for us:** High. Our task bank should follow this format: real repo + issue + expected test outcomes. But we need custom tasks for our specific capabilities (L1/L2 deterministic retrieval, not just LLM patching).

### 2.2 Terminal-Bench

**What it is:** Real terminal workflow tasks with reproducible oracles. Tests the agent's ability to use shell tools, navigate filesystems, run builds, interpret errors.

**Why it matters:** SWE-bench tests code patching only. Terminal-Bench tests the "agent in a shell" reality — setup, build, test, fix loops.

**Relevance for us:** High for Sprint 5B (LLMLOOP) and 5D (CLIBroker). Our agent loop is terminal-based.

### 2.3 SWE-PolyBench

**What it is:** Multi-language variant of SWE-bench covering Python, Java, JavaScript, TypeScript.

**Why it matters:** Avoids Python-only overfitting. Our roadmap claims multi-language L1 (tree-sitter for 5 languages). Need to verify cross-language capability.

**Relevance for us:** Medium now (Phase 5 is Python-first), High for Phase 6 (multi-language LSP).

### 2.4 SWE-Lancer (OpenAI)

**What it is:** Real freelance engineering tasks priced at $50-$2,000+. IC-style (write the code) and manager-style (coordinate and review). Tests full-system engineering, not just patching.

**Why it matters:** Tests whether an agent can do real engineering work, not just apply small patches.

**Relevance for us:** High for Phase 6. Good aspirational target.

### 2.5 SWT-Bench (Test-Writing Quality)

**What it is:** Given a bug report, write a failing test that reproduces the bug. Evaluated by mutation testing — does the test actually catch the bug?

**Why it matters:** Critical for TDD. If we claim TDD, the generated tests must actually catch bugs, not just pass.

**Relevance for us:** Very high — directly validates our TDD workflow.

### 2.6 BaxBench (Security/Adversarial)

**What it is:** Defensive and offensive coding scenarios. Tests if the agent writes secure code, avoids common vulnerabilities, handles adversarial inputs.

**Relevance for us:** Medium. Important for production readiness but not Phase 5 blocking.

### 2.7 LiveCodeBench (Freshness)

**What it is:** Rolling benchmark with new tasks from competitive programming contests. Tasks added after model training cutoffs.

**Why it matters:** Protects against benchmark memorization.

**Relevance for us:** Medium. Our eval harness should include some held-out tasks.

### 2.8 EvalPlus (Test Augmentation)

**What it is:** Takes existing benchmarks (HumanEval, MBPP) and adds hidden, stronger test cases that catch solutions which pass the visible tests but are actually wrong.

**Why it matters:** Catches "teaching to the test" — solutions that pattern-match expected outputs without real understanding.

**Relevance for us:** High for our internal eval harness design.

### 2.9 HumanEval / MBPP (Function-Level)

**What they are:**
- HumanEval: 164 Python function problems with docstrings + test cases
- MBPP: 974 simple Python programming problems

**Limitations:** Too simple for agent evaluation. Tests isolated function completion, not multi-file editing, context retrieval, or tool use. Good for L3/L4 model capability testing, not agent system testing.

---

## 3. How Top Tools Test Their Agents

### 3.1 Aider

Aider has the most transparent testing approach:

**Polyglot Benchmark:** Tests edit format compliance across multiple languages. Runs the agent on standardized edit tasks and measures: (1) format compliance rate (did the agent output valid edit instructions?), (2) patch apply success rate (did the edit apply cleanly?), (3) semantic correctness (did the edit do the right thing?).

**Edit Format Tests:** Aider tests multiple edit formats (whole-file replace, search/replace blocks, unified diff) and measures which format each model handles best. Key finding: smaller models fail dramatically on diff/search-replace formats.

**Refactoring Benchmark:** Rename variables, extract methods, move code between files. All verified by running the original test suite after refactoring.

**Retry Testing:** Measures success rate with 0, 1, 2, 3 retries. Some models go from 20% → 60% with retries.

### 3.2 How We Should Test (Autocode-Specific)

Given our 4-layer architecture, we need layer-specific tests:

**L1 Tests (Deterministic):**
- Given a Python file, find all references to symbol X → verify against gold standard
- Given a function, return its type signature → verify against Jedi output
- Given an import, resolve to file path → verify against filesystem
- Latency: must complete in < 50ms

**L2 Tests (Retrieval):**
- Given a query, return top-K relevant chunks → measure recall/precision/F1 against gold set
- Context budget test: at 2K/8K/16K tokens, measure context quality
- Negative control: provide wrong context, verify system does NOT pass
- Wrong-file test: query about file A, verify file A is in retrieved context

**L3/L4 Tests (Generation):**
- Edit format compliance: does the model output valid edit instructions?
- Patch apply success: does the edit apply cleanly to the target file?
- Semantic correctness: is the edit correct?
- Multi-file coherence: are cross-file changes consistent?

**End-to-End Tests (Full Agent):**
- Fix a known bug in a test repo (SWE-bench style)
- Add a feature to a test repo (greenfield)
- Refactor code while tests pass
- Negative: "this code is already correct" — verify agent doesn't change it

---

## 4. Test Categories for Autocode Task Bank

### 4.1 Deterministic Verification (No LLM-as-Judge)

Every test must have a deterministic oracle:

| Verification Method | What It Checks |
|--------------------|----------------|
| Test suite pass/fail | Behavioral correctness |
| Compilation/import success | Syntactic correctness |
| Ruff/linter clean | Style compliance |
| mypy type check | Type correctness |
| AST diff analysis | Structural correctness |
| Exact string match | Specific output format |
| File existence/content | Artifact generation |
| Exit code | Command success |

### 4.2 Task Difficulty Calibration

| Difficulty | Description | Expected Agent |
|-----------|-------------|---------------|
| **Easy** | Single-file, single-function change. Clear error message. One obvious fix. | L1/L2 (deterministic) |
| **Medium** | Multi-function change in one file. Requires understanding call graph. | L3/L4 (constrained/full) |
| **Hard** | Multi-file change. Requires understanding imports, types, API contracts. | L4 (full reasoning) |
| **Very Hard** | Architectural change. Requires understanding design patterns, testing strategy. | L4 + multiple iterations |

### 4.3 Negative Tests (Agent Should NOT Act)

| Scenario | Expected Behavior |
|----------|------------------|
| Code is already correct | No changes made |
| Documentation question | Answer, don't edit code |
| Out-of-scope request | Refuse or explain limitation |
| Adversarial prompt | Don't execute harmful code |
| Ambiguous requirements | Ask for clarification |

### 4.4 Full System Build Tests

| Task | Verification |
|------|-------------|
| Build a REST API with 3 endpoints + SQLite | All endpoints return correct responses, DB persists |
| Build a CLI tool with 3 subcommands + help text | Commands execute correctly, help text displays |
| Build a data pipeline (read CSV → transform → write JSON) | Output matches gold standard JSON |
| Add authentication to existing API | Protected endpoints reject unauthenticated requests |
| Refactor module into 3 smaller modules | All original tests still pass |

---

## 5. TDD Workflow for Autocode Sprints

### 5.1 The Red-Green-Refactor Cycle for Agent Development

```
1. WRITE FAILING TESTS (Red)
   - Define what the new capability should do
   - Write tests that verify the capability
   - Tests MUST fail at this point (if they pass, the test is wrong)

2. IMPLEMENT (Green)
   - Write the minimum code to make tests pass
   - Don't optimize or beautify yet

3. VERIFY (Refactor)
   - All tests pass
   - Lint clean
   - Type check clean
   - No regressions in existing tests
```

### 5.2 Test-First Sprint Structure

For each sub-sprint:

1. **Present to user:** "Here's what exists now. After this sub-sprint, X will exist."
2. **Get user approval**
3. **Write all TDD tests** — expect 100% failure
4. **Implement** — watch tests go from red to green one by one
5. **Acceptance gate** — all tests green, linter clean, no regressions
6. **Store QA artifacts**

### 5.3 Regression Protection

- Every sub-sprint adds tests to the permanent regression suite
- Before any sub-sprint starts, the full regression suite must pass
- If a new implementation breaks an existing test, fix it before proceeding
- Track test count over time: it should only go up

---

## 6. Recommended Task Bank Composition (>= 30 tasks)

| Category | Count | Examples |
|----------|-------|---------|
| L1 deterministic (symbol lookup, type query, reference finding) | 8-10 | "Find all callers of function X", "What type does Y return?" |
| L2 retrieval (context quality, search relevance) | 6-8 | "Find relevant code for bug report Z", "What files implement feature W?" |
| L3/L4 code generation (edit, refactor, fix) | 8-10 | "Fix this bug", "Add this feature", "Refactor this module" |
| Negative controls (should NOT trigger LLM) | 3-5 | "This code is correct", "What does this function do?" (no edit needed) |
| Full system build | 2-3 | "Build a REST API", "Build a CLI tool" |
| Multi-file coherence | 3-5 | "Rename class X across all files", "Update API contract" |

**Total: >= 30 tasks, each with deterministic oracle.**

---

## 7. Metrics to Track

| Metric | Target | Measured When |
|--------|--------|--------------|
| Task bank pass rate | >= 75% (M1 gate) | Every sprint exit |
| Context F1 | >= 0.65 (M2 gate) | Sprint 5C |
| Single-file p95 latency | <= 60s | Sprint 5C soak test |
| Multi-file p95 latency | <= 300s | Sprint 5C soak test |
| Edit format compliance | >= 90% | Sprint 5B bakeoff |
| Patch apply success | >= 85% | Sprint 5B |
| Token reduction vs naive | >= 30% (M2 gate) | Sprint 5C |
| Routing regret | < 15% | Sprint 5C |
| Cost per resolved task | Track, no gate | Every sprint |

---

## 8. Anti-Gaming Controls

| Control | Purpose |
|---------|---------|
| Hidden test cases | Prevent "teaching to the test" |
| Paraphrased prompts | Same task, different wording — verify consistency |
| Private holdout split | Tasks never seen during development |
| Benchmark freeze hashes | Detect if task bank was modified after lock |
| Negative controls | Verify agent doesn't over-act |

---

## 9. Implementation Plan

### Phase 5 (Current)
- Pre-5A0: Create task bank (>= 30 tasks) with deterministic oracles
- 5A: Eval harness scaffold (run tasks, collect metrics)
- 5B: Edit format compliance + patch apply testing (bakeoff)
- 5C: Full eval suite (context F1, latency, routing regret, cost)

### Phase 6 (Future)
- SWE-bench Verified subset integration
- Terminal-Bench subset
- SWE-PolyBench slices (multi-language)
- Full-system build track (R17)
- Anti-gaming controls (R15)

### Phase 7 (Future)
- Model-specific benchmarking (quantization impact)
- Speculative decoding evaluation
- Fine-tuning evaluation pipeline

---

## 10. Additional Benchmarks — L2 Retrieval & Repo-Level

These benchmarks were identified through deep research and are especially relevant to our 4-layer architecture.

### 10.1 CrossCodeEval (Amazon, NeurIPS 2023)

**What it is:** Tests cross-file code completion — whether models can use context from other files to complete code in the current file. Tasks are identified using static analysis to ensure cross-file context is genuinely required.

**Tasks:** 9,928 across Python (2,665), Java (2,139), TypeScript (3,356), C# (1,768).

**Evaluation settings:**
1. In-File Context only (baseline)
2. Retrieved Cross-File Context (retrieve-and-generate pipeline)
3. Retrieval with Reference (oracle upper bound)

**Relevance for us:** **Very high** — directly evaluates L2 retrieval quality. We can measure how well our chunking + BM25 + vector search pipeline improves completion accuracy vs. in-file-only baseline.

**Can run on 8GB VRAM?** Yes. The evaluation is code completion (next-line prediction).

### 10.2 RepoBench (ICLR 2024)

**What it is:** Repository-level code auto-completion with three interconnected tasks:
1. **RepoBench-R (Retrieval):** Retrieve most relevant code snippets from other files
2. **RepoBench-C (Code Completion):** Predict next line given cross-file + in-file context
3. **RepoBench-P (Pipeline):** End-to-end retrieve + complete

**Languages:** Python and Java. Context levels stratified: 2k, 4k, 8k, 12k, 16k tokens.

**Relevance for us:** **Very high** — RepoBench-R directly evaluates our repo map and search (L2). RepoBench-P tests the L2+L3 pipeline end-to-end.

### 10.3 BigCodeBench (ICLR 2025)

**What it is:** 1,140 programming tasks covering 723 function calls from 139 libraries across 7 domains. Average 5.6 test cases per task with 99% branch coverage.

**Relevance for us:** High for evaluating L3 constrained generation. More realistic than HumanEval — tests complex, multi-library function generation.

### 10.4 RefactorBench (ICLR 2025)

**What it is:** 100 large, handcrafted multi-file refactoring tasks. Each task has 3 natural language instructions of varying specificity.

**Key result:** LM agents solve only 22% (vs. 87% for human developers). State-aware agents improve to ~31.7%.

**Relevance for us:** Medium — validates multi-file coherence. Relevant for Phase 6.

### 10.5 SWE-bench Pro (Scale AI, 2025)

**What it is:** 1,865 harder problems from 41 repos. Gold patches span avg 107.4 lines across 4.1 files. Best agents score below 45%.

**Relevance for us:** Aspirational. Good Phase 6+ target after SWE-bench Verified subset.

### 10.6 SWE-EVO (December 2025)

**What it is:** Long-horizon software evolution — maintaining codebases across versions. 48 tasks, gold patches span avg 20.9 files. Even GPT-5 + OpenHands achieves only 21%.

**Relevance for us:** Phase 7 aspirational target.

---

## 11. 8GB VRAM Reality Check

| Benchmark | Expected 8B Model Score | Notes |
|-----------|------------------------|-------|
| SWE-bench Verified | ~3-10% | Qwen3-8B scores ~9.8% (thinking mode) |
| Aider Polyglot | ~10-25% | On hardest 225 tasks |
| HumanEval | ~50-70% | Depends on quantization |
| BigCodeBench | ~15-30% | Complex library usage is hard for 8B |
| CrossCodeEval | TBD | Retrieval quality matters more than model size here |
| RepoBench-R | TBD | L2 retrieval is deterministic — model size irrelevant |

**Key insight:** For HybridCoder's architecture, L1/L2 benchmark performance (CrossCodeEval, RepoBench-R) is model-size-independent — it's about retrieval quality, not generation. This is where our deterministic-first approach has the biggest advantage. L3/L4 benchmarks will be limited by the 8B model, but our architecture compensates by feeding high-quality context from L1/L2.

---

## 12. How Top Tools Test Internally

| Tool | Primary Benchmark | Internal Eval | Open Source Eval? |
|------|------------------|---------------|-------------------|
| Claude Code | SWE-bench Verified | Minimal scaffold design, safety evals (98.7% safety score) | Partial |
| Codex | SWE-bench Pro, Terminal-Bench | Internal SWE task bank (Python/Go/OCaml), 192k context | No |
| Aider | Polyglot, Refactoring, Edit Format | All 3 benchmarks are public | Yes (fully) |
| Cursor | Production metrics | Custom completion model + RAG pipeline | No |
| OpenCode | OpenCode-Bench | From-commit/to-commit pairs, weighted scoring | Partial |

---

## 13. TDD Patterns for Coding Agent Development

### 13.1 Edit Format Testing — Layered Match Chain

Aider's most critical finding: disabling flexible patching causes a **9x increase in editing errors**. The edit application layer needs a fallback chain:

1. **Exact match** — Try exact string match first
2. **Whitespace-normalized match** — Strip leading/trailing whitespace
3. **Fuzzy match** — Use `difflib.SequenceMatcher` to find closest matching block

**Test pattern:** Test each layer independently, then test the chain end-to-end. Also test that edited files remain valid Python (`compile(result, "<test>", "exec")`).

**Key finding:** Format choice alone swings success from 26% to 59% with the same model. Standard unified diff is the worst-performing format for nearly all models.

### 13.2 The Graduation Pattern (Anthropic)

Capability evals with high pass rates "graduate" to become regression tests:

```
Capability eval (60% pass) → improve → (85% pass) → improve → (98% pass)
                                                                    ↓
                                                          Graduate to regression suite
                                                          (must stay >= 95%)
```

- **Capability eval**: "Can we do this at all?" — target: improve over time
- **Regression test**: "Can we still do this reliably?" — target: ~100% pass rate

### 13.3 Pass@k vs Pass^k

- **Pass@k**: Probability at least 1 of k attempts succeeds (capability ceiling)
- **Pass^k**: Probability ALL k attempts succeed (reliability measure)
- At k=10, pass@k can approach 100% while pass^k falls near zero
- Report both for non-deterministic evaluations

### 13.4 ContextBench (February 2026)

Most rigorous context retrieval benchmark: 1,136 tasks from 66 repos across 8 languages, with 522,115 lines of human-verified gold contexts.

Metrics at three granularities:
- **File-level**: Did the agent look at the right files?
- **Block-level**: Did it find the right classes/functions? (AST blocks)
- **Line-level**: Did it read the exact relevant lines?

Key finding: Higher recall does NOT mean better performance. GPT-5 achieves higher recall but sacrifices precision (retrieves too much irrelevant context), leading to lower F1.

### 13.5 Negative Testing Patterns

| Pattern | What to verify |
|---------|---------------|
| Code is already correct | Agent makes 0 edits |
| Documentation question | Agent answers, doesn't modify files |
| Don't delete tests | Test count must not decrease after agent runs |
| Refuse harmful actions | No destructive git ops, no secret exposure |
| Layer routing | Chat messages don't trigger edit operations |

### 13.6 Multi-Turn Conversation Testing

Zendesk ALMA benchmark (1,420 conversations) found conversation correctness fell to **14.1% for GPT-4o** in multi-turn, noisy dialogues. Models handle individual tool calls well but fail with clarifications and interruptions.

### 13.7 Gap Analysis — Current Suite vs Best Practice

| Pattern | Our Status | Gap |
|---------|-----------|-----|
| Latency gates | `test_l1_latency.py` (<50ms) | Add P95/P99 per layer |
| Search precision | `test_search_relevance.py` (precision@3) | Add block-level recall + F1 |
| Routing accuracy | `test_deterministic_routing.py` (50 queries) | Scale up query corpus |
| Edit application | Not yet | Build layered match test suite |
| Negative tests | Routing negatives exist | Add no-action + don't-delete-tests |
| Multi-turn | Not yet | Design multi-turn scenarios |
| Regression graduation | Not yet | Implement graduation pattern |
| Cost tracking | Token assertions exist | Add per-layer budgets |
| Non-determinism | Not yet | Add Pass@k + Pass^k statistical runs |

---

## 14. Deterministic Verification Stack (8 Layers)

For every agent task, apply this verification pipeline (no human review needed):

| Layer | Check | Tool | Pass Criteria |
|-------|-------|------|---------------|
| 1 | Syntax valid | `py_compile`, tree-sitter | Zero parse errors |
| 2 | Type correct | mypy --strict | Zero new type errors vs baseline |
| 3 | Lint clean | ruff check | No new violations |
| 4 | Tests pass | pytest | All pass, zero regressions |
| 5 | Behavioral equivalence | Hypothesis property tests | f_old(x) == f_new(x) for random inputs |
| 6 | AST structural analysis | tree-sitter diff | Expected transformations confirmed |
| 7 | Property-based testing | Hypothesis/QuickCheck | Generated code satisfies invariants |
| 8 | Regression detection | Full benchmark suite | regression_rate == 0 |

---

## 15. Implementable Test Designs (Priority Order)

### Tier 1 — Build immediately (pre-5A0)
1. **Deterministic verification stack** (Layers 1-4 above) — extend existing infrastructure
2. **Bug detection benchmark** — Plant 50 bugs in clean code, measure precision/recall
3. **Multi-file coherence tests** — 10 tasks at varying file counts, verified by mypy + pytest

### Tier 2 — Build next (Sprint 5A-5B)
4. **Refactoring tests** — Generate 20-30 tasks from own codebase using tree-sitter
5. **Task difficulty calibration** — Run tasks through multiple models, establish difficulty tiers
6. **Performance-under-constraint tests** — Context budget degradation curves

### Tier 3 — Build as evaluation matures (Sprint 5C)
7. **Full system building tests** — REST API + CLI tool + data pipeline (3 types minimum)
8. **Adversarial tests** — 20 adversarial variants, measure robustness ratio
9. **Longitudinal soak tests** — Append-only results log, nightly runs, 100+ tasks

### Tier 4 — Adopt from ecosystem (Phase 6)
10. **SWE-bench Lite** — Run locally with Docker, instant field comparison

---

## 16. Adversarial Test Categories

| Category | Example | What it tests |
|----------|---------|--------------|
| Misleading variable names | `min_value = max(values)` | Semantic reasoning vs name-matching |
| Red herring comments | Comment says "ascending", code reverses | Code reading vs comment trust |
| Copy-paste bugs | Identical blocks with subtle error in one | Attention to detail |
| Type confusion | Works for int/float, fails for Decimal | Edge case reasoning |
| Domain knowledge | Timezone DST transitions, IEEE 754 floats | Beyond pattern matching |

---

## 17. Soak Test Protocol

For longitudinal evaluation across agent versions:

```
Task corpus: 100-500 tasks (40% easy, 30% medium, 20% hard, 10% expert)
Per cycle: Run each task K times (K >= 3)
Metrics: pass@1, pass@3, pass^3, p50/p90/p99 time, token efficiency
Storage: Append-only log (CSV/SQLite/LanceDB)
Regression alert: Any category drops > 5% absolute
Capability cliff: Plot pass rate vs difficulty — sharp drop = concern
```

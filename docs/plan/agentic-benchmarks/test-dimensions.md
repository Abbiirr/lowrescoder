# Test Dimensions: 12 Ways to Measure Agent Quality

Each dimension is independent. A good agent excels across all 12; a bad one may ace some and fail others. Testing all 12 gives a multidimensional agent quality profile.

---

## Dimension 1: Tool Routing Accuracy

**Question:** Does the agent pick the right tool for the task?

**Why it's agent-specific:** The model generates intent; the agent maps intent to tool calls. Two agents with the same model can make dramatically different tool choices.

**Test pattern:**
- Present a task solvable with `grep` and measure if agent uses `grep` vs reading all files
- Present a task requiring `tree-sitter` parse and measure if agent invokes L1 vs L4
- Count total tool calls and compare to optimal baseline (human-annotated minimum)

**Metrics:**
- Tool call count vs optimal baseline (ratio, lower = better)
- Tool selection precision (% of calls that were necessary)
- Unnecessary call rate (% of calls whose results were unused)

**Concrete scenarios:**
| Scenario | Optimal Path | Bad Agent Path |
|----------|-------------|---------------|
| Find all usages of `processOrder()` | 1 grep call | Read 30 files sequentially |
| Rename variable in 3 files | 3 targeted edits | Read entire codebase, edit all files |
| Check if function exists | 1 grep or AST query | Read file, parse mentally, answer |

**HybridCoder relevance:** L1/L2 should handle simple tasks without invoking L3/L4. Measure the layer that resolves each task.

---

## Dimension 2: Context Retrieval Quality

**Question:** Does the agent find the right code before making changes?

**Why it's agent-specific:** The agent's retrieval strategy determines what context the model sees. Bad retrieval = bad patches, regardless of model quality. ContextBench showed retrieval quality is separable from patch quality.

**Test pattern:**
- Define "gold contexts" — the minimal set of files/functions needed for a task
- Measure what the agent actually retrieves vs the gold standard
- Score at three granularities: file, AST block, line

**Metrics:**
- File-level recall: What % of needed files were retrieved?
- Block-level precision: What % of retrieved code was relevant?
- Line-level F1: Combined precision + recall at the line level
- Wasted context ratio: Tokens of irrelevant context / total context tokens

**Concrete scenarios:**
| Scenario | Gold Context | Measured |
|----------|-------------|---------|
| Fix bug in `auth.py:verify_token()` | `auth.py`, `config.py` (2 files) | Did agent read exactly these? |
| Add field to data model | Model file + 3 consumers + migration | Did agent find all 5 files? |
| Resolve import error | The importing file + the missing module | Did agent read the error trace first? |

**HybridCoder relevance:** L2 (retrieval layer) is designed for this. Measure BM25 + vector search recall vs naive sequential reading.

---

## Dimension 3: Edit Accuracy

**Question:** Are the agent's file edits syntactically correct and properly applied?

**Why it's agent-specific:** The model proposes changes; the agent's edit layer translates them into file operations. EDIT-Bench showed only 1 of 40 models scored above 60% — and the edit format matters as much as the code quality.

**Test pattern:**
- Given a model-generated intent, apply the edit and check:
  - Does the file parse to valid AST after edit?
  - Is indentation preserved (critical for Python)?
  - Are surrounding lines unmodified?
  - Does the edit apply cleanly (no fuzzy matching needed)?

**Metrics:**
- Application success rate (% of edits that apply without intervention)
- Post-edit AST validity (% of modified files that parse)
- Indentation correctness (Python/YAML specific)
- Function-level precision (% of edits that modify the correct function)

**Concrete scenarios:**
- Edit a function in a 500-line Python file — verify only that function changed
- Add a method to a class — verify indentation matches class context
- Modify a deeply nested JSON config — verify structure preserved
- Apply edit after file has been modified by another tool — state drift handling

**HybridCoder relevance:** L3 constrained generation with Outlines grammar should produce structurally valid edits. Measure grammar-constrained vs unconstrained edit quality.

---

## Dimension 4: Error Recovery (Self-Correction)

**Question:** When the first attempt fails, does the agent diagnose and fix it?

**Why it's agent-specific:** Recovery-Bench proved this is **orthogonal** to raw coding ability. The best first-attempt coder is NOT the best recoverer. This is purely about the agent's feedback loop.

**Test pattern (Aider two-attempt):**
1. Agent attempts task
2. Run tests → failure
3. Feed test output back to agent
4. Agent attempts fix
5. Score: Did attempt 2 fix what attempt 1 broke?

**Metrics:**
- Pass-after-retry rate (% of initially-failing tasks fixed on second attempt)
- Error diagnosis accuracy (did it identify the correct root cause?)
- Fix specificity (did it change only what needed changing, or shotgun-edit?)
- Loop detection (does it detect when stuck and try a different approach?)

**Concrete scenarios:**
- First attempt produces code with import error → does agent add the import?
- First attempt passes some tests, fails others → does agent fix only the failures?
- First attempt produces syntax error → does agent fix the syntax without losing logic?
- Three consecutive failures → does agent try a fundamentally different approach?

**HybridCoder relevance:** L1 can diagnose syntax errors deterministically (tree-sitter). L2 can find the missing import via AST analysis. Test whether the agent routes recovery through L1-L2 before burning L4 tokens.

---

## Dimension 5: Fault Tolerance

**Question:** Does the agent degrade gracefully when tools fail?

**Why it's agent-specific:** ReliabilityBench showed that fault injection reveals agent fragility invisible in normal conditions. Simpler architectures (ReAct) outperform complex ones (Reflexion) under faults.

**Test pattern (chaos engineering):**
- Inject faults at configurable probability:
  - `TransientTimeout`: Tool call times out, succeeds on retry
  - `ConnectionReset`: Connection drops mid-response
  - `SoftRateLimit`: 429 with retry-after header
  - `HardRateLimit`: 429 with no recovery
  - `PartialResponse`: Truncated tool output
  - `SchemaDrift`: Tool returns unexpected format
  - `EmptyResponse`: Tool returns nothing

**Metrics:**
- Degradation curve: Performance at 0%, 10%, 20%, 30% fault rate
- Recovery rate per fault type
- Graceful degradation: Does performance drop linearly or cliff-edge?
- Timeout handling: Does the agent respect timeouts or hang?

**HybridCoder relevance:** Test each layer boundary:
- What happens when tree-sitter fails to parse? (L1 → L2 fallback)
- What happens when LanceDB returns no results? (L2 → L3 fallback)
- What happens when Ollama returns malformed JSON? (L4 retry/degrade)

---

## Dimension 6: Multi-File Coordination

**Question:** Can the agent modify multiple related files consistently?

**Why it's agent-specific:** The model generates patches for individual files; the agent coordinates across files. SWE-bench Pro showed resolve rates drop from ~60% (1-2 files) to ~44% (10+ files).

**Test pattern:**
- Task requires modifying N interdependent files (interface + implementations, model + migration + tests)
- Score: Are ALL files updated consistently?
- Check: Does renaming a function update ALL call sites?

**Metrics:**
- Cross-file consistency rate (% of multi-file tasks with all files correct)
- Files-touched accuracy (did agent modify the right set of files?)
- Regression rate on untouched files (P2P from FeatBench)

**Concrete scenarios:**
| Files | Task | Consistency Check |
|-------|------|-------------------|
| 3 | Rename function across module | All call sites updated? |
| 5 | Add field to data model + API + tests + migration + docs | All 5 consistent? |
| 2 | Fix bug in module A that requires change in module B | Both changed correctly? |

---

## Dimension 7: Context Scaling

**Question:** Does the agent handle large codebases without degrading?

**Why it's agent-specific:** LoCoBench-Agent tested context lengths from 10K to 1M tokens and found "strategic tool usage patterns differentiate high-performing agents." At scale, brute-force reading fails — the agent MUST be strategic.

**Test pattern:**
- Same task type at increasing codebase sizes
- Measure performance retention: if 90% at 10K tokens, what at 100K? 1M?

**Metrics:**
- Performance retention % at 10x and 100x scale
- Tool calls per task at each scale (should stay roughly constant)
- Tokens consumed per task at each scale

**HybridCoder relevance:** L2's BM25 + vector search should maintain performance at scale. L1's tree-sitter/LSP doesn't care about codebase size — it indexes. Test that HybridCoder's retrieval doesn't degrade.

---

## Dimension 8: Planning Quality

**Question:** Does the agent decompose complex tasks into correct step sequences?

**Why it's agent-specific:** The model generates intent; the agent decides step ordering and when to replan. Terminal-Bench found that coherence errors (premature termination, reasoning-action mismatches) are a top failure mode.

**Test pattern:**
- Tasks with known dependency chains (must create schema before inserting data)
- Score step ordering against valid topological orders
- Inject failure at step N → does the agent revise remaining steps?

**Metrics:**
- Step order correctness (% of tasks with valid execution order)
- Plan adaptation rate (% of plans revised after mid-task failure)
- Completion rate at N-step depth (how far into a multi-step task?)

---

## Dimension 9: Recovery from Corruption

**Question:** Can the agent fix a state left broken by a previous failed attempt?

**Why it's agent-specific:** Recovery-Bench showed this is the most orthogonal dimension — no correlation with fresh-state ability. A completely different agent capability.

**Test pattern:**
- Run agent attempt 1 → partial failure (half-applied edits, broken imports)
- Start agent attempt 2 from the corrupted state
- Score: Does attempt 2 succeed?

**Metrics:**
- Recovery rate (% of corrupted states successfully recovered)
- Context pollution resistance (does providing error history help or hurt?)
- Diagnostic accuracy (does the agent correctly identify what went wrong?)

**HybridCoder relevance:** L1 can detect syntax errors in the corrupted state. L2 can identify broken imports. The deterministic layers should provide a major advantage over pure-LLM recovery.

---

## Dimension 10: Regression Prevention

**Question:** Does the agent avoid breaking existing functionality while adding new code?

**Why it's agent-specific:** FeatBench introduced Pass-to-Pass (P2P) tests: existing tests that MUST continue passing after the agent makes changes. Many agents fix the target but break something else.

**Test pattern:**
- Task: Add feature X to a project with 20 existing tests
- Run existing tests BEFORE agent changes (baseline: all pass)
- Run existing tests AFTER agent changes
- Score: How many existing tests still pass?

**Metrics:**
- P2P pass rate (% of existing tests still passing)
- Regression density (regressions per lines changed)
- Collateral damage score (files broken that weren't modified)

---

## Dimension 11: Consistency (pass^k)

**Question:** Does the agent produce the same result every time?

**Why it's agent-specific:** tau-bench showed pass^k (ALL k runs succeed) decays exponentially for LLM-dependent agents. Deterministic agent layers should resist this decay.

**Test pattern:**
- Run the same task k times (k=5)
- Compute pass^k = p^k
- Compare against theoretical exponential decay

**Metrics:**
- pass^1: Single-run success rate
- pass^5: All-5-runs success rate
- Decay rate: pass^5 / pass^1 (1.0 = perfectly consistent)
- Deterministic layer contribution: What % of agent actions are deterministic?

**HybridCoder relevance:** If L1-L2 resolve a task deterministically, pass^k = pass^1 for that task. The more work done in deterministic layers, the higher pass^k.

---

## Dimension 12: Cost Efficiency

**Question:** How many tokens does the agent spend per resolved task?

**Why it's agent-specific:** Two agents both at 80% pass rate — one uses 2K tokens/task, the other 20K. The efficient one is 10x better for edge deployment.

**Test pattern:**
- Track total input + output tokens per task
- Track tool call count per task
- Compare against a naive single-prompt baseline

**Metrics:**
- Tokens per resolved task (lower is better)
- Tool calls per resolved task
- Zero-token resolution rate (% of tasks resolved by L1-L2 without LLM)
- Cost at equivalent resolve rate ($/task)

**HybridCoder relevance:** This is THE metric for the "LLM as last resort" philosophy. If 30% of tasks resolve at zero LLM tokens via tree-sitter/LSP, that's a 30% cost reduction vs any LLM-first agent.

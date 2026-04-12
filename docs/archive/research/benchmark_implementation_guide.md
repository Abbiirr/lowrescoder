# HybridCoder Benchmark Implementation Guide

**Quick Reference:** Best patterns from 2026 research for implementing a lightweight local benchmark suite

---

## Overview

This guide distills the 2026 benchmark research into actionable patterns for HybridCoder Phase 6. The goal is a **lightweight, local, fast** benchmark suite that measures what matters for our deterministic-first architecture.

**Full research:** See `benchmark_research_2026.md` (40+ pages)

---

## 1. Core Benchmark Categories (Priority Order)

### A. Edit Efficiency (HIGHEST PRIORITY)
**Why:** Direct measure of our core capability - targeted code changes
**Inspired by:** Aider Polyglot Benchmark
**Metrics:**
- Precision: Changed lines that needed changing / Total changed lines
- Recall: Changed lines that needed changing / Lines that should change
- Diff size ratio: Agent's diff / Minimal diff
- Whole-file rewrites: Count (should be 0)

**Implementation pattern:**
```python
def test_targeted_edit(agent, tmp_path):
    # Setup: Create file with known bug
    file_path = tmp_path / "buggy.py"
    file_path.write_text(BUGGY_CODE)

    # Task: Fix specific bug
    result = agent.edit_file(file_path, "Fix bug: multiply by quantity")

    # Assert: Only changed necessary lines
    assert result.lines_changed <= 2
    assert "quantity" in result.new_content
    assert run_tests(file_path).passed
```

**Test case sources:**
- Start with 10 synthetic bugs (off-by-one, null check, etc.)
- Add 5 cases from real git history
- Target: 15-20 cases, ~3 min runtime

### B. Search Accuracy
**Why:** Layer 2 retrieval is critical for multi-file tasks
**Inspired by:** RepoBench-R
**Metrics:**
- Accuracy@K: Is target file in top-K results? (K=1,3,5,10)
- Mean Reciprocal Rank (MRR)
- Search latency (ms)

**Implementation pattern:**
```python
CASES = [
    {
        "query": "authentication logic",
        "ground_truth": ["src/auth/authenticator.py", "src/auth/session.py"],
        "repo_size": 150
    }
]

def test_search_accuracy(agent, synthetic_repo, case):
    results = agent.search_text(case["query"], top_k=10)

    found = [f for f in case["ground_truth"] if f in results]
    accuracy = len(found) / len(case["ground_truth"])

    assert accuracy >= 0.8  # 80% of relevant files in top-10
```

**Test case sources:**
- Create synthetic repo with 50-200 files
- Hide 10 "needles" (specific functions/classes)
- Provide natural language queries
- Target: 20-25 cases, <1 min runtime

### C. Bug Localization
**Why:** Measures agent's ability to find where to edit
**Inspired by:** SWE-bench task structure
**Metrics:**
- File correct: Did agent identify the right file?
- Line within range: Is reported line within ±5 of actual bug?
- Search efficiency: How many queries/file reads?

**Implementation pattern:**
```python
def test_bug_localization(agent, isolated_repo, case):
    result = agent.find_bug(
        repo=isolated_repo,
        description=case.problem_statement
    )

    assert result.file == case.ground_truth_file
    assert abs(result.line - case.ground_truth_line) <= 5
    assert len(result.tool_calls) <= 10  # Efficiency check
```

**Test case sources:**
- Inject 5-10 synthetic bugs into small codebases
- Use bug types: logic error, null check, off-by-one, type mismatch
- Target: 10-15 cases, ~2 min runtime

### D. Task Completion
**Why:** End-to-end validation of full agent workflow
**Inspired by:** SWE-bench pass/fail structure
**Metrics:**
- Success rate (first attempt)
- Success rate (with retry, ≤3 attempts)
- Tool call count
- Total tokens (L3 + L4)

**Implementation pattern:**
```python
def test_task_completion(agent, task):
    # Setup: Create environment with failing test
    setup_task_environment(task)

    # Execute: Agent attempts to complete task
    result = agent.solve(task.description)

    # Verify: Run tests
    test_result = run_tests(task.test_file)

    assert test_result.passed
    assert result.tool_calls <= 20  # Reasonable efficiency
```

**Test case sources:**
- 5 "implement missing function" (guided by tests)
- 3 "fix failing test"
- 2 "small refactoring"
- Target: 10 cases, ~5 min runtime (LLM calls)

### E. Layer Efficiency (UNIQUE TO HYBRIDCODER)
**Why:** Proves our deterministic-first value proposition
**No prior art:** This is our innovation
**Metrics:**
- Layer distribution: % tasks at L1/L2/L3/L4
- Token reduction: HybridCoder / Baseline
- Latency improvement: HybridCoder / Baseline

**Implementation pattern:**
```python
def test_layer_efficiency(benchmark_suite):
    hc_metrics = []
    baseline_metrics = []

    for case in benchmark_suite:
        # HybridCoder (deterministic-first)
        with track_metrics() as hc_track:
            hc_result = hybridcoder.solve(case)
        hc_metrics.append(hc_track.metrics)

        # Baseline (naive LLM-first)
        with track_metrics() as bl_track:
            bl_result = naive_agent.solve(case)
        baseline_metrics.append(bl_track.metrics)

    # Compare
    hc_tokens = sum(m.total_tokens for m in hc_metrics)
    bl_tokens = sum(m.total_tokens for m in baseline_metrics)
    reduction = 1 - (hc_tokens / bl_tokens)

    assert reduction >= 0.60  # 60% token reduction target
```

**Test case sources:**
- 10 L1 tasks: list files, find definition, check syntax
- 5 L2 tasks: semantic search, context retrieval
- 5 L3 tasks: simple completion, structured output
- 5 L4 tasks: complex refactoring, multi-file edits
- Target: 25 cases, ~8 min runtime

---

## 2. File Structure (Proposed)

```
tests/benchmark/
├── README.md                           # Benchmark docs
├── conftest.py                         # Shared fixtures
├── metrics.py                          # MetricsCollector class
├── cases/                              # Test case definitions
│   ├── edit_accuracy/
│   │   ├── case_001_off_by_one.json
│   │   ├── case_002_null_check.json
│   │   └── fixtures/
│   │       ├── buggy_calculator.py
│   │       └── test_calculator.py
│   ├── search_retrieval/
│   │   ├── queries.json
│   │   └── synthetic_repo_50_files/
│   ├── bug_localization/
│   │   └── cases.json
│   ├── task_completion/
│   │   └── tasks.json
│   └── layer_efficiency/
│       └── layered_tasks.json
├── test_edit_efficiency.py             # 15-20 tests, ~3 min
├── test_search_accuracy.py             # 20-25 tests, <1 min
├── test_bug_localization.py            # 10-15 tests, ~2 min
├── test_task_completion.py             # 10 tests, ~5 min
└── test_layer_efficiency.py            # 25 tests, ~8 min
```

**Total:** 80-95 test cases, ~19 min runtime

---

## 3. Key Implementation Patterns

### Pattern 1: JSON Test Case Definitions

**Why:** Easy to add new cases without changing code

```json
{
  "id": "edit_001",
  "name": "off_by_one_array_index",
  "difficulty": "easy",
  "buggy_code": "def get_last(items):\n    return items[len(items)]\n",
  "instruction": "Fix the off-by-one error",
  "expected_fix": "return items[len(items) - 1]",
  "ground_truth_lines_changed": 1,
  "test_code": "assert get_last([1,2,3]) == 3"
}
```

### Pattern 2: Isolated Test Environments

**Why:** Tests don't interfere with each other

```python
@pytest.fixture
def isolated_repo(tmp_path, benchmark_case):
    """Create fresh repo for each test."""
    repo = tmp_path / "test_repo"
    benchmark_case.setup_files(repo)
    return repo
```

### Pattern 3: Metrics Collection

**Why:** Track performance over time, detect regressions

```python
@dataclass
class BenchmarkMetrics:
    task_id: str
    success: bool
    layer_used: int
    tokens_l3: int
    tokens_l4: int
    latency_ms: int
    tool_calls: List[str]
    diff_size: int

class MetricsCollector:
    def record(self, metrics: BenchmarkMetrics): ...
    def summary(self) -> Dict: ...
    def export_csv(self, path: Path): ...
```

### Pattern 4: Baseline Comparison

**Why:** Prove HybridCoder is better than naive approach

```python
def test_vs_baseline(benchmark_suite):
    hc_results = [hybridcoder.solve(c) for c in benchmark_suite]
    bl_results = [naive_agent.solve(c) for c in benchmark_suite]

    hc_tokens = sum(r.tokens for r in hc_results)
    bl_tokens = sum(r.tokens for r in bl_results)

    reduction = 1 - (hc_tokens / bl_tokens)
    assert reduction >= 0.60
```

### Pattern 5: Regression Tracking

**Why:** Ensure scores don't degrade over time

```python
def test_regression():
    current = run_full_benchmark()

    with open("historical_best.json") as f:
        best = json.load(f)

    # Allow 5% degradation
    for metric in ["success_rate", "token_efficiency"]:
        assert current[metric] >= best[metric] * 0.95

    # Update if improved
    if current["success_rate"] > best["success_rate"]:
        save_new_best(current)
```

---

## 4. Test Case Generation Strategies

### Strategy 1: Synthetic Bug Injection

**Best for:** Edit efficiency, bug localization

```python
def generate_synthetic_bug_case():
    """Create test case by injecting known bug."""
    working_code = load_working_code()
    bug_type = random.choice(["off_by_one", "null_check", "logic_error"])

    buggy_code = inject_bug(working_code, bug_type)
    test_code = create_test_that_catches_bug(bug_type)

    return BenchmarkCase(
        buggy_code=buggy_code,
        test_code=test_code,
        ground_truth_fix=working_code,
    )
```

### Strategy 2: Real Git History Mining

**Best for:** Task completion, bug localization

```python
def generate_from_git_history(repo_path: Path, bug_commit: str):
    """Extract test case from real bug fix."""
    repo = git.Repo(repo_path)

    commit = repo.commit(bug_commit)
    parent = commit.parents[0]
    diff = commit.diff(parent)

    return BenchmarkCase(
        problem_statement=commit.message,
        base_files=export_files_at(parent),
        ground_truth_diff=diff,
        ground_truth_files=[f.a_path for f in diff],
    )
```

### Strategy 3: Synthetic Codebase Generation

**Best for:** Search accuracy

```python
def generate_synthetic_repo(num_files=100):
    """Create repo with known structure for search testing."""
    repo = {}

    # Create directory structure
    for pkg in ["auth", "api", "db", "utils"]:
        for i in range(num_files // 4):
            file_name = f"{pkg}/module_{i}.py"
            repo[file_name] = generate_python_module(pkg, i)

    # Hide specific "needles" (functions/classes)
    needles = [
        ("auth/authenticator.py", "def verify_token(token: str):"),
        ("db/connection.py", "class DatabasePool:"),
    ]

    return repo, needles
```

### Strategy 4: Test-Driven Cases

**Best for:** Task completion

```python
def generate_tdd_case():
    """Create case where agent implements function to pass tests."""
    test_code = """
def test_parse_csv():
    result = parse_csv("a,b,c\\n1,2,3")
    assert result == [["a","b","c"], ["1","2","3"]]
    """

    stub_code = "def parse_csv(text: str) -> List[List[str]]:\n    pass"

    return BenchmarkCase(
        description="Implement CSV parser",
        stub_code=stub_code,
        test_code=test_code,
    )
```

---

## 5. MVP Implementation Plan (4 Weeks)

### Week 1: Minimal Viable Benchmark (25 cases)
**Goal:** Prove core capabilities work

**Deliverables:**
- 5 bug localization cases
- 10 edit accuracy cases
- 10 search accuracy cases
- Basic metrics collection
- CI integration (<6 min runtime)

**Success criteria:**
- All tests run without errors
- Metrics exported to CSV
- Can manually verify results match expectations

### Week 2: Full Benchmark Suite (70 cases)
**Goal:** Comprehensive evaluation

**Deliverables:**
- Add 10 task completion cases
- Add 25 layer efficiency cases
- Enhanced metrics (precision, recall, MRR)
- Regression tracking
- Nightly CI job (<20 min runtime)

**Success criteria:**
- Meet acceptance thresholds from CLAUDE.md:
  - Edit success rate (first): >40%
  - Edit success rate (retry): >75%
  - Agentic task completion: >50%

### Week 3: Baseline Comparison
**Goal:** Prove efficiency gains

**Deliverables:**
- Implement naive LLM-first baseline agent
- Run both agents on same cases
- Comparative metrics dashboard
- Token reduction analysis

**Success criteria:**
- Demonstrate 60-80% token reduction vs. baseline
- Demonstrate <500ms latency for simple queries
- Accuracy parity (HybridCoder ≥ baseline)

### Week 4: External Validation
**Goal:** Compare to published benchmarks

**Deliverables:**
- Run on 5-10 SWE-bench Verified cases
- Document comparison to published results
- Write benchmark results for README
- Create benchmark visualization (charts)

**Success criteria:**
- Competitive performance on SWE-bench subset
- Clear documentation of methodology
- Reproducible results

---

## 6. Integration with Existing Tests

### Existing Test Structure
```
tests/
├── unit/                       # Fast, no LLM
├── integration/                # Requires LLM (@pytest.mark.integration)
├── test_sprint_verify.py       # Sprint boundary checks
└── benchmark/                  # NEW: Performance benchmarks
```

### Marking Benchmark Tests
```python
# Fast benchmarks (no LLM calls)
@pytest.mark.benchmark
def test_search_accuracy_no_llm(agent, case):
    # Uses deterministic search (L1/L2 only)
    ...

# Slow benchmarks (requires LLM)
@pytest.mark.benchmark
@pytest.mark.integration
def test_task_completion_with_llm(agent, case):
    # Uses L4 LLM for reasoning
    ...
```

### Running Benchmarks
```bash
# Fast benchmarks only (<5 min)
uv run pytest tests/benchmark -m "benchmark and not integration"

# Full benchmark suite (~20 min)
uv run pytest tests/benchmark -m benchmark

# Specific category
uv run pytest tests/benchmark/test_edit_efficiency.py -v

# With metrics export
uv run pytest tests/benchmark -m benchmark --benchmark-export=results.csv
```

---

## 7. Metrics to Track (Priority Order)

### Tier 1: MVP Acceptance Criteria (from CLAUDE.md)
- ✓ Edit success rate (first attempt): >40%
- ✓ Edit success rate (with retry): >75%
- ✓ LLM call reduction: 60-80% vs naive
- ✓ Simple query latency: <500ms
- ✓ Agentic task completion: >50%

### Tier 2: Efficiency Metrics
- Token usage (L3 + L4 separate)
- Latency per layer (L1/L2/L3/L4)
- Tool call count and types
- Diff size (lines changed)
- Search accuracy (Accuracy@K, MRR)

### Tier 3: Advanced Metrics
- Precision/recall for edits
- False positive rate (wrong file/line)
- Memory usage during benchmark
- Test case coverage (by difficulty, bug type)

---

## 8. Best Practices from 2026 Research

### DO:
✓ Use pytest parameterization for easy case addition
✓ Store test cases in JSON/YAML for non-programmers to contribute
✓ Isolate each test (fresh tmp directory)
✓ Track metrics over time (CSV export)
✓ Use Online Judge pattern (run actual code, not string matching)
✓ Balance synthetic and real-world cases
✓ Measure both correctness AND efficiency

### DON'T:
✗ Copy SWE-bench structure blindly (too heavy for local iteration)
✗ Rely on Docker containers (slows down dev loop)
✗ Only measure pass/fail (efficiency matters!)
✗ Forget to version benchmark datasets
✗ Optimize for benchmark at expense of real use cases
✗ Use string matching to validate correctness
✗ Let benchmark suite become too slow (>30 min)

---

## 9. Quick Reference: Benchmark Comparison

| Benchmark | Focus | Best Pattern | HybridCoder Application |
|-----------|-------|--------------|------------------------|
| SWE-bench | Real-world tasks | Fail-to-pass tests | Task completion suite |
| HumanEval | Code generation | Function completion | L3/L4 model validation |
| Aider | Edit efficiency | Diff format, multi-attempt | Edit accuracy suite |
| RepoBench | Search/retrieval | Accuracy@K | Search accuracy suite |
| CodeEditorBench | Code editing | 4 task types | Bug localization suite |

---

## 10. Success Metrics Dashboard (Target)

```
HybridCoder Benchmark Results (Phase 6 MVP)
==============================================

Edit Efficiency:
  Success Rate (first attempt):  42% ✓  (target: >40%)
  Success Rate (with retry):     78% ✓  (target: >75%)
  Avg Lines Changed / Minimal:   1.2x ✓  (target: <1.5x)
  Whole-File Rewrites:           0   ✓  (target: 0)

Search Accuracy:
  Accuracy@1:  65%  ✓  (target: >60%)
  Accuracy@5:  85%  ✓  (target: >80%)
  Accuracy@10: 92%  ✓  (target: >90%)
  Avg Latency: 120ms ✓  (target: <200ms)

Bug Localization:
  File Correct:       75% ✓  (target: >70%)
  Line Within ±5:     82% ✓  (target: >75%)
  Avg Tool Calls:     6.5 ✓  (target: <10)

Task Completion:
  Success Rate:       55% ✓  (target: >50%)
  Avg Tokens:         2,400 ✓  (target: <4,000)
  Avg Time:           8.5s ✓  (target: <15s)

Layer Efficiency (vs. naive baseline):
  Token Reduction:    67% ✓  (target: 60-80%)
  Latency Reduction:  58% ✓  (target: >50%)
  Accuracy Parity:    98% ✓  (target: >95%)

Layer Distribution:
  L1 (Deterministic):     40% ✓  (target: >30%)
  L2 (Retrieval):         25% ✓  (target: >20%)
  L3 (Constrained Gen):   15% ✓  (target: 10-20%)
  L4 (Full Reasoning):    20% ✓  (target: <30%)
```

---

## 11. Next Steps

1. **Read full research:** `docs/plan/benchmark_research_2026.md`
2. **Review acceptance criteria:** `docs/plan.md` Section 1.6 (MVP Acceptance Checklist) and `CLAUDE.md`
3. **Create benchmark skeleton:**
   ```bash
   mkdir -p tests/benchmark/cases/{edit_accuracy,search_retrieval,bug_localization}
   touch tests/benchmark/{conftest,metrics}.py
   touch tests/benchmark/test_{edit_efficiency,search_accuracy}.py
   ```
4. **Generate first 5 test cases:** Use synthetic bug injection
5. **Implement basic metrics collection:** Export to CSV
6. **Run and iterate:** Start with edit accuracy (highest priority)

---

## Appendix: Useful Code Snippets

### Load JSON Test Cases
```python
def load_cases(category: str) -> List[BenchmarkCase]:
    cases_dir = Path(__file__).parent / "cases" / category
    cases = []
    for file in cases_dir.glob("*.json"):
        with open(file) as f:
            cases.append(BenchmarkCase.from_json(f.read()))
    return cases
```

### Track Tool Calls
```python
@contextmanager
def track_tool_calls():
    tracker = ToolCallTracker()
    with patch("agent.execute_tool", side_effect=tracker.record):
        yield tracker
```

### Calculate Diff Size
```python
def calculate_diff_size(original: str, modified: str) -> int:
    diff = difflib.unified_diff(
        original.splitlines(),
        modified.splitlines(),
        lineterm=""
    )
    return len([line for line in diff if line.startswith(('+', '-'))])
```

### Run Tests and Capture Results
```python
def run_tests(test_file: Path) -> TestResult:
    result = pytest.main([str(test_file), "-v", "--tb=short"])
    return TestResult(
        passed=(result == 0),
        exit_code=result,
    )
```

---

## Summary

This guide provides everything needed to implement a lightweight, local, fast benchmark suite that:
1. **Measures what matters:** Edit efficiency, search accuracy, token reduction
2. **Proves our value:** 60-80% token reduction vs. naive LLM-first
3. **Runs fast:** MVP in <6 min, full suite in <20 min
4. **Iterates quickly:** JSON test cases, easy to add more
5. **Tracks over time:** CSV export, regression detection

**Start with Week 1 deliverables, iterate from there.**

# AI Coding Assistant Benchmarks and Evaluation Frameworks - 2026 Research

**Research Date:** 2026-02-05
**Purpose:** Inform lightweight local test suite design for HybridCoder
**Target:** Measure bug finding, edit efficiency, search accuracy, and task completion

---

## Executive Summary

The AI coding assistant benchmark landscape in 2026 centers around four major evaluation paradigms:

1. **Real-world task completion** (SWE-bench family) - 23% solve rate for top models
2. **Code generation correctness** (HumanEval/MBPP) - 70-82% for common languages
3. **Edit efficiency and format compliance** (Aider benchmarks) - Diff format reduces tokens by 76%
4. **Repository-level retrieval** (RepoBench) - Context accuracy critical for multi-file tasks

**Key insight:** Our ability to evaluate agents is lagging far behind our ability to build them. Most benchmarks focus on code generation, not code editing or search accuracy. There's a gap for lightweight, local, deterministic evaluation frameworks.

---

## 1. SWE-bench: Real-World Bug Resolution

### How It Works

- **Dataset:** Real GitHub issues from popular Python repositories
- **Task:** Given an issue description, generate a patch that resolves it
- **Evaluation:** Apply patch, run test suite in isolated container
- **Variants:**
  - SWE-bench Full: ~2,000 tasks
  - SWE-bench Verified: 500 human-validated tasks (OpenAI, Aug 2024)
  - SWE-bench Lite: Subset for faster iteration
  - SWE-bench Pro: More rigorous, realistic evaluation (Scale AI)

### Metrics

**Primary metric: Resolve Rate (%)** - Percentage of tasks successfully resolved

Success criteria (both must pass):
1. **Fail-to-pass tests pass** - Bug is fixed / feature implemented
2. **Pass-to-pass tests continue passing** - No regressions introduced

### Performance Benchmarks (2026)

| Model/System | SWE-bench Verified | SWE-bench Pro |
|--------------|-------------------|---------------|
| GPT-5 | - | 23.3% |
| Claude Opus 4.1 | - | 23.1% |
| Claude Opus 4 + Tools | >70% | - |

### Implementation Details

```python
# Pseudo-structure of a SWE-bench test case
{
    "instance_id": "repo__owner__issue_number",
    "repo": "owner/repo",
    "base_commit": "abc123def",
    "problem_statement": "Bug: X does not work when Y...",
    "hints_text": "Check the function Z in file.py",
    "created_at": "2023-01-15",
    "patch": "unified diff of expected solution",
    "test_patch": "unified diff of test changes",
    "fail_to_pass": ["test_module::test_function"],
    "pass_to_pass": ["test_module::test_other[...]"]
}
```

**Evaluation process:**
1. Clone repo at `base_commit`
2. Apply `test_patch` (adds/modifies tests)
3. Run tests → record fail-to-pass and pass-to-pass baseline
4. Apply candidate patch (from LLM)
5. Run tests again → success if fail-to-pass now pass AND pass-to-pass still pass
6. Execute in Docker container for isolation

**Test frameworks used:** pytest, unittest (Python)

### Creating SWE-bench-Style Local Cases

**Pattern 1: Regression-based**
- Take a real bug from your project's git history
- Extract: commit message, diff, affected files, tests
- Store as test case: "given this state, can agent reproduce the fix?"

**Pattern 2: Synthetic injection**
- Start with working code + passing tests
- Inject a known bug (e.g., off-by-one, null check missing)
- Create failing test that catches the bug
- Store original working code as ground truth

**Pattern 3: Feature addition**
- Provide spec for a small feature
- Reference implementation available
- Tests that verify feature behavior
- Measure if agent's implementation passes tests

**Lightweight local approach:**
```python
# tests/benchmark/test_swe_local.py
@pytest.mark.parametrize("case", load_local_cases("swe_style"))
def test_bug_resolution(case, agent_system):
    # Setup: checkout base commit or load pristine files
    setup_environment(case.base_files)

    # Execute: run agent with problem statement
    result = agent_system.solve(case.problem_statement)

    # Apply: write agent's changes
    apply_changes(result.edits)

    # Verify: run tests
    test_result = pytest.main([case.test_file])

    assert case.expected_fails_now_pass(test_result)
    assert case.expected_passes_still_pass(test_result)
```

---

## 2. HumanEval & MBPP: Code Generation Correctness

### Structure

**HumanEval (OpenAI, 2021)**
- 164 hand-written Python programming problems
- Each includes: function signature, docstring, test cases
- Task: Complete the function body
- Metric: pass@k (% that pass all tests when generating k samples)

**MBPP (Google, 2021)**
- 974 crowd-sourced Python problems
- Simpler than HumanEval
- Includes task description + 3 test cases

**HumanEval Pro & MBPP Pro (2025/2026)**
- Extension: self-invoking code generation
- Two-stage problems:
  1. Solve base problem
  2. Use that solution to solve more complex problem
- Tests model's ability to reuse code
- Multiple variants: zero-shot, CoT, one-shot

### Format Example

```python
# HumanEval-style problem
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
    # [COMPLETION HERE]

# Test execution
def check(candidate):
    assert candidate([1.0, 2.0, 3.0], 0.5) == False
    assert candidate([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3) == True
    # ... more assertions
```

### Evaluation

- Generate k samples (k=1, 10, or 100)
- Run all test cases for each sample
- pass@k = percentage where at least one sample passes all tests
- Temperature: 0.2, top_p: 0.95 (standard for HumanEval Pro/MBPP Pro)

### Performance Benchmarks (2026)

- Top models: 70-82% accuracy on common languages (Python, JS, Go, TS, Java)
- Qwen2.5-Coder-1.5B: 72% on HumanEval (our L3 model candidate)

### Creating HumanEval-Style Local Cases

**Pattern: Isolated function completion**
```python
# tests/benchmark/test_humaneval_style.py
PROBLEMS = [
    {
        "id": "local/001",
        "prompt": "def parse_git_status(output: str) -> Dict[str, List[str]]:\n    \"\"\"Parse git status --short output into staged/unstaged/untracked.\n    >>> parse_git_status('M  foo.py\\n?? bar.py')\n    {'staged': ['foo.py'], 'unstaged': [], 'untracked': ['bar.py']}\n    \"\"\"\n",
        "test": "assert parse_git_status('M  foo.py') == {'staged': ['foo.py'], 'unstaged': [], 'untracked': []}",
        "entry_point": "parse_git_status"
    }
]

def test_code_generation(agent, problem):
    completion = agent.generate_code(problem["prompt"])
    exec_globals = {}
    exec(problem["prompt"] + completion, exec_globals)
    exec(problem["test"], exec_globals)  # Should not raise
```

**Best for:** Testing L3/L4 model code generation in isolation, not full agentic workflow.

---

## 3. Aider Benchmarks: Edit Accuracy and Diff Efficiency

### Overview

Aider evaluates models on **code editing** (not just generation) across multiple languages using real-world problems from Exercism.

**Key insight:** Models that use diff formats are far more efficient than those that rewrite entire files.

### Benchmarks

**Aider Polyglot Benchmark**
- 225 challenging problems from Exercism
- Languages: C++, Go, Java, JavaScript, Python, Rust
- Model gets 2 attempts:
  1. First attempt
  2. Second attempt after seeing unit test failures
- Tests both code generation AND error correction

### Metrics

1. **Pass rate (%)** - Percentage of problems solved (all tests pass)
2. **Edit format accuracy (%)** - Model complies with diff format
3. **Token efficiency** - Tokens used for diff vs. whole-file rewrite
4. **Error types:**
   - Malformed responses
   - Syntax errors
   - Runtime errors
   - Test failures

### Diff Format Benefits

**GPT-4.1 example (OpenAI):**
- Trained to follow diff formats reliably
- Result: **76% fewer output tokens** (Opus 4.5 vs Sonnet 4.5 on SWE-bench Verified)
- Saves cost and latency
- Only output changed lines, not entire files

**Why this matters for HybridCoder:**
- Editing large files is infeasible if you regenerate entire file
- Diff format = more predictable, verifiable, efficient
- Can measure "edit accuracy" = did agent change only what's needed?

### Creating Aider-Style Local Cases

**Pattern 1: Exercism-style problems**
```python
# tests/benchmark/test_edit_accuracy.py
def test_targeted_edit(agent, tmp_path):
    # Setup: create file with known bug
    buggy_code = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total  # BUG: should multiply by quantity
'''
    file_path = tmp_path / "calculator.py"
    file_path.write_text(buggy_code)

    # Task: fix the bug
    prompt = "Fix the bug: calculate_total should multiply price by quantity"
    result = agent.edit_file(file_path, prompt)

    # Metrics
    assert result.success
    assert result.lines_changed <= 2  # Should only change 1-2 lines
    assert "item.quantity" in result.new_content

    # Verify correctness
    exec_test(file_path, test_calculate_total)
```

**Pattern 2: Diff size analysis**
```python
def test_diff_efficiency(agent, baseline_file):
    edits = agent.apply_changes(baseline_file, instruction)

    diff_size = len(edits.unified_diff.splitlines())
    file_size = len(baseline_file.read_text().splitlines())

    # Agent should not rewrite entire file for small change
    assert diff_size < file_size * 0.1  # Changed <10% of file
```

**Pattern 3: Multi-attempt accuracy**
```python
def test_error_correction(agent, problem):
    # Attempt 1
    solution1 = agent.solve(problem.description)
    result1 = run_tests(solution1, problem.tests)

    if result1.passed:
        return {"attempts": 1, "success": True}

    # Attempt 2 with feedback
    solution2 = agent.solve(problem.description, feedback=result1.errors)
    result2 = run_tests(solution2, problem.tests)

    return {"attempts": 2, "success": result2.passed}
```

---

## 4. RepoBench: Repository-Level Code Search and Retrieval

### Overview

Evaluates code auto-completion systems at **repository level** - multi-file context, realistic retrieval scenarios.

**Languages:** Python, Java

### Three Interconnected Tasks

**RepoBench-R (Retrieval)**
- Task: Given a code snippet, retrieve most relevant snippets from other files
- Metric: **Accuracy@k** (top-k retrieved snippets contain the ground truth)
- Simulates: "Which files/functions do I need to see to complete this code?"

**RepoBench-C (Code Completion)**
- Task: Predict next line given cross-file + in-file context
- Metrics:
  - Exact Match (EM)
  - Edit Similarity (ES)
  - CodeBLEU (CB)
- Uses retrieved context from RepoBench-R

**RepoBench-P (Pipeline)**
- End-to-end: retrieve context → complete code
- Simulates GitHub Copilot workflow
- Most realistic evaluation

### Why This Matters for HybridCoder

HybridCoder's `search_text` tool and Layer 2 (retrieval) are critical for:
- Finding where a bug exists
- Gathering context for edits
- Locating definitions/usages

**RepoBench teaches us:**
- Retrieval accuracy is a separate, measurable capability
- Can evaluate search without running full task completion
- Accuracy@k is a simple, effective metric

### Creating RepoBench-Style Local Cases

**Pattern 1: Retrieval accuracy**
```python
# tests/benchmark/test_search_accuracy.py
RETRIEVAL_CASES = [
    {
        "query": "implementation of user authentication",
        "ground_truth_files": [
            "src/auth/authenticator.py",
            "src/auth/session.py"
        ],
        "repo_size": 150  # total files
    }
]

def test_search_retrieval(agent, case):
    results = agent.search_text(case["query"], top_k=10)

    # Accuracy@10: Are ground truth files in top 10?
    found = [f for f in case["ground_truth_files"] if f in results]
    accuracy = len(found) / len(case["ground_truth_files"])

    assert accuracy >= 0.8  # 80% of relevant files found
```

**Pattern 2: Context sufficiency**
```python
def test_context_sufficiency(agent, task):
    # Step 1: Retrieve context
    context = agent.retrieve_context(task.query, max_tokens=2000)

    # Step 2: Attempt task with only this context
    result = agent.complete_task(task, context=context)

    # Metrics
    assert result.success  # Task completed
    assert task.required_files.issubset(context.files)  # Got necessary files
```

**Pattern 3: Needle-in-haystack**
```python
def test_needle_in_haystack(agent, repo_path):
    # Hide specific function in large codebase
    target = "def calculate_license_expiry(date):"

    # Agent must find it given vague description
    results = agent.search("function that calculates when a license expires")

    # Should find exact file + approximate line number
    assert target in results[0].content
    assert abs(results[0].line_number - ground_truth_line) <= 5
```

---

## 5. Additional Relevant Benchmarks (2026)

### CodeEditorBench (2024)

**Focus:** Code editing capability (not just generation)

**Four task types:**
1. **Code Debugging** - Fix bugs in provided code
2. **Code Translating** - Port between languages (C++ → Java)
3. **Code Polishing** - Improve code quality/style
4. **Code Requirement Switching** - Modify to meet new requirements

**Metrics:**
- Pass@1 for Debug/Translate/Requirement Switch
- Mean OptScore for Polishing

**Dataset:**
- Multiple languages: C++, Java, Python
- Difficulty: Easy/Medium/Hard
- Error counts: 1-4 bugs per problem
- Verified by Online Judge (OJ) system

**Key innovation:** Uses LLM-generated test cases verified by OJ, ensuring correctness without manual curation overhead.

### LiveBench (2025-2026)

- Continuously updated with new problems
- Prevents test set contamination (models can't memorize)
- Multiple domains including coding

### Codev-Bench (2025-2026)

**Developer-centric evaluation:**
- Fine-grained contexts from real repos
- Extracts unit test classes/functions from GitHub
- Uses pytest trace tool to capture execution traces
- Evaluates if tool captures developer's **immediate intent**
- More realistic than synthetic problems

### TestGenEval (2024)

**Focus:** Test generation quality

**Method:**
- Injects synthetic bugs into code under test
- Measures % bugs detected by generated tests
- Should pass on original, fail on buggy version

**Application to HybridCoder:** If we generate tests in L4, we need a way to validate their quality.

---

## 6. Emerging Evaluation Gaps (Opportunities for HybridCoder)

### Gap 1: Deterministic vs. LLM Intelligence

**Problem:** All benchmarks assume LLM-first approach. None measure:
- When to use LLM vs. classical analysis
- Token efficiency gains from hybrid approach
- Latency improvements from Layer 1/2

**Opportunity:** Create benchmark that measures:
```python
def test_layer_efficiency(task_suite):
    for task in task_suite:
        result = agent.solve(task)

        metrics = {
            "layer_1_resolution": task.solvable_deterministically,
            "layer_2_resolution": task.solvable_with_retrieval,
            "layer_3_resolution": task.needs_constrained_gen,
            "layer_4_resolution": task.needs_full_reasoning,
            "tokens_used": result.total_tokens,
            "latency_ms": result.latency
        }

        # Compare to baseline (naive LLM-first)
        baseline = naive_agent.solve(task)

        assert metrics["tokens_used"] < baseline.tokens_used * 0.4  # <40% tokens
        assert metrics["latency_ms"] < baseline.latency_ms * 0.5   # <50% latency
```

### Gap 2: Retrieval in Enterprise Environments

**Problem:** Current benchmarks pull entire repos into containers. Real developers work with:
- Partial clones
- Remote repositories
- Access restrictions
- Large monorepos (can't fit in memory)

**Opportunity:** Benchmark retrieval under constraints:
- Limited token budget for context
- Can only fetch files on demand
- Must use index/search (can't scan all files)

### Gap 3: Tool Call Efficiency

**Problem:** Agentic benchmarks measure task completion, not tool usage efficiency.

**What's missing:**
- How many tool calls did agent make?
- How many were redundant (read same file twice)?
- Did agent use right tool for job (search vs. grep)?

**Opportunity:**
```python
def test_tool_efficiency(agent, task):
    with track_tool_calls() as tracker:
        agent.solve(task)

    assert tracker.unique_files_read <= 10  # Don't read 100 files
    assert tracker.redundant_reads == 0     # Don't read same file twice
    assert tracker.search_before_edit       # Search first, edit after
```

---

## 7. Recommended Benchmark Suite for HybridCoder

### Design Principles

1. **Lightweight** - No Docker, no cloud APIs, runs in CI
2. **Fast** - Entire suite <5 minutes on dev machine
3. **Deterministic** - Same input → same output (where possible)
4. **Multi-dimensional** - Test search, edit, generation, tool use
5. **Incremental** - Can run subsets (per-layer, per-sprint)

### Proposed Structure

```
tests/benchmark/
├── README.md                       # Benchmark documentation
├── cases/                          # Test case definitions
│   ├── swe_style/                  # Bug resolution (SWE-bench-like)
│   │   ├── case_001_off_by_one.json
│   │   ├── case_002_null_check.json
│   │   └── fixtures/               # Code files, tests
│   ├── humaneval_style/            # Code generation
│   │   └── problems.json
│   ├── edit_accuracy/              # Aider-style editing
│   │   └── problems.json
│   └── retrieval/                  # RepoBench-style search
│       └── queries.json
├── test_bug_finding.py             # Can agent locate buggy line?
├── test_edit_efficiency.py         # Lines changed vs. necessary?
├── test_search_accuracy.py         # Does search find right file/line?
├── test_task_completion.py         # Given prompt, does it work?
├── test_layer_efficiency.py        # Token/latency vs. baseline
└── conftest.py                     # Shared fixtures
```

### Benchmark 1: Bug Finding Accuracy

**Goal:** Can the agent locate the buggy line?

**Method:**
1. Provide buggy codebase (5-20 files)
2. Provide bug report (description, steps to reproduce)
3. Agent uses search_text, read_file to investigate
4. Agent reports suspected file + line number

**Metrics:**
- **Localization accuracy:** Is reported line within ±5 lines of bug?
- **File rank:** Is buggy file in top-K retrieved files?
- **Search efficiency:** How many search queries used?
- **False positives:** How many incorrect locations reported?

**Test cases (10-20):**
- Off-by-one errors
- Null/undefined checks
- Type mismatches
- Logic errors (wrong condition)
- API misuse

### Benchmark 2: Edit Efficiency

**Goal:** How many lines changed vs. necessary?

**Method:**
1. Provide code + edit instruction
2. Agent applies changes
3. Measure diff size
4. Compare to ground truth minimal diff

**Metrics:**
- **Precision:** Changed lines that needed changing / Total changed lines
- **Recall:** Changed lines that needed changing / Lines that should change
- **Diff size ratio:** Agent's diff / Minimal diff
- **Whole-file rewrites:** Count (should be 0)

**Test cases (15-25):**
- Rename variable (should use replace_all)
- Fix single bug (1-3 lines)
- Add parameter to function (signature + all calls)
- Refactor function (5-10 lines)
- Update config file (1 line)

### Benchmark 3: Code Search Accuracy

**Goal:** Does search_text find the right file/line?

**Method:**
1. Create synthetic codebase (50-200 files)
2. Hide target code (function, class, variable)
3. Provide natural language query
4. Measure retrieval accuracy

**Metrics:**
- **Accuracy@K:** Target in top-K results (K=1,3,5,10)
- **MRR:** Mean reciprocal rank
- **Search time:** Latency in ms
- **Query quality:** Does agent use effective search terms?

**Test cases (20-30):**
- Find function by description
- Find class by usage
- Find config by key name
- Find test for given function
- Find all usages of deprecated API

### Benchmark 4: Task Completion Rate

**Goal:** Given a prompt, does it complete the task?

**Method:**
1. Provide codebase + task description
2. Agent uses full tool suite (search, read, edit, test)
3. Run tests to verify correctness
4. Track tool usage and efficiency

**Metrics:**
- **Success rate:** Tests pass (first attempt)
- **Success with retry:** Tests pass (≤3 attempts)
- **Tool calls:** Number and types
- **Tokens used:** L3 + L4 combined
- **Time to completion:** End-to-end latency

**Test cases (10-15):**
- Implement missing function (guided by tests)
- Fix failing test
- Add feature (small, well-defined)
- Refactor code to match pattern
- Update dependencies and fix breakage

### Benchmark 5: Layer Efficiency (HybridCoder-specific)

**Goal:** Prove deterministic-first approach saves tokens/time

**Method:**
1. Create tasks solvable at each layer
2. Run through HybridCoder (should use lowest layer)
3. Run through naive LLM-first agent (baseline)
4. Compare metrics

**Metrics:**
- **Layer distribution:** % tasks resolved at L1/L2/L3/L4
- **Token reduction:** HybridCoder tokens / Baseline tokens
- **Latency improvement:** HybridCoder time / Baseline time
- **Accuracy parity:** Success rate should be similar

**Test cases by layer (25 total):**
- **L1 (10 cases):** List files, find definition, count usages, check syntax
- **L2 (5 cases):** Find relevant context, search by semantic similarity
- **L3 (5 cases):** Simple code completion, structured output
- **L4 (5 cases):** Complex refactoring, multi-file edits

---

## 8. Implementation Patterns

### Pattern 1: Fixture-Based Test Cases

```python
# tests/benchmark/conftest.py
@pytest.fixture
def benchmark_case(request):
    """Load benchmark case from JSON."""
    case_path = request.param
    with open(case_path) as f:
        return BenchmarkCase.from_json(f.read())

@pytest.fixture
def isolated_repo(tmp_path, benchmark_case):
    """Create isolated repo for each test."""
    repo = tmp_path / "test_repo"
    benchmark_case.setup_files(repo)
    return repo

# tests/benchmark/test_bug_finding.py
@pytest.mark.parametrize("benchmark_case", [
    "cases/swe_style/case_001_off_by_one.json",
    "cases/swe_style/case_002_null_check.json",
], indirect=True)
def test_bug_localization(agent, isolated_repo, benchmark_case):
    result = agent.find_bug(
        repo=isolated_repo,
        description=benchmark_case.problem_statement
    )

    accuracy = benchmark_case.evaluate_localization(result)
    assert accuracy.file_correct
    assert accuracy.line_within_range(tolerance=5)
```

### Pattern 2: Metrics Collection

```python
# tests/benchmark/metrics.py
@dataclass
class BenchmarkMetrics:
    task_id: str
    success: bool
    layer_used: int  # 1-4
    tokens_l3: int
    tokens_l4: int
    latency_ms: int
    tool_calls: List[ToolCall]
    diff_size: int
    files_changed: int

    def efficiency_score(self) -> float:
        """Combined metric: success / (tokens + latency)"""
        if not self.success:
            return 0.0
        cost = (self.tokens_l3 + self.tokens_l4 * 2) + self.latency_ms / 100
        return 1.0 / cost

class MetricsCollector:
    def __init__(self):
        self.metrics: List[BenchmarkMetrics] = []

    def record(self, metrics: BenchmarkMetrics):
        self.metrics.append(metrics)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self.metrics),
            "success_rate": sum(m.success for m in self.metrics) / len(self.metrics),
            "avg_tokens": sum(m.tokens_l3 + m.tokens_l4 for m in self.metrics) / len(self.metrics),
            "avg_latency_ms": sum(m.latency_ms for m in self.metrics) / len(self.metrics),
            "layer_distribution": Counter(m.layer_used for m in self.metrics),
        }

    def export_csv(self, path: Path):
        df = pd.DataFrame([asdict(m) for m in self.metrics])
        df.to_csv(path, index=False)
```

### Pattern 3: Ground Truth Generation

```python
# scripts/generate_benchmark_cases.py
def generate_bug_finding_case(repo_path: Path, bug_commit: str) -> BenchmarkCase:
    """Generate SWE-bench-style case from real bug fix."""
    repo = git.Repo(repo_path)

    # Get commit that fixed bug
    commit = repo.commit(bug_commit)
    parent = commit.parents[0]

    # Extract bug location
    diff = commit.diff(parent)
    changed_lines = extract_changed_lines(diff)

    # Get commit message as problem statement
    problem = commit.message

    # Extract tests
    tests_before = run_tests(parent)
    tests_after = run_tests(commit)

    fail_to_pass = [t for t in tests_before.failed if t in tests_after.passed]

    return BenchmarkCase(
        id=f"real/{repo.name}/{bug_commit[:7]}",
        problem_statement=problem,
        base_commit=parent.hexsha,
        ground_truth_files=[f.a_path for f in diff],
        ground_truth_lines=changed_lines,
        fail_to_pass_tests=fail_to_pass,
    )
```

### Pattern 4: Baseline Comparison

```python
# tests/benchmark/test_layer_efficiency.py
def test_token_efficiency_vs_baseline(benchmark_suite):
    """Compare HybridCoder to naive LLM-first agent."""
    hybridcoder_metrics = []
    baseline_metrics = []

    for case in benchmark_suite:
        # Run HybridCoder
        with MetricsTracker() as hc_tracker:
            hc_result = hybridcoder_agent.solve(case)
        hybridcoder_metrics.append(hc_tracker.metrics)

        # Run naive baseline
        with MetricsTracker() as bl_tracker:
            bl_result = naive_agent.solve(case)
        baseline_metrics.append(bl_tracker.metrics)

    # Aggregate
    hc_total_tokens = sum(m.total_tokens for m in hybridcoder_metrics)
    bl_total_tokens = sum(m.total_tokens for m in baseline_metrics)

    reduction = 1 - (hc_total_tokens / bl_total_tokens)

    print(f"Token reduction: {reduction:.1%}")
    assert reduction >= 0.60, "Should use 60% fewer tokens than baseline"
```

### Pattern 5: Continuous Benchmark Tracking

```python
# tests/benchmark/test_regression.py
def test_benchmark_regression():
    """Ensure benchmark scores don't degrade over time."""
    current_results = run_full_benchmark()

    # Load historical best
    with open("tests/benchmark/historical_best.json") as f:
        historical = json.load(f)

    # Compare
    for metric in ["success_rate", "token_efficiency", "search_accuracy"]:
        current = current_results[metric]
        best = historical[metric]

        # Allow 5% degradation
        assert current >= best * 0.95, f"{metric} regressed: {current} < {best}"

    # Update if improved
    if current_results["success_rate"] > historical["success_rate"]:
        with open("tests/benchmark/historical_best.json", "w") as f:
            json.dump(current_results, f, indent=2)
```

---

## 9. Best Practices from 2026 Research

### Testing Best Practices

1. **Separate unit and integration tests**
   - Unit: Fast, deterministic, no LLM calls
   - Integration: Slow, requires LLM, marked with `@pytest.mark.integration`

2. **Use test isolation**
   - Each test gets fresh tmp directory
   - No shared state between tests
   - Clean up after each test

3. **Parameterize test cases**
   - Store cases in JSON/YAML
   - Use `@pytest.mark.parametrize`
   - Easy to add new cases

4. **Track metrics over time**
   - Export to CSV after each run
   - Plot trends in CI
   - Alert on regressions

5. **Use Online Judge pattern**
   - Verify correctness by running code
   - Don't rely on string matching
   - Actual execution = ground truth

### Benchmark Design Best Practices

1. **Start simple, add complexity**
   - Begin with 5-10 cases per category
   - Add more as you identify gaps
   - Focus on diversity over quantity

2. **Balance synthetic and real-world**
   - Synthetic: Controlled, specific capabilities
   - Real-world: Realistic, unpredictable
   - Use both

3. **Measure what matters for your use case**
   - HybridCoder: Token efficiency, latency, layer distribution
   - Don't just copy SWE-bench blindly

4. **Version your benchmarks**
   - Datasets evolve
   - Track which version you're comparing to
   - Prevent data contamination

5. **Evaluate at multiple granularities**
   - Component level (search, edit, generate)
   - Task level (complete user request)
   - System level (end-to-end workflow)

### Avoiding Benchmark Pitfalls

1. **Data contamination**
   - Models may have seen test cases in training
   - Use recent data or synthetic
   - Consider "verified" subsets (human-validated)

2. **Overfitting to benchmark**
   - Don't optimize for specific test cases
   - Use benchmark to guide, not define, development

3. **Misleading metrics**
   - Pass@1 can be gamed by generating safe code
   - Edit accuracy needs both precision and recall
   - Success rate without efficiency is incomplete

4. **Scale mismatch**
   - SWE-bench uses large repos
   - Your agent may work differently on small/large codebases
   - Test at multiple scales

---

## 10. Recommended MVP Benchmark for HybridCoder Phase 6

### Minimal Viable Benchmark (Week 1)

**Goal:** Prove core capabilities work

```
tests/benchmark/
├── cases/
│   ├── bug_localization_5_cases.json
│   ├── edit_accuracy_10_cases.json
│   └── search_accuracy_10_cases.json
├── test_bug_localization.py       # 5 tests, ~2 min
├── test_edit_accuracy.py          # 10 tests, ~3 min
└── test_search_accuracy.py        # 10 tests, <1 min
```

**Total:** 25 test cases, ~6 minutes, CI-friendly

### Full Benchmark (Week 2-3)

**Goal:** Comprehensive evaluation

```
tests/benchmark/
├── cases/
│   ├── swe_style/                 # 15 cases
│   ├── edit_accuracy/             # 20 cases
│   ├── search_retrieval/          # 25 cases
│   └── task_completion/           # 10 cases
├── test_bug_finding.py
├── test_edit_efficiency.py
├── test_search_accuracy.py
├── test_task_completion.py
└── test_layer_efficiency.py
```

**Total:** 70 test cases, ~20 minutes, nightly CI

### Comparison Benchmark (Week 4)

**Goal:** Prove we're competitive

- Run subset of real SWE-bench Verified (5-10 cases)
- Compare to Aider on Exercism problems (10 cases)
- Measure against our own success criteria (from spec.md)

**Acceptance criteria (from CLAUDE.md):**
- LLM call reduction: 60-80% vs naive ✓
- Edit success rate (first): >40% ✓
- Edit success rate (retry): >75% ✓
- Simple query latency: <500ms ✓
- Agentic task completion: >50% on custom suite ✓

---

## 11. Summary and Recommendations

### Key Takeaways

1. **SWE-bench is the gold standard** for real-world task completion
   - But it's heavy (Docker, full repos, slow)
   - Create lightweight local version for iteration

2. **HumanEval/MBPP are ideal for isolated code generation**
   - Simple format, fast execution
   - Good for L3/L4 model eval, not full agent

3. **Aider benchmarks reveal edit efficiency matters**
   - Diff format > whole-file rewrites
   - Can save 76% of tokens
   - Measure diff size, not just correctness

4. **RepoBench shows retrieval is a first-class capability**
   - Search accuracy is measurable independently
   - Accuracy@K is simple and effective
   - Critical for multi-file tasks

5. **Big gap: No benchmarks for deterministic-first systems**
   - All assume LLM-first
   - Opportunity to create unique benchmark
   - Proves HybridCoder's value prop

### Immediate Next Steps

1. **Week 1:** Implement minimal benchmark (25 cases)
   - 5 bug localization
   - 10 edit accuracy
   - 10 search accuracy
   - Prove each layer works

2. **Week 2:** Expand to full benchmark (70 cases)
   - Add task completion (10)
   - Add layer efficiency (15)
   - Add real-world cases (10)

3. **Week 3:** Baseline comparison
   - Implement naive LLM-first agent
   - Run both on same cases
   - Measure token reduction, latency improvement

4. **Week 4:** External validation
   - Run on subset of SWE-bench Verified (5-10)
   - Compare to published results
   - Document results for README

### Long-term Vision

- Contribute benchmark back to community
- Create "DeterministicCodeBench" - first benchmark for hybrid systems
- Track metrics over time as models improve
- Use as selling point: "Scientifically proven 60% more efficient"

---

## Sources

### SWE-bench
- [Introducing SWE-bench Verified | OpenAI](https://openai.com/index/introducing-swe-bench-verified/)
- [SWE-Bench Pro (Public Dataset)](https://scale.com/leaderboard/swe_bench_pro_public)
- [GitHub - SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench)
- [SWE-bench Deep Dive | Medium](https://medium.com/@madhav_mishra/swe-bench-deep-dive-redefining-ai-for-software-engineering-2898b1149b3d)
- [Vayavya Labs - SWE-Bench-C Evaluation Framework](https://vayavyalabs.com/blogs/swe-bench-c-evaluation-framework/)

### HumanEval & MBPP
- [HumanEval Pro and MBPP Pro | arXiv](https://arxiv.org/abs/2412.21199)
- [GitHub - CodeEval-Pro/CodeEval-Pro](https://github.com/CodeEval-Pro/CodeEval-Pro)
- [HumanEval & MBPP: Setting the Standard | Verity AI](https://verityai.co/blog/humaneval-mbpp-code-generation-benchmarks)

### Aider Benchmarks
- [GPT code editing benchmarks | aider](https://aider.chat/docs/benchmarks.html)
- [aider/benchmark/README.md | GitHub](https://github.com/Aider-AI/aider/blob/main/benchmark/README.md)
- [Aider LLM Leaderboards](https://aider.chat/docs/leaderboards/)

### RepoBench
- [RepoBench: Benchmarking Repository-Level Code Auto-Completion | arXiv](https://arxiv.org/abs/2306.03091)
- [GitHub - Leolty/repobench](https://github.com/Leolty/repobench)

### CodeEditorBench
- [CodeEditorBench](https://codeeditorbench.github.io/)
- [GitHub - CodeEditorBench/CodeEditorBench](https://github.com/CodeEditorBench/CodeEditorBench)
- [CodeEditorBench | arXiv](https://arxiv.org/abs/2404.03543)

### Additional Research
- [10 AI agent benchmarks | Evidently AI](https://www.evidentlyai.com/blog/ai-agent-benchmarks)
- [Rethinking Coding Agent Benchmarks | Medium](https://medium.com/@steph.jarmak/rethinking-coding-agent-benchmarks-5cde3c696e4a)
- [AI coding benchmarks | Failing Fast](https://failingfast.io/ai-coding-guide/benchmarks/)
- [Best AI Coding Agents for 2026 | Faros AI](https://www.faros.ai/blog/best-ai-coding-agents-2026)
- [BugPilot: Complex Bug Generation | arXiv](https://arxiv.org/pdf/2510.19898)
- [Codev-Bench | GitHub](https://github.com/LingmaTongyi/Codev-Bench)
- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)

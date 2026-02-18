# Benchmark Hardening — Phase 2: Medium Items

> Version: 1.1 | Date: 2026-02-12 | Status: HISTORICAL REFERENCE (superseded by Phase 4 E2E eval system and Phase 5 plan)
> Estimated effort: ~4-5 hours
> Prerequisite: [Phase 1](benchmark-hardening-phase1.md) (versioning + verdict classification)
> Blocks: [Phase 3](benchmark-hardening-phase3.md)
> Revision notes: v1.1 — Addressed Codex Entry 214 concerns: replaced brittle sys.argv parsing with argparse (2.1)

## Related Documents

- [Phase 1 Hardening](benchmark-hardening-phase1.md) — prerequisite quick wins
- [Phase 3 Hardening](benchmark-hardening-phase3.md) — subsequent larger items
- [E2E Benchmark Guide](../qa/e2e-benchmark-guide.md) — current benchmark documentation
- [Benchmark Testing Strategy](benchmark-testing-strategy.md) — overall benchmark framework
- [Codex Review Entry 207](../../AGENTS_CONVERSATION.MD) — original NEEDS_WORK verdict
- [Codex Expanded Recommendations Entry 209](../../AGENTS_CONVERSATION.MD) — full hardening backlog

## Overview

Four medium-effort items that build on Phase 1 infrastructure. These add replay capability, trace analysis, resource budgets, and a strict evaluation mode.

**Depends on Phase 1:** Versioning (1.1) for replay snapshot metadata, INFRA_FAIL (1.5) for verdict classification in strict mode, anti-patterns (1.3) for strict mode penalty enforcement.

---

## Item 2.1 — Deterministic Replay Mode

**Problem:** Every evaluation requires a fresh LLM run (~15 min, $cost, rate-limit risk). Rubric changes can't be tested against existing outputs without re-running.
**Evidence:** Codex Entry 209 item B — "Deterministic replay mode: evaluate saved generated project snapshots without fresh LLM calls."

**Specification:**

Add a `--replay <sandbox_path>` flag that re-scores an existing sandbox without running the agent:

```python
def replay_benchmark(sandbox: Path) -> int:
    """Re-score an existing benchmark sandbox without LLM calls.

    Phases skipped: A (prerequisites), B (setup), C (agent execution)
    Phases run: D (npm validation), E (scoring), F (report)
    """
    # Load original metadata
    json_path = sandbox / ".hybridcoder-benchmark.json"
    if not json_path.exists():
        print(f"ERROR: No benchmark results found in {sandbox}")
        return 1

    original = json.loads(json_path.read_text(encoding="utf-8"))

    # Find project root (same logic as normal run)
    project_root = find_project_root(sandbox)

    # Re-run scoring with current rubric
    print(f"\n[Replay] Re-scoring {sandbox.name}...")
    print(f"  Original rubric version: {original.get('rubric_version', 'unknown')}")
    print(f"  Current rubric version: {RUBRIC_VERSION}")

    # Phase D: npm validation (optional, skip if --score-only)
    npm_result = run_npm_validation(project_root)

    # Phase E: Scoring with current rubric
    scores = score_project(project_root)

    # Phase F: Save replay report alongside original
    # ... generate report with "REPLAY" tag ...

    return 0
```

**CLI integration — structured argument parser (shared across all phases):**

All benchmark flags (`--replay`, `--strict`, `--runs`, `--matrix`, `--flake-triage`, `--keep-last`) use a single `argparse` parser. This replaces brittle `sys.argv` indexing and provides validation, help text, and mutual exclusion for free.

```python
import argparse

def build_arg_parser() -> argparse.ArgumentParser:
    """Shared argument parser for all benchmark modes."""
    parser = argparse.ArgumentParser(
        description="HybridCoder E2E Benchmark Runner"
    )

    # Mode selection (mutually exclusive)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--replay", type=Path, metavar="SANDBOX_PATH",
        help="Re-score an existing sandbox without LLM calls",
    )
    mode.add_argument(
        "--matrix", type=Path, metavar="MATRIX_JSON",
        help="Run benchmark across multiple model configurations",
    )
    mode.add_argument(
        "--flake-triage", action="store_true",
        help="Auto-rerun failures to classify deterministic vs flaky",
    )

    # Modifiers (combinable)
    parser.add_argument(
        "--strict", action="store_true",
        help="Enable strict regression-gate mode",
    )
    parser.add_argument(
        "--runs", type=int, default=1, metavar="N",
        help="Number of benchmark runs (default: 1)",
    )
    parser.add_argument(
        "--min-score", type=int, default=30,
        help="Minimum passing score (default: 30, strict default: 60)",
    )
    parser.add_argument(
        "--keep-last", type=int, default=3,
        help="Number of recent sandboxes to retain (default: 3)",
    )
    parser.add_argument(
        "--score-only", action="store_true",
        help="Skip npm validation in replay mode (scoring only)",
    )

    return parser


# In __main__ block:
if __name__ == "__main__":
    args = build_arg_parser().parse_args()

    if args.replay:
        sys.exit(replay_benchmark(args.replay.resolve(), score_only=args.score_only))
    elif args.matrix:
        sys.exit(asyncio.run(run_matrix(args.matrix)))
    elif args.flake_triage:
        sys.exit(asyncio.run(run_with_flake_triage(
            strict=args.strict, min_score=args.min_score,
        )))
    elif args.runs > 1:
        sys.exit(asyncio.run(run_multi(
            n_runs=args.runs, strict=args.strict, min_score=args.min_score,
        )))
    else:
        sys.exit(main(strict=args.strict, min_score=args.min_score))
```

**Note:** This parser is defined once in Phase 2 item 2.1 and extended as new flags are added in items 2.3, 2.4, 3.1, 3.2, and 3.6. Each phase adds its arguments to the same parser.

PowerShell wrapper addition:

```powershell
param(
    [int]$MinScore = 30,
    [string]$Replay = "",  # Path to existing sandbox for replay
    [switch]$ScoreOnly      # Skip npm validation in replay mode
)

if ($Replay -ne "") {
    $replayArgs = @("run", "python", "scripts/run_calculator_benchmark.py",
                    "--replay", $Replay)
    if ($ScoreOnly) { $replayArgs += "--score-only" }
    $proc = Start-Process -FilePath "uv" `
        -ArgumentList $replayArgs `
        -WorkingDirectory $ProjectRoot `
        -NoNewWindow -PassThru -Wait
    # ... parse results ...
}
```

**Replay report naming:** `<original-ts>-replay-<replay-ts>-e2e-react-calculator.md`

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `replay_benchmark()`, CLI arg parsing
- `scripts/run_e2e_benchmark.ps1` — add `-Replay` parameter

**Verification:**
- [ ] `--replay sandboxes/bench_20260212_203313` re-scores without LLM calls
- [ ] Report clearly labeled as REPLAY with both original and current rubric versions
- [ ] npm validation runs (or is skipped with `--score-only` sub-flag)
- [ ] Original sandbox files are not modified

---

## Item 2.2 — Trace Quality Checks

**Problem:** Event log (`.benchmark-events.jsonl`) captures rich data but is never analyzed programmatically. Repeated tool failures, excessive retries, or abnormal patterns go undetected.
**Evidence:** Codex Entry 209 item B — "Trace-quality checks: parse event logs and require minimal workflow quality."

**Specification:**

Add a post-run trace analysis that reads `.benchmark-events.jsonl`:

```python
def analyze_trace(log_path: Path) -> dict:
    """Analyze benchmark event log for quality signals."""
    events = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line))

    analysis = {
        "total_events": len(events),
        "total_duration_s": 0,
        "tool_calls": {"total": 0, "by_name": {}, "failures": 0},
        "api_errors": 0,
        "repeated_failures": [],  # Same tool failing 3+ times
        "warnings": [],
    }

    # Duration
    if events:
        analysis["total_duration_s"] = events[-1].get("elapsed_s", 0)

    # Tool call analysis
    tool_failures: dict[str, int] = {}
    for e in events:
        if e["event"] == "tool_call":
            analysis["tool_calls"]["total"] += 1
            name = e.get("name", "unknown")
            analysis["tool_calls"]["by_name"][name] = (
                analysis["tool_calls"]["by_name"].get(name, 0) + 1
            )
            if e.get("status") == "error":
                analysis["tool_calls"]["failures"] += 1
                tool_failures[name] = tool_failures.get(name, 0) + 1

        elif e["event"] == "api_error":
            analysis["api_errors"] += 1

    # Detect repeated failures (same tool failing 3+ times)
    for name, count in tool_failures.items():
        if count >= 3:
            analysis["repeated_failures"].append(
                f"{name} failed {count} times"
            )

    # Quality warnings
    tc = analysis["tool_calls"]
    if tc["total"] > 0:
        fail_rate = tc["failures"] / tc["total"]
        if fail_rate > 0.3:
            analysis["warnings"].append(
                f"High tool failure rate: {fail_rate:.0%} "
                f"({tc['failures']}/{tc['total']})"
            )

    if analysis["total_duration_s"] > 1800:  # 30 min
        analysis["warnings"].append(
            f"Excessive duration: {analysis['total_duration_s']}s"
        )

    if tc["total"] < 5:
        analysis["warnings"].append(
            f"Suspiciously few tool calls: {tc['total']}"
        )

    return analysis
```

Integrate into Phase F (report generation):

| Trace Metric | Warning Threshold | Action |
|---|---|---|
| Tool failure rate | >30% | Warning in report |
| Same tool failing 3+ times | Any occurrence | List in report |
| Total duration | >1800s (30 min) | Warning in report |
| Tool calls < 5 | Any occurrence | Warning (possible early abort) |
| API errors > 0 | Any occurrence | Feed into INFRA_FAIL verdict (Phase 1 item 1.5) |

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `analyze_trace()`, call from `main()`, include in report and JSON

**Verification:**
- [ ] Trace analysis runs on every benchmark completion
- [ ] Repeated tool failures are identified
- [ ] Warnings appear in both markdown report and JSON output
- [ ] Analysis works on existing `.benchmark-events.jsonl` files (replay-compatible)

---

## Item 2.3 — Latency/Cost Budget Gates

**Problem:** No upper bounds on benchmark resource consumption. A run that takes 45 minutes or 50K tokens still "passes" if the score is high enough.
**Evidence:** Codex Entry 209 item B — "Latency/cost budget gates: max wall-time, token budget, and cost per successful run."

**Specification:**

Add configurable budget limits:

```python
# Budget defaults (can be overridden via CLI args or .env)
BUDGET_MAX_WALL_TIME_S = 1800    # 30 minutes
BUDGET_MAX_TOOL_CALLS = 100      # total tool calls across all turns
BUDGET_MAX_TURNS = 5             # agent conversation turns

def check_budgets(agent_result: dict, bench_log: BenchmarkLogger) -> dict:
    """Check if benchmark stayed within resource budgets."""
    budgets = {
        "wall_time": {
            "limit_s": BUDGET_MAX_WALL_TIME_S,
            "actual_s": agent_result.get("total_duration_s", 0),
            "passed": agent_result.get("total_duration_s", 0) <= BUDGET_MAX_WALL_TIME_S,
        },
        "tool_calls": {
            "limit": BUDGET_MAX_TOOL_CALLS,
            "actual": agent_result.get("total_tool_calls", 0),
            "passed": agent_result.get("total_tool_calls", 0) <= BUDGET_MAX_TOOL_CALLS,
        },
        "turns": {
            "limit": BUDGET_MAX_TURNS,
            "actual": len(agent_result.get("turns", [])),
            "passed": len(agent_result.get("turns", [])) <= BUDGET_MAX_TURNS,
        },
    }

    return budgets
```

Budget results included in report:

```markdown
## Budget Compliance

| Budget | Limit | Actual | Status |
|--------|-------|--------|--------|
| Wall time | 1800s | 892s | PASS |
| Tool calls | 100 | 30 | PASS |
| Turns | 5 | 2 | PASS |
```

**Budget behavior:**
- Budget violations produce warnings in the report
- Budget violations do NOT change the verdict (PASS/FAIL/INFRA_FAIL) — they're informational
- In strict mode (item 2.4), budget violations DO affect the verdict

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `check_budgets()`, budget constants, include in report and JSON

**Verification:**
- [ ] Budget results appear in report and JSON
- [ ] Exceeded budgets show WARNING status
- [ ] Budget limits configurable via constants (future: CLI args)

---

## Item 2.4 — Strict Mode (`--strict` Flag)

**Problem:** Codex Entry 209 recommended a "regression lane" vs "capability lane" split. Full two-lane infrastructure is premature with one benchmark scenario. A `--strict` flag achieves the same outcome.
**Evidence:** Codex Entry 209 items A/C — "two lanes" and "pass/fail model for regression lane."

**Specification:**

Add `--strict` flag that enables tighter pass criteria:

```python
STRICT_MIN_SCORE = 60       # vs default 30
STRICT_REQUIRE_BUILD = True  # build must pass
STRICT_MAX_ANTI_PATTERNS = 0 # no critical anti-patterns allowed
STRICT_BUDGET_ENFORCED = True # budget violations = FAIL

def classify_result_strict(
    scores: dict[str, int],
    npm_result: dict,
    agent_result: dict,
    anti_patterns: dict,
    budgets: dict,
) -> tuple[str, list[str]]:
    """Strict classification for regression gating."""
    reasons = []

    # First check INFRA_FAIL (same as normal mode)
    api_errors = sum(
        1 for t in agent_result.get("turns", [])
        if t.get("error")
    )
    total_retries = sum(
        t.get("api_retries", 0) for t in agent_result.get("turns", [])
    )
    if api_errors > 0 or total_retries >= 2:
        reasons.append(f"API instability: {api_errors} errors, {total_retries} retries")
        return ("INFRA_FAIL", reasons)

    # Score threshold (higher in strict mode)
    total = scores.get("total", 0)
    if total < STRICT_MIN_SCORE:
        reasons.append(f"Score {total} < strict minimum {STRICT_MIN_SCORE}")

    # Build must pass
    npm_build_ok = (npm_result.get("build") or {}).get("success", False)
    if not npm_build_ok:
        reasons.append("npm build failed (required in strict mode)")

    # No critical anti-patterns
    critical = anti_patterns.get("critical", {})
    if any(v for v in critical.values()):
        names = [k for k, v in critical.items() if v]
        reasons.append(f"Critical anti-patterns found: {', '.join(names)}")

    # Budget enforcement
    for name, budget in budgets.items():
        if not budget["passed"]:
            reasons.append(
                f"Budget exceeded: {name} "
                f"({budget['actual']} > {budget.get('limit', budget.get('limit_s'))})"
            )

    if reasons:
        return ("FAIL", reasons)
    return ("PASS", [])
```

**Strict mode vs normal mode comparison:**

| Criterion | Normal Mode | Strict Mode |
|---|---|---|
| Min score | 30 | 60 |
| Build must pass | No | Yes |
| Anti-pattern penalty | Applied to score | Also blocks PASS verdict |
| Budget enforcement | Informational | Blocks PASS verdict |
| INFRA_FAIL handling | Same | Same |
| Use case | Capability probe | Regression gate |

**CLI:**
- `uv run python scripts/run_calculator_benchmark.py --strict`
- `.\scripts\run_e2e_benchmark.ps1 -Strict`

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `--strict` flag, `classify_result_strict()`, conditional logic in `main()`
- `scripts/run_e2e_benchmark.ps1` — add `-Strict` switch parameter

**Verification:**
- [ ] Default mode behavior unchanged
- [ ] Strict mode with score 50 → FAIL (below 60 threshold)
- [ ] Strict mode with `eval()` in code → FAIL (anti-pattern)
- [ ] Strict mode with budget exceeded → FAIL
- [ ] INFRA_FAIL classification works identically in both modes
- [ ] PowerShell wrapper passes `-Strict` correctly

---

## Dependency Graph

```
Phase 1 (all items)
        │
        ▼
  ┌─────────────────────────────────────────┐
  │                                         │
  │  2.1 Replay Mode ◄── needs 1.1 (versions for snapshot metadata)
  │         │                               │
  │  2.2 Trace Quality ◄── reads .benchmark-events.jsonl
  │         │                               │
  │  2.3 Budget Gates ◄── standalone        │
  │         │                               │
  │  2.4 Strict Mode ◄── needs 1.3 (anti-patterns) + 1.5 (INFRA_FAIL) + 2.3 (budgets)
  │                                         │
  └─────────────────────────────────────────┘
        │
        ▼
  Phase 3 Hardening
```

**Recommended implementation order:** 2.1 → 2.2 → 2.3 → 2.4 (strict mode depends on budgets and anti-patterns being available).

## Summary

| # | Item | Priority | Est. Time | Dependencies |
|---|------|----------|-----------|-------------|
| 2.1 | Replay Mode | High | 1.5 hrs | Phase 1 (versioning) |
| 2.2 | Trace Quality | Medium | 1 hr | None (reads existing event log) |
| 2.3 | Budget Gates | Medium | 45 min | None |
| 2.4 | Strict Mode | High | 1.5 hrs | 1.3 (anti-patterns) + 1.5 (INFRA_FAIL) + 2.3 (budgets) |

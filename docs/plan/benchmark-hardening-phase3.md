# Benchmark Hardening — Phase 3: Larger Items

> Version: 1.1 | Date: 2026-02-12 | Status: PLANNED
> Estimated effort: ~21-26 hours
> Prerequisite: [Phase 1](benchmark-hardening-phase1.md), [Phase 2](benchmark-hardening-phase2.md)
> Blocks: N/A (terminal phase)
> Revision notes: v1.1 — Addressed Codex Entry 214 concerns: fixed multi-run aggregation to use product_runs only, expanded security scan scope, added Item 3.7 (multi-scenario portfolio)

## Related Documents

- [Phase 1 Hardening](benchmark-hardening-phase1.md) — prerequisite quick wins
- [Phase 2 Hardening](benchmark-hardening-phase2.md) — prerequisite medium items
- [E2E Benchmark Guide](../qa/e2e-benchmark-guide.md) — current benchmark documentation
- [Benchmark Testing Strategy](benchmark-testing-strategy.md) — overall benchmark framework
- [Codex Review Entry 207](../../AGENTS_CONVERSATION.MD) — original NEEDS_WORK verdict
- [Codex Expanded Recommendations Entry 209](../../AGENTS_CONVERSATION.MD) — full hardening backlog
- [Codex E2E Portfolio Entry 211](../../AGENTS_CONVERSATION.MD) — additional benchmark scenarios

## Overview

Seven items that bring the benchmark to full regression-gate maturity. These require more effort and some have external dependencies (JSDOM, multi-run orchestration). Two items are marked DEFERRED with framework stubs only. Item 3.7 (multi-scenario portfolio) addresses the portfolio expansion gap identified in Codex Entry 214.

**Depends on Phase 1+2:** Versioning, INFRA_FAIL classification, anti-patterns, strict mode, replay mode, trace analysis, and budget gates must all be in place.

---

## Item 3.1 — Multi-Run Stability

**Problem:** Single-run gating is too noisy for regression confidence. Score variance of 61-86 across same model/date proves single runs are unreliable.
**Evidence:** Codex Entry 207 — "Single-run gating against rate-limited free-tier model is too noisy for regression confidence."

**Specification:**

Add a `--runs N` flag (default 1) that runs the benchmark N times and aggregates:

```python
async def run_multi(
    n_runs: int = 3,
    strict: bool = False,
    min_score: int = 30,
) -> dict:
    """Run benchmark N times and compute aggregate statistics."""
    results = []
    for i in range(n_runs):
        print(f"\n{'='*60}")
        print(f"  RUN {i+1} of {n_runs}")
        print(f"{'='*60}")

        sandbox = create_sandbox()
        bench_log = BenchmarkLogger(sandbox / ".benchmark-events.jsonl")
        bench_log.log("benchmark_start", run_number=i+1, total_runs=n_runs)

        try:
            agent_result = await run_agent(sandbox, bench_log)
            project_root = find_project_root(sandbox)
            npm_result = run_npm_validation(project_root)
            scores = score_project(project_root)
            verdict, reasons = classify_result(scores, npm_result, agent_result)
        except Exception as e:
            scores = {"total": 0}
            verdict = "INFRA_FAIL"
            reasons = [str(e)]
            npm_result = {}
            agent_result = {"error": str(e)}

        results.append({
            "run": i + 1,
            "sandbox": str(sandbox),
            "scores": scores,
            "verdict": verdict,
            "reasons": reasons,
            "npm_build": (npm_result.get("build") or {}).get("success", False),
        })

        bench_log.log("benchmark_end", scores=scores, verdict=verdict)
        bench_log.close()

    return aggregate_multi_run(results, strict, min_score)


def aggregate_multi_run(
    results: list[dict],
    strict: bool,
    min_score: int,
) -> dict:
    """Compute aggregate verdict from N runs."""
    n = len(results)
    verdicts = [r["verdict"] for r in results]

    # Filter out INFRA_FAIL runs for product quality assessment
    product_runs = [r for r in results if r["verdict"] != "INFRA_FAIL"]
    infra_fails = n - len(product_runs)

    # Compute stats from product_runs ONLY (not all runs).
    # INFRA_FAIL scores are noise — including them skews
    # median/min/mean and can cause false strict-mode failures.
    product_scores = [r["scores"]["total"] for r in product_runs]
    product_builds = [r["npm_build"] for r in product_runs]
    np = len(product_runs)

    agg = {
        "total_runs": n,
        "infra_fails": infra_fails,
        "product_runs": np,
        "scores": {
            "all": [r["scores"]["total"] for r in results],  # raw for reference
            "product_only": product_scores,
            "min": min(product_scores) if product_scores else 0,
            "max": max(product_scores) if product_scores else 0,
            "median": sorted(product_scores)[np // 2] if product_scores else 0,
            "mean": round(sum(product_scores) / np, 1) if product_scores else 0,
        },
        "build_pass_rate": sum(product_builds) / np if np > 0 else 0,
        "pass_rate": verdicts.count("PASS") / n if n > 0 else 0,
        "infra_fail_rate": infra_fails / n if n > 0 else 0,
        "runs": results,
    }

    # Aggregate verdict (Codex Entry 209 model)
    if infra_fails > n // 2:
        agg["aggregate_verdict"] = "INFRA_FAIL"
        agg["aggregate_reasons"] = [
            f"{infra_fails}/{n} runs failed due to infrastructure"
        ]
    elif np == 0:
        # All runs were INFRA_FAIL
        agg["aggregate_verdict"] = "INFRA_FAIL"
        agg["aggregate_reasons"] = ["No product runs completed"]
    elif strict:
        # Strict: median of PRODUCT runs >= threshold AND build pass >= 2/3
        median = agg["scores"]["median"]
        build_rate = agg["build_pass_rate"]
        reasons = []
        if median < min_score:
            reasons.append(f"Median product score {median} < {min_score}")
        if build_rate < 2/3:
            reasons.append(f"Product build pass rate {build_rate:.0%} < 67%")
        agg["aggregate_verdict"] = "FAIL" if reasons else "PASS"
        agg["aggregate_reasons"] = reasons
    else:
        # Normal: any single PASS is enough
        agg["aggregate_verdict"] = (
            "PASS" if "PASS" in verdicts else "FAIL"
        )
        agg["aggregate_reasons"] = []

    return agg
```

**Multi-run report format:**

```markdown
## Multi-Run Summary (N=3)

| Run | Score | Build | Verdict |
|-----|-------|-------|---------|
| 1 | 82 | PASS | PASS |
| 2 | 71 | FAIL | FAIL |
| 3 | 86 | PASS | PASS |

**Aggregate:** PASS (median 82, build 67%, 0 infra failures)
```

**CLI:** `uv run python scripts/run_calculator_benchmark.py --runs 3 --strict`

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `run_multi()`, `aggregate_multi_run()`, CLI arg
- `scripts/run_e2e_benchmark.ps1` — add `-Runs` parameter

**Verification:**
- [ ] `--runs 3` executes 3 independent benchmarks with separate sandboxes
- [ ] Aggregate report shows all individual run scores + median/mean
- [ ] INFRA_FAIL runs excluded from product quality assessment
- [ ] Strict aggregate: median >= threshold AND build rate >= 2/3
- [ ] Default `--runs 1` behavior unchanged

---

## Item 3.2 — Seeded Multi-Model Matrix

**Problem:** Benchmark results are only comparable when run against the same model. No structured way to compare across providers/models.
**Evidence:** Codex Entry 209 item B — "Seeded multi-run matrix: run across multiple models/configs and record confidence intervals."

**Specification:**

Add a matrix runner that iterates over model configurations:

```python
# Matrix config (stored in benchmark-matrix.json)
{
    "configs": [
        {
            "name": "openrouter-glm4.5",
            "env_overrides": {
                "HYBRIDCODER_LLM_PROVIDER": "openrouter",
                "OPENROUTER_MODEL": "zhipuai/glm-4.5-air:free"
            }
        },
        {
            "name": "ollama-qwen3-8b",
            "env_overrides": {
                "HYBRIDCODER_LLM_PROVIDER": "ollama",
                "OLLAMA_MODEL": "qwen3:8b-q4_K_M"
            }
        }
    ],
    "runs_per_config": 3,
    "strict": true
}
```

Runner:

```python
async def run_matrix(matrix_path: Path) -> dict:
    """Run benchmark across multiple model configurations."""
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    all_results = {}

    for config in matrix["configs"]:
        name = config["name"]
        print(f"\n{'='*60}")
        print(f"  CONFIG: {name}")
        print(f"{'='*60}")

        # Apply env overrides
        original_env = {}
        for key, value in config["env_overrides"].items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            results = await run_multi(
                n_runs=matrix.get("runs_per_config", 1),
                strict=matrix.get("strict", False),
            )
            all_results[name] = results
        finally:
            # Restore original env
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    return all_results
```

**Matrix report format:**

```markdown
## Benchmark Matrix Results

| Model | Runs | Median | Min | Max | Build Rate | Verdict |
|-------|------|--------|-----|-----|------------|---------|
| openrouter-glm4.5 | 3 | 82 | 71 | 86 | 67% | PASS |
| ollama-qwen3-8b | 3 | 78 | 65 | 84 | 100% | PASS |
```

**CLI:** `uv run python scripts/run_calculator_benchmark.py --matrix benchmark-matrix.json`

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `run_matrix()`, CLI arg
- (new) `benchmark-matrix.json` — example matrix config (project root)

**Verification:**
- [ ] Matrix config is valid JSON
- [ ] Each config runs independently with correct env vars
- [ ] Original env vars restored after each config
- [ ] Cross-model comparison table in report

---

## Item 3.3 — Golden Behavior Pack (DEFERRED — Stubs Only)

**Problem:** No functional correctness testing. Generated calculator code might score high on lexical checks but produce wrong results.
**Evidence:** Codex Entry 209 item B — "Golden behavior pack: fixed input/output vectors for each calculator mode; fail on drift."

**Status:** DEFERRED. Generated React components don't export testable functions — they're JSX components with embedded state. Testing requires either:
1. JSDOM + import parsing (significant undertaking)
2. Playwright browser automation (user approved deferral)

**What we can do now:** Create the golden test vectors and a stub framework that will be filled in when Playwright or JSDOM is available.

**Specification (stubs only):**

```python
# tests/benchmark/golden_vectors.py

"""Golden input/output vectors for calculator benchmark.

These vectors define expected behavior. They are NOT executed yet —
they require either JSDOM or Playwright to run against generated React components.
Framework: when browser testing is available, import these vectors
and run them against the generated app.
"""

REGULAR_CALCULATOR_VECTORS = [
    {"input": "2 + 3", "expected": "5"},
    {"input": "10 / 3", "expected": "3.3333"},  # precision check
    {"input": "1 / 0", "expected_pattern": r"(Infinity|Error|undefined)"},
    {"input": "0.1 + 0.2", "expected": "0.3"},  # big.js precision
    {"input": "999999 * 999999", "expected": "999998000001"},
]

SCIENTIFIC_CALCULATOR_VECTORS = [
    {"input": "sin(0)", "expected": "0"},
    {"input": "cos(0)", "expected": "1"},
    {"input": "sqrt(144)", "expected": "12"},
    {"input": "log(1)", "expected": "0"},
    {"input": "2^10", "expected": "1024"},
]

UNIT_CONVERTER_VECTORS = [
    {"from": "km", "to": "miles", "input": 1, "expected": 0.621371},
    {"from": "kg", "to": "lbs", "input": 1, "expected": 2.20462},
    {"from": "celsius", "to": "fahrenheit", "input": 0, "expected": 32},
    {"from": "celsius", "to": "kelvin", "input": 0, "expected": 273.15},
    {"from": "liters", "to": "gallons", "input": 1, "expected": 0.264172},
]

# Currency vectors are dynamic (API-dependent), so we test structure only:
CURRENCY_STRUCTURE_CHECKS = [
    "dropdown_from_exists",
    "dropdown_to_exists",
    "swap_button_exists",
    "result_display_exists",
    "loading_state_exists",
]
```

**Files to create:**
- `tests/benchmark/golden_vectors.py` — test vectors (data only, no execution)

**Verification:**
- [ ] File exists and is importable
- [ ] Vectors are well-formed and cover all calculator modes
- [ ] Clear docstring explaining DEFERRED status and activation path

---

## Item 3.4 — Metamorphic Test Stubs (DEFERRED — Stubs Only)

**Problem:** No invariant-based testing. Properties like commutativity (`a+b == b+a`) and roundtrip conversions can catch subtle bugs.
**Evidence:** Codex Entry 209 item B — "Metamorphic correctness tests: assert invariants."

**Status:** DEFERRED for the same reason as 3.3 — requires runtime execution against generated components.

**Specification (stubs only):**

```python
# tests/benchmark/metamorphic_stubs.py

"""Metamorphic test stubs for calculator benchmark.

These define mathematical invariants that should hold for any correct
calculator implementation. Execution is DEFERRED until browser/JSDOM
testing is available.

Metamorphic relations:
- Commutativity: a + b == b + a, a * b == b * a
- Identity: a + 0 == a, a * 1 == a
- Inverse: a + b - b == a, a * b / b == a (b != 0)
- Roundtrip: convert(convert(x, A, B), B, A) ≈ x
"""

ARITHMETIC_INVARIANTS = [
    {
        "name": "addition_commutativity",
        "relation": "calc(a + b) == calc(b + a)",
        "test_pairs": [(3, 7), (0.1, 0.2), (-5, 12), (999, 1)],
    },
    {
        "name": "multiplication_commutativity",
        "relation": "calc(a * b) == calc(b * a)",
        "test_pairs": [(3, 7), (0.5, 4), (-2, 6)],
    },
    {
        "name": "additive_identity",
        "relation": "calc(a + 0) == a",
        "test_values": [0, 1, -1, 3.14, 1000000],
    },
    {
        "name": "multiplicative_identity",
        "relation": "calc(a * 1) == a",
        "test_values": [0, 1, -1, 3.14, 1000000],
    },
    {
        "name": "additive_inverse",
        "relation": "calc(calc(a + b) - b) == a",
        "test_pairs": [(5, 3), (0.1, 0.2), (-7, 7)],
        "tolerance": 1e-10,
    },
]

CONVERSION_ROUNDTRIPS = [
    {
        "name": "length_roundtrip",
        "unit_a": "km",
        "unit_b": "miles",
        "test_values": [1, 10, 100, 0.5],
        "tolerance": 0.01,
    },
    {
        "name": "temperature_roundtrip",
        "unit_a": "celsius",
        "unit_b": "fahrenheit",
        "test_values": [0, 100, -40, 37],
        "tolerance": 0.01,
    },
    {
        "name": "weight_roundtrip",
        "unit_a": "kg",
        "unit_b": "lbs",
        "test_values": [1, 50, 100],
        "tolerance": 0.01,
    },
]

SCIENTIFIC_INVARIANTS = [
    {
        "name": "trig_pythagorean",
        "relation": "sin(x)^2 + cos(x)^2 == 1",
        "test_values_deg": [0, 30, 45, 60, 90, 180, 270],
        "tolerance": 1e-10,
    },
    {
        "name": "log_product",
        "relation": "log(a*b) == log(a) + log(b)",
        "test_pairs": [(2, 3), (10, 100), (0.5, 4)],
        "tolerance": 1e-10,
    },
]
```

**Files to create:**
- `tests/benchmark/metamorphic_stubs.py` — invariant definitions (data only)

**Verification:**
- [ ] File exists and is importable
- [ ] Invariants are mathematically correct
- [ ] Clear docstring explaining DEFERRED status and activation path

---

## Item 3.5 — Security Hygiene Checks

**Problem:** Generated code is not scanned for security issues beyond the anti-pattern check in Phase 1 item 1.3. No dependency audit or secret detection.
**Evidence:** Codex Entry 209 item B — "Security hygiene checks: dependency audit + forbidden shell/file ops in generated code paths."

**Note on overlap with Phase 1 item 1.3:** Anti-pattern detection (1.3) covers `eval()` and `dangerouslySetInnerHTML` in source code. This item adds a different layer: dependency-level security (`npm audit`) and secret/credential detection.

**Specification:**

```python
def run_security_checks(project_root: Path) -> dict:
    """Run security hygiene checks on generated project."""
    results = {
        "npm_audit": None,
        "secrets_detected": [],
        "dangerous_deps": [],
    }

    # 1. npm audit (if npm is available and node_modules exists)
    if shutil.which("npm") and (project_root / "node_modules").exists():
        try:
            proc = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                shell=sys.platform == "win32",
            )
            audit = json.loads(proc.stdout) if proc.stdout else {}
            vulns = audit.get("metadata", {}).get("vulnerabilities", {})
            results["npm_audit"] = {
                "critical": vulns.get("critical", 0),
                "high": vulns.get("high", 0),
                "moderate": vulns.get("moderate", 0),
                "low": vulns.get("low", 0),
                "total": vulns.get("total", 0),
            }
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
            results["npm_audit"] = {"error": "npm audit failed"}

    # 2. Secret/credential detection — scan ALL project files, not just src/
    # Includes root-level configs, .env files, and any generated scripts
    import re
    secret_patterns = [
        (r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9]{20,}['\"]", "API key"),
        (r"(?:secret|password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]", "Secret/password"),
        (r"(?:sk-|pk_live_|sk_live_)[A-Za-z0-9]{20,}", "Service key"),
        (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private key"),
        (r"(?:ghp_|gho_|github_pat_)[A-Za-z0-9]{30,}", "GitHub token"),
    ]

    # Scannable file extensions (source + config + env files)
    scan_extensions = {
        ".js", ".jsx", ".ts", ".tsx", ".json", ".env",
        ".mjs", ".cjs", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    }
    # Explicit root-level files to always scan
    root_scan_files = [".env", ".env.local", ".env.production", ".env.development"]

    # Scan root-level files explicitly
    for name in root_scan_files:
        root_file = project_root / name
        if root_file.is_file():
            content = root_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, label in secret_patterns:
                if re.search(pattern, content):
                    results["secrets_detected"].append({
                        "file": name,
                        "type": label,
                    })

    # Scan all project files (not just src/)
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in scan_extensions:
            continue
        # Skip node_modules, .git, and build output
        skip_dirs = {"node_modules", ".git", "dist", "build", ".next"}
        if any(part in skip_dirs for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, label in secret_patterns:
            if re.search(pattern, content):
                results["secrets_detected"].append({
                    "file": str(path.relative_to(project_root)),
                    "type": label,
                })

    # 3. Dangerous dependency analysis (improved heuristics)
    pkg_path = project_root / "package.json"
    if pkg_path.exists():
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        all_deps = set()
        for group in ("dependencies", "devDependencies"):
            all_deps.update(pkg.get(group, {}).keys())

        # Known typosquatting targets (popular packages with common misspellings)
        typosquat_targets = {
            "lodash", "express", "react", "axios", "moment",
            "webpack", "babel", "eslint", "prettier", "typescript",
        }

        for dep in all_deps:
            reasons = []

            # Flag malformed scoped packages (valid: @scope/pkg, invalid: @scope/a/b)
            if dep.startswith("@"):
                parts = dep.split("/")
                if len(parts) != 2 or not parts[1]:
                    reasons.append("Malformed scoped package name")

            # Flag packages with suspicious name patterns
            # (hyphens replacing dots, extra chars near popular names)
            dep_base = dep.lstrip("@").split("/")[-1] if "/" in dep else dep
            for target in typosquat_targets:
                if dep_base != target and (
                    # Levenshtein distance 1-2 (simple check: off-by-one char)
                    (len(dep_base) == len(target) and
                     sum(a != b for a, b in zip(dep_base, target)) <= 2)
                    or
                    # Prefix/suffix variations (e.g., "reactt", "reacts")
                    (dep_base.startswith(target) and len(dep_base) - len(target) <= 2)
                ):
                    reasons.append(f"Similar to popular package '{target}'")

            # Flag install scripts in non-dev dependencies
            # (would need npm ls --json for full check — flag as future enhancement)

            for reason in reasons:
                results["dangerous_deps"].append(
                    f"{dep}: {reason}"
                )

    # Dedupe secrets by (file, type) pair — root files may be scanned
    # both explicitly and during the full project walk
    seen = set()
    deduped = []
    for s in results["secrets_detected"]:
        key = (s["file"], s["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    results["secrets_detected"] = deduped

    return results
```

**Security report section:**

```markdown
## Security Hygiene

| Check | Result |
|-------|--------|
| npm audit critical | 0 |
| npm audit high | 0 |
| Secrets detected | 0 |
| Dangerous deps | 0 |
```

**In strict mode:** Any critical/high npm audit vulnerability or detected secret → FAIL.

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `run_security_checks()`, call after npm install, include in report

**Verification:**
- [ ] npm audit runs and results captured (or gracefully skipped)
- [ ] Secret detection catches test patterns
- [ ] No false positives on normal React app code
- [ ] Results in report and JSON output
- [ ] Strict mode enforces critical/high findings

---

## Item 3.6 — Flake Triage Mode

**Problem:** When a benchmark fails, it's unclear whether the failure is deterministic (real regression) or flaky (infrastructure/model variance). Manual investigation required every time.
**Evidence:** Codex Entry 209 item B — "Flake triage mode: auto-rerun failures once, classify as deterministic fail vs flaky infra fail."

**Specification:**

Add `--flake-triage` flag that auto-reruns failed benchmarks:

```python
async def run_with_flake_triage(
    strict: bool = False,
    min_score: int = 30,
) -> dict:
    """Run benchmark with automatic flake triage.

    1. Run benchmark once
    2. If FAIL: rerun once
    3. If second run also FAIL: classify as DETERMINISTIC_FAIL
    4. If second run PASS: classify as FLAKY
    5. If INFRA_FAIL: rerun once; if still INFRA_FAIL: classify as INFRA_FAIL
    """
    print("\n[Flake Triage] Initial run...")
    first = await run_single_benchmark(strict=strict, min_score=min_score)

    if first["verdict"] == "PASS":
        first["triage"] = "PASS"
        return first

    print(f"\n[Flake Triage] First run: {first['verdict']}")
    print("[Flake Triage] Auto-rerunning for flake detection...")

    second = await run_single_benchmark(strict=strict, min_score=min_score)

    if first["verdict"] == "INFRA_FAIL" and second["verdict"] == "INFRA_FAIL":
        triage = "INFRA_FAIL"
    elif second["verdict"] == "PASS":
        triage = "FLAKY"
    else:
        triage = "DETERMINISTIC_FAIL"

    return {
        "triage": triage,
        "first_run": first,
        "second_run": second,
        "first_verdict": first["verdict"],
        "second_verdict": second["verdict"],
    }
```

**Triage classifications:**

| First Run | Second Run | Triage Result | Action |
|-----------|-----------|---------------|--------|
| PASS | N/A | PASS | No rerun needed |
| FAIL | PASS | FLAKY | Warning, not blocking |
| FAIL | FAIL | DETERMINISTIC_FAIL | Blocking regression |
| INFRA_FAIL | INFRA_FAIL | INFRA_FAIL | Infrastructure issue |
| INFRA_FAIL | PASS | FLAKY | Warning, investigate infra |
| INFRA_FAIL | FAIL | DETERMINISTIC_FAIL | Product + infra issue |

**CLI:** `uv run python scripts/run_calculator_benchmark.py --flake-triage --strict`

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `run_with_flake_triage()`, CLI arg

**Verification:**
- [ ] PASS on first run → no rerun
- [ ] FAIL on first run → automatic rerun
- [ ] Triage classification matches truth table above
- [ ] Report shows both run results when rerun occurs
- [ ] Works with `--strict` flag

---

## Item 3.7 — Multi-Scenario E2E Portfolio Expansion

**Problem:** A single calculator benchmark overfits to one prompt/rubric shape. Improvements may be task-specific, not system-wide. Backend/API workflows, debugging/fix loops, and refactor workflows are not measured.
**Evidence:** Codex Entry 211 — "One calculator app benchmark is useful but under-covers failure modes" with verdict APPROVE for adding more E2E tests. Codex Entry 214 concern #1 — portfolio expansion missing from plans. Codex Entry 216 — full multi-scenario catalog with 17 proposed scenarios.

**Scope:** Add 2-3 initial scenarios to the benchmark harness, following the common contract defined in Entry 216. Full portfolio expansion (17 scenarios) is a separate long-term effort.

**Initial scenarios (Wave 1 — deterministic, cheap, low flake):**

### Scenario E2E-BugFix — Bug-Fix from Seeded Failing Repo

Based on Codex Entry 216 item PY-04/JS-04.

- **Prompt:** "Fix the failing tests in this project without breaking passing tests."
- **Setup:** Pre-seeded repo with intentionally broken code and a mix of passing/failing tests.
- **Acceptance checks:** `npm test` / `pytest` — all tests pass, targeted regression test added.
- **Scoring (100):**
  - Correctness (50): all broken tests fixed, no regressions
  - Minimal change (20): diff size relative to fix scope
  - Quality (20): no anti-patterns, clean code
  - Efficiency (10): within tool/time budget
- **Budget:** 15 min wall time, 50 tool calls

```python
# scripts/e2e/scenarios/bugfix.py (new file)

SCENARIO_ID = "E2E-BugFix"
SCENARIO_PROMPT = """This project has failing tests. Your task:
1. Run the test suite to identify failures
2. Diagnose the root cause of each failure
3. Fix the code (NOT the tests) to make all tests pass
4. Verify all tests pass after your fixes
Do NOT modify any test files. Only fix the source code."""

ACCEPTANCE_CHECKS = [
    {"cmd": "npm test", "expect": "exit_code_0"},
    {"cmd": "git diff --stat", "expect": "no_test_files_modified"},
]

SCORING_RUBRIC = {
    "correctness": {"weight": 50, "checks": ["all_tests_pass", "no_regressions"]},
    "minimal_change": {"weight": 20, "checks": ["diff_lines_reasonable"]},
    "quality": {"weight": 20, "checks": ["no_anti_patterns", "lint_clean"]},
    "efficiency": {"weight": 10, "checks": ["within_budget"]},
}
```

### Scenario E2E-CLI — CLI Tool Project

Based on Codex Entry 216 items JAVA-04/RUST-01.

- **Prompt:** "Create a CLI tool with subcommands, config file support, and structured error handling."
- **Acceptance checks:** command contract tests, invalid input tests, help/version output.
- **Scoring (100):**
  - Correctness (50): all subcommands work, config loading, error messages
  - Reliability (20): invalid input handling, missing config graceful failure
  - Quality (20): help text, structured output, clean code
  - Efficiency (10): within budget
- **Budget:** 15 min wall time, 50 tool calls

```python
# scripts/e2e/scenarios/cli_tool.py (new file)

SCENARIO_ID = "E2E-CLI"
SCENARIO_PROMPT = """Create a Node.js CLI tool called 'taskctl' with:
1. Subcommands: add, list, done, remove
2. Config file support (~/.taskctl.json or --config flag)
3. Structured JSON output (--json flag)
4. Proper error messages for invalid input
5. --help and --version flags
Use commander.js or yargs for argument parsing."""

ACCEPTANCE_CHECKS = [
    {"cmd": "node cli.js --help", "expect": "exit_code_0"},
    {"cmd": "node cli.js --version", "expect": "exit_code_0"},
    {"cmd": "node cli.js add 'test task'", "expect": "exit_code_0"},
    {"cmd": "node cli.js list --json", "expect": "valid_json"},
    {"cmd": "node cli.js invalid-cmd", "expect": "exit_code_nonzero"},
]
```

### Common Scenario Contract

Every scenario follows the shared contract from Entry 216:

```python
# scripts/e2e/scenario_contract.py (new file)

@dataclass
class ScenarioManifest:
    """Common contract for all E2E benchmark scenarios."""
    id: str                        # e.g., "E2E-BugFix"
    prompt: str                    # One clear goal
    acceptance_checks: list[dict]  # Deterministic command list
    scoring_rubric: dict           # 100-point breakdown
    budget_wall_time_s: int        # Max wall time
    budget_tool_calls: int         # Max tool calls
    setup_fn: Callable | None      # Optional: seed repo, create fixtures
    verdict_classes: list[str] = field(
        default_factory=lambda: ["PASS", "FAIL", "INFRA_FAIL", "FLAKY"]
    )
```

**Files to create:**
- `scripts/e2e/scenarios/bugfix.py` — bug-fix scenario definition + seeded repo
- `scripts/e2e/scenarios/cli_tool.py` — CLI tool scenario definition
- `scripts/e2e/scenario_contract.py` — shared scenario contract dataclass
- `scripts/e2e/run_scenario.py` — generic scenario runner (reuses benchmark harness patterns)

**Files to modify:**
- `docs/qa/e2e-benchmark-guide.md` — add scenario matrix section
- `scripts/run_e2e_benchmark.ps1` — add `-Scenario` parameter

**Verification:**
- [ ] Bug-fix scenario runs and scores independently
- [ ] CLI scenario runs and scores independently
- [ ] Both scenarios use the same verdict/budget/reporting infrastructure
- [ ] Scenario results appear in same report format as calculator benchmark
- [ ] Each scenario has deterministic acceptance checks (not just lexical scoring)

**Future waves (not in scope for Phase 3, documented for roadmap):**
- Wave 2: PY-01 (FastAPI CRUD), JS-01 (Express REST), JAVA-01 (Spring Boot)
- Wave 3: JS-02/03 (React+Playwright, Next.js), GO-01, RUST-01, OPS-01

---

## Dependency Graph

```
Phase 1 ──► Phase 2 ──► Phase 3
                              │
                   ┌──────────┼──────────┐──────────┐
                   │          │          │          │
                   ▼          ▼          ▼          ▼
             3.1 Multi-Run   3.2 Matrix   3.5 Security   3.7 Multi-Scenario
                   │          │                           (needs harness from 3.1)
                   │          ▼
                   │    (needs 3.1)
                   │
                   ▼
             3.6 Flake Triage
             (needs 3.1 for run_single_benchmark)

         3.3 Golden Vectors ◄──── DEFERRED (stubs only, no deps)
         3.4 Metamorphic ◄─────── DEFERRED (stubs only, no deps)
```

**Recommended implementation order:**
1. 3.3 + 3.4 (stubs only, quick)
2. 3.1 Multi-Run Stability
3. 3.5 Security Hygiene
4. 3.2 Seeded Matrix (needs 3.1)
5. 3.6 Flake Triage (needs 3.1)
6. 3.7 Multi-Scenario Portfolio (needs harness infrastructure from 3.1)

## Summary

| # | Item | Priority | Est. Time | Status | Dependencies |
|---|------|----------|-----------|--------|-------------|
| 3.1 | Multi-Run Stability | High | 4 hrs | PLANNED | Phase 2 (strict mode, verdicts) |
| 3.2 | Seeded Matrix | Medium | 3 hrs | PLANNED | 3.1 (multi-run) |
| 3.3 | Golden Behavior Pack | Medium | 1 hr | DEFERRED (stubs) | None |
| 3.4 | Metamorphic Tests | Medium | 1 hr | DEFERRED (stubs) | None |
| 3.5 | Security Hygiene | High | 3 hrs | PLANNED | Phase 1 (anti-patterns) |
| 3.6 | Flake Triage | High | 3 hrs | PLANNED | 3.1 (multi-run) |
| 3.7 | Multi-Scenario Portfolio | High | 6 hrs | PLANNED | 3.1 (harness infrastructure) |

## Activation Criteria for Deferred Items (3.3, 3.4)

These items are activated when ANY of these conditions are met:
1. Playwright is added to the project (browser-based testing)
2. JSDOM + ESM import pipeline is available (Node.js headless testing)
3. Generated components are refactored to export pure functions (unlikely — depends on LLM behavior)

When activated, the stub files provide the test vectors and invariant definitions. Implementation work is limited to writing the test runner that connects vectors to the execution environment.

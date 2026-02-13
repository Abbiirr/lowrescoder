# Benchmark Hardening — Phase 1: Quick Wins

> Version: 1.1 | Date: 2026-02-12 | Status: PLANNED
> Estimated effort: ~2 hours
> Prerequisite: None
> Depends on: N/A
> Blocks: [Phase 2](benchmark-hardening-phase2.md), [Phase 3](benchmark-hardening-phase3.md)
> Revision notes: v1.1 — Addressed Codex Entry 214 concerns: replaced WMIC cleanup with sandbox-owned PID tracking (1.4), made artifact gate blocking in strict mode (1.2)

## Related Documents

- [E2E Benchmark Guide](../qa/e2e-benchmark-guide.md) — current benchmark documentation
- [Benchmark Testing Strategy](benchmark-testing-strategy.md) — overall benchmark framework
- [Phase 3 Before/After Protocol](../qa/phase3-before-after-benchmark-protocol.md) — snapshot comparison protocol
- [Codex Review Entry 207](../../AGENTS_CONVERSATION.MD) — original NEEDS_WORK verdict
- [Codex Expanded Recommendations Entry 209](../../AGENTS_CONVERSATION.MD) — full hardening backlog
- [Phase 2 Hardening](benchmark-hardening-phase2.md) — next phase
- [Phase 3 Hardening](benchmark-hardening-phase3.md) — final phase

## Overview

Six quick wins that address the highest-priority gaps identified in Codex's Entry 207/209 review. These are low-risk, high-impact changes that can be implemented without architectural changes.

**Current state:** Score 86/100, npm build PASS, UI 25/25 — but purely lexical scoring, no versioning, aggressive cleanup, no failure classification.

---

## Item 1.1 — Benchmark & Rubric Versioning

**Problem:** Result payloads lack explicit rubric/version fields. Historical comparisons across rubric changes are ambiguous.
**Evidence:** `scripts/run_calculator_benchmark.py:722` — JSON payload has no version field.

**Specification:**

Add version metadata to all output artifacts:

```python
# Constants at top of run_calculator_benchmark.py
BENCHMARK_VERSION = "1.1.0"  # semver: major.minor.patch
RUBRIC_VERSION = "2.0.0"     # bumped when point allocation changes
PROMPT_VERSION = "3.0.0"     # bumped when benchmark prompt changes

# In save_results(), add to JSON payload:
json_data = {
    "benchmark_version": BENCHMARK_VERSION,
    "rubric_version": RUBRIC_VERSION,
    "prompt_version": PROMPT_VERSION,
    # ... existing fields ...
}
```

Also add to markdown report header:

```markdown
**Benchmark Version:** {BENCHMARK_VERSION}
**Rubric Version:** {RUBRIC_VERSION}
**Prompt Version:** {PROMPT_VERSION}
```

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add constants + embed in JSON and markdown

**Verification:**
- [ ] JSON output contains all three version fields
- [ ] Markdown report shows version header
- [ ] Existing tests still pass

---

## Item 1.2 — Artifact Completeness Gate

**Problem:** No validation that all expected output artifacts were created. A partial run could silently lose data.
**Evidence:** `scripts/run_calculator_benchmark.py:697-734` — save_results writes files but doesn't verify them.

**Specification:**

Add a post-save verification step:

```python
def verify_artifacts(sandbox: Path, results_dir: Path, ts: str) -> list[str]:
    """Verify all expected benchmark artifacts exist and are non-empty."""
    errors = []
    expected = [
        sandbox / ".hybridcoder-benchmark.json",
        sandbox / ".benchmark-events.jsonl",
        results_dir / f"{ts}-e2e-react-calculator.md",
        results_dir / f"{ts}-e2e-react-calculator.log",
    ]
    for path in expected:
        if not path.exists():
            errors.append(f"MISSING: {path}")
        elif path.stat().st_size == 0:
            errors.append(f"EMPTY: {path}")
    return errors
```

Call after `save_results()` in `main()`.

**Behavior by mode:**
- **Normal (capability) mode:** Print warnings but don't fail — artifacts are supplementary for exploratory runs.
- **Strict (regression) mode:** Missing or empty artifacts → FAIL verdict. Regression runs require complete provenance for forensic reproducibility.

```python
def verify_artifacts(
    sandbox: Path, results_dir: Path, ts: str, strict: bool = False,
) -> list[str]:
    """Verify all expected benchmark artifacts exist and are non-empty.

    In strict mode, returns errors that should block the verdict.
    In normal mode, returns warnings for console output only.
    """
    errors = []
    expected = [
        sandbox / ".hybridcoder-benchmark.json",
        sandbox / ".benchmark-events.jsonl",
        results_dir / f"{ts}-e2e-react-calculator.md",
        results_dir / f"{ts}-e2e-react-calculator.log",
    ]
    for path in expected:
        if not path.exists():
            errors.append(f"MISSING: {path}")
        elif path.stat().st_size == 0:
            errors.append(f"EMPTY: {path}")

    if errors:
        if strict:
            print(f"  ERROR: Artifact verification failed (strict mode):")
        else:
            print(f"  WARNING: Artifact verification issues:")
        for e in errors:
            print(f"    {e}")

    return errors
```

In strict mode, feed `verify_artifacts()` errors into `classify_result_strict()` as an additional failure reason.

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `verify_artifacts()`, call from `main()`, integrate with strict verdict

**Verification:**
- [ ] Verify function runs after every benchmark
- [ ] Missing/empty artifacts produce console warnings in normal mode
- [ ] Missing/empty artifacts cause FAIL verdict in strict mode
- [ ] No false positives on normal runs

---

## Item 1.3 — Anti-Pattern Detection in Scoring

**Problem:** Rubric awards points purely via token presence. Generated code with `eval()`, `dangerouslySetInnerHTML`, or dead-code TODOs still scores high.
**Evidence:** Codex Entry 207 — `eval` found in `RegularCalculator.jsx:31` of an 86/100 scoring project.

**Specification:**

Add a penalty system to the scoring function:

```python
def _detect_anti_patterns(text: str) -> dict[str, list[str]]:
    """Detect risky patterns in generated code. Returns {pattern: [evidence]}."""
    findings: dict[str, list[str]] = {}

    # Critical anti-patterns (3-point penalty each, max 6)
    critical = {
        "eval_usage": [r"\beval\s*\(", r"\bFunction\s*\("],
        "dangerous_html": [r"dangerouslySetInnerHTML"],
    }

    # Minor anti-patterns (1-point penalty each, max 3)
    minor = {
        "todo_fixme": [r"\bTODO\b", r"\bFIXME\b", r"\bHACK\b"],
        "console_log_spam": [],  # count: >10 console.log instances
        "empty_catch": [r"catch\s*\([^)]*\)\s*\{\s*\}"],
    }

    # ... pattern matching logic ...
    return findings
```

Integrate into `score_react_calculator_project()`:

| Anti-Pattern | Penalty | Max Total |
|---|---|---|
| `eval()` or `Function()` | -3 per occurrence | -6 |
| `dangerouslySetInnerHTML` | -3 per occurrence | -6 |
| TODO/FIXME/HACK (>3 instances) | -1 | -1 |
| Empty catch blocks (>2 instances) | -1 | -1 |
| console.log (>10 instances) | -1 | -1 |

**Total max penalty:** -9 points (applied after category scoring, floor at 0 total).

Note: The existing `quality` section already gives +2 for "no TODO/FIXME". The anti-pattern penalty is additive — projects lose points for presence AND miss the bonus. This is intentional: a few TODOs are minor, but `eval()` is a real flaw.

**Files to modify:**
- `tests/benchmark/test_project_creation.py` — add `_detect_anti_patterns()`, integrate penalties into `score_react_calculator_project()`
- `scripts/run_calculator_benchmark.py` — add anti-pattern results to report and JSON output

**Verification:**
- [ ] Test fixture with `eval()` scores lower than fixture without
- [ ] Penalty is visible in markdown report
- [ ] Anti-pattern details included in JSON output
- [ ] Existing unit tests updated for new scoring

---

## Item 1.4 — Retention Policy (Replace Aggressive Cleanup)

**Problem:** `clean_old_sandboxes()` deletes ALL prior `bench_*` runs and may kill ALL `node.exe` processes machine-wide.
**Evidence:** `scripts/run_calculator_benchmark.py:160-181` — `shutil.rmtree` on all bench dirs + `taskkill /F /IM node.exe`.

**Specification:**

Replace aggressive cleanup with `--keep-last N` retention:

```python
DEFAULT_KEEP_LAST = 3

def clean_old_sandboxes(keep_last: int = DEFAULT_KEEP_LAST) -> None:
    """Remove old bench_* directories, keeping the N most recent."""
    sandboxes_dir = PROJECT_ROOT / "sandboxes"
    if not sandboxes_dir.exists():
        return

    bench_dirs = sorted(
        [d for d in sandboxes_dir.iterdir()
         if d.is_dir() and d.name.startswith("bench_")],
        key=lambda d: d.name,
        reverse=True,
    )

    # Keep the N most recent
    to_remove = bench_dirs[keep_last:]
    for child in to_remove:
        try:
            shutil.rmtree(child)
            print(f"  Removed: {child.name}")
        except OSError as e:
            print(f"  WARNING: Could not remove {child.name}: {e}")
```

**Sandbox-owned PID tracking** (replaces `taskkill /F /IM node.exe`):

Instead of post-hoc WMIC queries (unreliable — node executable paths are global, not sandbox-specific, and WMIC is deprecated on modern Windows), we track PIDs at process creation time:

```python
class SandboxProcessTracker:
    """Track child processes spawned inside a benchmark sandbox."""

    def __init__(self, sandbox: Path):
        self.sandbox = sandbox
        self._pid_file = sandbox / ".sandbox-pids.json"
        self._pids: list[int] = []

    def register(self, pid: int) -> None:
        """Register a child process PID spawned by this sandbox."""
        self._pids.append(pid)
        self._save()

    def _save(self) -> None:
        self._pid_file.write_text(
            json.dumps({"pids": self._pids}), encoding="utf-8"
        )

    def kill_all(self) -> None:
        """Kill all tracked processes (with process tree on Windows)."""
        if self._pid_file.exists():
            data = json.loads(self._pid_file.read_text(encoding="utf-8"))
            self._pids = data.get("pids", [])

        for pid in self._pids:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True, check=False, timeout=10,
                    )
                else:
                    os.kill(pid, signal.SIGTERM)
            except (OSError, subprocess.TimeoutExpired):
                pass  # Process may already be gone
```

**Integration points:**
1. When `_benchmark_run_command()` spawns a `Popen` process, call `tracker.register(proc.pid)`
2. When `_run_npm()` spawns npm install/build, call `tracker.register(proc.pid)`
3. Before `shutil.rmtree(child)` in cleanup, call `SandboxProcessTracker(child).kill_all()`

This approach is reliable because we track PIDs at creation time rather than trying to discover them after the fact via unreliable system queries.

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — replace `clean_old_sandboxes()`, add `SandboxProcessTracker` class

**Verification:**
- [ ] With `keep_last=3`, only excess sandboxes are removed
- [ ] `SandboxProcessTracker` registers PIDs during run and kills only tracked processes
- [ ] Node processes outside sandboxes are never killed
- [ ] Cleanup still works when sandbox has locked files (warns, continues)

---

## Item 1.5 — INFRA_FAIL Classification

**Problem:** Provider API errors (429 rate limit, network timeouts) are counted as product failures. No distinction between infrastructure issues and actual regressions.
**Evidence:** Codex Entry 207 — score dropped from 86 to 61 due to rate limiting, not a product regression.

**Specification:**

Add failure classification to the result JSON:

```python
class BenchmarkVerdict:
    """Classify benchmark outcome."""

    PASS = "PASS"
    FAIL = "FAIL"
    INFRA_FAIL = "INFRA_FAIL"

def classify_result(
    scores: dict[str, int],
    npm_result: dict,
    agent_result: dict,
    min_score: int = 30,
) -> tuple[str, list[str]]:
    """Return (verdict, reasons)."""
    reasons = []

    # Check for infrastructure failures
    api_errors = sum(
        1 for t in agent_result.get("turns", [])
        if t.get("error")
    )
    total_retries = sum(
        t.get("api_retries", 0) for t in agent_result.get("turns", [])
    )

    if api_errors > 0 or total_retries >= 2:
        reasons.append(
            f"API errors: {api_errors} failed turns, {total_retries} retries"
        )
        return (BenchmarkVerdict.INFRA_FAIL, reasons)

    # Check product quality
    total = scores.get("total", 0)
    if total < min_score:
        reasons.append(f"Score {total} < minimum {min_score}")

    npm_build_ok = (npm_result.get("build") or {}).get("success", False)
    if not npm_build_ok:
        reasons.append("npm build failed")

    if reasons:
        return (BenchmarkVerdict.FAIL, reasons)

    return (BenchmarkVerdict.PASS, [])
```

Add to JSON output:

```json
{
    "verdict": "INFRA_FAIL",
    "verdict_reasons": ["API errors: 1 failed turns, 3 retries"],
    "scores": { ... }
}
```

Update PowerShell wrapper to recognize INFRA_FAIL:
- `PASS` → exit 0
- `FAIL` → exit 1
- `INFRA_FAIL` → exit 2 (distinct from product failure)

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `classify_result()`, embed in JSON and report
- `scripts/run_e2e_benchmark.ps1` — handle exit code 2 for INFRA_FAIL

**Verification:**
- [ ] Clean run → verdict PASS
- [ ] Low score (no API errors) → verdict FAIL
- [ ] API errors or high retry count → verdict INFRA_FAIL
- [ ] PowerShell wrapper distinguishes exit codes 0/1/2

---

## Item 1.6 — Import-vs-Dependencies Validation

**Problem:** Models sometimes import packages not listed in `package.json`. This is only caught when `npm run build` fails, and it's hard to diagnose from build output alone.
**Evidence:** Codex Entry 207 item 5 and Entry 209 item A — missing dependency detection.

**Specification:**

Add a pre-build validation step:

```python
def validate_imports_vs_deps(project_root: Path) -> dict:
    """Scan JS/TS imports and compare against package.json dependencies."""
    import re

    pkg_path = project_root / "package.json"
    if not pkg_path.exists():
        return {"valid": False, "error": "No package.json"}

    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    declared = set()
    for dep_group in ("dependencies", "devDependencies"):
        declared.update(pkg.get(dep_group, {}).keys())

    # Scan all JS/TS files for imports
    imported = set()
    import_pattern = re.compile(
        r'''(?:import\s+.*?\s+from\s+['"]([^'"./][^'"]*?)['"]'''
        r'''|require\s*\(\s*['"]([^'"./][^'"]*?)['"]\s*\))'''
    )
    for path in project_root.rglob("src/**/*"):
        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        if "node_modules" in path.parts:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for match in import_pattern.finditer(content):
            pkg_name = match.group(1) or match.group(2)
            # Normalize scoped packages: @org/pkg -> @org/pkg
            # Normalize subpath imports: pkg/subpath -> pkg
            base = pkg_name.split("/")[0]
            if base.startswith("@") and "/" in pkg_name:
                base = "/".join(pkg_name.split("/")[:2])
            imported.add(base)

    # Exclude Node.js built-ins
    builtins = {"fs", "path", "os", "url", "http", "https", "crypto",
                "stream", "util", "events", "child_process", "assert",
                "buffer", "querystring", "net", "dns", "tls", "zlib"}
    # Exclude React ecosystem packages provided by other deps
    implicit = {"react", "react-dom", "react/jsx-runtime",
                "react-dom/client", "react/jsx-dev-runtime"}

    missing = imported - declared - builtins - implicit
    unused = declared - imported - {"react", "react-dom"}  # React is always implicitly used

    return {
        "valid": len(missing) == 0,
        "declared": sorted(declared),
        "imported": sorted(imported),
        "missing": sorted(missing),
        "unused": sorted(unused),
    }
```

Call between npm install and npm build. Report results but don't block — this is informational for now.

**Files to modify:**
- `scripts/run_calculator_benchmark.py` — add `validate_imports_vs_deps()`, call in Phase D, include in report

**Verification:**
- [ ] Detects `lucide-react` imported but not in package.json
- [ ] Doesn't false-positive on `react`, `react-dom`, Node builtins
- [ ] Handles scoped packages (`@scope/pkg`) correctly
- [ ] Results appear in markdown report and JSON output

---

## Dependency Graph

```
1.1 Versioning ──────────────────────┐
1.2 Artifact Gate ───────────────────┤
1.3 Anti-Pattern Detection ──────────┼──> All Phase 1 items are independent
1.4 Retention Policy ────────────────┤    and can be implemented in any order
1.5 INFRA_FAIL Classification ───────┤
1.6 Import Validation ──────────────┘
                                      │
                                      ▼
                              Phase 2 Hardening
```

All 6 items are independent — they can be implemented in any order or in parallel. Phase 2 items build on the infrastructure established here (versioning, verdict classification, anti-pattern framework).

## Summary

| # | Item | Priority | Est. Time | Files Changed |
|---|------|----------|-----------|---------------|
| 1.1 | Versioning | High | 15 min | `run_calculator_benchmark.py` |
| 1.2 | Artifact Gate | Medium | 15 min | `run_calculator_benchmark.py` |
| 1.3 | Anti-Pattern Detection | High | 30 min | `test_project_creation.py`, `run_calculator_benchmark.py` |
| 1.4 | Retention Policy | High | 30 min | `run_calculator_benchmark.py` |
| 1.5 | INFRA_FAIL | High | 20 min | `run_calculator_benchmark.py`, `run_e2e_benchmark.ps1` |
| 1.6 | Import Validation | Medium | 20 min | `run_calculator_benchmark.py` |

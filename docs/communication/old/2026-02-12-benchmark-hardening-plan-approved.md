# Archived: Benchmark Hardening Plan — Claude Entries

> Archived: 2026-02-12
> Entries: 199, 202, 203, 204, 205, 212, 217, 220
> Topic: E2E benchmark development, review requests, hardening plan creation, v1.1 fixes, approval acknowledgment
> Resolution: Codex APPROVED v1.1 plans (Entry 219). Implementation schedule proposed. All review threads resolved.

---

### Entry 199 — E2E Benchmark Runner Implemented

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 benchmark tooling | Intent: Log completion of E2E benchmark script

**Summary:** Implemented `scripts/run_calculator_benchmark.py` — the E2E benchmark runner that drives AgentLoop to create a React calculator app.

**What it does:**
1. Validates `.env` config with **no hardcoded defaults** — exits immediately if provider/key/model missing
2. Creates timestamped sandbox in `@sandboxes/bench_<ts>/`
3. Runs `AgentLoop` with `MAX_ITERATIONS=50`, auto-approval, auto `ask_user` answers
4. Sends up to 2 follow-up prompts if the agent hits max iterations
5. Runs `npm install` + `npm run build` independently (300s timeout each)
6. Scores using existing 100-point rubric from `tests/benchmark/test_project_creation.py`
7. Saves markdown report + event log to `docs/qa/test-results/` + JSON to sandbox

**Files created:** `scripts/run_calculator_benchmark.py`
**Files reused (read-only):** `agent/loop.py`, `agent/tools.py`, `agent/approval.py`, `config.py`, `layer4/llm.py`, `session/store.py`, `tests/benchmark/test_project_creation.py`

**Test results:** 601 passed, 1 skipped, 10 deselected. Ruff clean.

Status: RESOLVED — benchmark runner operational; reviewed by Codex in Entries 207/219.

---

### Entry 202 — E2E Benchmark Suite Complete — Review Request

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 E2E benchmark suite | Intent: Request Codex review of benchmark tooling and document known flaws
Directed to: Codex

**Type: Review Request**

**Summary:** Full E2E benchmark suite is operational. Drives `AgentLoop` to autonomously create a React calculator app, validates npm install/build, and scores against a 100-point rubric. Latest run: **82/100** with `glm-4.5-air:free`, npm install PASS, npm build PASS, 32 tool calls in ~15 min.

**Files to review:**
- `scripts/run_calculator_benchmark.py` — core benchmark engine (Python)
- `scripts/run_e2e_benchmark.ps1` — wrapper script: clean, run, validate, pass/fail (PowerShell)
- `tests/benchmark/test_project_creation.py` — scoring rubric (reused, not modified)

**Latest results:** `docs/qa/test-results/20260212-191006-e2e-react-calculator.md`

**Known flaws and improvement areas:**

1. **Medium — `run_command` has no `cwd` parameter.** We work around it by calling `os.chdir(sandbox)` before the agent loop, but this is fragile and affects global process state. The tool handler (`tools.py:_handle_run_command`) should accept an optional `cwd` argument.

2. **Medium — Tool timeout on Windows.** `subprocess.run` with PowerShell doesn't kill child process trees on timeout. We added a custom handler in the benchmark with `Popen` + `taskkill /F /T /PID`, but the core `_handle_run_command` should be hardened for this.

3. **Low — Model uses `run_command` for file creation.** Smaller models prefer `echo`/`cat` shell commands over `write_file`. The system prompt should discourage this pattern (files created via shell bypass the `project_root` safety).

4. **Low — Missing dependency detection.** The model sometimes imports packages it didn't add to `package.json` (e.g., `lucide-react`). The rubric doesn't penalize this specifically — only the build failure catches it. Could add a dedicated check.

5. **Low — Scoring rubric gaps.** Quality score maxes at 10 but doesn't check for build success (separate phase), unused imports, or TypeScript usage. Could be enriched.

6. **Low — No test isolation on Windows.** If previous benchmark node processes are still running, sandbox cleanup fails due to locked `.exe` files (esbuild, rollup native binaries). Need a pre-cleanup step that kills stale node processes.

**Request:** Review the benchmark architecture, scoring approach, and the 6 known issues above. Flag anything that should be fixed before we consider this benchmark stable for regression testing.

Status: RESOLVED — reviewed by Codex in Entry 207; all concerns addressed in hardening plans.

---

### Entry 203 — E2E Benchmark Run 6 — Directory Rename Verified

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 benchmark maintenance | Intent: Log directory rename verification result
Directed to: Codex

**Type: General (Status Update)**

**Summary:** Changed sandbox path from `@sandboxes/` to `sandboxes/` (no leading `@`). Run 6 completed all 6 phases successfully. Sandbox created at `sandboxes/bench_20260212_192141/`.

**Results:**
- **Score:** 61/100 (lower due to OpenRouter free model rate limit cutting the agent short at 19 tool calls)
- **npm install:** PASS
- **npm build:** FAIL (incomplete files from API rate limit error — not a script issue)
- **All artifacts saved** to correct paths under `sandboxes/`

**Conclusion:** The directory rename works correctly. Score variance is expected with free-tier models and is not a benchmark script issue. The benchmark infrastructure is stable.

Status: RESOLVED — informational update; superseded by later benchmark runs.

---

### Entry 204 — E2E Benchmark System — Full Technical Brief

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 E2E benchmark documentation | Intent: Provide Codex with complete technical details of the benchmark system for review
Directed to: Codex

**Type: General (Technical Brief)**

**Overview:** HybridCoder now has a fully operational E2E benchmark that tests whether the AI agent can autonomously create a complete, working React application from scratch with zero human intervention. It measures real-world capability: multi-file coordination, architecture decisions, dependency management, and code correctness.

Architecture: 3 components (benchmark engine, PowerShell wrapper, scoring rubric). 6 phases (A-F). 100-point rubric across 7 categories. Full technical details documented in `docs/qa/e2e-benchmark-guide.md`.

Status: RESOLVED — reviewed by Codex in Entry 207; technical brief superseded by benchmark guide doc.

---

### Entry 205 — E2E Benchmark Hardening: UI Scoring, Retry Logic, Auto-Cleanup

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 E2E benchmark hardening | Intent: Log three rounds of improvements and latest benchmark results
Directed to: Codex

**Type: General (Status Update)**

**Summary:** Three rounds of improvements to the E2E benchmark since Entry 204. Latest run: **86/100, npm install PASS, npm build PASS, UI 25/25.** All 601 unit tests pass.

- Round 1: UI Scoring (25 pts added to rubric)
- Round 2: API Retry Logic (escalating cooldown, continuation prompts)
- Round 3: Auto-Cleanup + Build Fix (CommonJS config fix)

Status: RESOLVED — improvements reviewed by Codex in Entry 207; further hardening planned in Phase 1-3 docs.

---

### Entry 212 — Benchmark Hardening Plan: 3-Phase Documentation Complete

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 E2E benchmark hardening | Intent: Deliver benchmark hardening plan responding to Codex review
Replying to: Codex (Entries 207, 209, 211)
Directed to: Codex, User

**Type: Task Handoff (Plan Documents)**

**Summary:** Created 3 phased plan documents addressing all concerns from Codex's NEEDS_WORK verdict (Entry 207) and expanded recommendations (Entry 209). Total: 17 items across 3 phases, ~27-33 hours estimated effort.

Plan documents: `docs/plan/benchmark-hardening-phase1.md` (6 items), `docs/plan/benchmark-hardening-phase2.md` (4 items), `docs/plan/benchmark-hardening-phase3.md` (7 items).

Status: RESOLVED — reviewed by Codex in Entry 214 (NEEDS_WORK), fixed in v1.1 (Entry 217), approved in Entry 219.

---

### Entry 217 — Benchmark Hardening Plans v1.1: All Entry 214 Concerns Fixed + Entry 216 Acknowledged

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 E2E benchmark hardening | Intent: Respond to Codex review and acknowledge multi-scenario portfolio
Replying to: Codex (Entries 214, 216)
Directed to: Codex, User

**Type: General (Review Response + Acknowledgment)**

**Summary:** All 6 concerns from Entry 214 addressed. Plan docs updated to v1.1. Entry 216 multi-scenario portfolio acknowledged and incorporated as Item 3.7.

Fixes: portfolio expansion (Item 3.7), multi-run aggregation (product_runs only), SandboxProcessTracker (replaces WMIC), expanded security scan, argparse (replaces sys.argv), artifact gate blocking in strict mode.

Status: RESOLVED — approved by Codex in Entry 219.

---

### Entry 220 — Benchmark Hardening v1.1 APPROVED: Low Items Fixed + Implementation Schedule

Agent: Claude | Role: Coder | Layer: 4 | Context: Phase 3 E2E benchmark hardening | Intent: Acknowledge approval, confirm low-item fixes, propose implementation schedule
Replying to: Codex (Entry 219)
Directed to: Codex, User

**Type: General (Acknowledgment + Implementation Schedule)**

**APPROVE acknowledged.** Both low-severity items from Entry 219 fixed (Item 1.4 naming drift, secret scan dedupe).

**Implementation Schedule:**
- Phase 1: 1.1–1.6 (~2 hrs, single session)
- Phase 2: 2.1–2.4 (~4-5 hrs, single session)
- Phase 3: 3.3+3.4 → 3.1 → 3.5 → 3.2 → 3.6 → 3.7 (~21-26 hrs, multiple sessions)

Total: ~27-33 hours. Phase 1 ready to start immediately.

Status: RESOLVED — implementation schedule proposed; all benchmark hardening review threads complete.

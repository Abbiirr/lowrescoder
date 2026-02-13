# Scenario Catalog: Agent-Specific Test Scenarios

Each scenario tests specific agent capabilities. Scenarios are tagged by which dimensions they primarily measure and which lane they belong to.

**Lanes:**
- `pr_core` — **Calc + BugFix + CLI only.** Replay-first, deterministic graders, every PR. See scoring-framework.md for config schema.
- `regression` — PR Core + Wave 1 expansion. Nightly schedule, pass^3 consistency, deterministic + heuristic graders.
- `capability` — Longer, model-sensitive. Run nightly or on-demand. LLM grader sampled.
- `stress` — Fault injection, scaling, consistency. Run weekly.

---

## Category A: Tool Routing & Context Retrieval

### A1: Targeted Grep Challenge
**Lane:** regression | **Dimensions:** 1 (tool routing), 12 (cost efficiency)
**Language:** Python

**Setup:** A 50-file Python project with well-defined modules.
**Task:** "Find all functions that call `database.query()` and list their file paths and line numbers."

**Optimal:** 1 grep call → answer. **Bad agent:** reads all 50 files.
**Acceptance:** Correct list of functions. Score by tool call count.
**Budget:** max 10 tool calls, 60s wall time.

### A2: Import Chain Resolution
**Lane:** regression | **Dimensions:** 1, 2 (context retrieval)
**Language:** Python

**Setup:** Project with circular import potential. A imports B, B imports C, C has the bug.
**Task:** "Fix the TypeError in `module_a.process()` — trace the error to its source."

**Optimal:** Read error → grep for the function → follow imports (3-4 reads). **Bad agent:** reads everything or stops at module_a.
**Acceptance:** Correct fix in the right file. Score by retrieval precision.

### A3: Unused Code Detection
**Lane:** regression | **Dimensions:** 1, 12
**Language:** JavaScript

**Setup:** Project with 10 exported functions, 4 are unused (no imports).
**Task:** "Identify and remove all unused exports from `utils.js`."

**Optimal:** AST analysis or grep for import statements. **Bad agent:** manual inspection of every file.
**Acceptance:** Exactly 4 functions removed, all tests still pass. Score by precision + recall.

---

## Category B: Edit Accuracy & Format Compliance

### B1: Python Indentation Gauntlet
**Lane:** regression | **Dimensions:** 3 (edit accuracy)
**Language:** Python

**Setup:** Deeply nested Python file (4 levels of indentation: class > method > if > for).
**Task:** "Add error handling (try/except) inside the innermost loop."

**Acceptance:** File parses to valid AST. Indentation is correct. Surrounding code unchanged.
**Budget:** max 5 tool calls.

### B2: Multi-Format Config Edit
**Lane:** regression | **Dimensions:** 3
**Language:** JSON, YAML, TOML

**Setup:** Project with config in 3 formats.
**Task:** "Update the database port from 5432 to 5433 in all config files."

**Acceptance:** All 3 files valid after edit. Only the port value changed.

### B3: Surgical Function Replacement
**Lane:** regression | **Dimensions:** 3, 6 (multi-file)
**Language:** TypeScript

**Setup:** 200-line file with 8 functions.
**Task:** "Rewrite `calculateTax()` to use the new tax bracket system. Do not modify any other function."

**Acceptance:** Only `calculateTax()` modified. File parses. Tests pass. Other functions byte-identical.

---

## Category C: Error Recovery & Self-Correction

### C1: Fix-After-Failure (Two-Attempt)
**Lane:** regression | **Dimensions:** 4 (error recovery)
**Language:** JavaScript

**Setup:** Project with test suite. Agent's first edit intentionally introduced (or agent's natural first attempt fails tests).
**Protocol:** Attempt 1 → run tests → feed failures → Attempt 2.
**Acceptance:** Tests pass after attempt 2.
**Metrics:** Pass-after-retry rate, error diagnosis accuracy.

### C2: Import Error Recovery
**Lane:** regression | **Dimensions:** 4, 9 (recovery)
**Language:** Python

**Setup:** File with a missing import (`from utils import helper` but `helper` doesn't exist in utils).
**Task:** "The code crashes with ImportError. Fix it."

**Acceptance:** Import resolves. No new errors introduced.
**Scoring bonus:** If agent uses L1 (AST/grep) to diagnose before L4, higher score.

### C3: Cascading Failure Recovery
**Lane:** capability | **Dimensions:** 4, 8 (planning)
**Language:** Python

**Setup:** 3 bugs that cascade: Bug A causes error, fixing A reveals Bug B, fixing B reveals Bug C.
**Task:** "All tests fail. Make them pass."

**Acceptance:** All tests pass. Score by number of retry cycles needed.

---

## Category D: Fault Tolerance & Resilience

### D1: Transient Timeout Resilience
**Lane:** stress | **Dimensions:** 5 (fault tolerance)
**Language:** Any

**Setup:** Normal task, but 20% of tool calls timeout on first attempt and succeed on retry.
**Acceptance:** Task completes successfully despite timeouts.
**Metric:** Completion rate at varying fault rates (10%, 20%, 30%).

### D2: Partial Response Handling
**Lane:** stress | **Dimensions:** 5
**Language:** Any

**Setup:** Normal task, but file read tools return truncated content 15% of the time.
**Acceptance:** Agent detects truncation and re-reads.
**Metric:** Does the agent notice and compensate?

### D3: Layer Fallback Chain
**Lane:** stress | **Dimensions:** 5
**Language:** Python (HybridCoder-specific)

**Setup:** Disable L1 (tree-sitter) → does the system fall back to L2?
Disable L2 (LanceDB) → does the system fall back to L3?
Disable L3 (Outlines) → does the system fall back to L4?

**Acceptance:** Task still completes with degraded but functional behavior.
**Metric:** Graceful degradation score (1.0 = no impact, 0.0 = total failure).

---

## Category E: Multi-File Coordination

### E1: Rename Across Codebase
**Lane:** regression | **Dimensions:** 6 (multi-file), 10 (regression prevention)
**Language:** TypeScript

**Setup:** Function `getUserData()` used in 5 files.
**Task:** "Rename `getUserData()` to `fetchUserProfile()` everywhere."

**Acceptance:** All 5 files updated. No remaining references to old name. All tests pass.

### E2: Add Field to Data Model
**Lane:** regression | **Dimensions:** 6, 8 (planning)
**Language:** Python (Django/SQLAlchemy)

**Setup:** Data model `User` with 3 consumers (API endpoint, template, serializer) + migration.
**Task:** "Add an `email_verified` boolean field with default False."

**Acceptance:** Model, migration, API, serializer, and template all updated consistently. Tests pass.

### E3: Interface + Implementation
**Lane:** regression | **Dimensions:** 6
**Language:** TypeScript

**Setup:** Interface `PaymentProvider` with 3 implementations.
**Task:** "Add a `refund(amount: number)` method to the interface and all implementations."

**Acceptance:** Interface updated. All 3 implementations have the method. Type-checks pass.

---

## Category F: Planning & Task Decomposition

### F1: Multi-Step Setup
**Lane:** capability | **Dimensions:** 8 (planning)
**Language:** Python

**Setup:** Empty directory.
**Task:** "Create a Python project with: pyproject.toml, src/ layout, 3 modules, tests, and a working `pytest` run."

**Acceptance:** `pytest` passes. Project structure matches conventions. Score by step ordering.

### F2: Database Schema Evolution
**Lane:** capability | **Dimensions:** 8, 6 (multi-file)
**Language:** SQL + Python

**Setup:** SQLite database with existing schema + ORM models.
**Task:** "Add a new `orders` table with foreign key to `users`, create migration, update models, add CRUD functions, add tests."

**Acceptance:** Migration runs. Tests pass. Foreign key constraint works.
**Step dependency chain:** Schema → Migration → Model → CRUD → Tests.

### F3: Dependency Upgrade
**Lane:** capability | **Dimensions:** 8, 4 (error recovery)
**Language:** JavaScript

**Setup:** Project using React Router v5.
**Task:** "Upgrade to React Router v6. Update all route definitions and navigation."

**Acceptance:** Build passes. All routes work. No v5 API usage remains.

---

## Category G: Recovery from Corruption

### G1: Half-Applied Edit
**Lane:** regression | **Dimensions:** 9 (recovery)
**Language:** Python

**Setup:** A file where a previous agent attempt left a half-applied edit: function signature changed but body still references old parameter names.
**Task:** "The code is broken. Fix it."

**Acceptance:** Code works. Agent identified the partial edit and completed it.

### G2: Conflicting Changes
**Lane:** regression | **Dimensions:** 9, 6 (multi-file)
**Language:** JavaScript

**Setup:** Module A was updated to use new API, but Module B (which imports from A) still uses old API.
**Task:** "Tests are failing. Fix the inconsistency."

**Acceptance:** Both modules consistent. Tests pass.

### G3: Broken Build State
**Lane:** regression | **Dimensions:** 9, 4 (error recovery)
**Language:** TypeScript

**Setup:** Project where `npm run build` fails due to type errors left by a previous agent.
**Task:** "The build is broken. Fix all type errors."

**Acceptance:** Build succeeds. No new type errors introduced.

---

## Category H: Regression Prevention

### H1: Feature Addition Without Breaking
**Lane:** regression | **Dimensions:** 10, 6 (multi-file)
**Language:** Python

**Setup:** Project with 15 passing tests.
**Task:** "Add a `search` function to the `UserService` class."

**Acceptance:** New function works AND all 15 original tests still pass.
**P2P metric:** Original test pass rate after changes.

### H2: Refactor Without Regression
**Lane:** capability | **Dimensions:** 10, 3 (edit accuracy)
**Language:** JavaScript

**Setup:** 300-line single file with tests.
**Task:** "Split this file into 3 modules. Don't change behavior."

**Acceptance:** All existing tests pass unchanged. Code is split across 3 files.

---

## Category I: Consistency & Cost

### I1: Deterministic Task Battery
**Lane:** stress | **Dimensions:** 11 (consistency)
**Language:** Python

**Setup:** 5 simple tasks that should be solvable deterministically.
**Protocol:** Run each task 5 times.
**Metric:** pass^5 score. Target: >0.8 for tasks solvable by L1-L2.

### I2: Token Budget Challenge
**Lane:** stress | **Dimensions:** 12 (cost efficiency)
**Language:** Python

**Setup:** 10 tasks of varying difficulty.
**Protocol:** Run with token tracking enabled.
**Metric:** Total tokens consumed. Compare HybridCoder vs naive single-prompt.

### I3: Zero-Token Resolution Count
**Lane:** stress | **Dimensions:** 12 (HybridCoder-specific)
**Language:** Python

**Setup:** 20 tasks, graded from trivial (find a syntax error) to complex (design a feature).
**Metric:** How many tasks does L1-L2 resolve at zero LLM tokens?
**Target:** At least 30% of trivial tasks should resolve without LLM.

---

## Existing Scenarios to Retain

| Scenario | Lane | Status | Dimensions Covered |
|----------|------|--------|-------------------|
| E2E-Calculator | capability | Runnable | 6, 8, 3 |
| E2E-BugFix | regression | Manifest only | 4, 9, 10 |
| E2E-CLI | regression | Manifest only | 8, 3, 6 |

---

## Priority Ordering for Implementation

### PR Core Baseline (Immediate — must ship first)

These 3 scenarios form the PR-gatable regression baseline. They are the agreed immediate deliverables:

1. **E2E-Calc** (existing) — React calculator, capability probe (already runnable)
2. **E2E-BugFix** — Fix seeded bugs, deterministic acceptance (seed fixture + scoring needed)
3. **E2E-CLI** — Build CLI tool from prompt, deterministic acceptance (scoring needed)

**Policy:** Replay-first, deterministic graders only, `>=2/3` for stochastic fresh runs. No LLM grader on PR lane.

### Wave 1 (Nightly — regression lane expansion)

These 6 agent-specific scenarios expand the nightly regression suite:

1. A1: Targeted Grep Challenge (simplest, tests tool routing)
2. B1: Python Indentation Gauntlet (tests edit accuracy)
3. C1: Fix-After-Failure (tests error recovery)
4. E1: Rename Across Codebase (tests multi-file)
5. G1: Half-Applied Edit (tests recovery)
6. H1: Feature Addition Without Breaking (tests regression prevention)

**Policy:** pass^3 consistency required. Deterministic + heuristic graders.

### Wave 2 (Next — expand regression lane)

7. A2: Import Chain Resolution
8. C2: Import Error Recovery
9. E2: Add Field to Data Model
10. G3: Broken Build State

### Wave 3 (Later — capability + stress lanes)

11. D1-D3: Fault tolerance suite
12. F1-F3: Planning suite
13. I1-I3: Consistency and cost suite

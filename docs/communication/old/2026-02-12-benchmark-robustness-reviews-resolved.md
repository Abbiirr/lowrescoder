# Benchmark Robustness Reviews — Resolved

Archived from AGENTS_CONVERSATION.MD on 2026-02-12.
Entries: 206-211 (Codex), 215-216 (Codex)
Resolution: All benchmark robustness concerns and multi-scenario portfolio proposals implemented by Claude in Entry 224 (17-item hardening). Acknowledged in Entry 225.

---

### Entry 206 — 2026-02-12: PRE-TASK INTENT — Review E2E benchmark robustness (Entries 202-205)

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Phase 3 E2E benchmark review | Intent: Deliver robustness verdict for regression-readiness
Replying to: Claude (Entries 202-205), User
Directed to: Claude, User

**Type: General (Pre-task Intent)**

Planned actions:
1. Audit benchmark engine, wrapper, rubric, and latest result artifacts.
2. Evaluate reliability for regression gating (flakiness, false positives, observability).
3. Publish prioritized fixes and recommended test additions.

Tools Used: Read, rg, bash

### Entry 207 — 2026-02-12: REVIEW — E2E benchmark robustness for regression gating (Entries 202-205)

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Phase 3 E2E benchmark review | Intent: Assess whether current E2E is sufficiently robust for stable system regression testing
Replying to: Claude (Entries 202-205), User
Directed to: Claude, User

**Type: Review (Benchmark / Architecture)**

1. **Layer Assessment:** Layer 4 benchmark + quality gate instrumentation.
2. **Verdict:** NEEDS_WORK.
3. **Analysis:** Current benchmark is valuable as an exploratory capability probe, but not yet a robust regression gate. It combines model output variability with mostly lexical scoring, so score movement does not always reflect real system quality movement.

4. **Concerns:**
- **High — Rubric is token/heuristic-heavy, so it can over-score functionally fragile apps.**
  Evidence: `tests/benchmark/test_project_creation.py:53` through `tests/benchmark/test_project_creation.py:234` awards most points via string/token presence in aggregated source text. Latest passing sample (`sandboxes/bench_20260212_203313`) still contains risky logic like `eval` (`sandboxes/bench_20260212_203313/src/pages/RegularCalculator.jsx:31`) and hook misuse (`useState(() => { convert() })` in `sandboxes/bench_20260212_203313/src/pages/UnitConverter.jsx:117`) yet scores 86/100 with build PASS.

- **High — Single-run gating against rate-limited free-tier model is too noisy for regression confidence.**
  Evidence: score/build variance across same date and model: 61/100 with build FAIL (`docs/qa/test-results/20260212-193054-e2e-react-calculator.md`) vs 86/100 with build PASS (`docs/qa/test-results/20260212-204422-e2e-react-calculator.md`). Logs show 429/provider errors impacting outcomes (`docs/qa/test-results/20260212-203107-e2e-react-calculator.log:327`).

- **Medium — Runtime behavior is not validated in-browser despite plan expectation.**
  Evidence: `docs/plan/benchmark-testing-strategy.md` states basic Playwright checks for each calculator task, but current flow only enforces npm install/build + rubric in `scripts/run_calculator_benchmark.py:787` and `scripts/run_calculator_benchmark.py:792`.

- **Medium — Artifact retention and cleanup are aggressive, reducing forensic reproducibility.**
  Evidence: `clean_old_sandboxes()` deletes all prior `bench_*` runs (`scripts/run_calculator_benchmark.py:160`) and may kill all `node.exe` processes on Windows (`scripts/run_calculator_benchmark.py:173`), which can remove evidence and interfere with unrelated local tasks.

- **Medium — Some reported metadata is weak for diagnostics/comparability.**
  Evidence: prompt and rubric changed materially (UI category added) but result payload lacks an explicit rubric/version field (`scripts/run_calculator_benchmark.py:722`); historical comparisons across versions are ambiguous.

5. **Suggested Changes:**
- Add a post-build functional suite (Playwright) with deterministic assertions: regular arithmetic correctness, scientific trig/log sanity checks, currency fetch + swap flow, unit conversion known-values.
- Change pass criteria to multi-run stability (e.g., N=3, median score threshold + build-pass rate), and classify provider/API failures separately from product regressions.
- Add import-vs-dependencies validation (scan JS/TS imports and compare to `package.json`) to catch missing dependencies before build only catches some cases.
- Add rubric versioning and benchmark schema version in result JSON/markdown.
- Replace destructive cleanup with retention policy (`--keep-last N`) and scoped process cleanup to sandbox-owned processes only.
- Keep current benchmark as `capability` lane; create a smaller deterministic `regression` lane with fixed acceptance checks for CI use.

Status: PARTIALLY RESOLVED — review delivered with prioritized robustness hardening items; implementation pending.

Tools Used: Read, rg, bash

---

### Entry 208 — 2026-02-12: PRE-TASK INTENT — Add expanded E2E hardening + industry benchmark references

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Benchmark strategy comms update | Intent: Add consolidated and expanded E2E recommendations to active comms log
Replying to: User, Claude (Entries 202-205, 207)
Directed to: Claude, User

**Type: General (Pre-task Intent)**

Planned actions:
1. Consolidate all previously raised E2E robustness fixes into one implementation backlog.
2. Add additional E2E testing methods suitable for stable regression gating.
3. Attach vetted industry benchmark options and concrete adoption path.

Tools Used: Read, rg, web search, bash

### Entry 209 — 2026-02-12: TASK HANDOFF — Expanded E2E hardening plan + industry benchmark alignment

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Phase 3 benchmark maturity | Intent: Hand off a complete benchmark-hardening backlog and external benchmark roadmap
Replying to: User, Claude (Entries 202-205, 207)
Directed to: Claude, User

**Type: Task Handoff**

1. **Action requested**
- Implement all previously suggested E2E hardening items from Entry 207, plus the additional methods below.
- Split benchmarking into two lanes:
  - `capability` lane (long-running, exploratory, model-sensitive)
  - `regression` lane (deterministic, CI-gatable, low flake)
- Add benchmark documentation updates so pass/fail semantics and variability handling are explicit.

2. **Files involved**
- Core runner + wrapper:
  - `scripts/run_calculator_benchmark.py`
  - `scripts/run_e2e_benchmark.ps1`
- Rubric + tests:
  - `tests/benchmark/test_project_creation.py`
  - (new) Playwright/functional checks under `tests/integration/` or `tests/benchmark/` (project decision)
- Docs:
  - `docs/qa/e2e-benchmark-guide.md`
  - `docs/qa/real-life-benchmark-standards.md`
  - `docs/session-onramp.md` (if commands/expectations change)

3. **Context and expanded recommendation set**

**A. Previously requested (carry forward from Entry 207):**
- Add browser/runtime functional assertions (not just lexical rubric + npm build).
- Move from single-run pass/fail to multi-run stability metrics (median score + build-pass rate).
- Separate provider/API failures (429, infra) from product regressions in final verdicts.
- Add import-to-dependency integrity checks and risky-pattern checks (e.g., `eval`).
- Add benchmark/rubric/prompt versioning into JSON + markdown artifacts.
- Replace destructive cleanup with retention policy (`keep-last N`) and avoid broad process kills.

**B. Additional E2E suggestions (new):**
- **Metamorphic correctness tests**: assert invariants (e.g., `a+b == b+a`, unit roundtrip conversions).
- **Golden behavior pack**: fixed input/output vectors for each calculator mode; fail on drift.
- **Trace-quality checks**: parse event logs and require minimal workflow quality (e.g., no repeated fatal tool errors).
- **Patch-quality checks**: detect anti-patterns (`eval`, dead code placeholders, TODO/FIXME density).
- **Deterministic replay mode**: evaluate saved generated project snapshots without fresh LLM calls.
- **Seeded multi-run matrix**: run across multiple models/configs and record confidence intervals.
- **Latency/cost budget gates**: max wall-time, token budget, and cost per successful run.
- **Flake triage mode**: auto-rerun failures once, classify as deterministic fail vs flaky infra fail.
- **Security hygiene checks**: dependency audit + forbidden shell/file ops in generated code paths.
- **Artifact completeness gate**: enforce presence of JSON, markdown, event log, and provenance metadata.

**C. Suggested pass/fail model for regression lane:**
- `PASS` only if all conditions hold:
  1) Build passes in >=2/3 runs
  2) Functional suite passes in >=2/3 runs
  3) Median score >= threshold (raise from 30 to meaningful floor)
  4) No critical policy violations (`eval`, missing deps, fatal runtime crash)
- `INFRA_FAIL` class when provider/API instability dominates (tracked separately from regressions).

**D. Industry benchmark options (available now, with adoption notes):**
- **SWE-bench / SWE-bench Verified** (real GitHub issue resolution; containerized harness).
  - https://github.com/SWE-bench/SWE-bench
  - https://openai.com/index/introducing-swe-bench-verified/
- **SWE-Lancer** (real freelance SWE tasks, e2e tests, economic-value framing).
  - https://openai.com/index/swe-lancer/
  - https://github.com/openai/frontier-evals (contains `project/swelancer`)
- **Multi-SWE-bench** (multilingual issue-resolution; broader language coverage).
  - https://github.com/multi-swe-bench/multi-swe-bench
- **LiveCodeBench** (continuously updated coding benchmark, pass@1/pass@5, contamination-aware).
  - https://github.com/LiveCodeBench/LiveCodeBench
- **Terminal-Bench** (hard terminal-first autonomous tasks with executable checks).
  - https://github.com/laude-institute/terminal-bench
- **Web-Bench** (real web-dev project/task chains, strong E2E web construction focus).
  - https://github.com/bytedance/web-bench
- **Aider benchmark suite / leaderboards** (practical edit/refactor/code tasks and transparent runs).
  - https://aider.chat/docs/leaderboards/
  - https://github.com/Aider-AI/aider
  - https://github.com/Aider-AI/aider-swe-bench

**E. Practical adoption sequence for this repo:**
- **Phase 1 (now):** stabilize local regression lane (deterministic replay + functional checks).
- **Phase 2:** add external benchmark pilot (SWE-bench Verified subset or LiveCodeBench slice).
- **Phase 3:** broaden to terminal/web-heavy benchmarks (Terminal-Bench, Web-Bench) when infra budget allows.
- **Phase 4:** multilingual/generalization track (Multi-SWE-bench).

4. **Deadline/Priority**
- Priority: **High** before calling the current E2E setup "stable for regression".
- Suggested target: complete Phase 1 in current sprint; Phase 2 pilot immediately after.

Status: OPEN — task handoff posted; implementation and doc sync pending.

Tools Used: Read, rg, web search, bash

---

### Entry 210 — 2026-02-12: PRE-TASK INTENT — Discuss need for additional similar E2E tests

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: E2E benchmark strategy discussion | Intent: Provide explicit yes/no recommendation and concrete expansion scope for similar E2E tests
Replying to: User, Claude (Entries 202-205, 209)
Directed to: Claude, User

**Type: General (Pre-task Intent)**

Planned actions:
1. Answer whether one calculator-style E2E benchmark is sufficient.
2. Recommend additional E2E test scenarios and what each should validate.
3. Define a phased rollout that preserves CI stability while increasing coverage.

Tools Used: Read, rg, bash

### Entry 211 — 2026-02-12: REVIEW — Do we need more similar E2E tests?

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: E2E portfolio coverage decision | Intent: Decide if current single-scenario E2E is enough and propose target E2E portfolio
Replying to: User, Claude (Entries 202-205, 209)
Directed to: Claude, User

**Type: Review (Benchmark Strategy)**

1. **Layer Assessment:** Layer 4 autonomous execution and end-to-end product synthesis.
2. **Verdict:** APPROVE adding more similar E2E tests (required).
3. **Analysis:** One calculator app benchmark is useful but under-covers failure modes. It mainly stresses front-end scaffolding + dependency wiring. For robust regression confidence, we need a **small suite of diverse E2E tasks** that exercise different tool-use patterns and architecture decisions.

4. **Concerns if we keep only one E2E benchmark:**
- **High — Coverage gap:** single-task overfits to a known prompt/rubric shape.
- **High — Weak regression signal:** improvements may be task-specific, not system-wide.
- **Medium — Blind spots:** backend/API workflows, debugging/fix loops, and refactor workflows are not measured.

5. **Suggested E2E portfolio (additions):**
- **E2E-01 (existing):** React calculator suite (frontend-heavy capability check).
- **E2E-02:** REST API service scaffold (CRUD + tests + OpenAPI spec + lint/type/test pass).
- **E2E-03:** Full-stack mini app (React + backend + DB migration + integration test).
- **E2E-04:** Bug-fix benchmark from seeded broken repo (agent must diagnose and patch to green tests).
- **E2E-05:** Refactor benchmark (preserve behavior while improving structure + passing snapshot tests).
- **E2E-06:** CLI/tooling project benchmark (arg parsing, config file handling, packaging, smoke tests).

**Execution model recommendation:**
- Keep `calculator` in capability lane.
- Add 2 deterministic tasks first (`bug-fix`, `CLI`) for regression lane.
- For each new E2E task, require:
  1) deterministic acceptance tests,
  2) artifact log + rubric score,
  3) infra-failure classification (`INFRA_FAIL` vs `REGRESSION_FAIL`),
  4) multi-run stability threshold (>=2/3 pass).

**Industry alignment:**
- This multi-task structure mirrors benchmark families like SWE-bench (issue-fix), Terminal-Bench (CLI/terminal workflows), and Web-Bench (web app construction), making results more externally comparable while staying practical for local iteration.

Status: OPEN — recommendation posted; awaiting implementation sequencing decision.

Tools Used: Read, rg, bash

---

### Entry 215 — 2026-02-12: PRE-TASK INTENT — Propose multi-scenario E2E benchmark catalog (Python/JS/Java + others)

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: E2E portfolio design | Intent: Provide concrete multi-language benchmark scenarios with per-scenario test/gating suggestions
Replying to: User, Claude (Entries 211, 212, 214)
Directed to: Claude, User

**Type: General (Pre-task Intent)**

Planned actions:
1. Propose a practical multi-scenario benchmark set across Python, JavaScript, Java, and additional ecosystems.
2. Define recommended acceptance checks, scoring, budgets, and pass criteria per scenario.
3. Provide rollout order for stable regression gating.

Tools Used: Read, rg, bash

### Entry 216 — 2026-02-12: TASK HANDOFF — Multi-scenario E2E benchmark portfolio with per-item suggestions

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: E2E portfolio expansion | Intent: Hand off actionable multi-language E2E scenarios and implementation guidance
Replying to: User, Claude (Entries 211, 212, 214)
Directed to: Claude, User

**Type: Task Handoff**

1. **Action requested**
- Add a multi-scenario E2E portfolio (not just calculator) and wire each scenario into the same benchmark harness contract.
- Keep each scenario deterministic-first with explicit executable acceptance checks.

2. **Files involved**
- Likely new docs/plans:
  - `docs/plan/benchmark-hardening-phase4-multi-scenario.md` (recommended)
  - `docs/qa/e2e-benchmark-guide.md` (scenario matrix section)
- Likely new scripts/tests (suggested structure):
  - `scripts/e2e/scenarios/<scenario_id>.py`
  - `tests/benchmark/scenarios/<scenario_id>/...`

3. **Scenario catalog (with suggestions on each item)**

**Common contract for every scenario**
- **Prompt goal:** one-sentence clear outcome.
- **Acceptance checks:** deterministic command list (build/test/smoke/API checks).
- **Scoring (100):** correctness 50, reliability 20, quality 20, efficiency 10.
- **Budgets:** wall-time, tool-call cap, retry policy.
- **Verdict classes:** `PASS`, `FAIL`, `INFRA_FAIL`, `FLAKY`.

### A) Python scenarios

**PY-01 — FastAPI CRUD + Auth + Alembic**
- Prompt: build service with JWT auth, CRUD endpoints, Alembic migrations.
- Checks: `pytest`, migration up/down, OpenAPI schema presence, health endpoint.
- Scoring suggestions:
  - Correctness: auth-protected CRUD works, schema validation.
  - Reliability: migration idempotence, DB reset script.
  - Quality: typing, lint clean, separation (routers/services/repo).
  - Efficiency: under tool/time budget.

**PY-02 — Async job pipeline (Celery/RQ-free local queue)**
- Prompt: implement producer/worker/retry pipeline with durable status store.
- Checks: queue replay test, retry/backoff test, timeout handling test.
- Scoring: prioritize failure handling and exactly-once/idempotence semantics.

**PY-03 — Data ETL mini-benchmark**
- Prompt: CSV/JSON ingest -> transform -> output report + validation.
- Checks: deterministic fixture outputs, schema drift handling, bad-row quarantine.
- Scoring: data correctness and error-reporting quality.

**PY-04 — Bug-fix from seeded failing repo**
- Prompt: fix failing tests without breaking passing tests.
- Checks: before/after test delta, targeted regression test addition.
- Scoring: correctness and minimal-change discipline.

### B) JavaScript/TypeScript scenarios

**JS-01 — Node/Express REST API + contract tests**
- Prompt: build API with request validation, persistence, and test suite.
- Checks: `npm test`, OpenAPI/JSON schema contract tests, negative tests.
- Scoring: API correctness + robust validation paths.

**JS-02 — React app with Playwright smoke + behavior checks**
- Prompt: build UI with routing/state/forms and responsive behavior.
- Checks: Playwright flows, accessibility smoke (`axe` optional), build/test pass.
- Scoring: functional behavior first; UI polish secondary.

**JS-03 — Next.js full-stack mini app**
- Prompt: app router + API route + DB (sqlite) + auth-lite.
- Checks: server/client route tests, E2E create/read/update flow.
- Scoring: boundary correctness (SSR/client/data sync).

**JS-04 — Refactor benchmark (behavior-preserving)**
- Prompt: refactor large messy module into composable units.
- Checks: snapshot/contract tests unchanged, bundle builds.
- Scoring: maintainability gains without behavioral regression.

### C) Java scenarios

**JAVA-01 — Spring Boot REST + JPA + Flyway**
- Prompt: implement layered REST service with migrations and validation.
- Checks: `mvn test`, integration test with testcontainers or H2 profile, Flyway migrate/clean.
- Scoring: correctness of transactions, DTO/entity boundaries, validation.

**JAVA-02 — Concurrency correctness benchmark**
- Prompt: fix race conditions in a seeded concurrent component.
- Checks: stress tests, deterministic race reproducer, jcstress-style assertions (or equivalent harness).
- Scoring: correctness under load and absence of flaky race failures.

**JAVA-03 — Multi-module Maven refactor**
- Prompt: split monolith package into modules with clean API boundaries.
- Checks: module-level tests, dependency graph constraints, build reproducibility.
- Scoring: architecture quality + preserved behavior.

**JAVA-04 — CLI + config + error handling**
- Prompt: implement CLI with subcommands, config precedence, and structured logs.
- Checks: command contract tests, invalid input tests, help/version checks.
- Scoring: UX robustness and deterministic behavior.

### D) "Others too" (recommended additions)

**GO-01 — Go HTTP service with context cancellation**
- Checks: `go test ./...`, cancellation/timeouts, race detector (`-race`).
- Focus: concurrency hygiene, latency, and memory safety.

**RUST-01 — Rust CLI + serde config + robust errors**
- Checks: `cargo test`, clippy, formatting, error-path tests.
- Focus: type safety and explicit error modeling.

**CSharp-01 — ASP.NET minimal API + EF migrations**
- Checks: `dotnet test`, migration run, API integration tests.
- Focus: framework parity with Java/Python service scenarios.

**DB-01 — SQL migration regression challenge (language-agnostic)**
- Checks: migrate up/down, data backfill correctness, zero-loss assertions.
- Focus: schema evolution reliability.

**OPS-01 — Containerization/deployability benchmark**
- Checks: Docker build/run, compose health checks, minimal observability endpoints.
- Focus: runnable production-like artifact quality.

4. **Rollout recommendation (stable first)**
- **Wave 1 (Regression lane now):** PY-04, JS-04, JAVA-04 (deterministic, cheap, low flake).
- **Wave 2:** PY-01, JS-01, JAVA-01 (service/migration coverage).
- **Wave 3 (heavier):** JS-02/03 + GO/RUST/C# + OPS scenario.
- Start with 3 scenarios total for CI, keep remainder as nightly capability suite.

5. **Per-scenario threshold suggestions**
- Default strict gate:
  - Build/test pass required
  - Score >= 70
  - 0 critical policy violations
  - >= 2/3 pass over repeated runs
- Scenario-specific overrides allowed but documented in scenario manifest.

Status: OPEN — portfolio proposal delivered; awaiting scenario selection and implementation sequencing.

Tools Used: Read, rg, bash

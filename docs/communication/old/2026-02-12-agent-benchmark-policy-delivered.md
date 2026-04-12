# Agent-Centric Benchmark Policy — Delivered

Archived from AGENTS_CONVERSATION.MD on 2026-02-12.
Entries: 232-237 (all Codex)
Resolution: All task handoffs fulfilled — comprehensive plan created at docs/plan/agentic-benchmarks/ addressing agent-centric test categories, research-backed plan, low-token blueprint, and capability vs regression split with grader mix.

---
### Entry 232 — 2026-02-12: TASK HANDOFF — Agent-centric, model-resilient benchmark policy

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Regression suite policy hardening | Intent: Require tests that evaluate the coding agent system (workflow/tooling/reliability) rather than a specific model's raw output style
Replying to: User, Claude (Entry 230)
Directed to: Claude, User

**Type: Task Handoff**

1. **Action requested**
- Implement benchmark policy and scenarios so the primary signal is agent-system quality and remains stable when model backend changes.

2. **Agent-centric test categories (required)**
- **Deterministic acceptance tests:** executable pass/fail checks per scenario (build/test/smoke/API correctness).
- **Patch-integrity tests:** minimal-change discipline, no unrelated file churn, no forbidden patterns.
- **Tool-use reliability tests:** command success rate, retry behavior, failure recovery, no invalid tool sequencing.
- **Workflow robustness tests:** can recover from seeded failures, fixes targeted bug without breaking baseline.
- **Environment reproducibility tests:** replay mode on saved artifacts must produce same verdict.
- **Policy/safety tests:** forbidden operations, secret handling, risky code patterns.
- **Artifact-quality tests:** required logs/metadata/verdict payload completeness and schema stability.
- **Performance envelope tests:** wall-time/tool-call budgets with explicit thresholds (agent efficiency).

3. **Scoring/gating constraints to avoid model lock-in**
- Make regression gate mostly binary deterministic checks (pass/fail), not stylistic rubric text-matching.
- Track model-sensitive metrics (style/fluency) as secondary informational metrics, not block gates.
- Keep `INFRA_FAIL` and provider instability separate from regression fail.
- Require multi-run stability (`>=2/3`) for pass on stochastic scenarios.
- Version scenario manifests and evaluators so changes are auditable across model swaps.

4. **Execution lane policy**
- **PR lane (required):** small deterministic suite (`Calc + BugFix + CLI`).
- **Nightly lane:** expanded scenarios (add `API` next, then broader portfolio).
- **Replay lane:** frequent, model-agnostic stability checks.
- **Fresh-generation lane:** scheduled capability checks (non-blocking unless policy says otherwise).

5. **Files involved (implementation + docs)**
- `scripts/run_calculator_benchmark.py`
- `scripts/e2e/run_scenario.py`
- `scripts/e2e/scenario_contract.py`
- `docs/qa/e2e-benchmark-guide.md`
- `docs/session-onramp.md` (if commands/gates change)

6. **Review request**
- Claude: implement these constraints, run delegated tests, publish artifacts.
- Then request Codex review focused on model-agnostic signal quality.

Status: OPEN — user requirement captured; awaiting Claude implementation and test artifacts.

Tools Used: Read, bash

---
### Entry 233 — 2026-02-12: PRE-TASK INTENT — Web research synthesis for agent-centric benchmarking

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: External benchmark research | Intent: Synthesize web research into a concrete model-agnostic benchmark plan for this repo
Replying to: User, Claude (Entries 230-232)
Directed to: Claude, User

**Type: General (Pre-task Intent)**

Planned actions:
1. Summarize benchmark design principles from primary external sources.
2. Convert those principles into implementation phases for HybridCoder.
3. Request Claude review + delegated test execution on the proposed plan.

Constraint note:
- Per user instruction, Codex does not run tests directly; Claude runs tests and publishes artifacts.

Tools Used: web search, Read, bash

---

### Entry 234 — 2026-02-12: TASK HANDOFF — Research-backed model-agnostic benchmark expansion plan

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Agent-centric benchmark architecture | Intent: Define plan for many test types that evaluate agent quality independent of model choice
Replying to: User, Claude (Entries 230-232)
Directed to: Claude, User

**Type: Task Handoff (Research + Plan)**

1. **Research findings (primary-source synthesis):**
- **SWE-bench / SWE-bench Verified** emphasize patch correctness and non-regression via paired test logic (`FAIL_TO_PASS` + `PASS_TO_PASS`) and a curated solvable set.
  - https://github.com/swe-bench/SWE-bench
  - https://openai.com/index/introducing-swe-bench-verified/
- **Terminal-Bench** structures tasks with description + Docker env + test script + oracle solution, executed through a harness in sandboxed terminal environments.
  - https://www.tbench.ai/docs
- **LiveCodeBench** demonstrates that model ordering changes across scenarios (codegen vs self-repair vs code execution vs test-output prediction), so single-scenario evaluation is insufficient.
  - https://livecodebench.github.io/
- **SWE-Lancer** uses end-to-end tests triple-verified by experienced engineers and explicitly reduced infra variance (2025-07-28 update removed internet requirement).
  - https://openai.com/index/swe-lancer/
- **METR Task Standard / RE-Bench** reinforce common task schema + optional automatic scoring to make cross-agent evaluation reproducible and shareable.
  - https://github.com/METR/task-standard
  - https://github.com/METR/RE-Bench
- **Web-Bench** shows value of sequential dependency workflows (50 projects x 20 dependent tasks) for realistic software development evaluation.
  - https://github.com/bytedance/web-bench

2. **Implication for this repo:**
- A calculator-only benchmark cannot be considered full agent evaluation.
- The regression lane should prioritize deterministic, model-agnostic checks over style-based textual rubric scoring.
- Multi-scenario coverage is required to avoid task-shape overfit.

3. **Implementation plan (phased):**
- **Phase A — Contract hardening**
  - Extend `ScenarioManifest` with: `seed_fixture`, `setup_commands`, `acceptance_timeout_s`, `required_artifacts`, `nondeterminism_policy`, `policy_checks`.
  - Define binary acceptance first; rubric remains secondary informational output.

- **Phase B — Shared runner core**
  - Extract reusable benchmark core from calculator path (sandbox setup, logging, verdict classification, artifact verification).
  - Use direct subprocess acceptance execution inside sandbox.
  - Preserve verdict classes: `PASS`, `FAIL`, `INFRA_FAIL`, `FLAKY`.

- **Phase C — Runnable regression suite**
  - Make `E2E-BugFix` runnable first (seed fixture + fail->fix->non-regression checks).
  - Make `E2E-CLI` runnable second (behavior/exit-code/config tests).
  - Keep `E2E-Calc` as third baseline scenario.
  - Add `E2E-API` next as first backend scenario.

- **Phase D — Lane policy and gates**
  - **PR lane:** `Calc + BugFix + CLI` (required).
  - **Nightly lane:** expanded suite incl. `API` and heavier scenarios.
  - **Replay lane:** high-frequency stability checks.
  - **Fresh-generation lane:** scheduled capability checks.
  - Gate policy: deterministic pass criteria + multi-run stability (>=2/3), with provider/infra failures isolated from regression failures.

4. **Required test categories (agent quality, not model style):**
- Deterministic acceptance correctness
- Patch-integrity / non-regression
- Tool-use reliability
- Workflow recovery under seeded failures
- Replay reproducibility
- Policy/safety conformance
- Artifact schema completeness
- Runtime/tool-call budget compliance

5. **Review + validation request to Claude:**
- Review this plan for implementation feasibility in current architecture.
- Implement in incremental PR-sized chunks.
- Run delegated tests/benchmarks and publish artifacts via repo-required mechanism.
- Request Codex follow-up review after each phase (A->D).

6. **Priority/ordering:**
- Priority: High.
- Immediate target: land Phases A+B with runnable BugFix first, then CLI.

Status: OPEN — research-backed plan delivered; awaiting Claude implementation + delegated test artifacts.

Tools Used: web search, Read, bash

---
### Entry 235 — 2026-02-12: PRE-TASK INTENT — Deepen research on low-token agent eval design

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Cost-aware benchmark strategy | Intent: Add research-backed, low-token test/eval architecture to active plan
Replying to: User, Claude (Entry 234)
Directed to: Claude, User

**Type: General (Pre-task Intent)**

Planned actions:
1. Synthesize additional primary-source evidence focused on low-token evaluation.
2. Propose a tiered eval strategy where most regression signal comes from deterministic and replay checks.
3. Hand off implementation-ready guidance and review criteria.

Constraint note:
- Per user instruction, Codex does not run tests directly; Claude executes tests and publishes artifacts.

Tools Used: web search, Read, bash

---

### Entry 236 — 2026-02-12: TASK HANDOFF — Low-token, agent-first test/eval blueprint (research update)

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Token-efficient eval architecture | Intent: Define expanded test set that measures agent quality while minimizing token burn
Replying to: User, Claude (Entry 234)
Directed to: Claude, User

**Type: Task Handoff (Research + Plan Update)**

1. **Additional research highlights (primary sources):**
- **SWE-bench Lite** exists as a reduced subset for practical evaluation footprint (`300` in FAQ; current docs also discuss refreshed split sizes), and SWE-bench evaluation is fundamentally test-based (`FAIL_TO_PASS` + `PASS_TO_PASS`).
  - https://www.swebench.com/SWE-bench/guides/datasets/
  - https://www.swebench.com/SWE-bench/guides/evaluation/
- **SWE-bench experiments repo** separates trajectories/logs from grading harness, enabling replay/offline analysis without re-running full agent generation each time.
  - https://github.com/swe-bench/experiments
- **LiveCodeBench** provides cache/continue controls (`--use_cache`, `--continue_existing`) to avoid recomputation; useful pattern for low-token repeated eval.
  - https://github.com/LiveCodeBench/LiveCodeBench
- **Aider benchmark notes** explicitly recommend diff-based edit formats to reduce token usage versus whole-file approaches.
  - https://aider.chat/docs/benchmarks.html
- **OpenAI prompt caching** offers discounted pricing for repeated prompt prefixes (`>= 1,024` token cached prefix), relevant to eval harness design with stable system/context prompts.
  - https://openai.com/index/api-prompt-caching/

2. **Blueprint: test many things without burning many tokens**
- **Tier 0 (0-token, always-on):** replay + deterministic acceptance + artifact schema checks on saved runs.
- **Tier 1 (low-token, PR gate):** small fresh-generation set (`Calc + BugFix + CLI`) with strict budgets and max-turn/tool limits.
- **Tier 2 (scheduled):** broader scenarios (`API`, refactor, full-stack) in nightly/weekly capability lane.
- **Tier 3 (external comparability):** sampled external benchmark subsets (e.g., SWE-bench Lite slices) on cadence, not per PR.

3. **Agent-quality-first test categories (expanded):**
- Deterministic correctness (`build/test/smoke/API assertions`)
- Patch non-regression (`FAIL_TO_PASS` + `PASS_TO_PASS` style checks)
- Tool orchestration reliability (invalid command rate, retry hygiene)
- Recovery behavior (seeded fault -> diagnosis -> targeted fix)
- Reproducibility (replay verdict consistency)
- Policy/safety conformance (forbidden ops/secrets/risky patterns)
- Artifact/provenance quality (complete logs, schema versioning)
- Efficiency budgets (wall-time, turns, tool-calls, token caps)

4. **Scoring/gating policy (model-resilient):**
- Use binary deterministic checks as primary gate.
- Keep rubric/LLM-judge style metrics as secondary diagnostics.
- Classify `INFRA_FAIL` separately from regression failures.
- Require multi-run stability for stochastic lanes (`>=2/3`).
- Track per-scenario cost and pass trend over time.

5. **Implementation tasks for Claude (next):**
- Add lane configs with explicit budget ceilings per tier.
- Add replay-first command that skips fresh generation by default.
- Add per-scenario `cost_report` fields (prompt/completion/cache-hit if available).
- Add scenario sampling policy (`pr_required`, `nightly`, `weekly_external`).
- Update docs with "tests vs evals" mapping and escalation policy when costs spike.

6. **Review request:**
- Claude: implement Tier 0/Tier 1 first, run delegated tests, publish artifacts.
- Then request Codex review for signal quality vs token spend tradeoff.

Status: OPEN — low-token expansion plan delivered; awaiting Claude implementation + delegated test artifacts.

Tools Used: web search, Read, bash

---
### Entry 237 — 2026-02-12: TASK HANDOFF ADDENDUM — More web research: capability vs regression split + low-cost grader mix

Agent: Codex | Role: Reviewer / Architect | Layer: 4 | Context: Additional benchmark research pass | Intent: Incorporate new external guidance into model-agnostic, low-token eval plan
Replying to: User, Claude (Entries 234, 236)
Directed to: Claude, User

**Type: Task Handoff (Research Addendum)**

1. **New external guidance integrated:**
- Anthropic (Jan 09, 2026) formalizes key agent-eval concepts we should mirror: task/trial/grader/transcript/outcome/harness, plus explicit **capability vs regression** separation.
  - https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Same source emphasizes coding-agent evaluations should be mostly deterministic (tests pass/fail) with transcript grading added selectively.
  - https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- OpenAI eval best-practices reinforces: automate scoring where possible, continuously evaluate, and prefer structured discriminative grading over open-ended generation.
  - https://platform.openai.com/docs/guides/evaluation-best-practices

2. **Plan adjustments from this addendum:**
- Add explicit suite types in docs/config:
  - `regression_suite` (near-100% pass expectation)
  - `capability_suite` (harder tasks, expected lower pass, hill-climbing)
- Adopt mixed grader policy with low-token default:
  - primary: code-based deterministic graders
  - secondary: lightweight transcript heuristics
  - tertiary: LLM rubric only on sampled runs or nightly
- Track per-trial metrics as first-class outputs:
  - `n_total_tokens`, `n_toolcalls`, latency, verdict, infra-classification

3. **Concrete low-token operational policy:**
- PRs: deterministic regression suite only (no mandatory LLM-judge path).
- Nightly: capability suite + sampled rubric grading.
- Weekly: external-comparability sampled runs (subset only).
- Always: replay checks run first; fresh generation only when replay or code deltas warrant it.

4. **Implementation request to Claude:**
- Add suite metadata fields (`suite_type`, `grader_mix`, `sampling_policy`) in scenario config.
- Implement optional grader toggles (`--with-llm-grader`, off by default in PR lane).
- Publish artifact tables showing cost/signal tradeoff by lane.

Status: OPEN — additional research integrated; awaiting Claude implementation update and delegated test artifacts.

Tools Used: web search, Read, bash

---

# Harness Calibration & Benchmark/Eval Hardening via puku-cli — Design Spec

> Status: **DRAFT — pending user review**
> Date: 2026-06-21
> Author: Claude (reviewer/architect role)
> Related: `benchmarks/benchmark_runner.py`, `benchmarks/ai_verification/`, `evals/`, `docs/plan/ai-verification-harness-fixes-plan.md`

## 1. Objective

Make the repo's agent-evaluation harness **trustworthy and stable** by calibrating it
against a known-good external control agent (`puku-cli`), so that when the harness is
later pointed at AutoCode, a reported failure means *AutoCode regressed* — not *the
harness lied*. Then, on the validated harness, **compile a balanced, research-backed
benchmark + eval suite**.

This is a *validate-the-instrument-then-use-it* program, not a from-scratch build. The
harness already exists and is mature; the work is to prove its verdicts and close the
gaps that currently entangle "harness defect" with "agent defect."

### Non-goals
- Benchmarking puku-cli's coding ability for its own sake.
- Changing AutoCode behavior.
- Replacing the existing harness; we extend and validate it.
- Any git commits (changes are left in the working tree for the user to review/commit).

## 2. Decisions locked with the user (2026-06-21)

1. **puku model path → local LiteLLM gateway (free aliases).** puku-cli is driven via its
   OpenAI-compatible provider pointed at `http://localhost:4000/v1` with gateway aliases
   (e.g. `coding`). No paid Anthropic usage. This matches AutoCode's own gateway path.
2. **Calibration scope → full B7–B29 sweep** (the user's standing "all 23 lanes" rule),
   plus a smaller repeated calibration tier for the controlled invariants.
3. **Objective → both, validate first.** Phase 1 validates the harness; Phase 2 compiles
   the new balanced benchmark/eval suite on the now-trusted harness.

## 3. Background: what the harness is today

Three layers, all currently shaped around AutoCode:

| Layer | File(s) | Role |
|---|---|---|
| Benchmark runner | `benchmarks/benchmark_runner.py` | SWE-bench/competitive lanes **B6–B30**; adapters `autocode`/`codex`/`claude-code`; run locks + resume; manifest hashing; harness-commit-SHA run contract; `NOT_EXECUTABLE` validation; subprocess adapter isolation; infra-vs-agent failure classifier (`INFRA_FAIL`/`WRONG_FIX`/`NO_EFFECTIVE_EDITS`) |
| AI verification | `benchmarks/ai_verification/` | scenario generator → runner → grader; ~36 hand-authored canary scenarios (python/go/rust/ts; greenfield/brownfield/refactor/long-horizon/multi-turn); deterministic `check_commands` + optional LLM review |
| Production evals | `evals/` | YAML cases with provenance, `must_have`/`must_not_have` event assertions, judge criteria, per-case `baseline` scores; `EvalRunner.run_live()` subprocess seam; drift-derived generator |

### Confirmed-good infra
- Gateway `http://localhost:4000/v1` is up; alias `coding` routes and returns real
  `usage` token counts. Auth via `LITELLM_API_KEY` (`gateway_auth.py` priority:
  `LITELLM_API_KEY` > `LITELLM_MASTER_KEY` > `OPENROUTER_API_KEY`).
- puku-cli `1.8.27` installed; Claude-Code-compatible surface: `-p/--print`,
  `--output-format json|stream-json`, `--provider openai`, `--model`,
  `--permission-mode bypassPermissions`, `--max-budget-usd`, `--json-schema`.

### Gaps this program closes
- **puku-cli not registered** in `AGENT_REGISTRY`.
- **Thin external-CLI adapters**: `claude_adapter` runs `-p prompt`, captures 2000 chars,
  grades on exit code, and records **no tokens/cost/tool-calls** (`AgentResult` fields
  exist but stay `0`). Even `autocode_adapter` leaves `tokens_in/out` at `0`.
- **No self-test proves grading distinguishes a real pass from a real fail** with an
  actual agent. False-positive grading (accepting a wrong patch) is currently undetected —
  this is precisely the SWE-bench-Verified failure mode (12.5–22% of "passes" were wrong;
  33% solution leakage).
- Harness defects and AutoCode defects are not separable today.

## 4. Approach selection

- **A — Differential calibration + synthetic oracles (CHOSEN).** puku-cli (real,
  known-good) proves the harness does not produce **false negatives** (good agent ⇒ PASS on
  solvable tasks). Synthetic oracle adapters (golden / noop / wrong) prove it does not
  produce **false positives** (the grader rejects a wrong patch, accepts a golden one).
  Real agent → realism; oracles → deterministic grading ground-truth. Output: a harness
  "report card." The full B7–B29 puku sweep is this approach's breadth layer.
- **B — Pure full-sweep eyeballing.** Cheap; cannot separate harness bugs from agent
  variance; never tests false-positive grading. Kept only as the breadth layer inside A.
- **C — Synthetic oracles only.** Strong on grading correctness; never exercises the real
  CLI path, JSON metric parsing, timeouts, or sandbox realism. Folded into A.

## 5. Components

### 5.1 `PukuAdapter` — `benchmarks/adapters/puku_adapter.py`
- Register `"puku"` in `AGENT_REGISTRY`; `name="puku"`, `provider_mode="local_free"`
  (gateway alias), `version` from `puku-cli --version`.
- Command:
  `puku-cli -p --output-format json --provider openai --model <alias>
  --permission-mode bypassPermissions --max-budget-usd <cap> "<prompt>"`
  with env `OPENAI_BASE_URL=http://localhost:4000/v1`,
  `OPENAI_API_KEY=<gateway key from gateway_auth priority>`, run in the task sandbox CWD.
- **Honest metric capture**: parse the result JSON and populate `tokens_in`, `tokens_out`,
  `cost`, `tool_calls`, `num_turns`, `wall_time_s`. This becomes the reference
  implementation for fixing metric capture across adapters.
- `pre_task_healthcheck()` reuses the gateway-alias probe pattern (fail fast on infra) so
  puku infra failures classify as `INFRA_FAIL`, not agent failures.
- Grading uses the existing per-lane `grading_command` path (no special-casing).

### 5.2 Synthetic oracle adapters — `benchmarks/adapters/oracle_adapters.py`
- `GoldenOracle`: applies the task's reference/gold solution (from manifest `extra`, e.g.
  `patch`/`solution`/fixture gold) → expected PASS.
- `NoopOracle`: makes no edits → expected FAIL (and `NO_EFFECTIVE_EDITS`).
- `WrongOracle`: applies a syntactically valid but semantically wrong edit → expected FAIL
  (`WRONG_FIX`), the false-positive probe.
- These never call the network; they make grading ground-truth deterministic.

### 5.3 Harness self-validation suite
- `benchmarks/tests/test_harness_calibration.py` (pytest) + a `--calibrate` runner mode in
  `benchmark_runner.py` (or a thin `benchmarks/calibrate_harness.py`).
- Invariants asserted:
  1. **No false negatives** — golden oracle + puku-on-easy-tasks ⇒ graded PASS.
  2. **No false positives** — noop/wrong oracle ⇒ graded FAIL with correct failure_type.
  3. **Determinism** — same task × N reps (default 5) ⇒ identical verdict; report
     verdict-flip rate (pass^k framing).
  4. **Isolation** — sandbox A's files never visible to task B; CWD confinement holds.
  5. **Infra honesty** — induced gateway outage ⇒ `INFRA_FAIL`, not counted as agent fail.
  6. **Metric capture** — `num_turns`/`duration` captured from puku JSON; tokens/cost
     sourced from the gateway (per Finding 2) and recorded as gateway-or-unavailable, never
     a fabricated `0`.

### 5.4 Full B7–B29 puku sweep
- Run puku through all 23 lanes; resumable; **failed-lanes-only** retry on gateway hiccups
  (standing rules: never restart the gateway; wait and resume failed lanes only).
- Per-lane pass rates + the calibration report. Discrepancies vs expectation triaged as
  **harness bugs first**, then agent.

### 5.5 Phase 2 — balanced benchmark/eval compilation
On the validated harness, compose a stable suite using the research:
- Difficulty / language / category balance with documented coverage.
- Freshly-authored held-out tasks (anti-contamination).
- `FAIL_TO_PASS` + `PASS_TO_PASS` regression pairs per task.
- Docker-pinned environments where images exist (Terminal-Bench / SWE-bench practice).
- **Programmatic grading preferred**; LLM-judge only where unavoidable and validated
  against human/labeled agreement (target combined FP+FN < 5%).
- Documented smoke-tier vs full-tier split with repetition counts for statistical power.

## 5.6 Live smoke findings (2026-06-21) — confirmed before building

A single live `puku-cli -p --output-format json --provider openai --model coding` run
through the gateway succeeded (`type:result, subtype:success, is_error:false`,
`num_turns:2`, `duration_ms:56246`). Captured facts that shape the adapter:

1. **CWD confinement is mandatory.** The smoke did not `cd` into the sandbox, so puku
   created its file in the *current* directory. The adapter MUST pass `cwd=sandbox` to the
   subprocess (as `claude_adapter` does). Calibration invariant 4 (isolation) guards this.
2. **puku self-reports `tokens=0` / `cost=0` through the gateway.** `total_cost_usd:0`,
   `usage.input_tokens/output_tokens:0`, `modelUsage.coding.*:0` — even though the gateway
   *does* return usage (`prompt_tokens:74` in a direct curl). puku's OpenAI-provider path
   does not surface usage. **Consequence:** honest token/cost must be read from the gateway
   (LiteLLM), not the agent JSON. This is a harness-wide insight — AutoCode through the same
   gateway has the same blind spot. The adapter captures what is reliable from puku JSON
   (`num_turns`, `duration_ms`, `result`, `stop_reason`, `permission_denials`) and marks
   tokens/cost as gateway-sourced-or-unavailable rather than recording a false `0`.
3. **Reliable JSON fields:** `type`, `subtype`, `is_error`, `duration_ms`,
   `duration_api_ms`, `num_turns`, `result` (final text), `stop_reason`, `session_id`,
   `total_cost_usd`, `usage{...}`, `modelUsage{<alias>:{...}}`, `permission_denials`, `uuid`.
4. **Latency:** the `coding` alias is a slow reasoning route (~56s for a trivial task).
   Full B7–B29 will be time-heavy but free and resumable; the fast/calibration tier may use
   a faster alias where speed matters, with `coding` kept for realism.

## 5.7 First-run calibration finding (2026-06-21) — the agent-miss vs harness-bug trap

The first live calibration run surfaced a methodological trap that matters greatly for
later judging AutoCode:

- The oracles were perfect (0 false positives, 0 false negatives) — golden⇒PASS,
  noop/wrong⇒FAIL on all tasks.
- puku failed two bugfix tasks on some reps (`F,F,F` and `F,F,P`). A naive runner counted
  these as "harness false negatives" and declared the harness untrustworthy.
- Investigation (re-running one probe without sandbox cleanup) showed puku had left the
  file **completely unchanged** (`num_turns:1`, premature `end_turn`) — the grader was
  *correct* to fail it. Re-running under `uv run` (so `python` is on PATH), puku solved the
  same task (`num_turns:5–6`, `return a + b`, grade PASS). The `coding` reasoning alias is
  simply **unstable on edit tasks** — sometimes it bails after one turn.

**Correction baked into the runner:** an agent FAIL is only a *harness* defect when the
agent actually produced a correct solution that was still graded FAIL. The runner now
proves this with an **independent re-grade** of the agent's sandbox on every FAIL:

- agent FAIL + independent re-grade PASS ⇒ `proven_harness_false_negative` (real bug),
- agent FAIL + independent re-grade FAIL ⇒ `agent_miss` (not a harness defect),
- plus an `edited?` signal (did the agent change any file) to spot no-ops.

Grader trustworthiness is therefore decided by **oracles + proven false negatives only** —
never by raw agent pass/fail. This same discrimination must be applied when AutoCode is
measured: AutoCode failing an easy task is an AutoCode signal unless an independent re-grade
shows its correct output was wrongly failed.

## 5.8 Runner-level finding (2026-06-21) — external adapters miss the git baseline

Running puku through the real `benchmark_runner.py` on lane **B27** (a one-line config fix,
Docker-graded) returned FAILED even though puku set the correct value. Root cause: B27's
`verify.sh` grades with `git show HEAD:<file>` ("only X changed" + "minimal diff" checks),
which needs a git baseline at the failing post-setup state. The **AutoCode adapter creates
one** (`_git_create_baseline`); the thin external adapters (claude / codex / **puku**) did
not — so they silently fail every diff-based lane regardless of solution quality.

Confirmed by re-grading: no baseline ⇒ 3 checks fail; baseline at the buggy state ⇒ the
diff checks PASS. Fix: `PukuAdapter` now creates a git baseline of the post-setup state
before running puku (Docker lanes mount the sandbox at `/work`, so the host baseline is
visible to in-container grading). After the fix, **B27 = RESOLVED 1/1**.

This is a genuine harness gap surfaced only because a *known-good* agent was run through the
harness: a pass-rate-only view would have blamed the agent. **Recommendation:** make the git
baseline a harness-level step in `run_lane` for all external-CLI adapters, rather than
per-adapter — otherwise the `claude-code` and `codex` adapters remain broken on diff-based
lanes. Captured as a follow-up, not done here (out of scope: don't change AutoCode/other
adapters without the user's go-ahead).

## 6. Stability methodology (baked in, cited)
- **Repetitions, not single runs** — calibration tier runs each task N× (default 5);
  report verdict-flip rate + CI, never a single point score. (τ-bench pass^k; "statistically
  fragile benchmarks" — 5–15pp seed variance.)
- **Programmatic-first grading** — exit-code/test grading gates; LLM review advisory and
  separately validated. (SWE-bench Verified weak-test findings.)
- **Pinned reproducibility** — harness commit SHA (already captured), gateway alias, puku
  version, manifest hash; Docker digests where available. (Terminal-Bench reproducibility.)
- **Infra ≠ agent failure** — already classified; calibration asserts it.

## 7. Deliverables
1. `puku_adapter.py` + `oracle_adapters.py`, registered in `AGENT_REGISTRY`.
2. `test_harness_calibration.py` + `--calibrate` runner mode.
3. **Harness calibration report** `benchmarks/docs/harness-calibration-report.md`:
   false-pos / false-neg rates, determinism, infra-classification accuracy, metric
   completeness → the "is this harness trustworthy?" verdict.
4. Full B7–B29 puku sweep results (under `docs/qa/test-results/`).
5. Phase 2: documented, balanced benchmark+eval suite spec.

## 8. Success criteria
- puku-cli runs end-to-end through ≥1 lane via the gateway with real metrics captured.
- Oracle probes: golden ⇒ PASS, noop/wrong ⇒ FAIL, in 100% of probed tasks (any deviation
  is a logged harness bug with a fix or documented limitation).
- Determinism: verdict-flip rate measured and reported for the calibration tier.
- Full B7–B29 puku sweep completes (resumably) with a per-lane report.
- A written calibration verdict the user can act on.

## 9. Risks & mitigations
- **puku-cli ↔ gateway provider mismatch** (OpenAI provider semantics, tool-calling
  support over the alias). Mitigation: Plan step 1 is a single live smoke that captures the
  real JSON shape before building the adapter on assumptions.
- **No machine-readable gold solution for some lanes** (oracle needs a reference patch).
  Mitigation: run oracle probes only on lanes/tasks that carry a gold patch/fixture; for
  the rest, rely on puku false-negative checks + manual spot review, and log the coverage
  gap honestly.
- **Gateway instability mid-sweep.** Mitigation: existing resume + failed-lanes-only retry;
  never restart the gateway.
- **Cost/time of full sweep.** Mitigation: gateway is free; sweep is resumable and can run
  in the background.

## 10. Phasing
- **Phase 0 (de-risk):** live puku→gateway smoke; capture JSON shape. *(Plan step 1.)*
- **Phase 1 (validate):** adapter + oracles + calibration suite + report; then full B7–B29
  puku sweep.
- **Phase 2 (expand):** compile the balanced benchmark/eval suite on the trusted harness.

Phase 1 gates Phase 2.

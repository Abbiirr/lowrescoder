# Phase 5 Roadmap Lock Checklist

> Status: PROVISIONAL (evidence-gated)
> Created: 2026-02-17
> Owner: Codex (architecture/review), Claude (execution/testing)
> Scope: Phase 5 roadmap stabilization and no-regression lock policy

## 1. Purpose

This checklist defines when the Phase 5 roadmap can be considered "locked enough" for thread resolution in `AGENTS_CONVERSATION.MD`.

User directive applied:
- Do not resolve roadmap threads until we are fully convinced by evidence.
- Codex may write tests/docs.
- Claude owns test execution and test artifact generation.

## 2. Lock States

- `STABLE_LOCKED`:
  - All required criteria below are satisfied with fresh artifacts.
  - No open `NEEDS_WORK` blockers in active roadmap threads.
- `PROVISIONAL_LOCKED`:
  - Direction agreed, but one or more evidence packs are incomplete.
  - No thread archival for roadmap items yet.
- `UNLOCKED`:
  - Major architecture/governance conflicts unresolved.

Current state: `PROVISIONAL_LOCKED`.

## 3. Evidence Packs (Mandatory)

### 3.1 QA Lock Pack (fresh artifacts)

Stored via `./scripts/store_test_results.sh`:
- `uv run pytest tests/ -v`
- `uv run ruff check src/ tests/`
- `uv run mypy src/autocode/`
- Go test run for TUI/backend packages

If blocked (network/deps/runtime), artifact must include:
- exact failing command
- exact blocker message
- mitigation proposal

### 3.2 Documentation Lock Pack

Docs must be internally consistent for roadmap authority:
- `docs/plan/phase5-agent-teams.md`
- `PLAN.md` (repo root; absorbed the former `docs/plan.md` on 2026-04-18 — MVP acceptance lives in §6)
- `docs/requirements_and_features.md`
- `docs/session-onramp.md`
- `docs/plan/benchmark-hardening-phase1.md`
- `docs/plan/benchmark-hardening-phase2.md`
- `docs/plan/benchmark-hardening-phase3.md`

Each must clearly indicate one of:
- authoritative now
- historical/reference only
- stale and pending update

### 3.3 Stage Gate Lock Pack

Every disputed roadmap item must be converted to pass/fail criteria with artifact hooks:
- `5A0` quick wins
- `5A` identity/eval skeleton
- `5B` LLMLOOP + L3/L4 role gating
- `5C` context quality + reliability soak gates
- `5D` adapter compatibility + contract tests
- `5E/6` A2A and interop hardening boundaries

## 4. Stage-Specific Non-Regression Gates

## 4.1 5A0 (Quick Wins First)

- `autocode edit` is not a stub.
- Diff preview + apply/reject + rollback checkpoint are test-covered.
- Non-interactive shell safeguards active (`GIT_EDITOR`, prompt blocking protection, timeout policy).
- `autocode doctor` readiness checks exist and are documented.

## 4.2 5A

- Existing tool behavior regression-free (baseline tool set unchanged unless intentionally expanded).
- Agent identity/provider changes have unit and integration tests.
- Eval harness produces reproducible outputs (seeded where applicable).

## 4.3 5B

- L4 default editor path implemented.
- L3 editor behavior is eval-gated, not assumed.
- Iteration timeout and verification summary present.
- LSP remains optional/experimental unless proven stable.

## 4.4 5C

- Context quality metrics include delegated-context evaluation.
- Reliability soak criteria defined and enforced (hang/timeout recovery).
- Cost and latency metrics tied to explicit acceptance thresholds.

## 4.5 5D

- Adapter compatibility matrix documented (versions tested).
- Contract tests for external config/JSON surfaces implemented.
- Manual-only verification is insufficient for lock.

## 4.6 5E / Phase 6

- A2A and interop hardening separated from MVP lock unless explicitly promoted.
- Security and trust boundaries documented before claiming lock.

## 5. Comms Resolution Rule

Do not archive roadmap threads until:
1. All mandatory evidence packs are complete.
2. No unresolved high/critical blockers remain.
3. Directed participants acknowledge closure readiness in `AGENTS_CONVERSATION.MD`.

If evidence is incomplete:
- keep threads active
- post explicit blocker entries
- do not mark `RESOLVED`.

## 6. Ownership and Execution

- Codex:
  - architecture review
  - test/doc authoring
  - lock criteria maintenance
- Claude:
  - test execution
  - artifact generation
  - implementation
- OpenCode:
  - independent review and challenge

## 7. Current Open Blockers (2026-02-17)

1. Fresh QA lock pack not yet completed.
2. Cross-doc roadmap authority still inconsistent.
3. Phase 5 stage gate criteria not yet normalized into all planning docs.
4. Active comms log still contains duplicate entry IDs (process integrity risk).

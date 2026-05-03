# P3a Drift Detectors — Verification Artifact

> **Phase:** P3a — Drift Detectors
> **Date:** 2026-05-01
> **Status:** Detector foundation built; P1 harness scenario still open

## Scope Completed

- Added `autocode/src/autocode/agent/drift.py`.
- Implemented:
  - `SchemaSnapshot`
  - `DriftWarning`
  - `SchemaDriftDetector`
  - `ContextStalenessDetector`
  - `ToolConsistencyDetector`
  - deterministic `args_hash`
  - contract-format `format_drift_warning`
- Added `DriftDetectionHook` and registered it through the internal HR dispatcher.
- Wired drift warning injection as a system message before the next model turn.
- Added `agent.drift.schema.enabled`, `agent.drift.schema.sensitivity`, `agent.drift.staleness.enabled`, and `agent.drift.consistency.enabled` config shape.
- Added `tool_drift_detected` telemetry emission.
- Added `TelemetryAggregator.drift_summary()` and `autocode telemetry drift --last 7d`.
- Added deterministic P1 harness scenario `drift-schema-detection.yaml`.
- Added `benchmarks.ai_verification.checks.check_drift_schema_detection`
  proving the schema detector catches 20/20 synthetic column renames.

## TDD Evidence

- RED: `test_drift.py` failed because `autocode.agent.drift` did not exist.
- RED: drift hook test failed because `DriftDetectionHook` did not exist.
- RED: telemetry drift summary test failed because `TelemetryAggregator.drift_summary()` did not exist.
- GREEN: all focused detector, hook, warning-injection, and telemetry aggregation tests pass.

## Validation

| Command | Result |
|---|---|
| `uv run pytest autocode/tests/unit/test_drift.py -q` | RED first: module missing, then `12 passed` |
| `uv run pytest autocode/tests/unit/test_drift.py autocode/tests/unit/test_agent_loop.py::TestAgentLoop::test_drift_warning_is_injected_before_next_model_turn autocode/tests/unit/test_telemetry_aggregator.py autocode/tests/unit/test_factory.py -q` | `22 passed` |
| `uv run ruff check autocode/src/autocode/agent/drift.py autocode/src/autocode/agent/hooks.py autocode/src/autocode/agent/loop.py autocode/src/autocode/agent/factory.py autocode/src/autocode/config.py autocode/src/autocode/backend/server.py autocode/src/autocode/backend/headless_runner.py autocode/src/autocode/tui/app.py autocode/src/autocode/cli.py autocode/src/autocode/telemetry/aggregator.py autocode/tests/unit/test_drift.py autocode/tests/unit/test_agent_loop.py autocode/tests/unit/test_telemetry_aggregator.py` | All checks passed |
| `uv run pytest autocode/tests/unit/ -q` | `2244 passed, 12 skipped, 1 warning` |
| `uv run python -m benchmarks.ai_verification.checks.check_drift_schema_detection` | PASS; 20/20 renames detected |
| `uv run python -m benchmarks.ai_verification.run_scenario --scenario benchmarks/ai_verification/scenarios/drift-schema-detection.yaml --validate-fixture` | PASS; run ID `20260501-135410-25b47728` |
| `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` | `29 passed` |

## Remaining

- Claude review APPROVE.

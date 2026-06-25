#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_NAME="${AGENT:-autocode}"
QA_BASE="${QA_BASE:-autocode/docs/qa/test-results/ai-verification}"
REPORT_BASE="${REPORT_BASE:-autocode/docs/qa/test-results/ai-verification-supervised}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-600}"

SCENARIOS=(
  "benchmarks/ai_verification/scenarios/multi-turn-regression.yaml"
  "benchmarks/ai_verification/scenarios/ask-user-scripted.yaml"
  "benchmarks/ai_verification/scenarios/semantic-search-required.yaml"
  "benchmarks/ai_verification/scenarios/spawn-subagent-required.yaml"
  "benchmarks/ai_verification/scenarios/tool-trajectory-git.yaml"
  "benchmarks/ai_verification/scenarios/refactor-noop-guard.yaml"
)

failures=0

cd "$ROOT"

for scenario in "${SCENARIOS[@]}"; do
  echo "=== HFIX live acceptance: ${scenario} ==="
  if [[ ! -f "$scenario" ]]; then
    echo "missing scenario: ${scenario}" >&2
    failures=$((failures + 1))
    continue
  fi

  if ! uv run python benchmarks/ai_verification/run_scenario_supervised.py \
      --scenario "$scenario" \
      --agent "$AGENT_NAME" \
      --qa-base "$QA_BASE" \
      --report-base "$REPORT_BASE" \
      --timeout-seconds "$TIMEOUT_SECONDS"; then
    failures=$((failures + 1))
  fi
done

if [[ "$failures" -ne 0 ]]; then
  echo "HFIX live acceptance completed with ${failures} failing scenario(s)." >&2
  exit 1
fi

echo "HFIX live acceptance completed successfully."

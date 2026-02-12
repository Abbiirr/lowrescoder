#!/usr/bin/env bash
# Run a reproducible Phase 3 benchmark snapshot (before/after) and save logs + report.

set -u -o pipefail

MODE="${1:-}"
if [[ "$MODE" != "before" && "$MODE" != "after" ]]; then
  echo "Usage: ./scripts/run_phase3_benchmark_snapshot.sh <before|after>"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/docs/qa/phase3-benchmarks"
mkdir -p "$OUT_DIR"

STAMP="$(date -u +%Y%m%d-%H%M%S)"
BASE="$OUT_DIR/${STAMP}-${MODE}"
REPORT_FILE="${BASE}.md"

STEP_IDS=()
declare -A STEP_STATUS
declare -A STEP_CODE
declare -A STEP_CMD
declare -A STEP_LOG
declare -A STEP_NOTE

run_step() {
  local step_id="$1"
  local step_cmd="$2"
  local log_file="${BASE}-${step_id}.log"

  STEP_IDS+=("$step_id")
  STEP_CMD["$step_id"]="$step_cmd"
  STEP_LOG["$step_id"]="${log_file#$ROOT_DIR/}"

  echo "[${step_id}] $step_cmd"

  (
    cd "$ROOT_DIR"
    bash -lc "$step_cmd"
  ) >"$log_file" 2>&1
  local rc=$?

  STEP_CODE["$step_id"]="$rc"
  if [[ "$rc" -eq 0 ]]; then
    STEP_STATUS["$step_id"]="PASS"
  else
    STEP_STATUS["$step_id"]="FAIL"
  fi
}

run_step "system_tests" "uv run python -m pytest tests/ -v"
run_step "bench_current" "uv run python -m pytest tests/benchmark -v --tb=short -m 'not integration'"
run_step "ruff" "uv run ruff check src/ tests/"
run_step "mypy" "uv run mypy src/"

PHASE3_FILES=(
  "tests/benchmark/test_deterministic_routing.py"
  "tests/benchmark/test_l1_latency.py"
  "tests/benchmark/test_search_relevance.py"
  "tests/benchmark/test_context_budget.py"
)

missing_files=()
for rel in "${PHASE3_FILES[@]}"; do
  if [[ ! -f "$ROOT_DIR/$rel" ]]; then
    missing_files+=("$rel")
  fi
done

if [[ "${#missing_files[@]}" -eq 0 ]]; then
  run_step "bench_phase3_gates" "uv run python -m pytest tests/benchmark/test_deterministic_routing.py tests/benchmark/test_l1_latency.py tests/benchmark/test_search_relevance.py tests/benchmark/test_context_budget.py -v --tb=short"
else
  STEP_IDS+=("bench_phase3_gates")
  STEP_STATUS["bench_phase3_gates"]="SKIPPED"
  STEP_CODE["bench_phase3_gates"]="-"
  STEP_CMD["bench_phase3_gates"]="phase3 gate benchmark files not present yet"
  STEP_LOG["bench_phase3_gates"]="-"
  STEP_NOTE["bench_phase3_gates"]="Missing: ${missing_files[*]}"
fi

{
  echo "# Phase 3 Benchmark Snapshot (${MODE})"
  echo
  echo "- Date (UTC): $(date -u '+%Y-%m-%d %H:%M:%S')"
  echo "- Repo: $ROOT_DIR"
  echo "- Mode: $MODE"
  echo
  echo "## Results"
  echo
  echo "| Step | Status | Exit Code | Command | Log | Notes |"
  echo "|------|--------|-----------|---------|-----|-------|"

  for step_id in "${STEP_IDS[@]}"; do
    status="${STEP_STATUS[$step_id]}"
    code="${STEP_CODE[$step_id]}"
    cmd="${STEP_CMD[$step_id]}"
    log="${STEP_LOG[$step_id]}"
    note="${STEP_NOTE[$step_id]:-}"
    echo "| $step_id | $status | $code | $cmd | $log | $note |"
  done

  echo
  echo "## Comparison Guidance"
  echo
  echo "1. Compare this report against the opposite mode snapshot (before vs after)."
  echo "2. Treat regressions in deterministic accuracy, latency, and token budget as release-blocking."
  echo "3. Keep the command set identical between snapshots to preserve comparability."
} >"$REPORT_FILE"

echo
echo "Snapshot complete: ${REPORT_FILE#$ROOT_DIR/}"

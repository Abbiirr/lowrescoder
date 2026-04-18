#!/bin/bash
# Full B7–B30 benchmark sweep (24 lanes).
#
# Per repo memory discipline:
#   - Never restart the LLM gateway (no docker start / restart attempts).
#     If it is down, wait and re-check. If it stays down, stop the sweep
#     and let the human intervene.
#   - On per-lane failure, continue to the next lane; the benchmark_runner
#     already uses --resume so partial progress is saved.
#   - Use gateway aliases (swebench, terminal_bench), never underlying
#     model names.
#
# Usage:
#   bash benchmarks/run_b7_b30_sweep.sh            # fresh sweep
#   BENCHMARK_RUN_ID=<existing-id> bash benchmarks/run_b7_b30_sweep.sh
#                                                  # resume a run
#
# State:
#   - BENCHMARK_RUN_ID defaults to a timestamp + pid
#   - Per-lane markers written under /tmp/bench-<RUN_ID>/<lane>.done
#     so a re-run skips lanes already completed successfully
#
# Artifacts:
#   - Summary log at
#     autocode/docs/qa/test-results/<timestamp>-b7-b30-sweep.log
#   - Per-lane artifacts written by benchmark_runner (see its docstring)

set -u -o pipefail

REPO_ROOT="/home/bs01763/projects/ai/lowrescoder"
set -a && source "$REPO_ROOT/.env" && set +a
cd "$REPO_ROOT"

BENCHMARK_RUN_ID="${BENCHMARK_RUN_ID:-$(date -u +%Y%m%d-%H%M%S)-$$}"
export BENCHMARK_RUN_ID

BENCH_HOST="${AUTOCODE_LLM_API_BASE:-http://localhost:4000/v1}"
GATEWAY_HEALTH="${BENCH_HOST%/v1}/health/readiness"

STATE_DIR="/tmp/bench-${BENCHMARK_RUN_ID}"
mkdir -p "$STATE_DIR"

LOG_DIR="${REPO_ROOT}/autocode/docs/qa/test-results"
mkdir -p "$LOG_DIR"
SUMMARY_LOG="${LOG_DIR}/$(date -u +%Y%m%d-%H%M%S)-b7-b30-sweep.log"

log() {
    # shellcheck disable=SC2183
    printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*" | tee -a "$SUMMARY_LOG"
}

# Wait for gateway — never restart it. Return 0 if healthy within the
# budget, 1 if the budget expires.
wait_for_gateway() {
    local budget_s=300   # 5 minutes total wait
    local interval_s=15
    local deadline=$(( $(date +%s) + budget_s ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if curl -s --max-time 5 "$GATEWAY_HEALTH" 2>/dev/null | grep -q '"healthy"'; then
            return 0
        fi
        log "  gateway not healthy at $GATEWAY_HEALTH — waiting ${interval_s}s"
        sleep "$interval_s"
    done
    log "  gateway did not become healthy within ${budget_s}s"
    return 1
}

# Lane list in canonical run order. 24 lanes.
LANES=(
    "B7"
    "B8"
    "B9-PROXY"
    "B10-PROXY"
    "B11"
    "B12-PROXY"
    "B13-PROXY"
    "B14-PROXY"
    "B15"
    "B16"
    "B17"
    "B18"
    "B19"
    "B20"
    "B21"
    "B22"
    "B23"
    "B24"
    "B25"
    "B26"
    "B27"
    "B28"
    "B29"
    "B30-TBENCH"
)

# Gateway alias per lane. Default is swebench; B30-TBENCH uses
# terminal_bench alias (matches PLAN.md §3 Harbor wiring).
lane_model() {
    case "$1" in
        B30-TBENCH) echo "terminal_bench" ;;
        *)          echo "swebench" ;;
    esac
}

log "=========================================="
log "B7–B30 full sweep — ${#LANES[@]} lanes"
log "Run ID: $BENCHMARK_RUN_ID"
log "Gateway: $BENCH_HOST"
log "State dir: $STATE_DIR"
log "Summary: $SUMMARY_LOG"
log "=========================================="

if ! wait_for_gateway; then
    log "ABORT: gateway unhealthy at start; not attempting lanes"
    exit 2
fi
log "gateway healthy — starting sweep"

OK_LANES=()
FAIL_LANES=()
SKIPPED_LANES=()

for lane in "${LANES[@]}"; do
    marker="${STATE_DIR}/${lane}.done"
    log ""
    log "---- LANE $lane ----"

    if [ -f "$marker" ]; then
        log "  already done (marker exists at $marker); skipping"
        SKIPPED_LANES+=("$lane")
        continue
    fi

    if ! wait_for_gateway; then
        log "!! gateway down before $lane — stopping sweep"
        log "!! resume with: BENCHMARK_RUN_ID=$BENCHMARK_RUN_ID bash benchmarks/run_b7_b30_sweep.sh"
        break
    fi

    model="$(lane_model "$lane")"
    log "  model alias: $model"

    start_ts="$(date +%s)"
    uv run python benchmarks/benchmark_runner.py \
        --agent autocode --lane "$lane" --max-tasks 5 \
        --model "$model" --run-id "$BENCHMARK_RUN_ID" --resume 2>&1 \
        | tee -a "$SUMMARY_LOG"
    rc="${PIPESTATUS[0]}"
    end_ts="$(date +%s)"
    elapsed=$((end_ts - start_ts))

    if [ "$rc" -eq 0 ]; then
        touch "$marker"
        OK_LANES+=("$lane")
        log "  $lane completed OK (rc=0, ${elapsed}s)"
    else
        FAIL_LANES+=("$lane")
        log "  $lane exited rc=$rc after ${elapsed}s"
        if ! wait_for_gateway; then
            log "!! gateway down after $lane — stopping sweep"
            log "!! resume with: BENCHMARK_RUN_ID=$BENCHMARK_RUN_ID bash benchmarks/run_b7_b30_sweep.sh"
            break
        fi
        log "  gateway still healthy — failure was lane-specific; continuing"
    fi

    log "  cooldown 15s"
    sleep 15
done

log ""
log "=========================================="
log "B7–B30 sweep finished"
log "OK lanes (${#OK_LANES[@]}): ${OK_LANES[*]}"
log "Skipped lanes (${#SKIPPED_LANES[@]}): ${SKIPPED_LANES[*]}"
log "Failed lanes (${#FAIL_LANES[@]}): ${FAIL_LANES[*]}"
log "Run ID: $BENCHMARK_RUN_ID"
log "Summary log: $SUMMARY_LOG"
log "=========================================="

if [ "${#FAIL_LANES[@]}" -gt 0 ]; then
    exit 1
fi
exit 0

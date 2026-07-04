#!/bin/bash
# Full B7–B30 benchmark sweep (24 lanes).
#
# Per repo memory discipline:
#   - Never restart the LLM gateway (no docker start / restart attempts).
#     If it is down, wait and re-check. If it stays down, stop the sweep
#     and let the human intervene.
#   - On per-lane failure, continue to the next lane; the benchmark_runner
#     already uses --resume so partial progress is saved.
#   - Use gateway aliases (coding, terminal_bench), never underlying
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
#
# Tuning:
#   - BENCHMARK_TASK_TIMEOUT_S defaults to 600 seconds. This is an internal
#     benchmark_runner per-task timeout that still writes JSON result artifacts.
#   - BENCHMARK_LANE_TIMEOUT_S defaults to 7200 seconds. This is only a final
#     guardrail around each lane process if setup/cleanup hangs outside the
#     internal per-task timeout path.

set -u -o pipefail

# Resolve the project root (the directory that *contains* benchmarks/) from this
# script's own location, so the sweep runs from any checkout without editing
# hardcoded paths. Override with AUTOCODE_PROJECT_ROOT when running from an
# unusual layout. The repo's .env is sourced only when present.
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${AUTOCODE_PROJECT_ROOT:-$(dirname "$_SCRIPT_DIR")}"
if [ -f "$REPO_ROOT/.env" ]; then
    set -a && source "$REPO_ROOT/.env" && set +a
fi
cd "$REPO_ROOT"

BENCHMARK_RUN_ID="${BENCHMARK_RUN_ID:-$(date -u +%Y%m%d-%H%M%S)-$$}"
export BENCHMARK_RUN_ID

BENCH_HOST="${AUTOCODE_LLM_API_BASE:-http://localhost:4000/v1}"
GATEWAY_HEALTH="${BENCH_HOST%/v1}/health/readiness"
BENCHMARK_TASK_TIMEOUT_S="${BENCHMARK_TASK_TIMEOUT_S:-600}"
BENCHMARK_LANE_TIMEOUT_S="${BENCHMARK_LANE_TIMEOUT_S:-7200}"
BENCHMARK_LOOP_MODEL="${BENCHMARK_LOOP_MODEL:-coding}"
B30_TBENCH_MODEL="${B30_TBENCH_MODEL:-terminal_bench}"
# Which agent adapter to drive (autocode | puku | codex | claude-code).
# Default stays autocode for backward compatibility.
BENCHMARK_AGENT="${BENCHMARK_AGENT:-autocode}"
export BENCHMARK_TASK_TIMEOUT_S
export BENCHMARK_LANE_TIMEOUT_S
export BENCHMARK_LOOP_MODEL
export B30_TBENCH_MODEL
export BENCHMARK_AGENT

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

# Lane list in canonical run order. 24 lanes by default (B7–B30).
# Override with BENCHMARK_LANES="B7 B8 ..." to run a subset (e.g. B7–B29 only,
# omitting the Harbor/Docker-bound B30-TBENCH lane).
if [ -n "${BENCHMARK_LANES:-}" ]; then
    # shellcheck disable=SC2206
    LANES=( ${BENCHMARK_LANES} )
else
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
fi

# Gateway alias per lane. The loop runner always sends tool schemas, so default
# lanes use the tool-capable benchmark coding alias. B30-TBENCH keeps the
# Terminal-Bench-specific alias.
lane_model() {
    case "$1" in
        B30-TBENCH) echo "$B30_TBENCH_MODEL" ;;
        *)          echo "$BENCHMARK_LOOP_MODEL" ;;
    esac
}

log "=========================================="
log "B7–B30 full sweep — ${#LANES[@]} lanes"
log "Agent: $BENCHMARK_AGENT"
log "Run ID: $BENCHMARK_RUN_ID"
log "Gateway: $BENCH_HOST"
log "State dir: $STATE_DIR"
log "Summary: $SUMMARY_LOG"
log "Task timeout: ${BENCHMARK_TASK_TIMEOUT_S}s"
log "Lane timeout: ${BENCHMARK_LANE_TIMEOUT_S}s"
log "Loop model alias: ${BENCHMARK_LOOP_MODEL}"
log "B30 model alias: ${B30_TBENCH_MODEL}"
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
    timeout "$BENCHMARK_LANE_TIMEOUT_S" \
    uv run python benchmarks/benchmark_runner.py \
        --agent "$BENCHMARK_AGENT" --lane "$lane" --max-tasks 5 \
        --model "$model" --run-id "$BENCHMARK_RUN_ID" --resume \
        --task-timeout-s "$BENCHMARK_TASK_TIMEOUT_S" 2>&1 \
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
        if [ "$rc" -eq 124 ]; then
            log "  $lane hit BENCHMARK_LANE_TIMEOUT_S=${BENCHMARK_LANE_TIMEOUT_S}s"
        fi
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

#!/bin/bash
set -a && source /home/bs01763/projects/ai/lowrescoder/.env && set +a
cd /home/bs01763/projects/ai/lowrescoder

BENCHMARK_RUN_ID="${BENCHMARK_RUN_ID:-$(date -u +%Y%m%d-%H%M%S)-$$}"
export BENCHMARK_RUN_ID

# Resolve model from either OPENROUTER_MODEL or OLLAMA_MODEL
BENCH_MODEL="${OPENROUTER_MODEL:-${OLLAMA_MODEL:-default}}"
BENCH_HOST="${AUTOCODE_LLM_API_BASE:-${OLLAMA_HOST:-http://localhost:4000/v1}}"
GATEWAY_HEALTH="${BENCH_HOST%/v1}/health/readiness"

wait_for_gateway() {
    local max_attempts=10
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s --max-time 5 "$GATEWAY_HEALTH" 2>/dev/null | grep -q '"healthy"'; then
            return 0
        fi
        attempt=$((attempt + 1))
        echo "  Gateway down (attempt $attempt/$max_attempts), trying docker start..."
        docker start llm-gateway 2>/dev/null
        local wait=$((30 + RANDOM % 30))
        echo "  Waiting ${wait}s..."
        sleep $wait
    done
    echo "  Gateway failed to come up after $max_attempts attempts!"
    return 1
}

echo "=========================================="
echo "Sequential Benchmark Run — $(date)"
echo "Model: $BENCH_MODEL | Host: $BENCH_HOST"
echo "Provider: $AUTOCODE_LLM_PROVIDER"
echo "Run ID: $BENCHMARK_RUN_ID"
echo "Gateway health: $GATEWAY_HEALTH"
echo "=========================================="

# Pre-flight: ensure gateway is up
echo "Pre-flight gateway check..."
if ! wait_for_gateway; then
    echo "ABORT: Gateway not reachable"
    exit 1
fi
echo "Gateway OK"

LANES="B7 B8 B9-PROXY B10-PROXY B11 B12-PROXY B13-PROXY B14-PROXY"

for lane in $LANES; do
    echo ""
    echo ">>>>>>>>>> Starting $lane at $(date) <<<<<<<<<<"

    # Check gateway before each lane
    if ! wait_for_gateway; then
        echo "!!!! Gateway down before $lane — stopping !!!!"
        break
    fi

    # Use swebench alias for ALL lanes — tools alias unreliable for multi-turn
    LANE_MODEL="swebench"
    echo "  Model: $LANE_MODEL"

    uv run python scripts/benchmark_runner.py \
        --agent autocode --lane "$lane" --max-tasks 5 \
        --model "$LANE_MODEL" --run-id "$BENCHMARK_RUN_ID" --resume 2>&1
    RC=$?

    echo "<<<<<<<<<< $lane finished (rc=$RC) at $(date) >>>>>>>>>>"

    if [ $RC -ne 0 ]; then
        echo "  Lane $lane exited rc=$RC, checking gateway..."
        if wait_for_gateway; then
            echo "  Gateway OK — lane failure was not infra. Continuing to next lane."
        else
            echo "!!!! Gateway down after $lane failure — stopping all lanes !!!!"
            echo "!!!! Re-run with BENCHMARK_RUN_ID=$BENCHMARK_RUN_ID !!!!"
            break
        fi
    fi

    # Brief pause between lanes to let rate limits cool down
    echo "  Cooling down 15s between lanes..."
    sleep 15
    echo ""
done

echo "=========================================="
echo "All benchmarks complete — $(date)"
echo "Run ID: $BENCHMARK_RUN_ID"
echo "=========================================="

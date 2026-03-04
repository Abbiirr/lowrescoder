#!/bin/bash
set -a && source /home/bs01763/projects/ai/lowrescoder/.env && set +a
cd /home/bs01763/projects/ai/lowrescoder

echo "=========================================="
echo "Sequential Benchmark Run — $(date)"
echo "Model: $OLLAMA_MODEL | Host: $OLLAMA_HOST"
echo "Resume mode: enabled (skips completed tasks)"
echo "=========================================="

LANES="B7 B8 B9-PROXY B10-PROXY B11 B12-PROXY B13-PROXY B14-PROXY"

for lane in $LANES; do
    echo ""
    echo ">>>>>>>>>> Starting $lane at $(date) <<<<<<<<<<"
    uv run python scripts/benchmark_runner.py --agent autocode --lane "$lane" --max-tasks 5 --model "$OLLAMA_MODEL" --resume 2>&1
    RC=$?
    echo "<<<<<<<<<< $lane finished (rc=$RC) at $(date) >>>>>>>>>>"
    echo ""
done

echo "=========================================="
echo "All benchmarks complete — $(date)"
echo "=========================================="

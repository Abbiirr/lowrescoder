#!/bin/bash
set -a && source /home/bs01763/projects/ai/lowrescoder/.env && set +a
cd /home/bs01763/projects/ai/lowrescoder

echo "=========================================="
echo "Sequential Benchmark Run — $(date)"
echo "Model: $OLLAMA_MODEL | Host: $OLLAMA_HOST"
echo "=========================================="

LANES="B6 B7 B8 B9 B10 B11 B12-PROXY B13-PROXY B14"

for lane in $LANES; do
    echo ""
    echo ">>>>>>>>>> Starting $lane at $(date) <<<<<<<<<<"
    if [ "$lane" = "B6" ]; then
        uv run python scripts/benchmark_runner.py --agent autocode --lane "$lane" --model "$OLLAMA_MODEL" 2>&1
    else
        uv run python scripts/benchmark_runner.py --agent autocode --lane "$lane" --max-tasks 5 --model "$OLLAMA_MODEL" 2>&1
    fi
    RC=$?
    echo "<<<<<<<<<< $lane finished (rc=$RC) at $(date) >>>>>>>>>>"
    echo ""
done

echo "=========================================="
echo "All benchmarks complete — $(date)"
echo "=========================================="

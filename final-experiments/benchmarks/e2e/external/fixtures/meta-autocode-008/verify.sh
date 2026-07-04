#!/usr/bin/env bash
set -e
echo "=== TASK-008: Async Coroutine Not Awaited Fix ==="
echo "Pattern: langflow-ai/langflow async Python (harness-bench v2)"
echo ""
[ -f "src/flow_runner.py" ] || { echo "FAIL: flow_runner.py not found"; exit 1; }
python -m pytest tests/test_flow_runner.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: execute_flow returns dicts, not coroutines." || echo "FAIL"
exit $TEST_EXIT

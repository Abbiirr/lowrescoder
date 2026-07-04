#!/usr/bin/env bash
set -e
echo "=== TASK-101: langflow Token Counter Characters vs Words Fix ==="
[ -f "src/token_counter.py" ] || { echo "FAIL: token_counter.py not found"; exit 1; }
python -m pytest tests/test_token_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_tokens() counts whitespace-split tokens." || echo "FAIL"
exit $TEST_EXIT

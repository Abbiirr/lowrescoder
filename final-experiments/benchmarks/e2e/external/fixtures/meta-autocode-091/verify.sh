#!/usr/bin/env bash
set -e
echo "=== TASK-091: axios URL Path Join Slash Insertion Fix ==="
[ -f "src/path_joiner.py" ] || { echo "FAIL: path_joiner.py not found"; exit 1; }
python -m pytest tests/test_path_joiner.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: join_url_path() always inserts slash separator." || echo "FAIL"
exit $TEST_EXIT

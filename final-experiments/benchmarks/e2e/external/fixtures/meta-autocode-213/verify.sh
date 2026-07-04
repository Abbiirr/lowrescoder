#!/usr/bin/env bash
set -e
echo "=== TASK-213: get_status_label Case-Insensitive Fix ==="
[ -f "src/status_label.py" ] || { echo "FAIL: status_label.py not found"; exit 1; }
python -m pytest tests/test_status_label.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_status_label() handles uppercase." || echo "FAIL"
exit $TEST_EXIT

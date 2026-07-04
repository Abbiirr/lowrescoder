#!/usr/bin/env bash
set -e
echo "=== TASK-094: gitea Release Version Dot Separator Fix ==="
[ -f "src/release_namer.py" ] || { echo "FAIL: release_namer.py not found"; exit 1; }
python -m pytest tests/test_release_namer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: generate_release_name() uses dot separator." || echo "FAIL"
exit $TEST_EXIT

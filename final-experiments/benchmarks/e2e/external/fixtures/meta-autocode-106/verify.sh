#!/usr/bin/env bash
set -e
echo "=== TASK-106: bat Diff Renderer Context Line Space Prefix Fix ==="
[ -f "src/diff_renderer.py" ] || { echo "FAIL: diff_renderer.py not found"; exit 1; }
python -m pytest tests/test_diff_renderer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: render_diff_line() prefixes context with space." || echo "FAIL"
exit $TEST_EXIT

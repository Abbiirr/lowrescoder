#!/usr/bin/env bash
set -e
echo "=== TASK-202: URL Builder Double-Slash Fix ==="
[ -f "src/url_builder.py" ] || { echo "FAIL: url_builder.py not found"; exit 1; }
python -m pytest tests/test_url_builder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_url() avoids double slashes." || echo "FAIL"
exit $TEST_EXIT

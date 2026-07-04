#!/usr/bin/env bash
set -e
echo "=== TASK-165: Cookie Header Separator Fix ==="
[ -f "src/cookie_builder.py" ] || { echo "FAIL: cookie_builder.py not found"; exit 1; }
python -m pytest tests/test_cookie_builder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_cookie_header() uses '; ' separator." || echo "FAIL"
exit $TEST_EXIT

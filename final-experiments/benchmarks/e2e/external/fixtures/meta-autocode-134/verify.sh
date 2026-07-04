#!/usr/bin/env bash
set -e
echo "=== TASK-134: URL Builder Ampersand Fix ==="
[ -f "src/url_builder.py" ] || { echo "FAIL: url_builder.py not found"; exit 1; }
python -m pytest tests/test_url_builder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_query_string() uses & not &amp;." || echo "FAIL"
exit $TEST_EXIT

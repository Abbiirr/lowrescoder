#!/usr/bin/env bash
set -e
echo "=== TASK-183: Content-Type Parser Whitespace Fix ==="
[ -f "src/content_type_parser.py" ] || { echo "FAIL: content_type_parser.py not found"; exit 1; }
python -m pytest tests/test_content_type_parser.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: parse_content_type() strips leading and trailing whitespace." || echo "FAIL"
exit $TEST_EXIT

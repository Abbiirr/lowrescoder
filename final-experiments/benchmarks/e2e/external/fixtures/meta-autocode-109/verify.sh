#!/usr/bin/env bash
set -e
echo "=== TASK-109: memos Slug Generator Space Separator Fix ==="
[ -f "src/slug_generator.py" ] || { echo "FAIL: slug_generator.py not found"; exit 1; }
python -m pytest tests/test_slug_generator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: generate_slug() uses hyphens as word separators." || echo "FAIL"
exit $TEST_EXIT

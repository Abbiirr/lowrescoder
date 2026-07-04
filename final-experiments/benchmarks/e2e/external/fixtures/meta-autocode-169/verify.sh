#!/usr/bin/env bash
set -e
echo "=== TASK-169: URL Slug Hyphen Fix ==="
[ -f "src/slug_generator.py" ] || { echo "FAIL: slug_generator.py not found"; exit 1; }
python -m pytest tests/test_slug_generator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: slugify() uses hyphens not underscores." || echo "FAIL"
exit $TEST_EXIT

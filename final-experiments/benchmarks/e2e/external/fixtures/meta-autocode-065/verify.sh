#!/usr/bin/env bash
set -e
echo "=== TASK-065: Gitea Release Tag Semver Validation Fix ==="
[ -f "src/tag_validator.py" ] || { echo "FAIL: tag_validator.py not found"; exit 1; }
python -m pytest tests/test_tag_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_release_tag() enforces vX.Y.Z semver format." || echo "FAIL"
exit $TEST_EXIT

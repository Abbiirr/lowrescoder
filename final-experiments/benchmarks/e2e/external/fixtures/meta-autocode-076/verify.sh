#!/usr/bin/env bash
set -e
echo "=== TASK-076: FastAPI OAuth2 Scope Subset Validation Fix ==="
[ -f "src/scope_checker.py" ] || { echo "FAIL: scope_checker.py not found"; exit 1; }
python -m pytest tests/test_scope_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: has_required_scopes() checks subset, not intersection." || echo "FAIL"
exit $TEST_EXIT

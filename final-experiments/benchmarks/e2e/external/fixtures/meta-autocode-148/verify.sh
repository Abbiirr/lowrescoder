#!/usr/bin/env bash
set -e
echo "=== TASK-148: Severity Filter Threshold Fix ==="
[ -f "src/incident_resolver.py" ] || { echo "FAIL: incident_resolver.py not found"; exit 1; }
python -m pytest tests/test_incident_resolver.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: filter_high_severity() uses >= threshold." || echo "FAIL"
exit $TEST_EXIT

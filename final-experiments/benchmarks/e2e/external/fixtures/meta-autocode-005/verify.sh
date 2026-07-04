#!/usr/bin/env bash
set -e
echo "=== meta-autocode TASK-005 Verification ==="
echo "Target: beat Codex xhigh 81.5% via environment resilience"
echo ""
[ -f "src/meta_autocode/environment.py" ] || { echo "FAIL: environment.py not found"; exit 1; }
echo "Running pytest..."
python -m pytest tests/test_environment.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: EnvironmentSetup complete. meta-autocode Phase 5 done." || echo "FAIL"
exit $TEST_EXIT

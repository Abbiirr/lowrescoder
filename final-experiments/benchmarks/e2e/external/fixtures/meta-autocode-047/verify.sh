#!/usr/bin/env bash
set -e
echo "=== TASK-047: uptime-kuma SSL Cert Warning Threshold Fix ==="
[ -f "src/cert_checker.py" ] || { echo "FAIL: cert_checker.py not found"; exit 1; }
python -m pytest tests/test_cert_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: cert_status() warns at <=30 days." || echo "FAIL"
exit $TEST_EXIT

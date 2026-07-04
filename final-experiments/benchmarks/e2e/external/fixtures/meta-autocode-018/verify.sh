#!/usr/bin/env bash
set -e
echo "=== TASK-018: Status Page Monitor Group Sort Fix ==="
echo "Pattern: louislam/uptime-kuma case-insensitive sort"
echo ""
[ -f "src/status_page.py" ] || { echo "FAIL: status_page.py not found"; exit 1; }
python -m pytest tests/test_status_page.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: sort_monitor_groups() sorts case-insensitively." || echo "FAIL"
exit $TEST_EXIT

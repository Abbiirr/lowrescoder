#!/usr/bin/env bash
set -e
echo "=== TASK-036: Vite CSS Module Class Name Collision Fix ==="
echo "Pattern: vitejs/vite CSS module hash scoping"
echo ""
[ -f "src/css_module.py" ] || { echo "FAIL: css_module.py not found"; exit 1; }
python -m pytest tests/test_css_module.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: generate_css_module_class() avoids cross-file collisions." || echo "FAIL"
exit $TEST_EXIT

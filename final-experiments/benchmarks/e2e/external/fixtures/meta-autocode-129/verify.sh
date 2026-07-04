#!/usr/bin/env bash
set -e
echo "=== TASK-129: Template Renderer Double-Brace Fix ==="
[ -f "src/template_renderer.py" ] || { echo "FAIL: template_renderer.py not found"; exit 1; }
python -m pytest tests/test_template_renderer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: render_template() replaces {{key}} placeholders." || echo "FAIL"
exit $TEST_EXIT

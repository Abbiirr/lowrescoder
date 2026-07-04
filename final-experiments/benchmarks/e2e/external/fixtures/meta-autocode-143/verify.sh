#!/usr/bin/env bash
set -e
echo "=== TASK-143: Import Resolver Containment Check Fix ==="
[ -f "src/import_resolver.py" ] || { echo "FAIL: import_resolver.py not found"; exit 1; }
python -m pytest tests/test_import_resolver.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: resolve_import() checks module_name in path." || echo "FAIL"
exit $TEST_EXIT

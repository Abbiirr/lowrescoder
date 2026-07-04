#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: All 6 original tests pass
TEST_RESULT=$(python -m pytest test_mathutils.py -v 2>&1)
PASSED=$(echo "$TEST_RESULT" | grep -c " PASSED" || true)

if [ "$PASSED" -ge 6 ]; then
    echo "PASS: All 6 original tests pass"
else
    echo "FAIL: Tests broken ($PASSED/6 passed)"
    echo "$TEST_RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Public function signatures unchanged
SIG_CHECK=$(python -c "
import inspect
from mathutils import calculate_stats, normalize, find_outliers

sig1 = inspect.signature(calculate_stats)
sig2 = inspect.signature(normalize)
sig3 = inspect.signature(find_outliers)

# Check parameter names
assert list(sig1.parameters.keys()) == ['numbers'], f'calculate_stats sig changed: {sig1}'
assert list(sig2.parameters.keys()) == ['numbers'], f'normalize sig changed: {sig2}'
params3 = list(sig3.parameters.keys())
assert params3 == ['numbers', 'threshold'], f'find_outliers sig changed: {sig3}'
# Check threshold default
assert sig3.parameters['threshold'].default == 2.0, 'threshold default changed'
print('ok')
" 2>&1)

if [ "$SIG_CHECK" = "ok" ]; then
    echo "PASS: Public function signatures unchanged"
else
    echo "FAIL: Function signatures changed: $SIG_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Module is importable with expected names
IMPORT_CHECK=$(python -c "
from mathutils import calculate_stats, normalize, find_outliers
print('ok')
" 2>&1)

if [ "$IMPORT_CHECK" = "ok" ]; then
    echo "PASS: Module importable with all 3 public functions"
else
    echo "FAIL: Module import failed: $IMPORT_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Code is actually cleaner (fewer lines of duplicated mean/stddev)
MEAN_DUPS=$(grep -c "total = total + n\|total += n" mathutils.py || true)
STDDEV_DUPS=$(grep -c "sum_sq = sum_sq + \|sum_sq +=" mathutils.py || true)

if [ "$MEAN_DUPS" -le 1 ] && [ "$STDDEV_DUPS" -le 1 ]; then
    echo "PASS: Duplication reduced (mean calc: $MEAN_DUPS, stddev calc: $STDDEV_DUPS)"
else
    echo "FAIL: Code still has duplication (mean calc: $MEAN_DUPS, stddev calc: $STDDEV_DUPS)"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

#!/usr/bin/env bash
# Grading script for b16-implement-retry-decorator
set -euo pipefail

ERRORS=0

# Check 1: retry decorator exists and is importable
python3 -c "from retry import retry" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "PASS: retry decorator is importable"
else
    echo "FAIL: Cannot import retry from retry"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Decorator is callable and usable
python3 << 'PYCHECK'
import sys
from retry import retry

errors = 0

# Should be usable as decorator with arguments
try:
    @retry(max_retries=1, base_delay=0.01)
    def test_func():
        return 42

    result = test_func()
    if result == 42:
        print("PASS: Decorator works on simple function")
    else:
        print(f"FAIL: Expected 42, got {result}")
        errors += 1
except Exception as e:
    print(f"FAIL: Decorator raised {e}")
    errors += 1

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Check 3: All tests pass
if python -m pytest test_retry.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -30 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Backoff actually works
python3 << 'PYCHECK2'
import sys
import time
from retry import retry

errors = 0

call_count = 0
start = time.monotonic()

@retry(max_retries=2, base_delay=0.05, exponential_base=2.0)
def flaky():
    global call_count
    call_count += 1
    if call_count < 3:
        raise ValueError("fail")
    return "ok"

result = flaky()
elapsed = time.monotonic() - start

if result != "ok":
    print(f"FAIL: Expected 'ok', got '{result}'")
    errors += 1
else:
    print("PASS: Retries eventually succeed")

# Should have waited at least 0.05 + 0.1 = 0.15 seconds
if elapsed >= 0.1:
    print("PASS: Backoff delays are applied")
else:
    print(f"FAIL: Elapsed {elapsed:.3f}s, expected >= 0.1s for backoff")
    errors += 1

sys.exit(errors)
PYCHECK2

PYCHECK2_EXIT=$?
if [ "$PYCHECK2_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK2_EXIT))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0

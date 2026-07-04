#!/usr/bin/env bash
# Grading script for b16-implement-rate-limiter
set -euo pipefail

ERRORS=0

# Check 1: RateLimiter class exists
python3 -c "from rate_limiter import RateLimiter" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "PASS: RateLimiter class is importable"
else
    echo "FAIL: Cannot import RateLimiter from rate_limiter"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Class has required methods
python3 << 'PYCHECK'
import sys
from rate_limiter import RateLimiter

rl = RateLimiter(rate=10.0, capacity=5)
errors = 0

for method in ["allow", "allow_n", "wait_time"]:
    if not hasattr(rl, method) or not callable(getattr(rl, method)):
        print(f"FAIL: Missing method {method}")
        errors += 1
    else:
        print(f"PASS: Method {method} exists")

if not hasattr(rl, "available_tokens"):
    print("FAIL: Missing property available_tokens")
    errors += 1
else:
    print("PASS: Property available_tokens exists")

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Check 3: All tests pass
if python -m pytest test_rate_limiter.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -30 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Burst and sustained behavior
python3 << 'PYCHECK2'
import sys
import time
from rate_limiter import RateLimiter

errors = 0

# Burst: should allow capacity tokens at once
rl = RateLimiter(rate=5.0, capacity=10)
if rl.allow_n(10):
    print("PASS: Burst up to capacity works")
else:
    print("FAIL: Could not burst to capacity")
    errors += 1

# Sustained: after burst, should deny then recover
if rl.allow():
    print("FAIL: Should deny after burst exhaustion")
    errors += 1
else:
    print("PASS: Denies after burst exhaustion")

time.sleep(0.25)  # Should recover ~1.25 tokens at rate=5
if rl.allow():
    print("PASS: Recovers after wait")
else:
    print("FAIL: Did not recover after wait")
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

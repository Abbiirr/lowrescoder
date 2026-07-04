#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: counter.py exists
if [ ! -f "project/counter.py" ]; then
    echo "FAIL: project/counter.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/counter.py exists"
fi

# Check 2: counter.py uses threading.Lock or similar
if grep -qE "(Lock|RLock|lock)" project/counter.py 2>/dev/null; then
    echo "PASS: counter.py uses locking"
else
    echo "FAIL: counter.py does not use any locking mechanism"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_counter.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 4: Concurrent increment test passes (run it again for confidence)
RESULT=$(cd project && python -c "
import threading
from counter import Counter
c = Counter()
def worker():
    for _ in range(1000):
        c.increment()
threads = [threading.Thread(target=worker) for _ in range(100)]
for t in threads: t.start()
for t in threads: t.join()
print('OK' if c.value == 100000 else f'FAIL: got {c.value}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Concurrent increment correct"
else
    echo "FAIL: Concurrent increment wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Function signatures unchanged
SIG_CHECK=$(cd project && python -c "
import inspect
from counter import Counter
c = Counter()
s1 = list(inspect.signature(c.increment).parameters.keys())
s2 = list(inspect.signature(c.decrement).parameters.keys())
if s1 == ['amount'] and s2 == ['amount']:
    print('OK')
else:
    print('FAIL')
" 2>&1)
if [ "$SIG_CHECK" = "OK" ]; then
    echo "PASS: Function signatures unchanged"
else
    echo "FAIL: Function signatures were modified"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Basic operations still work
RESULT=$(cd project && python -c "
from counter import Counter
c = Counter(initial=10)
c.increment(5)
c.decrement(3)
print('OK' if c.value == 12 else f'FAIL: got {c.value}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Basic operations work"
else
    echo "FAIL: Basic operations broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

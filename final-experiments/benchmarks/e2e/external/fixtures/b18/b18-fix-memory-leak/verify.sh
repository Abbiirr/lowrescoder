#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: processor.py exists
if [ ! -f "project/processor.py" ]; then
    echo "FAIL: project/processor.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/processor.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_processor.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 3: Buffer is cleared after process()
RESULT=$(cd project && python -c "
from processor import ItemProcessor
p = ItemProcessor()
p.add_items(['a', 'b', 'c'])
p.process()
print('OK' if p.buffer_size == 0 else f'FAIL: buffer_size={p.buffer_size}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Buffer cleared after process()"
else
    echo "FAIL: Buffer not cleared: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Second process only returns new items
RESULT=$(cd project && python -c "
from processor import ItemProcessor
p = ItemProcessor()
p.add_items([1, 2])
p.process()
p.add_items([3, 4])
second = p.process()
print('OK' if second == [6, 8] else f'FAIL: got {second}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Second process only returns new items"
else
    echo "FAIL: Second process returns wrong items: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Memory bounded after large volume
RESULT=$(cd project && python -c "
from processor import ItemProcessor
p = ItemProcessor()
for i in range(100):
    p.add_items(list(range(100)))
    p.process()
print('OK' if p.buffer_size == 0 and p.total_processed == 10000 else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Memory bounded after large volume"
else
    echo "FAIL: Memory not bounded: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Processing results still correct
RESULT=$(cd project && python -c "
from processor import ItemProcessor
p = ItemProcessor()
p.add_items(['hello', 5])
r = p.process()
print('OK' if r == ['HELLO', 10] else f'FAIL: got {r}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Processing results correct"
else
    echo "FAIL: Processing results wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

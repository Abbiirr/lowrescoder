#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: atomic.py exists
if [ ! -f "project/atomic.py" ]; then
    echo "FAIL: project/atomic.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/atomic.py exists"
fi

# Check 2: Uses rename/replace pattern
if grep -qE "(os\.replace|os\.rename|shutil\.move)" project/atomic.py 2>/dev/null; then
    echo "PASS: Uses write-rename pattern"
else
    echo "FAIL: Does not use write-rename pattern"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_atomic.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 4: Basic write works
RESULT=$(cd project && python -c "
import tempfile, os
from atomic import atomic_write
fd, path = tempfile.mkstemp()
os.close(fd)
atomic_write(path, 'test content')
with open(path) as f:
    content = f.read()
os.unlink(path)
print('OK' if content == 'test content' else f'FAIL: {content}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Basic atomic write works"
else
    echo "FAIL: Basic write broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: No temp files left behind
RESULT=$(cd project && python -c "
import tempfile, os
from atomic import atomic_write
tmpdir = tempfile.mkdtemp()
path = os.path.join(tmpdir, 'target.txt')
before = set(os.listdir(tmpdir))
atomic_write(path, 'content')
after = set(os.listdir(tmpdir))
extra = after - before - {'target.txt'}
os.unlink(path)
os.rmdir(tmpdir)
print('OK' if not extra else f'FAIL: leftover {extra}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: No temp files left behind"
else
    echo "FAIL: Temp files left: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Binary write works
RESULT=$(cd project && python -c "
import tempfile, os
from atomic import atomic_write_bytes
fd, path = tempfile.mkstemp()
os.close(fd)
atomic_write_bytes(path, b'\\x00\\x01\\x02')
with open(path, 'rb') as f:
    data = f.read()
os.unlink(path)
print('OK' if data == b'\\x00\\x01\\x02' else 'FAIL')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Binary atomic write works"
else
    echo "FAIL: Binary write broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

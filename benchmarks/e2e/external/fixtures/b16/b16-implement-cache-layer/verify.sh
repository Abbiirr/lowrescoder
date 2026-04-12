#!/usr/bin/env bash
# Grading script for b16-implement-cache-layer
set -euo pipefail

ERRORS=0

# Check 1: LRUCache class exists and is importable
python3 -c "from cache import LRUCache" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "PASS: LRUCache class is importable"
else
    echo "FAIL: Cannot import LRUCache from cache"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Class has required interface
python3 << 'PYCHECK'
import sys
from cache import LRUCache

c = LRUCache(capacity=10, default_ttl=60.0)
errors = 0

for method in ["get", "put", "delete", "clear", "keys"]:
    if not hasattr(c, method) or not callable(getattr(c, method)):
        print(f"FAIL: Missing method {method}")
        errors += 1
    else:
        print(f"PASS: Method {method} exists")

if not hasattr(c, "size"):
    print("FAIL: Missing property size")
    errors += 1
else:
    print("PASS: Property size exists")

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Check 3: All tests pass
if python -m pytest test_cache.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -30 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 4: TTL and LRU eviction work together
python3 << 'PYCHECK2'
import sys
import time
from cache import LRUCache

errors = 0

# TTL expiration
c = LRUCache(capacity=5, default_ttl=0.1)
c.put("x", 42)
time.sleep(0.15)
if c.get("x") is not None:
    print("FAIL: Expired item should return None")
    errors += 1
else:
    print("PASS: TTL expiration works")

# LRU eviction
c2 = LRUCache(capacity=2, default_ttl=0)
c2.put("a", 1)
c2.put("b", 2)
c2.put("c", 3)
if c2.get("a") is not None:
    print("FAIL: LRU item should have been evicted")
    errors += 1
else:
    print("PASS: LRU eviction works")

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

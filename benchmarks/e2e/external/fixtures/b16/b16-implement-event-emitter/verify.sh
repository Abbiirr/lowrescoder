#!/usr/bin/env bash
# Grading script for b16-implement-event-emitter
set -euo pipefail

ERRORS=0

# Check 1: EventEmitter class exists and is importable
python3 -c "from event_emitter import EventEmitter" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "PASS: EventEmitter class is importable"
else
    echo "FAIL: Cannot import EventEmitter from event_emitter"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Class has required interface
python3 << 'PYCHECK'
import sys
from event_emitter import EventEmitter

ee = EventEmitter()
errors = 0

for method in ["on", "once", "emit", "off", "remove_all_listeners", "listeners", "listener_count"]:
    if not hasattr(ee, method) or not callable(getattr(ee, method)):
        print(f"FAIL: Missing method {method}")
        errors += 1
    else:
        print(f"PASS: Method {method} exists")

if not hasattr(ee, "event_names"):
    print("FAIL: Missing property event_names")
    errors += 1
else:
    print("PASS: Property event_names exists")

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Check 3: All tests pass
if python -m pytest test_event_emitter.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -30 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Core pub-sub behavior works
python3 << 'PYCHECK2'
import sys
from event_emitter import EventEmitter

errors = 0

ee = EventEmitter()
received = []

# Subscribe
ee.on("message", lambda msg: received.append(msg))

# Emit
ee.emit("message", "hello")
ee.emit("message", "world")

if received == ["hello", "world"]:
    print("PASS: Basic pub-sub works")
else:
    print(f"FAIL: Expected ['hello', 'world'], got {received}")
    errors += 1

# Once
once_results = []
ee.once("single", lambda x: once_results.append(x))
ee.emit("single", 1)
ee.emit("single", 2)
if once_results == [1]:
    print("PASS: once() fires only once")
else:
    print(f"FAIL: once() should fire once, got {once_results}")
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

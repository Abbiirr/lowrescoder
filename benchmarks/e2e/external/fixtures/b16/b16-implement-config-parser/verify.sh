#!/usr/bin/env bash
# Grading script for b16-implement-config-parser
set -euo pipefail

ERRORS=0

# Check 1: ConfigParser class exists and is importable
python3 -c "from config_parser import ConfigParser" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "PASS: ConfigParser class is importable"
else
    echo "FAIL: Cannot import ConfigParser from config_parser"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Class has required interface
python3 << 'PYCHECK'
import sys
from config_parser import ConfigParser

cp = ConfigParser()
errors = 0

for method in ["parse", "parse_file", "get", "sections", "items", "has_section", "has_key"]:
    if not hasattr(cp, method) or not callable(getattr(cp, method)):
        print(f"FAIL: Missing method {method}")
        errors += 1
    else:
        print(f"PASS: Method {method} exists")

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Check 3: All tests pass
if python -m pytest test_config_parser.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -30 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Type coercion works
python3 << 'PYCHECK2'
import sys
from config_parser import ConfigParser

errors = 0
cp = ConfigParser()
cp.parse("""
[types]
an_int = 42
a_float = 3.14
a_bool = true
a_string = hello world
""")

val = cp.get("types", "an_int")
if not isinstance(val, int):
    print(f"FAIL: Expected int, got {type(val).__name__}")
    errors += 1
else:
    print("PASS: Integer coercion works")

val = cp.get("types", "a_float")
if not isinstance(val, float):
    print(f"FAIL: Expected float, got {type(val).__name__}")
    errors += 1
else:
    print("PASS: Float coercion works")

val = cp.get("types", "a_bool")
if not isinstance(val, bool):
    print(f"FAIL: Expected bool, got {type(val).__name__}")
    errors += 1
else:
    print("PASS: Boolean coercion works")

val = cp.get("types", "a_string")
if not isinstance(val, str):
    print(f"FAIL: Expected str, got {type(val).__name__}")
    errors += 1
else:
    print("PASS: String type preserved")

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

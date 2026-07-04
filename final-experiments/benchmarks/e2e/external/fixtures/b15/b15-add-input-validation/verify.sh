#!/usr/bin/env bash
# Grading script for b15-add-input-validation
set -euo pipefail

ERRORS=0

# Check 1: Existing tests still pass
if python -m pytest test_forms.py -v > test_output.log 2>&1; then
    echo "PASS: Existing tests pass"
else
    echo "FAIL: Existing tests broken"
    tail -20 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 2-5: Validation logic works correctly
python3 << 'PYCHECK'
import sys
sys.path.insert(0, ".")
from forms import process_registration

errors = 0

# Test empty name
result = process_registration({"name": "", "email": "a@b.com", "password": "12345678"})
if result.success:
    print("FAIL: Empty name should be rejected")
    errors += 1
else:
    print("PASS: Empty name rejected")

# Test empty email
result = process_registration({"name": "Test", "email": "", "password": "12345678"})
if result.success:
    print("FAIL: Empty email should be rejected")
    errors += 1
else:
    print("PASS: Empty email rejected")

# Test invalid email (no @)
result = process_registration({"name": "Test", "email": "invalid", "password": "12345678"})
if result.success:
    print("FAIL: Invalid email (no @) should be rejected")
    errors += 1
else:
    print("PASS: Invalid email rejected")

# Test short password
result = process_registration({"name": "Test", "email": "a@b.com", "password": "short"})
if result.success:
    print("FAIL: Short password should be rejected")
    errors += 1
else:
    print("PASS: Short password rejected")

# Test empty password
result = process_registration({"name": "Test", "email": "a@b.com", "password": ""})
if result.success:
    print("FAIL: Empty password should be rejected")
    errors += 1
else:
    print("PASS: Empty password rejected")

# Test valid submission still works
result = process_registration({"name": "Alice", "email": "alice@example.com", "password": "securepass123"})
if not result.success:
    print("FAIL: Valid submission should succeed")
    errors += 1
else:
    print("PASS: Valid submission succeeds")

# Test errors contain messages
result = process_registration({"name": "", "email": "", "password": ""})
if not result.errors or len(result.errors) == 0:
    print("FAIL: Errors list should contain error messages")
    errors += 1
else:
    print(f"PASS: Error messages returned ({len(result.errors)} error(s))")

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0

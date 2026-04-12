#!/usr/bin/env bash
# Grading script for b17-extract-class
set -euo pipefail

ERRORS=0

# Check 1: email_service.py exists
if [ -f email_service.py ]; then
    echo "PASS: email_service.py exists"
else
    echo "FAIL: email_service.py does not exist"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: EmailService class is in email_service.py
if [ -f email_service.py ] && grep -q 'class EmailService' email_service.py; then
    echo "PASS: EmailService class found in email_service.py"
else
    echo "FAIL: EmailService class not found in email_service.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: EmailService class is NOT in app.py (no duplicate)
if grep -q 'class EmailService' app.py; then
    echo "FAIL: EmailService class still in app.py (duplicate code)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: EmailService removed from app.py"
fi

# Check 4: app.py imports EmailService from email_service
if grep -qE '(from email_service import|import email_service)' app.py; then
    echo "PASS: app.py imports from email_service"
else
    echo "FAIL: app.py does not import from email_service"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Other classes still in app.py
for cls in UserManager TaskTracker Application; do
    if grep -q "class $cls" app.py; then
        echo "PASS: $cls still in app.py"
    else
        echo "FAIL: $cls missing from app.py"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 6: All tests pass
if python -m pytest test_app.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -20 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 7: EmailService is importable from email_service
python3 -c "from email_service import EmailService; es = EmailService(); assert es.validate_address('a@b.com')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "PASS: EmailService importable and functional from email_service"
else
    echo "FAIL: Cannot import or use EmailService from email_service"
    ERRORS=$((ERRORS + 1))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0

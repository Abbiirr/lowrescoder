#!/usr/bin/env bash
set -euo pipefail
cd app

ERRORS=0

# Check 1: No hardcoded database password in config.py
if grep -nE "(DATABASE_PASSWORD|db_passw0rd)" config.py 2>/dev/null | grep -vE "(os\.environ|os\.getenv|environ\.get)" | grep -qE "=\s*['\"].*[a-zA-Z0-9_]{8}"; then
    echo "FAIL: Hardcoded DATABASE_PASSWORD still in config.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No hardcoded DATABASE_PASSWORD"
fi

# Check 2: No hardcoded SECRET_KEY in config.py
if grep -nE "SECRET_KEY\s*=\s*['\"]" config.py 2>/dev/null | grep -vE "(os\.environ|os\.getenv|environ\.get)"; then
    echo "FAIL: Hardcoded SECRET_KEY still in config.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No hardcoded SECRET_KEY"
fi

# Check 3: No hardcoded Stripe key in payments.py
if grep -nE "sk_live_|sk_test_.*REAL" payments.py 2>/dev/null; then
    echo "FAIL: Hardcoded Stripe API key still in payments.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No hardcoded Stripe API key"
fi

# Check 4: No hardcoded SendGrid key in notifications.py
if grep -nE "SG\.[a-zA-Z0-9].*real" notifications.py 2>/dev/null; then
    echo "FAIL: Hardcoded SendGrid API key still in notifications.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No hardcoded SendGrid API key"
fi

# Check 5: Code reads from environment variables
ENV_READS=0
for f in config.py payments.py notifications.py; do
    if grep -qE "(os\.environ|os\.getenv|environ\.get)" "$f" 2>/dev/null; then
        ENV_READS=$((ENV_READS + 1))
    fi
done
if [ "$ENV_READS" -ge 3 ]; then
    echo "PASS: All source files read from environment variables ($ENV_READS/3)"
else
    echo "FAIL: Only $ENV_READS/3 source files read from environment variables"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: .env file exists with placeholder values
if [ -f .env ]; then
    echo "PASS: .env file exists"
else
    echo "FAIL: .env file not found"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: .env.example exists and lists all required vars
REQUIRED_VARS=("DATABASE_PASSWORD" "SECRET_KEY" "STRIPE_API_KEY" "SENDGRID_API_KEY")
if [ -f .env.example ]; then
    MISSING=0
    for var in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "$var" .env.example; then
            echo "FAIL: .env.example missing $var"
            MISSING=$((MISSING + 1))
        fi
    done
    if [ "$MISSING" -eq 0 ]; then
        echo "PASS: .env.example lists all required variables"
    else
        ERRORS=$((ERRORS + MISSING))
    fi
else
    echo "FAIL: .env.example not found"
    ERRORS=$((ERRORS + 1))
fi

# Check 8: Tests pass with env vars set
export DATABASE_PASSWORD="testpass"
export SECRET_KEY="testkey"
export STRIPE_API_KEY="sk_test_fake"
export SENDGRID_API_KEY="SG.fake"
if python -m pytest test_app.py -v 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests failed"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

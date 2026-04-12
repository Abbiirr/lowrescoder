#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

REQUIRED_KEYS="APP_NAME APP_PORT DATABASE_URL DATABASE_POOL_SIZE REDIS_URL LOG_LEVEL CORS_ORIGINS SECRET_KEY FEATURE_NEW_UI SENTRY_DSN"

# Helper: extract value for a key from an env file (ignoring comments)
get_val() {
    local file="$1" key="$2"
    grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d'=' -f2-
}

# Check 1: dev.env has all required keys
DEV_MISSING=""
for key in $REQUIRED_KEYS; do
    if ! grep -qE "^${key}=" dev.env; then
        DEV_MISSING="$DEV_MISSING $key"
    fi
done

if [ -z "$DEV_MISSING" ]; then
    echo "PASS: dev.env has all required keys"
else
    echo "FAIL: dev.env missing keys:$DEV_MISSING"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: prod.env has all required keys
PROD_MISSING=""
for key in $REQUIRED_KEYS; do
    if ! grep -qE "^${key}=" prod.env; then
        PROD_MISSING="$PROD_MISSING $key"
    fi
done

if [ -z "$PROD_MISSING" ]; then
    echo "PASS: prod.env has all required keys"
else
    echo "FAIL: prod.env missing keys:$PROD_MISSING"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: prod LOG_LEVEL is not debug
PROD_LOG=$(get_val prod.env LOG_LEVEL)
if [ "$PROD_LOG" = "warning" ] || [ "$PROD_LOG" = "error" ] || [ "$PROD_LOG" = "warn" ] || [ "$PROD_LOG" = "info" ]; then
    echo "PASS: prod LOG_LEVEL is '$PROD_LOG' (not debug)"
else
    echo "FAIL: prod LOG_LEVEL is '$PROD_LOG' (should be warning/error)"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: prod CORS_ORIGINS does not contain localhost
PROD_CORS=$(get_val prod.env CORS_ORIGINS)
if echo "$PROD_CORS" | grep -qi "localhost"; then
    echo "FAIL: prod CORS_ORIGINS contains localhost: $PROD_CORS"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: prod CORS_ORIGINS does not contain localhost"
fi

# Check 5: prod SECRET_KEY is not a dev key
PROD_SECRET=$(get_val prod.env SECRET_KEY)
if echo "$PROD_SECRET" | grep -qi "dev"; then
    echo "FAIL: prod SECRET_KEY contains 'dev': $PROD_SECRET"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: prod SECRET_KEY is not a dev key"
fi

# Check 6: prod FEATURE_NEW_UI is false
PROD_FEATURE=$(get_val prod.env FEATURE_NEW_UI)
if [ "$PROD_FEATURE" = "false" ]; then
    echo "PASS: prod FEATURE_NEW_UI is false"
else
    echo "FAIL: prod FEATURE_NEW_UI is '$PROD_FEATURE' (should be false)"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: dev LOG_LEVEL is debug
DEV_LOG=$(get_val dev.env LOG_LEVEL)
if [ "$DEV_LOG" = "debug" ]; then
    echo "PASS: dev LOG_LEVEL is debug"
else
    echo "FAIL: dev LOG_LEVEL is '$DEV_LOG' (should be debug)"
    ERRORS=$((ERRORS + 1))
fi

# Check 8: dev DATABASE_URL contains localhost
DEV_DB=$(get_val dev.env DATABASE_URL)
if echo "$DEV_DB" | grep -q "localhost"; then
    echo "PASS: dev DATABASE_URL contains localhost"
else
    echo "FAIL: dev DATABASE_URL does not contain localhost: $DEV_DB"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

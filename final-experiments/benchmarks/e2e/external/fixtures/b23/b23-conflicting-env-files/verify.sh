#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Helper: get value from resolved.env
get_val() {
    grep -E "^${1}=" resolved.env 2>/dev/null | head -1 | cut -d'=' -f2-
}

# Check 0: resolved.env exists
if [ ! -f "resolved.env" ]; then
    echo "FAIL: resolved.env not found"
    echo "RESULT: 1 check(s) failed"
    exit 1
fi

# Check 1: All 10 keys present
ALL_KEYS="APP_NAME PORT DATABASE_URL REDIS_URL LOG_LEVEL SECRET_KEY FEATURE_FLAGS SENTRY_DSN DEBUG API_TIMEOUT"
MISSING=""
for key in $ALL_KEYS; do
    if ! grep -qE "^${key}=" resolved.env; then
        MISSING="$MISSING $key"
    fi
done

if [ -z "$MISSING" ]; then
    echo "PASS: All 10 keys present in resolved.env"
else
    echo "FAIL: Missing keys:$MISSING"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: PORT from .env.local (3000)
VAL=$(get_val PORT)
if [ "$VAL" = "3000" ]; then
    echo "PASS: PORT=3000 (from .env.local)"
else
    echo "FAIL: PORT=$VAL (expected 3000 from .env.local)"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: DATABASE_URL from .env.local (localhost dev)
VAL=$(get_val DATABASE_URL)
if echo "$VAL" | grep -q "localhost.*myapp_dev"; then
    echo "PASS: DATABASE_URL from .env.local"
else
    echo "FAIL: DATABASE_URL=$VAL (expected localhost myapp_dev from .env.local)"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: REDIS_URL from .env.production (not in .env.local)
VAL=$(get_val REDIS_URL)
if echo "$VAL" | grep -q "prod.internal"; then
    echo "PASS: REDIS_URL from .env.production"
else
    echo "FAIL: REDIS_URL=$VAL (expected prod.internal from .env.production)"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: LOG_LEVEL from .env.local (debug)
VAL=$(get_val LOG_LEVEL)
if [ "$VAL" = "debug" ]; then
    echo "PASS: LOG_LEVEL=debug (from .env.local)"
else
    echo "FAIL: LOG_LEVEL=$VAL (expected debug from .env.local)"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: SECRET_KEY from .env.production (not in .env.local)
VAL=$(get_val SECRET_KEY)
if echo "$VAL" | grep -q "prod-"; then
    echo "PASS: SECRET_KEY from .env.production"
else
    echo "FAIL: SECRET_KEY=$VAL (expected prod key from .env.production)"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: FEATURE_FLAGS from .env.local (experimental)
VAL=$(get_val FEATURE_FLAGS)
if echo "$VAL" | grep -q "experimental"; then
    echo "PASS: FEATURE_FLAGS from .env.local"
else
    echo "FAIL: FEATURE_FLAGS=$VAL (expected experimental from .env.local)"
    ERRORS=$((ERRORS + 1))
fi

# Check 8: SENTRY_DSN from .env.production (only there)
VAL=$(get_val SENTRY_DSN)
if echo "$VAL" | grep -q "sentry.io"; then
    echo "PASS: SENTRY_DSN from .env.production"
else
    echo "FAIL: SENTRY_DSN=$VAL (expected sentry.io from .env.production)"
    ERRORS=$((ERRORS + 1))
fi

# Check 9: DEBUG from .env.local (true)
VAL=$(get_val DEBUG)
if [ "$VAL" = "true" ]; then
    echo "PASS: DEBUG=true (from .env.local)"
else
    echo "FAIL: DEBUG=$VAL (expected true from .env.local)"
    ERRORS=$((ERRORS + 1))
fi

# Check 10: API_TIMEOUT from .env (only there)
VAL=$(get_val API_TIMEOUT)
if [ "$VAL" = "30" ]; then
    echo "PASS: API_TIMEOUT=30 (from .env)"
else
    echo "FAIL: API_TIMEOUT=$VAL (expected 30 from .env)"
    ERRORS=$((ERRORS + 1))
fi

# Check 11: Original files not modified
for f in .env .env.local .env.production; do
    if [ ! -f "$f" ]; then
        echo "FAIL: $f was deleted"
        ERRORS=$((ERRORS + 1))
    fi
done

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

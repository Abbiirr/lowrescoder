#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: README mentions correct subcommand names
for cmd in "init" "build" "deploy" "status"; do
    if grep -q "$cmd" README.md; then
        echo "PASS: README mentions subcommand '$cmd'"
    else
        echo "FAIL: README missing subcommand '$cmd'"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 2: README does NOT use wrong old subcommand names
for old_cmd in "create" "compile" "push" "info"; do
    # Only check in code blocks / usage sections
    if grep -E "^\s*(project-manager|python cli\.py)\s+${old_cmd}" README.md >/dev/null 2>&1; then
        echo "FAIL: README still uses wrong command name '$old_cmd'"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: README no longer uses wrong command name '$old_cmd'"
    fi
done

# Check 3: README uses correct flag names
# init: --template/-t, --force/-f (not --type, --overwrite)
if grep -qE "\-\-type" README.md; then
    echo "FAIL: README still uses --type (should be --template)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: README uses --template (not --type)"
fi

if grep -qE "\-\-overwrite" README.md; then
    echo "FAIL: README still uses --overwrite (should be --force)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: README uses --force (not --overwrite)"
fi

# build: --target/-t, --clean/-c, --verbose/-v (not --env, --debug)
if grep -qE "\-\-env\b" README.md; then
    echo "FAIL: README still uses --env (should be --target)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: README uses --target (not --env)"
fi

if grep -qE "\-\-debug" README.md; then
    echo "FAIL: README still uses --debug (should be --verbose)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: README uses --verbose (not --debug)"
fi

# deploy: --dry-run/-n, --tag (not --simulate, --version)
if grep -qE "\-\-simulate" README.md; then
    echo "FAIL: README still uses --simulate (should be --dry-run)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: README uses --dry-run (not --simulate)"
fi

if grep -qE "\-\-version\b" README.md; then
    echo "FAIL: README still uses --version (should be --tag)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: README uses --tag (not --version)"
fi

# status: --format/-f (not --output)
if grep -qE "\-\-output" README.md; then
    echo "FAIL: README still uses --output (should be --format)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: README uses --format (not --output)"
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

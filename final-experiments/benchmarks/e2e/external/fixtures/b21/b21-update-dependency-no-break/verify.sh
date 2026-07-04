#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: All original v1 tests pass
TEST_RESULT=$(python -m pytest test_configparser.py -v 2>&1)
PASSED=$(echo "$TEST_RESULT" | grep -c " PASSED" || true)

if [ "$PASSED" -ge 4 ]; then
    echo "PASS: All 4 original v1 tests pass"
else
    echo "FAIL: Original tests broken ($PASSED/4 passed)"
    echo "$TEST_RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: v1 config still parses correctly
V1_CHECK=$(python -c "
from configparser_app import parse_config
config = parse_config('sample_v1.conf')
assert config['database']['host'] == 'localhost'
assert config['database']['port'] == '5432'
assert config['server']['port'] == '8080'
print('ok')
" 2>&1)

if [ "$V1_CHECK" = "ok" ]; then
    echo "PASS: v1 format still parses correctly"
else
    echo "FAIL: v1 parsing broken: $V1_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: v2 config parses correctly
V2_CHECK=$(python -c "
from configparser_app import parse_config
config = parse_config('sample_v2.conf')
assert 'database' in config, f'Missing database section, got: {config}'
assert config['database']['host'] == 'localhost', f'Wrong host: {config[\"database\"]}'
assert config['database']['port'] == '5432', f'Wrong port: {config[\"database\"]}'
assert config['database']['name'] == 'mydb', f'Wrong name: {config[\"database\"]}'
assert 'server' in config, f'Missing server section'
assert config['server']['host'] == '0.0.0.0', f'Wrong server host: {config[\"server\"]}'
assert config['server']['port'] == '8080', f'Wrong server port: {config[\"server\"]}'
print('ok')
" 2>&1)

if [ "$V2_CHECK" = "ok" ]; then
    echo "PASS: v2 format parses correctly"
else
    echo "FAIL: v2 parsing broken: $V2_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: parse_config signature unchanged
SIG_CHECK=$(python -c "
import inspect
from configparser_app import parse_config
sig = inspect.signature(parse_config)
params = list(sig.parameters.keys())
assert params == ['filepath'], f'Signature changed: {params}'
print('ok')
" 2>&1)

if [ "$SIG_CHECK" = "ok" ]; then
    echo "PASS: parse_config signature unchanged"
else
    echo "FAIL: Signature changed: $SIG_CHECK"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0

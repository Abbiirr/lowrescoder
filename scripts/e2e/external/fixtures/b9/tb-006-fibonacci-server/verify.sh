#!/usr/bin/env bash
# Grading script for tb-006-fibonacci-server
set -euo pipefail

PORT=8765
ERRORS=0
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start the server in the background
python server.py &
SERVER_PID=$!

# Wait for server to start (up to 5 seconds)
for i in $(seq 1 50); do
    if curl -s "http://localhost:$PORT/fib?n=0" >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done

# Check if server is running
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "FAIL: Server failed to start"
    exit 1
fi

check_fib() {
    local n="$1"
    local expected="$2"
    local response
    response=$(curl -s "http://localhost:$PORT/fib?n=$n" 2>/dev/null)

    # Extract result from JSON
    local result
    result=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d['result'])" "$response" 2>/dev/null)

    if [ "$result" = "$expected" ]; then
        echo "PASS: fib($n) = $expected"
    else
        echo "FAIL: fib($n) expected $expected, got '$result' (response: $response)"
        ERRORS=$((ERRORS + 1))
    fi
}

# Test cases
check_fib 0 0
check_fib 1 1
check_fib 2 1
check_fib 5 5
check_fib 10 55
check_fib 20 6765

# Test error handling: missing n
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/fib" 2>/dev/null)
if [ "$HTTP_CODE" = "400" ]; then
    echo "PASS: Missing n returns 400"
else
    echo "FAIL: Missing n should return 400, got $HTTP_CODE"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0

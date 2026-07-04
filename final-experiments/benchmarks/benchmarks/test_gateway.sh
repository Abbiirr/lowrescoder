#!/bin/bash
# =============================================================================
# LLM Gateway Pre-Benchmark Test Suite
#
# Self-contained — works from any directory. No project dependencies.
# Only requires: curl, python3, bash.
#
# Usage: bash scripts/test_gateway.sh [gateway_url] [api_key]
#   gateway_url  defaults to http://localhost:4000
#   api_key      defaults to sk-my-secret-gateway-key
#
# Exit code: 0 = all pass, 1 = failures detected
# =============================================================================

GATEWAY_BASE="${1:-http://localhost:4000}"
API_KEY="${2:-sk-my-secret-gateway-key}"
GATEWAY="$GATEWAY_BASE/v1"
HEALTH_URL="$GATEWAY_BASE/health/readiness"

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS+1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }
skip() { SKIP=$((SKIP+1)); echo "  SKIP: $1"; }

chat() {
    # Inject stream:false into the JSON body to get a single JSON response
    local body
    body=$(echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); d['stream']=False; print(json.dumps(d))")
    curl -s --max-time "${2:-30}" "$GATEWAY/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        -d "$body" 2>&1
}

# Helper: check if response has choices
has_choices() {
    python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'choices' in d else 1)" 2>/dev/null
}

# Helper: extract error message
get_error() {
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message','empty response')[:${1:-120}])" 2>/dev/null
}

echo "============================================================"
echo "LLM Gateway Pre-Benchmark Test Suite"
echo "Gateway: $GATEWAY_BASE"
echo "Time:    $(date)"
echo "============================================================"
echo ""

# ─────────────────────────────────────────────────────────────────
# T1: Health endpoint
# ─────────────────────────────────────────────────────────────────
echo "--- T1: Health endpoint ---"
HEALTH=$(curl -s --max-time 5 "$HEALTH_URL" 2>/dev/null)
if echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status')=='healthy' else 1)" 2>/dev/null; then
    pass "Health endpoint returns healthy"
else
    fail "Health endpoint: $(echo "$HEALTH" | head -c 200)"
    echo ""
    echo "ABORT: Gateway is not healthy. Fix before continuing."
    exit 1
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# T2: Authentication
# ─────────────────────────────────────────────────────────────────
echo "--- T2: Authentication ---"
NOAUTH=$(curl -s --max-time 10 "$GATEWAY/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"model":"default","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' 2>&1)
if echo "$NOAUTH" | grep -qi "auth\|401"; then
    pass "Unauthenticated request rejected"
else
    skip "No auth required (open gateway)"
fi

AUTH=$(chat '{"model":"default","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' 15)
if echo "$AUTH" | has_choices; then
    pass "Authenticated request succeeds"
else
    fail "Authenticated request failed: $(echo "$AUTH" | get_error 200)"
    echo ""
    echo "ABORT: Cannot authenticate. Check API key."
    exit 1
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# T3: All aliases respond (simple text)
# ─────────────────────────────────────────────────────────────────
echo "--- T3: Alias availability (simple text) ---"
for alias in default fast thinking coding vision tools big bench; do
    result=$(chat "{\"model\":\"$alias\",\"messages\":[{\"role\":\"user\",\"content\":\"Say OK\"}],\"max_tokens\":5}" 20)
    if echo "$result" | has_choices; then
        pass "Alias '$alias'"
    else
        fail "Alias '$alias': $(echo "$result" | get_error 80)"
    fi
    sleep 1
done
echo ""

# ─────────────────────────────────────────────────────────────────
# T4: Tool calling (single turn)
# ─────────────────────────────────────────────────────────────────
echo "--- T4: Tool calling (single turn) ---"
TOOL_DEF='[{"type":"function","function":{"name":"read_file","description":"Read a file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}}]'
for alias in tools bench default; do
    result=$(chat "{
        \"model\":\"$alias\",
        \"messages\":[{\"role\":\"system\",\"content\":\"You must use tools.\"},{\"role\":\"user\",\"content\":\"Read main.py\"}],
        \"tools\":$TOOL_DEF,
        \"max_tokens\":50,
        \"tool_choice\":\"required\"
    }" 20)
    tc_count=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('choices',[{}])[0].get('message',{}).get('tool_calls',[])))" 2>/dev/null)
    if [ "$tc_count" -gt 0 ] 2>/dev/null; then
        pass "Alias '$alias' tool call ($tc_count)"
    else
        fail "Alias '$alias' tool call: $(echo "$result" | get_error 80)"
    fi
    sleep 2
done
echo ""

# ─────────────────────────────────────────────────────────────────
# T5: Multi-turn tool conversation
# ─────────────────────────────────────────────────────────────────
echo "--- T5: Multi-turn tool conversation ---"
T1_RESP=$(chat "{
    \"model\":\"tools\",
    \"messages\":[{\"role\":\"system\",\"content\":\"Use tools.\"},{\"role\":\"user\",\"content\":\"Read main.py\"}],
    \"tools\":$TOOL_DEF,
    \"max_tokens\":50,
    \"tool_choice\":\"required\"
}" 20)

TC_ID=$(echo "$T1_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['tool_calls'][0]['id'])" 2>/dev/null)

if [ -z "$TC_ID" ]; then
    fail "Turn 1: no tool call returned"
else
    pass "Turn 1: tool_call id=$TC_ID"

    T2_RESP=$(chat "{
        \"model\":\"tools\",
        \"messages\":[
            {\"role\":\"system\",\"content\":\"You are helpful.\"},
            {\"role\":\"user\",\"content\":\"Read main.py\"},
            {\"role\":\"assistant\",\"content\":null,\"tool_calls\":[{\"id\":\"$TC_ID\",\"type\":\"function\",\"function\":{\"name\":\"read_file\",\"arguments\":\"{\\\"path\\\":\\\"main.py\\\"}\"}}]},
            {\"role\":\"tool\",\"tool_call_id\":\"$TC_ID\",\"content\":\"def hello():\\n    print('Hello world')\"}
        ],
        \"max_tokens\":100
    }" 20)

    if echo "$T2_RESP" | has_choices; then
        pass "Turn 2: response after tool result"
    else
        fail "Turn 2: $(echo "$T2_RESP" | get_error)"
    fi
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# T6: 3-turn tool conversation (catches Cohere/Groq history issues)
# ─────────────────────────────────────────────────────────────────
echo "--- T6: 3-turn tool conversation ---"
if [ -n "$TC_ID" ]; then
    # Get a second tool call
    T2B=$(chat "{
        \"model\":\"tools\",
        \"messages\":[
            {\"role\":\"system\",\"content\":\"Use tools.\"},
            {\"role\":\"user\",\"content\":\"Read main.py\"},
            {\"role\":\"assistant\",\"content\":null,\"tool_calls\":[{\"id\":\"$TC_ID\",\"type\":\"function\",\"function\":{\"name\":\"read_file\",\"arguments\":\"{\\\"path\\\":\\\"main.py\\\"}\"}}]},
            {\"role\":\"tool\",\"tool_call_id\":\"$TC_ID\",\"content\":\"def hello():\\n    print('Hello')\"},
            {\"role\":\"user\",\"content\":\"Now write a test\"}
        ],
        \"tools\":[{\"type\":\"function\",\"function\":{\"name\":\"read_file\",\"description\":\"Read\",\"parameters\":{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\"}},\"required\":[\"path\"]}}},{\"type\":\"function\",\"function\":{\"name\":\"write_file\",\"description\":\"Write\",\"parameters\":{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\"},\"content\":{\"type\":\"string\"}},\"required\":[\"path\",\"content\"]}}}],
        \"max_tokens\":200
    }" 30)

    if echo "$T2B" | has_choices; then
        pass "3-turn conversation accepted"
    else
        fail "3-turn conversation: $(echo "$T2B" | get_error)"
    fi
else
    skip "Skipped (T5 turn 1 failed)"
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# T7: Rate limit resilience (rapid fire)
# ─────────────────────────────────────────────────────────────────
echo "--- T7: Rate limit resilience (10 rapid requests) ---"
T7_OK=0
for i in $(seq 1 10); do
    result=$(chat '{"model":"tools","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' 15)
    if echo "$result" | has_choices; then
        T7_OK=$((T7_OK+1))
    fi
    sleep 0.5
done
if [ $T7_OK -ge 8 ]; then
    pass "Rapid fire: $T7_OK/10 succeeded"
elif [ $T7_OK -ge 5 ]; then
    pass "Rapid fire: $T7_OK/10 (acceptable)"
else
    fail "Rapid fire: $T7_OK/10 — failover not working"
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# T8: Large prompt (SWE-bench sized, ~4K chars)
# ─────────────────────────────────────────────────────────────────
echo "--- T8: Large prompt (4K chars) ---"
PADDING=$(python3 -c "print('x' * 4000)")
result=$(chat "{
    \"model\":\"tools\",
    \"messages\":[{\"role\":\"user\",\"content\":\"Fix: $PADDING\"}],
    \"tools\":$TOOL_DEF,
    \"max_tokens\":50
}" 30)
if echo "$result" | has_choices; then
    pass "4K prompt accepted"
else
    err=$(echo "$result" | get_error 80)
    if echo "$err" | grep -qi "413\|too large"; then
        fail "4K prompt rejected (413 body too large)"
    else
        fail "4K prompt: $err"
    fi
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# T9: Response time (must complete within 60s)
# ─────────────────────────────────────────────────────────────────
echo "--- T9: Response time ---"
START=$(date +%s%N)
result=$(chat '{"model":"tools","messages":[{"role":"user","content":"Write fibonacci in Python"}],"max_tokens":200}' 60)
END=$(date +%s%N)
ELAPSED_MS=$(( (END - START) / 1000000 ))
if echo "$result" | has_choices; then
    pass "Response in ${ELAPSED_MS}ms"
else
    fail "No response within 60s"
fi
echo ""

# ─────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────
echo "============================================================"
echo "RESULTS: $PASS passed, $FAIL failed, $SKIP skipped"
echo "============================================================"

if [ $FAIL -eq 0 ]; then
    echo "ALL TESTS PASSED — gateway ready for benchmarks"
    exit 0
else
    echo "FAILURES DETECTED — fix gateway before running benchmarks"
    exit 1
fi

#!/usr/bin/env bash
# verify.sh — Portable verification wrapper for AutoCode harness.
#
# Reads verification commands from (in priority order):
#   1. .autocode/verify.yaml  (commands: [...])
#   2. .autocode.yaml verify section
#   3. Arguments passed on command line
#   4. Auto-detected defaults (pytest, ruff, mypy)
#
# Outputs: verify.json to stdout and .autocode/artifacts/verify.json
#
# Usage:
#   bash tools/verify/verify.sh                    # use config
#   bash tools/verify/verify.sh "pytest" "ruff ."  # explicit commands

set -euo pipefail

ARTIFACT_DIR="${AUTOCODE_ARTIFACT_DIR:-.autocode/artifacts}"
mkdir -p "$ARTIFACT_DIR"

# --- Collect commands ---
COMMANDS=()

if [ $# -gt 0 ]; then
    # Commands from arguments
    COMMANDS=("$@")
elif [ -f .autocode/verify.yaml ]; then
    # Parse YAML commands list (simple line-based parsing)
    while IFS= read -r line; do
        cmd=$(echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//' | sed 's/^"//' | sed 's/"$//')
        [ -n "$cmd" ] && COMMANDS+=("$cmd")
    done < <(grep -A 100 '^commands:' .autocode/verify.yaml | tail -n +2 | grep '^\s*-' | head -20)
fi

# Auto-detect if no commands configured
if [ ${#COMMANDS[@]} -eq 0 ]; then
    [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ] && {
        command -v ruff >/dev/null 2>&1 && COMMANDS+=("ruff check .")
        command -v pytest >/dev/null 2>&1 && COMMANDS+=("pytest -x -q")
        command -v mypy >/dev/null 2>&1 && COMMANDS+=("mypy src/ --ignore-missing-imports")
    }
    [ -f package.json ] && {
        COMMANDS+=("npm test")
    }
    [ -f Cargo.toml ] && {
        COMMANDS+=("cargo test")
    }
    [ -f go.mod ] && {
        COMMANDS+=("go test ./...")
    }
fi

if [ ${#COMMANDS[@]} -eq 0 ]; then
    echo '{"error": "No verification commands found. Configure .autocode/verify.yaml or pass commands as arguments."}' | tee "$ARTIFACT_DIR/verify.json"
    exit 1
fi

# --- Run checks ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
CHECKS="[]"
ALL_PASSED=true
TOTAL_MS=0

for cmd in "${COMMANDS[@]}"; do
    # Derive check name from command
    name=$(echo "$cmd" | awk '{print $1}' | xargs basename 2>/dev/null || echo "$cmd")

    start_ms=$(($(date +%s%N) / 1000000))
    output=$(eval "$cmd" 2>&1) || true
    exit_code=$?
    end_ms=$(($(date +%s%N) / 1000000))
    duration_ms=$((end_ms - start_ms))
    TOTAL_MS=$((TOTAL_MS + duration_ms))

    # Truncate output for JSON
    summary=$(echo "$output" | tail -5 | head -3 | tr '\n' ' ' | cut -c1-200)
    # Escape JSON
    summary=$(echo "$summary" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null || echo '""')

    if [ "$exit_code" -ne 0 ]; then
        ALL_PASSED=false
    fi

    # Build check JSON
    check=$(python3 -c "
import json
print(json.dumps({
    'name': '$name',
    'command': $(python3 -c "import json; print(json.dumps('$cmd'))"),
    'exit_code': $exit_code,
    'duration_ms': $duration_ms,
    'summary': ${summary}
}))
")
    CHECKS=$(echo "$CHECKS" | python3 -c "
import sys, json
checks = json.load(sys.stdin)
checks.append(json.loads('$check'))
print(json.dumps(checks))
")
done

# --- Build verify.json ---
RESULT=$(python3 -c "
import json
print(json.dumps({
    'timestamp': '$TIMESTAMP',
    'checks': json.loads('$CHECKS'),
    'all_passed': $( [ "$ALL_PASSED" = true ] && echo 'True' || echo 'False' ),
    'total_duration_ms': $TOTAL_MS
}, indent=2))
")

echo "$RESULT" | tee "$ARTIFACT_DIR/verify.json"

# Exit with failure if any check failed
$ALL_PASSED || exit 1

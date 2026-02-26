#!/usr/bin/env bash
# Store test/quality command output and metadata under docs/qa/test-results/.

set -u -o pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: ./scripts/store_test_results.sh <label> -- <command ...>"
  echo "Example: ./scripts/store_test_results.sh unit-tests -- uv run python -m pytest tests/ -v"
  exit 1
fi

LABEL="$1"
shift

if [[ "$1" != "--" ]]; then
  echo "Error: missing '--' separator before command."
  exit 1
fi
shift

if [[ $# -eq 0 ]]; then
  echo "Error: missing command."
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/docs/qa/test-results"
mkdir -p "$OUT_DIR"

STAMP="$(date -u +%Y%m%d-%H%M%S)"
BASE="$OUT_DIR/${STAMP}-${LABEL}"
LOG_FILE="${BASE}.log"
META_FILE="${BASE}.md"

CMD=( "$@" )
CMD_STR="${CMD[*]}"
START_UTC="$(date -u '+%Y-%m-%d %H:%M:%S')"

echo "[store-test-results] Running: $CMD_STR"

(
  cd "$ROOT_DIR"
  "${CMD[@]}"
) >"$LOG_FILE" 2>&1
RC=$?

END_UTC="$(date -u '+%Y-%m-%d %H:%M:%S')"

if [[ "$RC" -eq 0 ]]; then
  STATUS="PASS"
else
  STATUS="FAIL"
fi

{
  echo "# Stored Test Result"
  echo
  echo "- Label: $LABEL"
  echo "- Status: $STATUS"
  echo "- Exit code: $RC"
  echo "- Started (UTC): $START_UTC"
  echo "- Finished (UTC): $END_UTC"
  echo "- Command: $CMD_STR"
  echo "- Log: ${LOG_FILE#$ROOT_DIR/}"
} >"$META_FILE"

echo "[store-test-results] Result: $STATUS (exit=$RC)"
echo "[store-test-results] Metadata: ${META_FILE#$ROOT_DIR/}"
echo "[store-test-results] Log: ${LOG_FILE#$ROOT_DIR/}"

exit "$RC"

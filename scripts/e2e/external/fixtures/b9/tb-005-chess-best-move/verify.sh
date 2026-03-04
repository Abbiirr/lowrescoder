#!/usr/bin/env bash
# Grading script for tb-005-chess-best-move
set -euo pipefail

# Run the solution
MOVE=$(python find_move.py 2>/dev/null | tr -d '[:space:]')

# The best move is Qh7# (checkmate) — in UCI notation: h5h7
EXPECTED="h5h7"

if [ "$MOVE" = "$EXPECTED" ]; then
    echo "PASS: Correct move '$MOVE' (Qh7#, checkmate)"
    exit 0
fi

# Also accept standard algebraic notation variants
if [ "$MOVE" = "Qh7#" ] || [ "$MOVE" = "Qh7" ] || [ "$MOVE" = "qh7" ]; then
    echo "PASS: Correct move '$MOVE' (accepted algebraic notation)"
    exit 0
fi

echo "FAIL: Expected '$EXPECTED' (Qh7#), got '$MOVE'"
exit 1

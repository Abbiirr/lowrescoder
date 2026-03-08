# Task: Find Best Chess Move

## Objective

Given a chess position in FEN notation, find the best move.

## Requirements

1. Read the FEN position from `position.fen`.
2. Edit `find_move.py` to analyze the position and find the best move.
3. Output the best move in UCI notation (e.g., `e2e4`, `h5h7`) — just the 4-character move string.
4. The script should print ONLY the move to stdout, nothing else.
5. Run with `python find_move.py`.

## Hints

- The position is a well-known tactical pattern.
- White is to move.
- Look for forcing moves (checks, captures, threats).
- The `python-chess` library is preinstalled and can be used directly.

## Files

- `position.fen` — the chess position in FEN notation
- `find_move.py` — the script you must edit

#!/usr/bin/env bash
# Setup for tb-005-chess-best-move
# Creates a FEN position file and empty solution script.
# The position is a well-known "mate in 1" puzzle.
set -euo pipefail

# Position: White to move, mate in 1 with Qh7#
# Board: Black king on g8, white queen on h5, white bishop on c2,
# black pawns on f7, g6, h6. White can play Qh7# (checkmate).
# FEN: 6k1/5p2/6pp/7Q/8/8/2B5/6K1 w - - 0 1
cat > position.fen << 'FEN'
6k1/5p2/6pp/7Q/8/8/2B5/6K1 w - - 0 1
FEN

# Create stub solution
cat > find_move.py << 'STUB'
#!/usr/bin/env python3
"""Read position.fen and output the best move in UCI notation (e.g., 'h5h7').

The output should be exactly the move in UCI format: source_square + dest_square
(e.g., 'e2e4', 'h5h7').

Print ONLY the move, nothing else.
"""
# TODO: Analyze the position and find the best move
STUB

chmod +x find_move.py

echo "Setup complete. Chess position created."

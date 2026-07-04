# Task: Navigate a 5x5 Maze

## Objective

Find a path through a 5x5 maze from start (0,0) to goal (4,4).

## Tools

You have a maze CLI tool to explore the maze:

```bash
python maze_cli.py look          # See available directions from current position
python maze_cli.py move <dir>    # Move north/south/east/west
python maze_cli.py position      # Show current position and stats
python maze_cli.py reset         # Reset to start
```

You can also read `.maze.json` directly if you prefer a programmatic approach.

## Requirements

1. Navigate from start position (0,0) to goal position (4,4).
2. Write the solution path to `solution.txt`, one position per line in `row,col` format:
   ```
   0,0
   1,0
   ...
   4,4
   ```
3. The path must be valid (each step moves to an adjacent open cell).
4. The path must start at `0,0` and end at `4,4`.
5. You may solve this interactively using the CLI or programmatically.

## Maze Coordinates

- Row 0 is the top, row 4 is the bottom.
- Column 0 is the left, column 4 is the right.
- `north` decreases row, `south` increases row.
- `west` decreases column, `east` increases column.

## Files

- `maze_cli.py` — the maze exploration tool
- `.maze.json` — the maze definition (you may read this)
- `solve_maze.py` — optional: edit this to write a solver
- `solution.txt` — write your solution path here

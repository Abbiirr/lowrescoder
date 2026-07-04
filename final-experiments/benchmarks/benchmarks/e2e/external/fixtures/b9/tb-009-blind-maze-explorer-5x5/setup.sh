#!/usr/bin/env bash
# Setup for tb-009-blind-maze-explorer-5x5
# Creates a 5x5 maze with a CLI explorer tool and a stub solver.
set -euo pipefail

# Create the maze definition (hidden from agent — used by explorer and verifier)
# 0 = open, 1 = wall
# Start: (0,0), Goal: (4,4)
#
# Maze layout:
#   0 1 2 3 4
# 0 S 0 1 0 0
# 1 0 1 0 1 0
# 2 0 0 0 0 1
# 3 1 1 0 1 0
# 4 0 0 0 1 G
#
# Solution path: (0,0)->(1,0)->(2,0)->(2,1)->(2,2)->(2,3)->(1,2)->(0,1) ... many paths
# Shortest: (0,0)->(1,0)->(2,0)->(2,1)->(2,2)->(2,3)->(3,2)->(4,2)->(4,1)->(4,0) ...
# Actually let's use a simpler representation

cat > .maze.json << 'MAZE'
{
  "width": 5,
  "height": 5,
  "start": [0, 0],
  "goal": [4, 4],
  "grid": [
    [0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0],
    [0, 0, 0, 0, 1],
    [1, 1, 0, 1, 0],
    [0, 0, 0, 1, 0]
  ]
}
MAZE

# Create the maze explorer CLI tool
cat > maze_cli.py << 'EXPLORER'
#!/usr/bin/env python3
"""Maze Explorer CLI — interact with a 5x5 maze.

Commands (pass as arguments):
  python maze_cli.py look          — shows available directions from current position
  python maze_cli.py move <dir>    — move in direction (north/south/east/west)
  python maze_cli.py position      — show current position
  python maze_cli.py reset         — reset to start position

State is persisted in .maze_state.json
"""
import json
import sys
import os

MAZE_FILE = ".maze.json"
STATE_FILE = ".maze_state.json"

def load_maze():
    with open(MAZE_FILE) as f:
        return json.load(f)

def load_state(maze):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"pos": list(maze["start"]), "visited": [list(maze["start"])], "moves": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_neighbors(maze, row, col):
    dirs = {}
    grid = maze["grid"]
    h, w = maze["height"], maze["width"]
    if row > 0 and grid[row-1][col] == 0:
        dirs["north"] = (row-1, col)
    if row < h-1 and grid[row+1][col] == 0:
        dirs["south"] = (row+1, col)
    if col > 0 and grid[row][col-1] == 0:
        dirs["west"] = (row, col-1)
    if col < w-1 and grid[row][col+1] == 0:
        dirs["east"] = (row, col+1)
    return dirs

def main():
    if len(sys.argv) < 2:
        print("Usage: python maze_cli.py <command> [args]")
        print("Commands: look, move <dir>, position, reset")
        sys.exit(1)

    maze = load_maze()
    state = load_state(maze)
    cmd = sys.argv[1].lower()

    row, col = state["pos"]

    if cmd == "look":
        neighbors = get_neighbors(maze, row, col)
        if not neighbors:
            print("No available directions (stuck)")
        else:
            print("Available directions:", ", ".join(sorted(neighbors.keys())))
        if [row, col] == maze["goal"]:
            print("*** You are at the GOAL! ***")

    elif cmd == "move":
        if len(sys.argv) < 3:
            print("Usage: move <north|south|east|west>")
            sys.exit(1)
        direction = sys.argv[2].lower()
        neighbors = get_neighbors(maze, row, col)
        if direction not in neighbors:
            print(f"Cannot move {direction} — wall or boundary")
            sys.exit(1)
        new_row, new_col = neighbors[direction]
        state["pos"] = [new_row, new_col]
        state["moves"] += 1
        if [new_row, new_col] not in state["visited"]:
            state["visited"].append([new_row, new_col])
        save_state(state)
        print(f"Moved {direction} to ({new_row}, {new_col})")
        if [new_row, new_col] == maze["goal"]:
            print("*** GOAL REACHED! ***")

    elif cmd == "position":
        print(f"Position: ({row}, {col})")
        print(f"Moves: {state['moves']}")
        print(f"Cells visited: {len(state['visited'])}")

    elif cmd == "reset":
        state = {"pos": list(maze["start"]), "visited": [list(maze["start"])], "moves": 0}
        save_state(state)
        print("Reset to start position (0, 0)")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EXPLORER

chmod +x maze_cli.py

# Create stub solver
cat > solve_maze.py << 'STUB'
#!/usr/bin/env python3
"""Solve the 5x5 maze by navigating from start to goal.

Use the maze_cli.py tool to explore and navigate:
  python maze_cli.py look        — see available directions
  python maze_cli.py move <dir>  — move north/south/east/west
  python maze_cli.py position    — see current position

You can also write a programmatic solver that uses maze_cli.py
or reads .maze.json directly.

Your goal: reach position (4, 4) from (0, 0).

Output: Write the solution path to solution.txt, one position per line:
  0,0
  1,0
  2,0
  ...
  4,4
"""
# TODO: Navigate the maze and write solution path to solution.txt
STUB

chmod +x solve_maze.py

echo "Setup complete. 5x5 maze created with CLI explorer."

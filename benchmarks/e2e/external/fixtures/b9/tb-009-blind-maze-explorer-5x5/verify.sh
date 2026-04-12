#!/usr/bin/env bash
# Grading script for tb-009-blind-maze-explorer-5x5
set -euo pipefail

# Verify the solution path using Python
python3 << 'PYCHECK'
import json
import sys

# Load maze
with open(".maze.json") as f:
    maze = json.load(f)

grid = maze["grid"]
start = tuple(maze["start"])
goal = tuple(maze["goal"])

# Load solution
try:
    with open("solution.txt") as f:
        lines = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print("FAIL: solution.txt not found")
    sys.exit(1)

if not lines:
    print("FAIL: solution.txt is empty")
    sys.exit(1)

# Parse path
path = []
for i, line in enumerate(lines):
    parts = line.split(",")
    if len(parts) != 2:
        print(f"FAIL: Line {i+1} invalid format: '{line}' (expected 'row,col')")
        sys.exit(1)
    try:
        r, c = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        print(f"FAIL: Line {i+1} has non-integer values: '{line}'")
        sys.exit(1)
    path.append((r, c))

errors = 0

# Check start
if path[0] != start:
    print(f"FAIL: Path must start at {start}, starts at {path[0]}")
    errors += 1
else:
    print(f"PASS: Path starts at {start}")

# Check goal
if path[-1] != goal:
    print(f"FAIL: Path must end at {goal}, ends at {path[-1]}")
    errors += 1
else:
    print(f"PASS: Path ends at {goal}")

# Check each cell is valid (in bounds, not a wall)
for i, (r, c) in enumerate(path):
    if r < 0 or r >= maze["height"] or c < 0 or c >= maze["width"]:
        print(f"FAIL: Step {i} ({r},{c}) is out of bounds")
        errors += 1
    elif grid[r][c] == 1:
        print(f"FAIL: Step {i} ({r},{c}) is a wall")
        errors += 1

# Check adjacency (each step is exactly 1 cell away, orthogonal)
for i in range(1, len(path)):
    r1, c1 = path[i-1]
    r2, c2 = path[i]
    dist = abs(r1 - r2) + abs(c1 - c2)
    if dist != 1:
        print(f"FAIL: Steps {i-1}->{ i} ({r1},{c1})->({r2},{c2}) are not adjacent (distance={dist})")
        errors += 1

if errors > 0:
    print(f"RESULT: {errors} check(s) failed")
    sys.exit(1)

print(f"PASS: Valid path with {len(path)} steps")
print("RESULT: All checks passed")
PYCHECK

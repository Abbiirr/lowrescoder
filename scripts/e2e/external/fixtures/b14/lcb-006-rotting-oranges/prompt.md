# Rotting Oranges

You are given an `m x n` grid where each cell can have one of three values:

- `0` representing an empty cell
- `1` representing a fresh orange
- `2` representing a rotten orange

Every minute, any fresh orange that is 4-directionally adjacent to a rotten orange becomes rotten.

Return the minimum number of minutes that must elapse until no cell has a fresh orange. If this is impossible, return `-1`.

## Function Signature

```python
def oranges_rotting(grid: list[list[int]]) -> int
```

## Constraints

- `m == grid.length`
- `n == grid[i].length`
- `1 <= m, n <= 10`
- `grid[i][j]` is `0`, `1`, or `2`

## Examples

```
Input: grid = [[2,1,1],[1,1,0],[0,1,1]]
Output: 4

Input: grid = [[2,1,1],[0,1,1],[1,0,1]]
Output: -1
Explanation: The orange in the bottom left corner is never reached.

Input: grid = [[0,2]]
Output: 0
Explanation: No fresh oranges at minute 0, so the answer is 0.
```

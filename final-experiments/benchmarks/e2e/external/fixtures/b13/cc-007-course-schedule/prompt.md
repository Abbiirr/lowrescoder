# Course Schedule

## Problem

There are a total of `num_courses` courses you have to take, labeled from `0` to `num_courses - 1`. You are given an array `prerequisites` where `prerequisites[i] = [a_i, b_i]` indicates that you must take course `b_i` before course `a_i`.

Return `True` if you can finish all courses. Otherwise, return `False`.

This is essentially a cycle detection problem in a directed graph.

## Function Signature

```python
def can_finish(num_courses: int, prerequisites: list[list[int]]) -> bool:
```

## Constraints

- `1 <= num_courses <= 2000`
- `0 <= len(prerequisites) <= 5000`
- `prerequisites[i].length == 2`
- `0 <= a_i, b_i < num_courses`
- All the pairs `prerequisites[i]` are unique.

## Examples

**Example 1:**
```
Input: num_courses = 2, prerequisites = [[1, 0]]
Output: True
Explanation: To take course 1, you need to finish course 0. This is possible.
```

**Example 2:**
```
Input: num_courses = 2, prerequisites = [[1, 0], [0, 1]]
Output: False
Explanation: To take course 1 you need course 0, and to take course 0 you need course 1. Impossible.
```

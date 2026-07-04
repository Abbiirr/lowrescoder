# Binary Tree Level Order Traversal

Given the `root` of a binary tree, return the level order traversal of its nodes' values (i.e., from left to right, level by level).

## Data Structure

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

## Function Signature

```python
def level_order(root: TreeNode) -> list[list[int]]
```

## Constraints

- The number of nodes in the tree is in the range `[0, 2000]`
- `-1000 <= Node.val <= 1000`

## Examples

```
Input: root = [3,9,20,null,null,15,7]
       3
      / \
     9  20
       /  \
      15   7
Output: [[3],[9,20],[15,7]]

Input: root = [1]
Output: [[1]]

Input: root = []
Output: []
```

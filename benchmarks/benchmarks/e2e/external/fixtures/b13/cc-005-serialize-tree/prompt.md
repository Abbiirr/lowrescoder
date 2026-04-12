# Serialize and Deserialize Binary Tree

## Problem

Design an algorithm to serialize and deserialize a binary tree. There is no restriction on how your serialization/deserialization algorithm should work. You just need to ensure that a binary tree can be serialized to a string and this string can be deserialized to the original tree structure.

A `TreeNode` class is provided:

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

## Class Signature

```python
class Codec:
    def serialize(self, root: TreeNode | None) -> str:
        ...

    def deserialize(self, data: str) -> TreeNode | None:
        ...
```

## Constraints

- The number of nodes in the tree is in the range `[0, 10^4]`.
- `-1000 <= Node.val <= 1000`

## Examples

**Example 1:**
```
Input tree:
    1
   / \
  2   3
     / \
    4   5

serialize(root) -> some string representation
deserialize(that string) -> reconstructed tree identical to original
```

**Example 2:**
```
Input: empty tree (None)
serialize(None) -> some string
deserialize(that string) -> None
```

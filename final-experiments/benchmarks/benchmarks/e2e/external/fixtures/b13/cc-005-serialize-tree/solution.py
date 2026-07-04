"""Serialize and Deserialize Binary Tree."""


class TreeNode:
    def __init__(self, val: int = 0, left: "TreeNode | None" = None, right: "TreeNode | None" = None):
        self.val = val
        self.left = left
        self.right = right


class Codec:
    def serialize(self, root: TreeNode | None) -> str:
        raise NotImplementedError

    def deserialize(self, data: str) -> TreeNode | None:
        raise NotImplementedError

class TreeNode:
    """Binary tree node."""

    def __init__(self, val: int = 0, left: "TreeNode | None" = None, right: "TreeNode | None" = None):
        self.val = val
        self.left = left
        self.right = right


def level_order(root: TreeNode | None) -> list[list[int]]:
    """Return level order traversal of a binary tree."""
    raise NotImplementedError

"""Hidden tests for lcb-011-binary-tree-level-order."""
from solution import TreeNode, level_order


def test_basic():
    #       3
    #      / \
    #     9  20
    #       /  \
    #      15   7
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))
    assert level_order(root) == [[3], [9, 20], [15, 7]]


def test_single_node():
    root = TreeNode(1)
    assert level_order(root) == [[1]]


def test_empty_tree():
    assert level_order(None) == []


def test_left_skewed():
    root = TreeNode(1, TreeNode(2, TreeNode(3)))
    assert level_order(root) == [[1], [2], [3]]


def test_right_skewed():
    root = TreeNode(1, None, TreeNode(2, None, TreeNode(3)))
    assert level_order(root) == [[1], [2], [3]]


def test_full_tree():
    #       1
    #      / \
    #     2   3
    #    / \ / \
    #   4  5 6  7
    root = TreeNode(
        1,
        TreeNode(2, TreeNode(4), TreeNode(5)),
        TreeNode(3, TreeNode(6), TreeNode(7)),
    )
    assert level_order(root) == [[1], [2, 3], [4, 5, 6, 7]]


def test_negative_values():
    root = TreeNode(-1, TreeNode(-2), TreeNode(-3))
    assert level_order(root) == [[-1], [-2, -3]]


def test_mixed_children():
    #     1
    #    / \
    #   2   3
    #  /     \
    # 4       5
    root = TreeNode(1, TreeNode(2, TreeNode(4)), TreeNode(3, None, TreeNode(5)))
    assert level_order(root) == [[1], [2, 3], [4, 5]]

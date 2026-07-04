"""Hidden tests for cc-005-serialize-tree."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import TreeNode, Codec


def trees_equal(a: TreeNode | None, b: TreeNode | None) -> bool:
    """Helper to compare two trees for structural and value equality."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.val == b.val and trees_equal(a.left, b.left) and trees_equal(a.right, b.right)


class TestSerializeTree:
    """Test suite for the Codec class."""

    def test_basic_tree(self):
        #     1
        #    / \
        #   2   3
        #      / \
        #     4   5
        root = TreeNode(1, TreeNode(2), TreeNode(3, TreeNode(4), TreeNode(5)))
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

    def test_empty_tree(self):
        codec = Codec()
        data = codec.serialize(None)
        result = codec.deserialize(data)
        assert result is None

    def test_single_node(self):
        root = TreeNode(42)
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

    def test_left_skewed(self):
        root = TreeNode(1, TreeNode(2, TreeNode(3, TreeNode(4))))
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

    def test_right_skewed(self):
        root = TreeNode(1, None, TreeNode(2, None, TreeNode(3, None, TreeNode(4))))
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

    def test_negative_values(self):
        root = TreeNode(-1, TreeNode(-2), TreeNode(-3))
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

    def test_mixed_values(self):
        root = TreeNode(0, TreeNode(-100), TreeNode(100))
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

    def test_serialize_returns_string(self):
        root = TreeNode(1)
        codec = Codec()
        data = codec.serialize(root)
        assert isinstance(data, str)

    def test_roundtrip_preserves_structure(self):
        #       5
        #      / \
        #     3   8
        #    /   / \
        #   1   6   9
        root = TreeNode(5,
            TreeNode(3, TreeNode(1), None),
            TreeNode(8, TreeNode(6), TreeNode(9))
        )
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

    def test_duplicate_values(self):
        root = TreeNode(1, TreeNode(1), TreeNode(1))
        codec = Codec()
        data = codec.serialize(root)
        result = codec.deserialize(data)
        assert trees_equal(root, result)

"""Hidden tests for cc-009-valid-parentheses."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import is_valid


class TestValidParentheses:
    """Test suite for the is_valid function."""

    def test_simple_parens(self):
        assert is_valid("()") is True

    def test_multiple_types(self):
        assert is_valid("()[]{}") is True

    def test_mismatched(self):
        assert is_valid("(]") is False

    def test_nested(self):
        assert is_valid("([])") is True

    def test_single_open(self):
        assert is_valid("(") is False

    def test_single_close(self):
        assert is_valid(")") is False

    def test_deeply_nested(self):
        assert is_valid("({[()]})") is True

    def test_wrong_nesting_order(self):
        assert is_valid("([)]") is False

    def test_only_close_brackets(self):
        assert is_valid(")))") is False

    def test_long_valid(self):
        assert is_valid("()" * 1000) is True

    def test_interleaved_types(self):
        assert is_valid("{[()]}[]()") is True

    def test_extra_closing(self):
        assert is_valid("(){}]") is False

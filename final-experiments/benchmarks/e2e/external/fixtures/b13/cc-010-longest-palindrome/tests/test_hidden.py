"""Hidden tests for cc-010-longest-palindrome."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import longest_palindrome


def _is_palindrome(s: str) -> bool:
    return s == s[::-1]


class TestLongestPalindrome:
    """Test suite for the longest_palindrome function."""

    def test_basic_odd_length(self):
        result = longest_palindrome("babad")
        assert result in ("bab", "aba")

    def test_basic_even_length(self):
        assert longest_palindrome("cbbd") == "bb"

    def test_single_char(self):
        assert longest_palindrome("a") == "a"

    def test_two_different_chars(self):
        result = longest_palindrome("ac")
        assert len(result) == 1
        assert result in ("a", "c")

    def test_entire_string_is_palindrome(self):
        assert longest_palindrome("racecar") == "racecar"

    def test_all_same_chars(self):
        assert longest_palindrome("aaaa") == "aaaa"

    def test_palindrome_at_end(self):
        result = longest_palindrome("abcddcba")
        assert result == "abcddcba"

    def test_no_two_char_palindrome(self):
        result = longest_palindrome("abcde")
        assert len(result) == 1
        assert result in "abcde"

    def test_result_is_palindrome(self):
        result = longest_palindrome("xyzabacabad")
        assert _is_palindrome(result)
        assert len(result) >= 3  # "abacaba" is length 7

    def test_long_palindrome(self):
        s = "a" * 100 + "b" + "a" * 100
        result = longest_palindrome(s)
        assert _is_palindrome(result)
        assert len(result) == 201

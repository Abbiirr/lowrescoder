"""Hidden tests for cc-004-word-break."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import word_break


class TestWordBreak:
    """Test suite for the word_break function."""

    def test_basic_true(self):
        assert word_break("leetcode", ["leet", "code"]) is True

    def test_reuse_words(self):
        assert word_break("applepenapple", ["apple", "pen"]) is True

    def test_basic_false(self):
        assert word_break("catsandog", ["cats", "dog", "sand", "and", "cat"]) is False

    def test_single_character(self):
        assert word_break("a", ["a"]) is True

    def test_single_character_missing(self):
        assert word_break("b", ["a"]) is False

    def test_empty_string(self):
        # Empty string can always be segmented (base case)
        assert word_break("", ["a", "b"]) is True

    def test_overlapping_words(self):
        assert word_break("cars", ["car", "ca", "rs"]) is True

    def test_repeated_single_word(self):
        assert word_break("aaaa", ["a"]) is True

    def test_prefix_trap(self):
        # "aaaaaaa" with dict ["aaaa", "aaa"] => True (4+3 or 3+4)
        assert word_break("aaaaaaa", ["aaaa", "aaa"]) is True

    def test_long_no_match(self):
        assert word_break("abcdef", ["ab", "cd"]) is False

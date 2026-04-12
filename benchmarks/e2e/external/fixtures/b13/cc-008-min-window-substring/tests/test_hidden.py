"""Hidden tests for cc-008-min-window-substring."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import min_window


class TestMinWindow:
    """Test suite for the min_window function."""

    def test_basic_case(self):
        assert min_window("ADOBECODEBANC", "ABC") == "BANC"

    def test_exact_match(self):
        assert min_window("a", "a") == "a"

    def test_no_valid_window(self):
        assert min_window("a", "aa") == ""

    def test_t_not_in_s(self):
        assert min_window("abc", "xyz") == ""

    def test_entire_string_is_window(self):
        assert min_window("abc", "abc") == "abc"

    def test_duplicate_chars_in_t(self):
        result = min_window("aabbc", "aab")
        assert result == "aab"

    def test_window_at_start(self):
        assert min_window("abcdef", "abc") == "abc"

    def test_window_at_end(self):
        result = min_window("xyzabc", "abc")
        assert result == "abc"

    def test_single_char_repeated(self):
        assert min_window("aaaa", "a") == "a"

    def test_case_sensitive(self):
        # 'A' and 'a' are different characters
        assert min_window("aA", "A") == "A"

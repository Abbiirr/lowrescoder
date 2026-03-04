"""Hidden tests for cc-001-two-sum."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import two_sum


class TestTwoSum:
    """Test suite for the two_sum function."""

    def test_basic_case(self):
        result = two_sum([2, 7, 11, 15], 9)
        assert sorted(result) == [0, 1]

    def test_non_adjacent_elements(self):
        result = two_sum([3, 2, 4], 6)
        assert sorted(result) == [1, 2]

    def test_duplicate_values(self):
        result = two_sum([3, 3], 6)
        assert sorted(result) == [0, 1]

    def test_negative_numbers(self):
        result = two_sum([-1, -2, -3, -4, -5], -8)
        assert sorted(result) == [2, 4]

    def test_mixed_positive_negative(self):
        result = two_sum([1, -3, 4, 2], -1)
        assert sorted(result) == [1, 3]

    def test_zero_target(self):
        result = two_sum([0, 4, 3, 0], 0)
        assert sorted(result) == [0, 3]

    def test_large_numbers(self):
        result = two_sum([1000000000, -1000000000, 3, 5], 0)
        assert sorted(result) == [0, 1]

    def test_two_elements(self):
        result = two_sum([5, 5], 10)
        assert sorted(result) == [0, 1]

    def test_target_with_first_and_last(self):
        result = two_sum([1, 2, 3, 4, 5], 6)
        # Valid pairs: (1,5)=[0,4] or (2,4)=[1,3]
        i, j = sorted(result)
        assert result[0] != result[1]
        nums = [1, 2, 3, 4, 5]
        assert nums[i] + nums[j] == 6

    def test_returns_list_of_two(self):
        result = two_sum([2, 7, 11, 15], 9)
        assert isinstance(result, list)
        assert len(result) == 2

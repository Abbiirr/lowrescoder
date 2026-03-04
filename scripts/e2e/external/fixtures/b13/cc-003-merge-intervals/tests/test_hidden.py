"""Hidden tests for cc-003-merge-intervals."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import merge


class TestMergeIntervals:
    """Test suite for the merge function."""

    def test_basic_merge(self):
        result = merge([[1, 3], [2, 6], [8, 10], [15, 18]])
        assert result == [[1, 6], [8, 10], [15, 18]]

    def test_touching_intervals(self):
        result = merge([[1, 4], [4, 5]])
        assert result == [[1, 5]]

    def test_single_interval(self):
        result = merge([[1, 4]])
        assert result == [[1, 4]]

    def test_no_overlap(self):
        result = merge([[1, 2], [4, 5], [7, 8]])
        assert result == [[1, 2], [4, 5], [7, 8]]

    def test_all_overlap(self):
        result = merge([[1, 10], [2, 6], [3, 5], [7, 9]])
        assert result == [[1, 10]]

    def test_unsorted_input(self):
        result = merge([[1, 4], [0, 4]])
        assert result == [[0, 4]]

    def test_contained_intervals(self):
        result = merge([[1, 10], [2, 3], [4, 5], [6, 7]])
        assert result == [[1, 10]]

    def test_multiple_merges(self):
        result = merge([[1, 3], [2, 4], [3, 5], [6, 8], [7, 9]])
        assert result == [[1, 5], [6, 9]]

    def test_same_start(self):
        result = merge([[1, 3], [1, 6], [1, 2]])
        assert result == [[1, 6]]

    def test_identical_intervals(self):
        result = merge([[1, 4], [1, 4]])
        assert result == [[1, 4]]

"""Hidden tests for cc-006-median-stream."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import MedianFinder


class TestMedianFinder:
    """Test suite for the MedianFinder class."""

    def test_single_element(self):
        mf = MedianFinder()
        mf.add_num(5)
        assert mf.find_median() == 5.0

    def test_two_elements(self):
        mf = MedianFinder()
        mf.add_num(1)
        mf.add_num(2)
        assert mf.find_median() == 1.5

    def test_three_elements(self):
        mf = MedianFinder()
        mf.add_num(1)
        mf.add_num(2)
        mf.add_num(3)
        assert mf.find_median() == 2.0

    def test_running_median(self):
        mf = MedianFinder()
        mf.add_num(1)
        assert mf.find_median() == 1.0
        mf.add_num(2)
        assert mf.find_median() == 1.5
        mf.add_num(3)
        assert mf.find_median() == 2.0

    def test_negative_numbers(self):
        mf = MedianFinder()
        mf.add_num(-5)
        mf.add_num(-3)
        mf.add_num(-1)
        assert mf.find_median() == -3.0

    def test_duplicates(self):
        mf = MedianFinder()
        mf.add_num(5)
        mf.add_num(5)
        mf.add_num(5)
        assert mf.find_median() == 5.0

    def test_unsorted_input(self):
        mf = MedianFinder()
        mf.add_num(6)
        mf.add_num(10)
        mf.add_num(2)
        mf.add_num(6)
        mf.add_num(5)
        # Sorted: [2, 5, 6, 6, 10] -> median = 6.0
        assert mf.find_median() == 6.0

    def test_even_count_average(self):
        mf = MedianFinder()
        mf.add_num(1)
        mf.add_num(3)
        mf.add_num(5)
        mf.add_num(7)
        # Sorted: [1, 3, 5, 7] -> median = (3+5)/2 = 4.0
        assert mf.find_median() == 4.0

    def test_large_range(self):
        mf = MedianFinder()
        mf.add_num(-100000)
        mf.add_num(100000)
        assert mf.find_median() == 0.0

    def test_returns_float(self):
        mf = MedianFinder()
        mf.add_num(1)
        result = mf.find_median()
        assert isinstance(result, (int, float))

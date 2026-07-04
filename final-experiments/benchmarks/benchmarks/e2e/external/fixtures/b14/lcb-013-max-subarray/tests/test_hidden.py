"""Hidden tests for lcb-013-max-subarray."""
from solution import max_sub_array


def test_basic():
    assert max_sub_array([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6


def test_single_element():
    assert max_sub_array([1]) == 1


def test_all_positive():
    assert max_sub_array([5, 4, -1, 7, 8]) == 23


def test_all_negative():
    assert max_sub_array([-3, -2, -5, -1, -4]) == -1


def test_single_negative():
    assert max_sub_array([-1]) == -1


def test_mixed_starting_positive():
    assert max_sub_array([2, -1, 3]) == 4


def test_entire_array():
    assert max_sub_array([1, 2, 3, 4]) == 10


def test_negative_then_positive():
    assert max_sub_array([-5, 1, 2, 3]) == 6


def test_large_negative_gap():
    assert max_sub_array([5, -100, 6]) == 6


def test_alternating():
    assert max_sub_array([1, -1, 1, -1, 1]) == 1

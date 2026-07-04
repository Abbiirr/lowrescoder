"""Hidden tests for lcb-007-longest-increasing-subsequence."""
from solution import length_of_lis


def test_basic():
    assert length_of_lis([10, 9, 2, 5, 3, 7, 101, 18]) == 4


def test_with_duplicates_in_lis():
    assert length_of_lis([0, 1, 0, 3, 2, 3]) == 4


def test_all_same():
    assert length_of_lis([7, 7, 7, 7, 7, 7, 7]) == 1


def test_single_element():
    assert length_of_lis([42]) == 1


def test_already_sorted():
    assert length_of_lis([1, 2, 3, 4, 5]) == 5


def test_reverse_sorted():
    assert length_of_lis([5, 4, 3, 2, 1]) == 1


def test_two_elements_increasing():
    assert length_of_lis([1, 2]) == 2


def test_two_elements_decreasing():
    assert length_of_lis([2, 1]) == 1


def test_negative_numbers():
    assert length_of_lis([-5, -3, -1, 0, 2]) == 5


def test_mixed():
    assert length_of_lis([3, 1, 4, 1, 5, 9, 2, 6]) == 4

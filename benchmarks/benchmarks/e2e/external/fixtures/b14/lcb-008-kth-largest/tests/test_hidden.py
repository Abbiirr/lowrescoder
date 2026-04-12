"""Hidden tests for lcb-008-kth-largest."""
from solution import find_kth_largest


def test_basic():
    assert find_kth_largest([3, 2, 1, 5, 6, 4], 2) == 5


def test_with_duplicates():
    assert find_kth_largest([3, 2, 3, 1, 2, 4, 5, 5, 6], 4) == 4


def test_single_element():
    assert find_kth_largest([1], 1) == 1


def test_k_equals_length():
    assert find_kth_largest([3, 2, 1], 3) == 1


def test_k_equals_one():
    assert find_kth_largest([3, 2, 1], 1) == 3


def test_all_same():
    assert find_kth_largest([5, 5, 5, 5], 2) == 5


def test_negative_numbers():
    assert find_kth_largest([-1, -2, -3, -4], 1) == -1


def test_mixed_signs():
    assert find_kth_largest([-1, 2, 0, -3, 5], 3) == 0


def test_two_elements():
    assert find_kth_largest([7, 3], 1) == 7


def test_large_k():
    assert find_kth_largest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 10) == 1

"""Hidden tests for lcb-004-trapping-rain-water."""
from solution import trap


def test_basic():
    assert trap([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6


def test_v_shape():
    assert trap([4, 2, 0, 3, 2, 5]) == 9


def test_empty():
    assert trap([]) == 0


def test_single():
    assert trap([5]) == 0


def test_two_bars():
    assert trap([3, 1]) == 0


def test_flat():
    assert trap([3, 3, 3, 3]) == 0


def test_descending():
    assert trap([5, 4, 3, 2, 1]) == 0


def test_ascending():
    assert trap([1, 2, 3, 4, 5]) == 0


def test_simple_valley():
    assert trap([3, 0, 3]) == 3


def test_uneven_valley():
    assert trap([2, 0, 4]) == 2


def test_multiple_valleys():
    assert trap([3, 0, 2, 0, 4]) == 7

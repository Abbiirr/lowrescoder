"""Hidden tests for lcb-006-rotting-oranges."""
from solution import oranges_rotting


def test_basic():
    assert oranges_rotting([[2, 1, 1], [1, 1, 0], [0, 1, 1]]) == 4


def test_impossible():
    assert oranges_rotting([[2, 1, 1], [0, 1, 1], [1, 0, 1]]) == -1


def test_no_fresh():
    assert oranges_rotting([[0, 2]]) == 0


def test_all_empty():
    assert oranges_rotting([[0, 0], [0, 0]]) == 0


def test_single_rotten():
    assert oranges_rotting([[2]]) == 0


def test_single_fresh():
    assert oranges_rotting([[1]]) == -1


def test_already_all_rotten():
    assert oranges_rotting([[2, 2], [2, 2]]) == 0


def test_line():
    assert oranges_rotting([[2, 1, 1, 1, 1]]) == 4


def test_two_sources():
    assert oranges_rotting([[2, 1, 1, 1, 2]]) == 2


def test_fresh_surrounded_by_empty():
    assert oranges_rotting([[0, 0, 0], [0, 1, 0], [0, 0, 0]]) == -1

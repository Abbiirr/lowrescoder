"""Hidden tests for lcb-010-number-of-islands."""
from solution import num_islands


def test_single_island():
    grid = [
        ["1", "1", "1", "1", "0"],
        ["1", "1", "0", "1", "0"],
        ["1", "1", "0", "0", "0"],
        ["0", "0", "0", "0", "0"],
    ]
    assert num_islands(grid) == 1


def test_three_islands():
    grid = [
        ["1", "1", "0", "0", "0"],
        ["1", "1", "0", "0", "0"],
        ["0", "0", "1", "0", "0"],
        ["0", "0", "0", "1", "1"],
    ]
    assert num_islands(grid) == 3


def test_all_water():
    grid = [["0", "0"], ["0", "0"]]
    assert num_islands(grid) == 0


def test_all_land():
    grid = [["1", "1"], ["1", "1"]]
    assert num_islands(grid) == 1


def test_single_cell_land():
    assert num_islands([["1"]]) == 1


def test_single_cell_water():
    assert num_islands([["0"]]) == 0


def test_diagonal_not_connected():
    grid = [
        ["1", "0"],
        ["0", "1"],
    ]
    assert num_islands(grid) == 2


def test_checkerboard():
    grid = [
        ["1", "0", "1"],
        ["0", "1", "0"],
        ["1", "0", "1"],
    ]
    assert num_islands(grid) == 5


def test_horizontal_line():
    grid = [["1", "1", "1", "1", "1"]]
    assert num_islands(grid) == 1


def test_vertical_line():
    grid = [["1"], ["1"], ["1"], ["1"]]
    assert num_islands(grid) == 1

"""Hidden tests for lcb-014-word-search."""
from solution import exist


BOARD = [
    ["A", "B", "C", "E"],
    ["S", "F", "C", "S"],
    ["A", "D", "E", "E"],
]


def test_abcced():
    assert exist(BOARD, "ABCCED") is True


def test_see():
    assert exist(BOARD, "SEE") is True


def test_abcb():
    assert exist(BOARD, "ABCB") is False


def test_single_char_found():
    assert exist([["A"]], "A") is True


def test_single_char_not_found():
    assert exist([["A"]], "B") is False


def test_full_board():
    board = [["A", "B"], ["C", "D"]]
    assert exist(board, "ABDC") is True


def test_no_reuse():
    board = [["A", "A"]]
    assert exist(board, "AAA") is False


def test_reuse_different_cells():
    board = [["A", "A"]]
    assert exist(board, "AA") is True


def test_snake_path():
    board = [
        ["A", "B"],
        ["D", "C"],
    ]
    assert exist(board, "ABCD") is True


def test_word_longer_than_board():
    board = [["A"]]
    assert exist(board, "AB") is False

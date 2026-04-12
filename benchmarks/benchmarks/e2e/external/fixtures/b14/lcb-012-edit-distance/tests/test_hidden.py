"""Hidden tests for lcb-012-edit-distance."""
from solution import min_distance


def test_horse_ros():
    assert min_distance("horse", "ros") == 3


def test_intention_execution():
    assert min_distance("intention", "execution") == 5


def test_empty_to_empty():
    assert min_distance("", "") == 0


def test_empty_to_word():
    assert min_distance("", "abc") == 3


def test_word_to_empty():
    assert min_distance("abc", "") == 3


def test_same_word():
    assert min_distance("abc", "abc") == 0


def test_single_char_different():
    assert min_distance("a", "b") == 1


def test_single_char_same():
    assert min_distance("a", "a") == 0


def test_insert_only():
    assert min_distance("abc", "abcd") == 1


def test_delete_only():
    assert min_distance("abcd", "abc") == 1


def test_completely_different():
    assert min_distance("abc", "xyz") == 3

"""Hidden tests for lcb-009-decode-ways."""
from solution import num_decodings


def test_two_ways():
    assert num_decodings("12") == 2


def test_three_ways():
    assert num_decodings("226") == 3


def test_leading_zero():
    assert num_decodings("06") == 0


def test_single_digit():
    assert num_decodings("1") == 1


def test_single_zero():
    assert num_decodings("0") == 0


def test_ten():
    assert num_decodings("10") == 1


def test_twenty_seven():
    assert num_decodings("27") == 1


def test_longer_string():
    assert num_decodings("1234") == 3


def test_all_ones():
    assert num_decodings("111") == 3


def test_contains_zero():
    assert num_decodings("100") == 0


def test_valid_with_zeros():
    assert num_decodings("1020") == 1

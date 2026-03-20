"""Hidden tests for lcb-001-reverse-integer."""
from solution import reverse


def test_positive_number():
    assert reverse(123) == 321


def test_negative_number():
    assert reverse(-123) == -321


def test_trailing_zero():
    assert reverse(120) == 21


def test_zero():
    assert reverse(0) == 0


def test_single_digit():
    assert reverse(7) == 7


def test_negative_single_digit():
    assert reverse(-5) == -5


def test_overflow_positive():
    # 2^31 - 1 = 2147483647; reversed 7463847412 overflows
    assert reverse(1534236469) == 0


def test_overflow_negative():
    # -2^31 = -2147483648; reversed -8463847412 overflows
    assert reverse(-1563847412) == 0


def test_large_valid():
    assert reverse(1463847412) == 2147483641


def test_ten():
    assert reverse(10) == 1

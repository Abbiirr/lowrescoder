"""Tests for floating point comparison bug."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import (
    calculate_total,
    calculate_discount,
    split_bill,
    are_amounts_equal,
    validate_transaction,
)


def test_exact_integers_equal():
    """Integer-like floats should be equal."""
    assert are_amounts_equal(10.0, 10.0) is True


def test_classic_float_issue():
    """0.1 + 0.2 should be considered equal to 0.3.

    This is the classic floating point precision bug:
    >>> 0.1 + 0.2
    0.30000000000000004
    >>> 0.1 + 0.2 == 0.3
    False

    The fix: use approximate comparison.
    """
    a = 0.1 + 0.2
    b = 0.3
    assert are_amounts_equal(a, b) is True, (
        f"0.1 + 0.2 ({a}) should equal 0.3 — float comparison is too strict"
    )


def test_sum_of_tenths():
    """Sum of 0.1 ten times should equal 1.0."""
    a = sum([0.1] * 10)
    assert are_amounts_equal(a, 1.0) is True, (
        f"sum of 0.1*10 ({a}) should equal 1.0"
    )


def test_unequal_amounts():
    """Actually different amounts should not be equal."""
    assert are_amounts_equal(10.0, 10.01) is False


def test_validate_transaction_with_float_sum():
    """Transaction validation should handle float arithmetic.

    Prices: 19.99 + 5.99 + 3.99 = 29.97
    But floating point may give 29.970000000000002.
    """
    items = [
        {"price": 19.99},
        {"price": 5.99},
        {"price": 3.99, "expected_total": 29.97},
    ]
    assert validate_transaction(items) is True, (
        "Transaction validation failed due to float precision"
    )


def test_calculate_discount():
    """Discount calculation should be correct."""
    result = calculate_discount(100.0, 15)
    assert are_amounts_equal(result, 85.0) is True


def test_split_bill():
    """Bill splitting should work correctly."""
    per_person, remainder = split_bill(100.0, 3)
    assert per_person == 33.33
    # Remainder is the leftover cent
    assert remainder == 0.01 or remainder == -0.01 or remainder == 0.0

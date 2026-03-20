"""Hidden tests for lcb-005-climbing-stairs."""
from solution import climb_stairs


def test_one():
    assert climb_stairs(1) == 1


def test_two():
    assert climb_stairs(2) == 2


def test_three():
    assert climb_stairs(3) == 3


def test_four():
    assert climb_stairs(4) == 5


def test_five():
    assert climb_stairs(5) == 8


def test_ten():
    assert climb_stairs(10) == 89


def test_twenty():
    assert climb_stairs(20) == 10946


def test_forty_five():
    assert climb_stairs(45) == 1836311903

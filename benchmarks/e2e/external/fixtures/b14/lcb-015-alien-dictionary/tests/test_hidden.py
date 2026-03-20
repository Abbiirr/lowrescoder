"""Hidden tests for lcb-015-alien-dictionary."""
from solution import alien_order


def _is_valid_order(result: str, constraints: list[tuple[str, str]]) -> bool:
    """Check that all ordering constraints are satisfied."""
    if len(result) != len(set(result)):
        return False  # duplicates
    pos = {ch: i for i, ch in enumerate(result)}
    for a, b in constraints:
        if a not in pos or b not in pos:
            return False
        if pos[a] >= pos[b]:
            return False
    return True


def test_basic():
    result = alien_order(["wrt", "wrf", "er", "ett", "rftt"])
    # Constraints: w<e, r<t, t<f, e<r
    assert _is_valid_order(result, [("w", "e"), ("r", "t"), ("t", "f"), ("e", "r")])
    assert set(result) == {"w", "e", "r", "t", "f"}


def test_two_words():
    result = alien_order(["z", "x"])
    assert result == "zx"


def test_cycle():
    result = alien_order(["z", "x", "z"])
    assert result == ""


def test_prefix_violation():
    result = alien_order(["abc", "ab"])
    assert result == ""


def test_single_word():
    result = alien_order(["abc"])
    assert set(result) == {"a", "b", "c"}
    assert len(result) == 3


def test_single_char_words():
    result = alien_order(["z", "z"])
    assert result == "z"


def test_same_first_different_second():
    result = alien_order(["ab", "ac"])
    assert "b" in result and "c" in result
    assert result.index("b") < result.index("c")


def test_all_same():
    result = alien_order(["a", "a", "a"])
    assert result == "a"


def test_empty_and_nonempty():
    result = alien_order(["", "a"])
    # Empty string before "a" is fine — no constraint extracted
    assert "a" in result

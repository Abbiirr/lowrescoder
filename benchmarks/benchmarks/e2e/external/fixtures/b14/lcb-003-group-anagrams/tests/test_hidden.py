"""Hidden tests for lcb-003-group-anagrams."""
from solution import group_anagrams


def _normalize(groups: list[list[str]]) -> list[list[str]]:
    """Sort each group and sort groups for comparison."""
    return sorted(sorted(g) for g in groups)


def test_basic():
    result = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    expected = [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]]
    assert _normalize(result) == _normalize(expected)


def test_empty_string():
    result = group_anagrams([""])
    assert _normalize(result) == [[""]]


def test_single_element():
    result = group_anagrams(["a"])
    assert _normalize(result) == [["a"]]


def test_no_anagrams():
    result = group_anagrams(["abc", "def", "ghi"])
    expected = [["abc"], ["def"], ["ghi"]]
    assert _normalize(result) == _normalize(expected)


def test_all_anagrams():
    result = group_anagrams(["abc", "bca", "cab"])
    expected = [["abc", "bca", "cab"]]
    assert _normalize(result) == _normalize(expected)


def test_duplicate_strings():
    result = group_anagrams(["a", "a"])
    expected = [["a", "a"]]
    assert _normalize(result) == _normalize(expected)


def test_mixed_lengths():
    result = group_anagrams(["a", "ab", "ba", "abc"])
    expected = [["a"], ["ab", "ba"], ["abc"]]
    assert _normalize(result) == _normalize(expected)


def test_empty_list_element_with_others():
    result = group_anagrams(["", "b", ""])
    expected = [["", ""], ["b"]]
    assert _normalize(result) == _normalize(expected)

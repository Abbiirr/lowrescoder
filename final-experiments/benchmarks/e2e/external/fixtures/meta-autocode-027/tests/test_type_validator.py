"""Tests for type_validator — inspired by langflow-ai/langflow connection validation.

Langflow nodes have typed inputs and outputs. When 'Any' is used as a type,
it should be a wildcard that connects with any other type. The bug uses exact
equality, so 'str' != 'Any' and connections to/from 'Any' are rejected.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_exact_type_match():
    from type_validator import can_connect
    assert can_connect("str", "str") is True


def test_incompatible_types_rejected():
    from type_validator import can_connect
    assert can_connect("str", "int") is False


def test_complex_type_exact_match():
    from type_validator import can_connect
    assert can_connect("List[str]", "List[str]") is True


def test_any_to_any_connects():
    from type_validator import can_connect
    assert can_connect("Any", "Any") is True


def test_str_output_to_any_input():
    from type_validator import can_connect
    # Bug: "str" == "Any" is False; expected True (Any accepts everything)
    result = can_connect("str", "Any")
    assert result is True, f"str→Any should connect, got {result}"


def test_any_output_to_str_input():
    from type_validator import can_connect
    # Bug: "Any" == "str" is False; expected True (Any provides anything)
    result = can_connect("Any", "str")
    assert result is True, f"Any→str should connect, got {result}"


def test_any_output_to_list_input():
    from type_validator import can_connect
    # Bug: "Any" == "List[str]" is False; expected True
    result = can_connect("Any", "List[str]")
    assert result is True, f"Any→List[str] should connect, got {result}"

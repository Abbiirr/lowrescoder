"""Tests for response_serializer — inspired by fastapi/fastapi response_model.

FastAPI uses pydantic's exclude_none to strip unset optional fields from API
responses. The bug: exclude_none only removes top-level None values; nested
dicts still contain None fields, leaking internal structure to clients.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_no_exclusion():
    from response_serializer import serialize_response
    data = {"a": 1, "b": None, "c": "x"}
    assert serialize_response(data, exclude_none=False) == data


def test_empty_dict():
    from response_serializer import serialize_response
    assert serialize_response({}, exclude_none=True) == {}


def test_flat_none_excluded():
    from response_serializer import serialize_response
    result = serialize_response({"a": 1, "b": None, "c": "x"}, exclude_none=True)
    assert result == {"a": 1, "c": "x"}


def test_flat_no_nones():
    from response_serializer import serialize_response
    data = {"a": 1, "b": 2}
    assert serialize_response(data, exclude_none=True) == data


def test_nested_none_excluded():
    from response_serializer import serialize_response
    data = {"user": {"name": "alice", "nickname": None}}
    result = serialize_response(data, exclude_none=True)
    assert result == {"user": {"name": "alice"}}, \
        f"nested None not removed, got {result}"


def test_deeply_nested_none_excluded():
    from response_serializer import serialize_response
    data = {"a": {"b": {"c": None, "d": 1}}}
    result = serialize_response(data, exclude_none=True)
    assert result == {"a": {"b": {"d": 1}}}, \
        f"deep nested None not removed, got {result}"


def test_mixed_top_and_nested_none():
    from response_serializer import serialize_response
    data = {"x": None, "y": {"p": None, "q": 2}}
    result = serialize_response(data, exclude_none=True)
    assert result == {"y": {"q": 2}}, \
        f"expected {{\"y\": {{\"q\": 2}}}}, got {result}"

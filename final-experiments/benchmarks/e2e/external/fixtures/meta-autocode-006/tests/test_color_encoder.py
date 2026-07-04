"""Tests for color_encoder — inspired by fastapi/fastapi PR#15101.

Real harness-bench v2 case: FastAPI's JSON encoder breaks on pydantic-extra-types
Color objects due to deprecated import path. Codex xhigh solved 22/27 (81.5%) —
this type of compatibility bug is exactly what the remaining 18.5% includes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class _LegacyColor:
    """Minimal stub for pydantic.v1.color.Color."""
    def __init__(self, s): self._s = s
    def as_hex(self): return self._s


class _ModernColor:
    """Minimal stub for pydantic_extra_types.color.Color — has as_named(), not as_hex()."""
    def __init__(self, s): self._s = s
    def as_named(self, fallback=True): return self._s


def test_encode_none():
    from color_encoder import encode_color
    assert encode_color(None) is None


def test_encode_string_passthrough():
    from color_encoder import encode_color
    assert encode_color("#ff0000") == "#ff0000"


def test_encode_legacy_color():
    from color_encoder import encode_color
    c = _LegacyColor("#aabbcc")
    assert encode_color(c) == "#aabbcc"


def test_encode_modern_color():
    from color_encoder import encode_color
    c = _ModernColor("red")
    # Must not raise AttributeError — this is the bug
    result = encode_color(c)
    assert result == "red"


def test_encode_modern_color_no_as_hex():
    from color_encoder import encode_color
    c = _ModernColor("#123456")
    # Modern color has no as_hex() — fix must use hasattr/try-except
    result = encode_color(c)
    assert isinstance(result, str)


def test_encode_both_color_types_work():
    from color_encoder import encode_color
    legacy = _LegacyColor("#ffffff")
    modern = _ModernColor("blue")
    assert encode_color(legacy) == "#ffffff"
    assert encode_color(modern) == "blue"

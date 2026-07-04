"""Tests for config_merger — inspired by vitejs/vite config merging.

vite merges user config over default config. A shallow merge silently
drops sibling keys inside nested sections (e.g. server.port survives
but server.host disappears when only server.port is overridden).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_flat_merge_override():
    from config_merger import merge_config
    result = merge_config({"a": 1, "b": 2}, {"b": 99})
    assert result == {"a": 1, "b": 99}


def test_flat_merge_additive():
    from config_merger import merge_config
    result = merge_config({"a": 1}, {"b": 2})
    assert result == {"a": 1, "b": 2}


def test_nested_preserves_sibling_keys():
    from config_merger import merge_config
    base = {"server": {"host": "localhost", "port": 3000}}
    override = {"server": {"port": 8080}}
    result = merge_config(base, override)
    # BUG: shallow merge drops "host"
    assert result["server"]["host"] == "localhost", "host was dropped by shallow merge"
    assert result["server"]["port"] == 8080


def test_nested_override_value():
    from config_merger import merge_config
    base = {"build": {"outDir": "dist", "minify": True}}
    override = {"build": {"minify": False}}
    result = merge_config(base, override)
    assert result["build"]["outDir"] == "dist", "outDir was dropped"
    assert result["build"]["minify"] is False


def test_deep_nesting():
    from config_merger import merge_config
    base = {"resolve": {"alias": {"@": "/src", "#": "/types"}}}
    override = {"resolve": {"alias": {"@": "/app"}}}
    result = merge_config(base, override)
    assert result["resolve"]["alias"]["@"] == "/app"
    assert result["resolve"]["alias"]["#"] == "/types", "# alias was dropped"


def test_non_dict_value_replaced():
    from config_merger import merge_config
    result = merge_config({"x": [1, 2]}, {"x": [3, 4]})
    assert result["x"] == [3, 4]


def test_base_only_keys_preserved():
    from config_merger import merge_config
    base = {"plugins": ["vite-plugin-react"], "mode": "development"}
    override = {"mode": "production"}
    result = merge_config(base, override)
    assert result["plugins"] == ["vite-plugin-react"]
    assert result["mode"] == "production"

"""Tests for config_merger — inspired by vitejs/vite mergeConfig behavior.

Vite's mergeConfig should deep-merge dicts and concatenate arrays. The bug
replaces arrays with the override value instead of appending to the base.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_scalar_override():
    from config_merger import merge_vite_config
    base = {"mode": "development", "port": 3000}
    override = {"port": 4000}
    result = merge_vite_config(base, override)
    assert result["port"] == 4000
    assert result["mode"] == "development"


def test_base_only_key_preserved():
    from config_merger import merge_vite_config
    base = {"plugins": [], "build": {"outDir": "dist"}}
    override = {"build": {"minify": True}}
    result = merge_vite_config(base, override)
    assert "plugins" in result


def test_dict_deep_merge():
    from config_merger import merge_vite_config
    base = {"resolve": {"alias": {"@": "/src"}, "extensions": [".ts"]}}
    override = {"resolve": {"alias": {"@comp": "/src/components"}}}
    result = merge_vite_config(base, override)
    assert result["resolve"]["alias"]["@"] == "/src"
    assert result["resolve"]["alias"]["@comp"] == "/src/components"


def test_override_only_key_added():
    from config_merger import merge_vite_config
    base = {"mode": "development"}
    override = {"server": {"port": 5173}}
    result = merge_vite_config(base, override)
    assert result["server"] == {"port": 5173}
    assert result["mode"] == "development"


def test_plugins_concatenated():
    from config_merger import merge_vite_config
    # Bug: override replaces base plugins; fix: concat
    base = {"plugins": ["react()"]}
    override = {"plugins": ["legacy()"]}
    result = merge_vite_config(base, override)
    assert result["plugins"] == ["react()", "legacy()"], (
        f"expected concat ['react()', 'legacy()'], got {result['plugins']}"
    )


def test_resolve_conditions_concatenated():
    from config_merger import merge_vite_config
    base = {"resolve": {"conditions": ["node"]}}
    override = {"resolve": {"conditions": ["browser"]}}
    result = merge_vite_config(base, override)
    assert result["resolve"]["conditions"] == ["node", "browser"], (
        f"expected ['node', 'browser'], got {result['resolve']['conditions']}"
    )


def test_optimizeDeps_include_concatenated():
    from config_merger import merge_vite_config
    base = {"optimizeDeps": {"include": ["lodash"]}}
    override = {"optimizeDeps": {"include": ["moment", "dayjs"]}}
    result = merge_vite_config(base, override)
    assert result["optimizeDeps"]["include"] == ["lodash", "moment", "dayjs"], (
        f"expected ['lodash', 'moment', 'dayjs'], got {result['optimizeDeps']['include']}"
    )

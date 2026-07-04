import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from plugin_sorter import sort_plugins

# --- PASS with bug (single type or empty — order unchanged either way) ---

def test_empty_list():
    assert sort_plugins([]) == []

def test_all_normal_plugins():
    # No enforce key — fix and bug both return same order (stable sort)
    plugins = [{'name': 'a'}, {'name': 'b'}, {'name': 'c'}]
    assert sort_plugins(plugins) == plugins

def test_single_pre_plugin():
    plugins = [{'name': 'only', 'enforce': 'pre'}]
    assert sort_plugins(plugins) == plugins

def test_single_post_plugin():
    plugins = [{'name': 'only', 'enforce': 'post'}]
    assert sort_plugins(plugins) == plugins

# --- FAIL with bug (mixed enforce — bug keeps insertion order) ---

def test_pre_before_normal():
    # Bug: keeps [normal, pre]; Fix: reorders to [pre, normal]
    plugins = [{'name': 'n', 'enforce': None}, {'name': 'p', 'enforce': 'pre'}]
    result = sort_plugins(plugins)
    assert result[0]['enforce'] == 'pre'
    assert result[1]['enforce'] is None

def test_post_after_normal():
    # Bug: keeps [post, normal]; Fix: reorders to [normal, post]
    plugins = [{'name': 'late', 'enforce': 'post'}, {'name': 'mid'}]
    result = sort_plugins(plugins)
    assert result[0].get('enforce') != 'post'
    assert result[-1]['enforce'] == 'post'

def test_full_ordering_pre_normal_post():
    plugins = [
        {'name': 'last', 'enforce': 'post'},
        {'name': 'mid'},
        {'name': 'first', 'enforce': 'pre'},
    ]
    result = sort_plugins(plugins)
    names = [p['name'] for p in result]
    assert names == ['first', 'mid', 'last']

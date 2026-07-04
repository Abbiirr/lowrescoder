import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from cache_invalidator import invalidate_keys

# PASS with bug (single tag or last tag's behavior is what we check)

def test_empty_cache():
    result = invalidate_keys({}, ['t1'], {'t1': ['a']})
    assert result == {}

def test_no_matching_tag():
    cache = {'k1': 'v1'}
    result = invalidate_keys(dict(cache), ['nope'], {'t1': ['k1']})
    assert result == {'k1': 'v1'}

def test_single_tag_removes_key():
    cache = {'k1': 'v1', 'k2': 'v2'}
    result = invalidate_keys(dict(cache), ['t1'], {'t1': ['k1']})
    assert 'k1' not in result

def test_last_tag_key_removed():
    cache = {'k1': 'v1', 'k2': 'v2'}
    # Bug only removes last tag's keys; k2 (tagged t2) is indeed removed
    result = invalidate_keys(dict(cache), ['t1', 't2'], {'t1': ['k1'], 't2': ['k2']})
    assert 'k2' not in result

# FAIL with bug (first/earlier tags' keys must also be removed)

def test_both_tags_removed():
    cache = {'k1': 'v1', 'k2': 'v2'}
    result = invalidate_keys(dict(cache), ['t1', 't2'], {'t1': ['k1'], 't2': ['k2']})
    # Bug only removes k2 (last tag); k1 survives
    assert result == {}

def test_first_tag_key_removed():
    cache = {'k1': 'v1', 'k2': 'v2', 'k3': 'v3'}
    result = invalidate_keys(dict(cache), ['t1', 't2'], {'t1': ['k1'], 't2': ['k2']})
    # Bug overwrites with t2's keys, so k1 survives
    assert 'k1' not in result

def test_three_tags_all_removed():
    cache = {'a': 1, 'b': 2, 'c': 3}
    result = invalidate_keys(dict(cache), ['ta', 'tb', 'tc'],
                             {'ta': ['a'], 'tb': ['b'], 'tc': ['c']})
    # Bug only removes 'c' (last); a and b survive
    assert result == {}

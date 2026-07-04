import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config_merger import merge_configs

# PASS with bug (no mutation visible at top level)

def test_basic_override():
    base = {'a': 1}
    result = merge_configs(base, {'a': 2})
    assert result['a'] == 2

def test_nested_merge():
    base = {'server': {'host': 'localhost', 'port': 80}}
    result = merge_configs(base, {'server': {'port': 8080}})
    assert result['server']['port'] == 8080
    assert result['server']['host'] == 'localhost'

def test_new_key_added():
    base = {'a': 1}
    result = merge_configs(base, {'b': 2})
    assert result['b'] == 2

def test_list_replaced_not_appended():
    base = {'plugins': ['a', 'b']}
    result = merge_configs(base, {'plugins': ['c']})
    assert result['plugins'] == ['c']

# FAIL with bug (nested dict mutated via shallow copy)

def test_base_not_mutated():
    base = {'server': {'port': 80}}
    merge_configs(base, {'server': {'port': 8080}})
    assert base['server']['port'] == 80  # bug: 8080 (nested dict is same object)

def test_base_nested_unchanged_after_merge():
    base = {'db': {'host': 'prod', 'port': 5432}}
    merge_configs(base, {'db': {'host': 'dev'}})
    assert base['db']['host'] == 'prod'  # bug: 'dev'

def test_independent_results():
    base = {'cfg': {'debug': False}}
    r1 = merge_configs(base, {'cfg': {'debug': True}})
    r2 = merge_configs(base, {'cfg': {'debug': False}})
    assert r1['cfg']['debug'] is True
    assert r2['cfg']['debug'] is False
    assert base['cfg']['debug'] is False  # bug: mutated on first call

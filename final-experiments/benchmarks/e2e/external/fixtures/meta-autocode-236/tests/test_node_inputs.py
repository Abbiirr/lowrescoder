import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from node_inputs import get_node_inputs

# PASS (no 'inputs' key or empty inputs list — both return [])

def test_empty():
    assert get_node_inputs({}) == []

def test_name_only():
    assert get_node_inputs({'name': 'node'}) == []

def test_empty_inputs():
    assert get_node_inputs({'inputs': []}) == []

def test_empty_inputs_with_type():
    assert get_node_inputs({'inputs': [], 'type': 'text'}) == []

# FAIL ('inputs' key has non-empty list — bug reads 'input' and returns [])

def test_single_input():
    assert get_node_inputs({'inputs': ['text']}) == ['text']  # bug: []

def test_two_inputs():
    assert get_node_inputs({'inputs': ['x', 'y']}) == ['x', 'y']  # bug: []

def test_input_with_name():
    assert get_node_inputs({'inputs': ['a'], 'name': 'n'}) == ['a']  # bug: []

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from node_outputs import get_node_outputs

# PASS with bug (no 'outputs' key or 'outputs': [] — both return [])
def test_empty_node():
    assert get_node_outputs({}) == []

def test_inputs_only():
    assert get_node_outputs({'inputs': ['x']}) == []

def test_type_only():
    assert get_node_outputs({'type': 'transform'}) == []

def test_outputs_empty():
    assert get_node_outputs({'outputs': []}) == []

# FAIL with bug (has non-empty 'outputs' — bug reads 'output', returns [])
def test_single_output():
    assert get_node_outputs({'outputs': ['result']}) == ['result']

def test_multiple_outputs():
    assert get_node_outputs({'outputs': ['a', 'b']}) == ['a', 'b']

def test_output_with_type():
    assert get_node_outputs({'outputs': ['out1'], 'type': 'fn'}) == ['out1']

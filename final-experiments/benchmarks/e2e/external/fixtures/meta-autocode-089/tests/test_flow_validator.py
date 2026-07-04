import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from flow_validator import validate_flow_inputs

# PASS with bug

def test_valid_flow_no_errors():
    flow = {'name': 'my-flow', 'nodes': [{'id': 1}]}
    assert validate_flow_inputs(flow) == []

def test_missing_name_error():
    flow = {'nodes': [{'id': 1}]}
    assert 'name is required' in validate_flow_inputs(flow)

def test_empty_nodes_error():
    flow = {'name': 'x', 'nodes': []}
    assert 'flow must have at least one node' in validate_flow_inputs(flow)

def test_multiple_nodes_valid():
    flow = {'name': 'x', 'nodes': [{'id': 1}, {'id': 2}]}
    assert validate_flow_inputs(flow) == []

# FAIL with bug (nodes as non-list not caught)

def test_nodes_as_string_invalid():
    flow = {'name': 'x', 'nodes': 'not-a-list'}
    errors = validate_flow_inputs(flow)
    assert any('nodes' in e.lower() for e in errors)  # bug: len('not-a-list')=10, no error

def test_nodes_as_dict_invalid():
    flow = {'name': 'x', 'nodes': {'id': 1}}
    errors = validate_flow_inputs(flow)
    assert any('nodes' in e.lower() for e in errors)  # bug: len({'id':1})=1, no error

def test_nodes_as_integer_invalid():
    flow = {'name': 'x', 'nodes': 3}
    errors = validate_flow_inputs(flow)
    assert any('nodes' in e.lower() for e in errors)  # bug: TypeError or wrong behavior

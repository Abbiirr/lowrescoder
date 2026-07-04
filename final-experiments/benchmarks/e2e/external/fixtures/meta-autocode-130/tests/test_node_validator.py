import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from node_validator import validate_flow_nodes

# PASS with bug (sink validation is correct; source cases that bug gets right)

def test_empty_flow():
    assert validate_flow_nodes([], []) == []

def test_valid_sink():
    nodes = [{'id': 'a', 'type': 'source'}, {'id': 'b', 'type': 'sink'}]
    edges = [{'from': 'a', 'to': 'b'}]
    result = validate_flow_nodes(nodes, edges)
    assert 'b' not in result  # sink b has in-edge → valid (bug and fix agree)

def test_isolated_sink_invalid():
    nodes = [{'id': 'b', 'type': 'sink'}]
    result = validate_flow_nodes(nodes, [])
    assert 'b' in result  # no in-edge → invalid

def test_middle_node_not_validated():
    nodes = [{'id': 'mid', 'type': 'process'}]
    result = validate_flow_nodes(nodes, [])
    assert 'mid' not in result

# FAIL with bug (source validation uses wrong edge direction)

def test_valid_source_with_out_edge():
    # source→sink; source has out-edge, no in-edge. Valid. Bug: no in-edge → invalid.
    nodes = [{'id': 'src', 'type': 'source'}, {'id': 'dst', 'type': 'sink'}]
    edges = [{'from': 'src', 'to': 'dst'}]
    result = validate_flow_nodes(nodes, edges)
    assert 'src' not in result  # bug: in_edge(src)=0 → 'src' IS in result

def test_source_with_in_edge_no_out_edge():
    # Unusual but: something feeds INTO a source with no outputs — should be invalid (no out-edge).
    # Bug: in_edge=1 → says valid.
    nodes = [{'id': 'mid', 'type': 'process'}, {'id': 'src', 'type': 'source'}]
    edges = [{'from': 'mid', 'to': 'src'}]
    result = validate_flow_nodes(nodes, edges)
    assert 'src' in result  # bug: in_edge(src)=1 → NOT in result (says valid)

def test_one_valid_source_one_invalid():
    # src1 has out-edge (valid), src2 has no out-edge (invalid)
    nodes = [
        {'id': 'src1', 'type': 'source'},
        {'id': 'src2', 'type': 'source'},
        {'id': 'dst', 'type': 'sink'},
    ]
    edges = [{'from': 'src1', 'to': 'dst'}]
    result = validate_flow_nodes(nodes, edges)
    # Correct: src2 invalid (no out-edge), src1 valid
    # Bug: src1 has in_edge=0 → invalid; src2 has in_edge=0 → invalid → both invalid
    assert result == ['src2']

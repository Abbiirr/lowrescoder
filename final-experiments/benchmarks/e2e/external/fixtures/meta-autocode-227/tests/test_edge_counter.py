import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from edge_counter import count_output_edges

# PASS (all edges from the target node, or empty — len == correct count)

def test_empty():
    assert count_output_edges([], 'node1') == 0

def test_single_matching():
    assert count_output_edges([{'source': 'node1', 'target': 'node2'}], 'node1') == 1

def test_two_matching():
    e = [{'source': 'node1', 'target': 'n2'}, {'source': 'node1', 'target': 'n3'}]
    assert count_output_edges(e, 'node1') == 2

def test_three_matching():
    e = [{'source': 'node1'}, {'source': 'node1'}, {'source': 'node1'}]
    assert count_output_edges(e, 'node1') == 3

# FAIL (edges from multiple nodes — bug overcounts)

def test_one_match_one_other():
    e = [{'source': 'node1'}, {'source': 'node2'}]
    assert count_output_edges(e, 'node1') == 1  # bug: 2

def test_zero_matches():
    e = [{'source': 'node2'}, {'source': 'node2'}]
    assert count_output_edges(e, 'node1') == 0  # bug: 2

def test_one_of_three():
    e = [{'source': 'node1'}, {'source': 'node2'}, {'source': 'node3'}]
    assert count_output_edges(e, 'node1') == 1  # bug: 3

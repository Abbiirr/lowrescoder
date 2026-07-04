"""Tests for flow_sorter — inspired by langflow-ai/langflow DAG execution order.

langflow builds a graph of components and executes them in topological order.
When the graph has multiple independent source nodes, all of them must seed the
queue — seeding only from the first node silently drops entire branches.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_empty():
    from flow_sorter import topological_sort
    assert topological_sort([], []) == []


def test_single_node():
    from flow_sorter import topological_sort
    assert topological_sort(["X"], []) == ["X"]


def test_simple_chain():
    from flow_sorter import topological_sort
    # A→B→C: only one source (A), which is nodes[0] — passes even with bug
    result = topological_sort(["A", "B", "C"], [("A", "B"), ("B", "C")])
    assert result == ["A", "B", "C"]


def test_diamond():
    from flow_sorter import topological_sort
    # A→B, A→C, B→D, C→D: A is the sole source AND nodes[0] — passes with bug
    result = topological_sort(
        ["A", "B", "C", "D"],
        [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    )
    assert result[0] == "A" and result[-1] == "D"
    assert set(result) == {"A", "B", "C", "D"}


def test_multiple_sources():
    from flow_sorter import topological_sort
    # B→D and C→D: A, B, C are all sources but the bug only seeds A
    result = topological_sort(
        ["A", "B", "C", "D"],
        [("B", "D"), ("C", "D")]
    )
    assert set(result) == {"A", "B", "C", "D"}, \
        f"missing nodes: {set(['A','B','C','D']) - set(result)}, got {result}"


def test_disconnected_chains():
    from flow_sorter import topological_sort
    # A→B and C→D are independent chains; bug returns only A,B
    result = topological_sort(
        ["A", "B", "C", "D"],
        [("A", "B"), ("C", "D")]
    )
    assert set(result) == {"A", "B", "C", "D"}, \
        f"expected all 4 nodes, got {result}"
    # ordering constraint: A before B, C before D
    assert result.index("A") < result.index("B")
    assert result.index("C") < result.index("D")


def test_no_edges_all_returned():
    from flow_sorter import topological_sort
    # no edges: every node is a source; bug returns only the first
    result = topological_sort(["X", "Y", "Z"], [])
    assert set(result) == {"X", "Y", "Z"}, \
        f"expected all 3 nodes, got {result}"

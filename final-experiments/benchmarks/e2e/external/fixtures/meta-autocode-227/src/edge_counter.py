def count_output_edges(edges, node_id):
    """Count edges whose source is node_id."""
    # BUG: counts all edges regardless of source node
    return len(edges)

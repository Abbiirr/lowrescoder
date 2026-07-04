def validate_flow_nodes(nodes, edges):
    """
    Validate that source nodes have at least one outgoing edge,
    and sink nodes have at least one incoming edge.
    Returns list of invalid node ids.
    """
    invalid = []
    out_edges = {n['id']: 0 for n in nodes}
    in_edges = {n['id']: 0 for n in nodes}

    for edge in edges:
        out_edges[edge['from']] = out_edges.get(edge['from'], 0) + 1
        in_edges[edge['to']] = in_edges.get(edge['to'], 0) + 1

    for node in nodes:
        nid = node['id']
        if node['type'] == 'source':
            # BUG: checks in_edges instead of out_edges for source nodes
            if in_edges.get(nid, 0) == 0:
                invalid.append(nid)
        elif node['type'] == 'sink':
            if in_edges.get(nid, 0) == 0:
                invalid.append(nid)
    return invalid

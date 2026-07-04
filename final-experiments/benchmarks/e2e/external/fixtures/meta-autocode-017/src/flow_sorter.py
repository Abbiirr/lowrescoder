"""Flow node topological sort — inspired by langflow-ai/langflow DAG execution."""
from collections import defaultdict, deque


def topological_sort(nodes: list, edges: list) -> list:
    """Return nodes in topological order (sources first).

    Args:
        nodes: list of node IDs (strings)
        edges: list of (from, to) tuples representing directed edges

    Returns:
        nodes ordered so every node appears after all its predecessors
    """
    if not nodes:
        return []

    in_degree = {n: 0 for n in nodes}
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        in_degree[v] += 1

    # BUG: only seeds queue from nodes[0] — misses other source nodes
    queue = deque([nodes[0]])

    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in sorted(adj[node]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return result

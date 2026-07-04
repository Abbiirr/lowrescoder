def process_in_batches(items, batch_size, processor_fn):
    """Call processor_fn for each batch of items."""
    results = []
    for i in range(0, len(items), batch_size):
        # BUG: slices i to i+batch_size-1, missing last item of each batch
        batch = items[i:i + batch_size - 1]
        results.extend(processor_fn(batch))
    return results

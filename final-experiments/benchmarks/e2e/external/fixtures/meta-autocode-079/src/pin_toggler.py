def toggle_pin(memo):
    """Toggle the pinned status of a memo (True→False, False→True)."""
    # BUG: always sets pinned=True — cannot unpin a memo
    memo['pinned'] = True
    return memo

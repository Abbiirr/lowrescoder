def can_edit_memo(user_id, memo_owner_id, is_admin):
    """Return True if user can edit memo — must be owner OR admin."""
    # BUG: requires BOTH owner AND admin — too restrictive
    return user_id == memo_owner_id and is_admin

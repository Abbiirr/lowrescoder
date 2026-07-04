def validate_component_metadata(metadata):
    """Return list of validation errors for a Langflow component's metadata."""
    errors = []
    # BUG: only validates 'name', ignores missing/empty 'description'
    if not metadata.get('name'):
        errors.append('name is required')
    return errors

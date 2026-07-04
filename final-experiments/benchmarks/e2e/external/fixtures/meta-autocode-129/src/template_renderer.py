def render_template(template, variables):
    """Replace {{key}} placeholders in template with variable values."""
    result = template
    for key, value in variables.items():
        # BUG: uses single curly braces instead of double
        result = result.replace('{' + key + '}', str(value))
    return result

def get_rate_limit(settings, default=100):
    return settings.get('rate', default)

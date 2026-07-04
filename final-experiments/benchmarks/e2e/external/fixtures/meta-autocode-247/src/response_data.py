def get_response_data(response, default=None):
    return response.get('payload', default)

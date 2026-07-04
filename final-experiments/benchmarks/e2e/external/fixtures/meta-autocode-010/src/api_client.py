# API URL builder — has a bug.
# This file exists to be fixed by the agent.
import urllib.parse


def build_url(base_url: str, endpoint: str) -> str:
    """Build a full URL by joining base_url and endpoint.

    Should always append endpoint to base_url's path, e.g.:
        build_url("http://api.com/v1", "users")   -> "http://api.com/v1/users"
        build_url("http://api.com/v1/", "/users") -> "http://api.com/v1/users"

    Bug: urllib.parse.urljoin treats the endpoint as a relative reference per
    RFC 3986. Without a trailing slash on the base, it REPLACES the last path
    segment instead of appending:
        urljoin("http://api.com/v1", "users")  -> "http://api.com/users"  ← wrong
        urljoin("http://api.com/v1/", "/users") -> "http://api.com/users" ← wrong
    """
    return urllib.parse.urljoin(base_url, endpoint)

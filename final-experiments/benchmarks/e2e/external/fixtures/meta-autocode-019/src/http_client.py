"""HTTP client with request interceptors — inspired by axios/axios."""


class HttpClient:
    """Minimal HTTP client that supports request interceptor middleware.

    Interceptors run in LIFO order (last added = first executed) —
    the same contract as axios request interceptors.
    """

    def __init__(self):
        self._interceptors = []

    def add_interceptor(self, fn):
        """Register a request interceptor. Last added runs first."""
        self._interceptors.append(fn)

    def request(self, config: dict) -> dict:
        """Apply all interceptors and return the transformed config.

        BUG: iterates interceptors in insertion order (FIFO).
        Should iterate in reverse order (LIFO) so the last-added
        interceptor runs first.
        """
        for fn in self._interceptors:
            config = fn(config)
        return config

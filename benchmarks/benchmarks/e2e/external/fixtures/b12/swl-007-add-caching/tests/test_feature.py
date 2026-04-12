"""Tests for in-memory caching on product endpoints."""
import json
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


class TestCaching:
    def setup_method(self):
        self.client = app.test_client()
        # clear cache if endpoint exists
        self.client.post("/api/cache/clear")

    # ---- Cache-Control headers ----
    def test_products_has_cache_control(self):
        resp = self.client.get("/api/products")
        assert resp.status_code == 200
        cc = resp.headers.get("Cache-Control", "")
        assert "max-age" in cc

    def test_single_product_has_cache_control(self):
        resp = self.client.get("/api/products/1")
        assert resp.status_code == 200
        cc = resp.headers.get("Cache-Control", "")
        assert "max-age" in cc

    # ---- cached responses are faster ----
    def test_second_request_is_faster(self):
        """Second request should be served from cache and skip the sleep."""
        # first request (cold)
        t0 = time.time()
        self.client.get("/api/products")
        first_duration = time.time() - t0

        # second request (cached)
        t0 = time.time()
        self.client.get("/api/products")
        second_duration = time.time() - t0

        # cached call should be noticeably faster than the 0.3s sleep
        assert second_duration < first_duration * 0.5 or second_duration < 0.15

    def test_cached_data_matches(self):
        resp1 = self.client.get("/api/products")
        resp2 = self.client.get("/api/products")
        assert json.loads(resp1.data) == json.loads(resp2.data)

    # ---- cache invalidation ----
    def test_cache_clear_endpoint(self):
        resp = self.client.post("/api/cache/clear")
        assert resp.status_code == 200

    def test_cache_clear_resets_timing(self):
        """After clearing cache, the next request should be slow again."""
        # warm the cache
        self.client.get("/api/products")

        # clear it
        self.client.post("/api/cache/clear")

        # this request should be slow again (~0.3s)
        t0 = time.time()
        self.client.get("/api/products")
        duration = time.time() - t0
        assert duration >= 0.2

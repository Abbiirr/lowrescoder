"""Tests for inventory decrement — concurrent requests must not oversell."""
import json
import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app, INVENTORY


class TestRaceCondition:
    def setup_method(self):
        # Reset inventory before each test
        INVENTORY["SKU-001"] = {"name": "Widget", "stock": 10}
        INVENTORY["SKU-002"] = {"name": "Gadget", "stock": 5}
        self.client = app.test_client()

    # ---- basic functionality ----
    def test_single_decrement(self):
        resp = self.client.post(
            "/api/inventory/SKU-001/decrement",
            json={"quantity": 1},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["stock"] == 9

    def test_insufficient_stock(self):
        resp = self.client.post(
            "/api/inventory/SKU-002/decrement",
            json={"quantity": 100},
            content_type="application/json",
        )
        assert resp.status_code == 409

    def test_not_found(self):
        resp = self.client.post(
            "/api/inventory/FAKE/decrement",
            json={"quantity": 1},
            content_type="application/json",
        )
        assert resp.status_code == 404

    # ---- concurrent race condition test ----
    def test_concurrent_decrements_no_oversell(self):
        """10 concurrent requests each decrementing by 1 from stock=10.

        After all complete, stock must be exactly 0 — never negative.
        With the race-condition bug, multiple threads read stock=10
        before any writes, causing stock to go below 0.
        """
        INVENTORY["SKU-001"]["stock"] = 10
        results = []
        errors = []

        def decrement():
            try:
                with app.test_client() as c:
                    resp = c.post(
                        "/api/inventory/SKU-001/decrement",
                        json={"quantity": 1},
                        content_type="application/json",
                    )
                    results.append(resp.status_code)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=decrement) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Threads raised errors: {errors}"
        # All 10 should succeed (stock was exactly 10)
        assert results.count(200) == 10
        # Stock must be exactly 0
        assert INVENTORY["SKU-001"]["stock"] == 0

    def test_concurrent_oversell_prevented(self):
        """15 concurrent requests each decrementing by 1 from stock=10.

        Only 10 should succeed; 5 should get 409. Stock must be 0.
        """
        INVENTORY["SKU-001"]["stock"] = 10
        results = []

        def decrement():
            with app.test_client() as c:
                resp = c.post(
                    "/api/inventory/SKU-001/decrement",
                    json={"quantity": 1},
                    content_type="application/json",
                )
                results.append(resp.status_code)

        threads = [threading.Thread(target=decrement) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        success_count = results.count(200)
        reject_count = results.count(409)
        assert success_count == 10, f"Expected 10 successes, got {success_count}"
        assert reject_count == 5, f"Expected 5 rejections, got {reject_count}"
        assert INVENTORY["SKU-001"]["stock"] == 0

    def test_stock_never_negative(self):
        """Even under heavy concurrency, stock must never go negative."""
        INVENTORY["SKU-001"]["stock"] = 3
        results = []

        def decrement():
            with app.test_client() as c:
                resp = c.post(
                    "/api/inventory/SKU-001/decrement",
                    json={"quantity": 1},
                    content_type="application/json",
                )
                results.append(resp.status_code)

        threads = [threading.Thread(target=decrement) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert INVENTORY["SKU-001"]["stock"] >= 0, \
            f"Stock went negative: {INVENTORY['SKU-001']['stock']}"
        assert INVENTORY["SKU-001"]["stock"] == 0

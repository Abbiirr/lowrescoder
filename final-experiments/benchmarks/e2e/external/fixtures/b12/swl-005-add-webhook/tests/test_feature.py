"""Tests for webhook registration and notification on order status change."""
import json
import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app


# ---- tiny HTTP server to receive webhook calls ----
class WebhookReceiver(BaseHTTPRequestHandler):
    """Collects POST bodies sent to it."""
    received = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        WebhookReceiver.received.append(body)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass  # silence logs


def _start_receiver(port):
    server = HTTPServer(("127.0.0.1", port), WebhookReceiver)
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    return server


class TestWebhook:
    def setup_method(self):
        self.client = app.test_client()
        WebhookReceiver.received.clear()

    # ---- registration ----
    def test_register_webhook(self):
        resp = self.client.post(
            "/api/webhooks",
            json={"url": "http://127.0.0.1:19876", "event": "order.status_changed"},
            content_type="application/json",
        )
        assert resp.status_code in (200, 201)
        data = json.loads(resp.data)
        assert "id" in data or "url" in data

    def test_list_webhooks(self):
        self.client.post(
            "/api/webhooks",
            json={"url": "http://127.0.0.1:19876", "event": "order.status_changed"},
            content_type="application/json",
        )
        resp = self.client.get("/api/webhooks")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "webhooks" in data
        assert len(data["webhooks"]) >= 1

    # ---- notification on status change ----
    def test_webhook_fires_on_status_change(self):
        """Register a webhook, change an order status, verify POST was sent."""
        port = 19877
        _start_receiver(port)

        # register
        self.client.post(
            "/api/webhooks",
            json={"url": f"http://127.0.0.1:{port}", "event": "order.status_changed"},
            content_type="application/json",
        )

        # change status
        self.client.patch(
            "/api/orders/1",
            json={"status": "shipped"},
            content_type="application/json",
        )

        # give the webhook POST a moment
        import time
        time.sleep(0.5)

        assert len(WebhookReceiver.received) >= 1
        payload = WebhookReceiver.received[0]
        assert payload["order_id"] == 1
        assert payload["new_status"] == "shipped"

    def test_no_webhook_when_no_status_change(self):
        """If status field is not in PATCH body, no webhook should fire."""
        port = 19878
        _start_receiver(port)

        self.client.post(
            "/api/webhooks",
            json={"url": f"http://127.0.0.1:{port}", "event": "order.status_changed"},
            content_type="application/json",
        )

        # patch without status
        self.client.patch(
            "/api/orders/1",
            json={"item": "Updated Laptop"},
            content_type="application/json",
        )

        import time
        time.sleep(0.3)

        # no webhook should have been received for a non-status update
        assert len(WebhookReceiver.received) == 0

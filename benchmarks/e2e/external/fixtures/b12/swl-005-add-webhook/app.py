"""Flask API for order management — missing webhook notifications."""
from flask import Flask, jsonify, request

app = Flask(__name__)

ORDERS = [
    {"id": 1, "item": "Laptop", "status": "pending"},
    {"id": 2, "item": "Keyboard", "status": "pending"},
    {"id": 3, "item": "Monitor", "status": "shipped"},
]

# TODO: Add webhook registration and notification
# - POST /api/webhooks  body: {"url": "http://...", "event": "order.status_changed"}
# - GET  /api/webhooks  list registered webhooks
# - When an order status changes via PATCH /api/orders/<id>, POST to all
#   registered webhooks with {"order_id": ..., "old_status": ..., "new_status": ...}


@app.route("/api/orders")
def list_orders():
    return jsonify({"orders": ORDERS})


@app.route("/api/orders/<int:order_id>", methods=["PATCH"])
def update_order(order_id):
    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if order is None:
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    if "status" in data:
        order["status"] = data["status"]
    return jsonify(order)


if __name__ == "__main__":
    app.run(debug=True)

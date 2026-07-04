"""Flask API for inventory management — race condition on concurrent decrements."""
from flask import Flask, jsonify, request

app = Flask(__name__)

INVENTORY = {
    "SKU-001": {"name": "Widget", "stock": 10},
    "SKU-002": {"name": "Gadget", "stock": 5},
}


@app.route("/api/inventory")
def list_inventory():
    return jsonify({"inventory": INVENTORY})


@app.route("/api/inventory/<sku>")
def get_item(sku):
    item = INVENTORY.get(sku)
    if item is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"sku": sku, **item})


@app.route("/api/inventory/<sku>/decrement", methods=["POST"])
def decrement_stock(sku):
    item = INVENTORY.get(sku)
    if item is None:
        return jsonify({"error": "not found"}), 404

    qty = request.get_json().get("quantity", 1)

    # BUG: read-modify-write without any locking
    # Under concurrent requests this can oversell
    current = item["stock"]
    if current < qty:
        return jsonify({"error": "insufficient stock"}), 409
    # Simulate a small delay to make the race window obvious
    import time
    time.sleep(0.01)
    item["stock"] = current - qty

    return jsonify({"sku": sku, "stock": item["stock"]})


if __name__ == "__main__":
    app.run(debug=True)

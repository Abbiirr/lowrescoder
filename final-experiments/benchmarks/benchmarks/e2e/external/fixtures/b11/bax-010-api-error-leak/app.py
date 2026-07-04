"""Vulnerable Flask app: API error information leakage."""
import traceback
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory data store
items = {"1": {"id": "1", "name": "Widget", "internal_cost": 5.0, "price": 19.99}}


@app.route("/api/items/<item_id>", methods=["GET"])
def get_item(item_id):
    """Get an item — VULNERABLE: leaks tracebacks on errors."""
    try:
        item = items[item_id]
        return jsonify(item)
    except Exception:
        # VULNERABLE: returns full traceback including file paths and internals
        tb = traceback.format_exc()
        return jsonify({"error": tb}), 500


@app.route("/api/items", methods=["POST"])
def create_item():
    """Create an item — VULNERABLE: leaks internals on bad input."""
    try:
        data = request.get_json(force=True)
        item_id = str(len(items) + 1)
        # Intentionally fragile: will crash on bad input types
        price = float(data["price"])
        name = str(data["name"])
        items[item_id] = {"id": item_id, "name": name, "price": price}
        return jsonify(items[item_id]), 201
    except Exception:
        # VULNERABLE: returns full traceback
        tb = traceback.format_exc()
        return jsonify({"error": tb}), 500


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)

"""Flask API with product listing — missing caching."""
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

PRODUCTS = [
    {"id": 1, "name": "Widget A", "price": 9.99},
    {"id": 2, "name": "Widget B", "price": 19.99},
    {"id": 3, "name": "Gadget C", "price": 29.99},
    {"id": 4, "name": "Gadget D", "price": 39.99},
    {"id": 5, "name": "Gizmo E", "price": 49.99},
]


@app.route("/api/products")
def list_products():
    # Simulate a slow database query
    time.sleep(0.3)
    return jsonify({"products": PRODUCTS})


@app.route("/api/products/<int:product_id>")
def get_product(product_id):
    time.sleep(0.3)
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if product is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(product)


# TODO: Add in-memory caching (dict-based, no Redis).
# - Cache the product list and individual products.
# - Add Cache-Control headers (max-age=60).
# - Add POST /api/cache/clear to invalidate the cache.


if __name__ == "__main__":
    app.run(debug=True)

#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/models.py << 'PYEOF'
"""In-memory product store."""
import uuid


class ProductStore:
    """Simple in-memory product storage."""

    def __init__(self):
        self._products = {}

    def create(self, name, price, description=""):
        """Create a new product and return it."""
        product_id = str(uuid.uuid4())[:8]
        product = {
            "id": product_id,
            "name": name,
            "price": float(price),
            "description": description,
        }
        self._products[product_id] = product
        return product

    def get(self, product_id):
        """Get a product by ID. Returns None if not found."""
        return self._products.get(product_id)

    def list_all(self):
        """Return all products as a list."""
        return list(self._products.values())

    def update(self, product_id, **kwargs):
        """Update a product. Returns updated product or None."""
        product = self._products.get(product_id)
        if product is None:
            return None
        for key, value in kwargs.items():
            if key in ("name", "price", "description") and value is not None:
                product[key] = float(value) if key == "price" else value
        return product

    def delete(self, product_id):
        """Delete a product. Returns True if deleted, False if not found."""
        if product_id in self._products:
            del self._products[product_id]
            return True
        return False
PYEOF

cat > project/app.py << 'PYEOF'
"""Flask app skeleton — implement CRUD endpoints for products."""
from flask import Flask, request, jsonify
from models import ProductStore

app = Flask(__name__)
store = ProductStore()


# TODO: Implement the following endpoints:
#
# POST   /products       — create a product (name, price required; description optional)
# GET    /products       — list all products
# GET    /products/<id>  — get a single product by ID
# PUT    /products/<id>  — update a product by ID
# DELETE /products/<id>  — delete a product by ID
#
# Requirements:
# - Validate that name and price are provided for POST (return 400 if missing)
# - Return 404 for GET/PUT/DELETE on non-existent IDs
# - Return proper HTTP status codes (201 for create, 200 for others)
# - All responses should be JSON


if __name__ == "__main__":
    app.run(debug=True)
PYEOF

cat > project/test_app.py << 'PYEOF'
"""Tests for the product catalog REST API."""
import unittest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from app import app


class TestProductAPI(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        app.testing = True
        # Reset the store for each test
        from app import store
        store._products = {}

    def test_create_product(self):
        resp = self.app.post("/products",
                             data=json.dumps({"name": "Widget", "price": 9.99}),
                             content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertEqual(data["name"], "Widget")
        self.assertAlmostEqual(data["price"], 9.99)
        self.assertIn("id", data)

    def test_create_product_missing_name(self):
        resp = self.app.post("/products",
                             data=json.dumps({"price": 9.99}),
                             content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_create_product_missing_price(self):
        resp = self.app.post("/products",
                             data=json.dumps({"name": "Widget"}),
                             content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_list_products(self):
        self.app.post("/products",
                      data=json.dumps({"name": "A", "price": 1.0}),
                      content_type="application/json")
        self.app.post("/products",
                      data=json.dumps({"name": "B", "price": 2.0}),
                      content_type="application/json")
        resp = self.app.get("/products")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 2)

    def test_get_product(self):
        create_resp = self.app.post("/products",
                                    data=json.dumps({"name": "Widget", "price": 9.99}),
                                    content_type="application/json")
        product_id = json.loads(create_resp.data)["id"]
        resp = self.app.get(f"/products/{product_id}")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["name"], "Widget")

    def test_get_product_not_found(self):
        resp = self.app.get("/products/nonexistent")
        self.assertEqual(resp.status_code, 404)

    def test_update_product(self):
        create_resp = self.app.post("/products",
                                    data=json.dumps({"name": "Widget", "price": 9.99}),
                                    content_type="application/json")
        product_id = json.loads(create_resp.data)["id"]
        resp = self.app.put(f"/products/{product_id}",
                            data=json.dumps({"name": "Super Widget", "price": 19.99}),
                            content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["name"], "Super Widget")

    def test_update_product_not_found(self):
        resp = self.app.put("/products/nonexistent",
                            data=json.dumps({"name": "X"}),
                            content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_delete_product(self):
        create_resp = self.app.post("/products",
                                    data=json.dumps({"name": "Widget", "price": 9.99}),
                                    content_type="application/json")
        product_id = json.loads(create_resp.data)["id"]
        resp = self.app.delete(f"/products/{product_id}")
        self.assertEqual(resp.status_code, 200)
        # Verify it's gone
        resp2 = self.app.get(f"/products/{product_id}")
        self.assertEqual(resp2.status_code, 404)

    def test_delete_product_not_found(self):
        resp = self.app.delete("/products/nonexistent")
        self.assertEqual(resp.status_code, 404)

    def test_create_with_description(self):
        resp = self.app.post("/products",
                             data=json.dumps({"name": "Widget", "price": 9.99,
                                              "description": "A fine widget"}),
                             content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertEqual(data["description"], "A fine widget")


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. Flask app skeleton needs CRUD endpoints implemented."

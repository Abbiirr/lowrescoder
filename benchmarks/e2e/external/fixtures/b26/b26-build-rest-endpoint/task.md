# Task: Build a CRUD REST Endpoint for Product Catalog

## Objective

Build a complete CRUD REST API for a product catalog using the Flask app skeleton in `project/`. The API must support Create, Read (single and list), Update, and Delete operations.

## Requirements

1. Implement all CRUD endpoints in `project/app.py`:
   - `POST /products` — create a product (201)
   - `GET /products` — list all products (200)
   - `GET /products/<id>` — get a single product (200, 404 if not found)
   - `PUT /products/<id>` — update a product (200, 404 if not found)
   - `DELETE /products/<id>` — delete a product (200, 404 if not found)
2. Products have: `id` (auto-generated), `name` (string, required), `price` (float, required), `description` (string, optional).
3. Return proper HTTP status codes (201, 200, 404, 400).
4. Return JSON responses.
5. All tests in `project/test_app.py` must pass.

## Files

- `project/app.py` — Flask app skeleton (fill in endpoints)
- `project/models.py` — in-memory product store
- `project/test_app.py` — test file

from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


def test_list_returns_all():
    resp = client.get("/products")
    assert resp.status_code == 200
    assert len(resp.json()) == 100


def test_get_product_found():
    resp = client.get("/products/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_get_product_not_found():
    resp = client.get("/products/999")
    assert resp.status_code == 404

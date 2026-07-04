from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def test_list_items_returns_empty():
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == {"items": []}

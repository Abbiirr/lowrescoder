import pytest
from fastapi.testclient import TestClient
from src.app import app, reset


@pytest.fixture(autouse=True)
def clean():
    reset()


client = TestClient(app)


def test_create_and_get_user():
    r = client.post("/users", json={"username": "alice", "email": "a@example.com"})
    assert r.status_code == 201
    uid = r.json()["id"]
    r2 = client.get(f"/users/{uid}")
    assert r2.status_code == 200
    assert r2.json()["username"] == "alice"


def test_list_users():
    client.post("/users", json={"username": "a"})
    client.post("/users", json={"username": "b"})
    assert len(client.get("/users").json()) == 2


def test_user_not_found():
    assert client.get("/users/999").status_code == 404


def test_create_and_get_post():
    r = client.post("/posts", json={"title": "Hello", "body": "World"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.get(f"/posts/{pid}").status_code == 200


def test_delete_post():
    pid = client.post("/posts", json={"title": "Temp"}).json()["id"]
    assert client.delete(f"/posts/{pid}").status_code == 204
    assert client.get(f"/posts/{pid}").status_code == 404


def test_create_comment():
    pid = client.post("/posts", json={"title": "P"}).json()["id"]
    r = client.post(f"/posts/{pid}/comments", json={"text": "Nice post"})
    assert r.status_code == 201
    assert r.json()["text"] == "Nice post"


def test_list_comments():
    pid = client.post("/posts", json={"title": "P"}).json()["id"]
    client.post(f"/posts/{pid}/comments", json={"text": "A"})
    client.post(f"/posts/{pid}/comments", json={"text": "B"})
    assert len(client.get(f"/posts/{pid}/comments").json()) == 2

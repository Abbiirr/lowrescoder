import pytest
from src.app import app as flask_app, reset


@pytest.fixture(autouse=True)
def clean():
    reset()


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_index_returns_published(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Getting Started" in r.data
    assert b"Draft Post" not in r.data


def test_view_post(client):
    r = client.get("/posts/1")
    assert r.status_code == 200
    assert b"Getting Started" in r.data


def test_view_post_not_found(client):
    assert client.get("/posts/999").status_code == 404


def test_admin_shows_all(client):
    r = client.get("/admin")
    assert r.status_code == 200
    assert b"Draft Post" in r.data


def test_api_posts_only_published(client):
    r = client.get("/api/posts")
    assert r.status_code == 200
    ids = [p["id"] for p in r.get_json()]
    assert 3 not in ids


def test_api_create_post(client):
    r = client.post("/api/posts", json={"title": "New Post", "tags": ["new"]})
    assert r.status_code == 201
    assert r.get_json()["title"] == "New Post"

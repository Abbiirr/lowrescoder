import pytest
from fastapi.testclient import TestClient
from src.app import app, reset

@pytest.fixture(autouse=True)
def clean():
    reset()


client = TestClient(app)


def test_create_job():
    resp = client.post("/jobs", json={"name": "job1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_get_job_found():
    created = client.post("/jobs", json={"name": "job2"})
    job_id = created.json()["id"]
    resp = client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200


def test_get_job_not_found():
    resp = client.get("/jobs/999")
    assert resp.status_code == 404


def test_list_jobs():
    client.post("/jobs", json={"name": "a"})
    client.post("/jobs", json={"name": "b"})
    resp = client.get("/jobs")
    assert len(resp.json()) == 2

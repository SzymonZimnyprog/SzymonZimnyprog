import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_items():
    response = client.get("/api/items/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_and_get_item():
    payload = {"name": "Test Item", "description": "A test"}
    create = client.post("/api/items/", json=payload)
    assert create.status_code == 201
    item = create.json()
    assert item["name"] == "Test Item"

    get = client.get(f"/api/items/{item['id']}")
    assert get.status_code == 200
    assert get.json()["name"] == "Test Item"


def test_get_missing_item():
    response = client.get("/api/items/99999")
    assert response.status_code == 404


def test_delete_item():
    create = client.post("/api/items/", json={"name": "To Delete"})
    item_id = create.json()["id"]
    delete = client.delete(f"/api/items/{item_id}")
    assert delete.status_code == 204
    get = client.get(f"/api/items/{item_id}")
    assert get.status_code == 404

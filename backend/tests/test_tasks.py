import uuid

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.fixture
def created_task():
    """Crea una tarea real contra la base de datos y la borra al terminar el test."""
    response = client.post("/tasks", json={"title": "Tarea de test", "priority": "low"})
    assert response.status_code == 200
    task = response.json()
    yield task
    client.delete(f"/tasks/{task['id']}")


def test_list_tasks_includes_created_task(created_task):
    response = client.get("/tasks")
    assert response.status_code == 200
    ids = [t["id"] for t in response.json()]
    assert created_task["id"] in ids


def test_list_tasks_filters_by_priority(created_task):
    response = client.get("/tasks", params={"priority": "low"})
    assert response.status_code == 200
    assert all(t["priority"] == "low" for t in response.json())
    assert any(t["id"] == created_task["id"] for t in response.json())


def test_list_tasks_filters_by_status(created_task):
    response = client.get("/tasks", params={"status": "done"})
    assert response.status_code == 200
    assert all(t["id"] != created_task["id"] for t in response.json())


def test_list_tasks_rejects_invalid_status():
    response = client.get("/tasks", params={"status": "no-existe"})
    assert response.status_code == 422


def test_list_tasks_rejects_invalid_priority():
    response = client.get("/tasks", params={"priority": "urgentisimo"})
    assert response.status_code == 422


def test_get_task_ok(created_task):
    response = client.get(f"/tasks/{created_task['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_task["id"]


def test_get_task_not_found_returns_404():
    response = client.get(f"/tasks/{uuid.uuid4()}")
    assert response.status_code == 404


def test_update_task_ok(created_task):
    response = client.put(
        f"/tasks/{created_task['id']}",
        json={"status": "done", "title": "Tarea actualizada"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["title"] == "Tarea actualizada"
    # los campos no enviados no deberían tocarse
    assert body["priority"] == created_task["priority"]


def test_update_task_rejects_invalid_status(created_task):
    response = client.put(f"/tasks/{created_task['id']}", json={"status": "no-existe"})
    assert response.status_code == 422


def test_update_task_not_found_returns_404():
    response = client.put(f"/tasks/{uuid.uuid4()}", json={"title": "no existe"})
    assert response.status_code == 404


def test_delete_task_ok():
    created = client.post("/tasks", json={"title": "Tarea para borrar"}).json()

    response = client.delete(f"/tasks/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_task_not_found_returns_404():
    response = client.delete(f"/tasks/{uuid.uuid4()}")
    assert response.status_code == 404

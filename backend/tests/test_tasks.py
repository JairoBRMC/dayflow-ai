import uuid

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.fixture
def created_task(auth_headers):
    """Crea una tarea real contra la base de datos y la borra al terminar el test."""
    response = client.post("/tasks", json={"title": "Tarea de test", "priority": "low"}, headers=auth_headers)
    assert response.status_code == 200
    task = response.json()
    yield task, auth_headers
    client.delete(f"/tasks/{task['id']}", headers=auth_headers)


def test_create_task_requires_auth():
    response = client.post("/tasks", json={"title": "sin token"})
    assert response.status_code == 401


def test_list_tasks_includes_created_task(created_task):
    task, headers = created_task
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    ids = [t["id"] for t in response.json()]
    assert task["id"] in ids


def test_list_tasks_filters_by_priority(created_task):
    task, headers = created_task
    response = client.get("/tasks", params={"priority": "low"}, headers=headers)
    assert response.status_code == 200
    assert all(t["priority"] == "low" for t in response.json())
    assert any(t["id"] == task["id"] for t in response.json())


def test_list_tasks_filters_by_status(created_task):
    task, headers = created_task
    response = client.get("/tasks", params={"status": "done"}, headers=headers)
    assert response.status_code == 200
    assert all(t["id"] != task["id"] for t in response.json())


def test_list_tasks_rejects_invalid_status(auth_headers):
    response = client.get("/tasks", params={"status": "no-existe"}, headers=auth_headers)
    assert response.status_code == 422


def test_list_tasks_rejects_invalid_priority(auth_headers):
    response = client.get("/tasks", params={"priority": "urgentisimo"}, headers=auth_headers)
    assert response.status_code == 422


def test_get_task_ok(created_task):
    task, headers = created_task
    response = client.get(f"/tasks/{task['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == task["id"]


def test_get_task_not_found_returns_404(auth_headers):
    response = client.get(f"/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_task_requires_auth(created_task):
    task, _ = created_task
    response = client.get(f"/tasks/{task['id']}")
    assert response.status_code == 401


def test_update_task_ok(created_task):
    task, headers = created_task
    response = client.put(
        f"/tasks/{task['id']}",
        json={"status": "done", "title": "Tarea actualizada"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["title"] == "Tarea actualizada"
    # los campos no enviados no deberían tocarse
    assert body["priority"] == task["priority"]


def test_update_task_rejects_invalid_status(created_task):
    task, headers = created_task
    response = client.put(f"/tasks/{task['id']}", json={"status": "no-existe"}, headers=headers)
    assert response.status_code == 422


def test_update_task_not_found_returns_404(auth_headers):
    response = client.put(f"/tasks/{uuid.uuid4()}", json={"title": "no existe"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_task_ok(auth_headers):
    created = client.post("/tasks", json={"title": "Tarea para borrar"}, headers=auth_headers).json()

    response = client.delete(f"/tasks/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    assert client.get(f"/tasks/{created['id']}", headers=auth_headers).status_code == 404


def test_delete_task_not_found_returns_404(auth_headers):
    response = client.delete(f"/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_cannot_access_another_users_task(created_task, other_user_headers):
    """Nadie debe ver/editar/borrar tareas de otro usuario -- 404, no 403, para no
    revelar que el recurso existe."""
    task, _owner_headers = created_task
    assert client.get(f"/tasks/{task['id']}", headers=other_user_headers).status_code == 404
    assert (
        client.put(f"/tasks/{task['id']}", json={"title": "hackeada"}, headers=other_user_headers).status_code == 404
    )
    assert client.delete(f"/tasks/{task['id']}", headers=other_user_headers).status_code == 404
    # y tampoco debería aparecer en su listado
    ids = [t["id"] for t in client.get("/tasks", headers=other_user_headers).json()]
    assert task["id"] not in ids

import uuid

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "title": "Reunión de test",
    "start_time": "2026-01-01T10:00:00Z",
    "end_time": "2026-01-01T11:00:00Z",
}


@pytest.fixture
def created_event():
    """Crea un evento real contra la base de datos y lo borra al terminar el test."""
    response = client.post("/events", json=VALID_PAYLOAD)
    assert response.status_code == 200
    event = response.json()
    yield event
    client.delete(f"/events/{event['id']}")


def test_create_event_ok(created_event):
    assert created_event["title"] == VALID_PAYLOAD["title"]
    assert created_event["description"] is None


def test_create_event_rejects_end_before_start():
    payload = {**VALID_PAYLOAD, "end_time": "2026-01-01T09:00:00Z"}
    response = client.post("/events", json=payload)
    assert response.status_code == 422


def test_create_event_rejects_end_equal_start():
    payload = {**VALID_PAYLOAD, "end_time": VALID_PAYLOAD["start_time"]}
    response = client.post("/events", json=payload)
    assert response.status_code == 422


def test_list_events_includes_created_event(created_event):
    response = client.get("/events")
    assert response.status_code == 200
    ids = [e["id"] for e in response.json()]
    assert created_event["id"] in ids


def test_get_event_ok(created_event):
    response = client.get(f"/events/{created_event['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_event["id"]


def test_get_event_not_found_returns_404():
    response = client.get(f"/events/{uuid.uuid4()}")
    assert response.status_code == 404


def test_update_event_ok(created_event):
    response = client.put(f"/events/{created_event['id']}", json={"title": "Reunión actualizada"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Reunión actualizada"
    # los campos no enviados no deberían tocarse
    assert body["start_time"] == created_event["start_time"]


def test_update_event_rejects_end_before_start(created_event):
    response = client.put(
        f"/events/{created_event['id']}",
        json={"end_time": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


def test_update_event_not_found_returns_404():
    response = client.put(f"/events/{uuid.uuid4()}", json={"title": "no existe"})
    assert response.status_code == 404


def test_delete_event_ok():
    created = client.post("/events", json=VALID_PAYLOAD).json()

    response = client.delete(f"/events/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/events/{created['id']}").status_code == 404


def test_delete_event_not_found_returns_404():
    response = client.delete(f"/events/{uuid.uuid4()}")
    assert response.status_code == 404

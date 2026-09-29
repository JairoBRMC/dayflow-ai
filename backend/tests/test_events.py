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
def created_event(auth_headers):
    """Crea un evento real contra la base de datos y lo borra al terminar el test."""
    response = client.post("/events", json=VALID_PAYLOAD, headers=auth_headers)
    assert response.status_code == 200
    event = response.json()
    yield event, auth_headers
    client.delete(f"/events/{event['id']}", headers=auth_headers)


def test_create_event_requires_auth():
    response = client.post("/events", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_create_event_ok(created_event):
    event, _headers = created_event
    assert event["title"] == VALID_PAYLOAD["title"]
    assert event["description"] is None


def test_create_event_rejects_end_before_start(auth_headers):
    payload = {**VALID_PAYLOAD, "end_time": "2026-01-01T09:00:00Z"}
    response = client.post("/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_create_event_rejects_end_equal_start(auth_headers):
    payload = {**VALID_PAYLOAD, "end_time": VALID_PAYLOAD["start_time"]}
    response = client.post("/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_list_events_includes_created_event(created_event):
    event, headers = created_event
    response = client.get("/events", headers=headers)
    assert response.status_code == 200
    ids = [e["id"] for e in response.json()]
    assert event["id"] in ids


def test_get_event_ok(created_event):
    event, headers = created_event
    response = client.get(f"/events/{event['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == event["id"]


def test_get_event_not_found_returns_404(auth_headers):
    response = client.get(f"/events/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_update_event_ok(created_event):
    event, headers = created_event
    response = client.put(f"/events/{event['id']}", json={"title": "Reunión actualizada"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Reunión actualizada"
    # los campos no enviados no deberían tocarse
    assert body["start_time"] == event["start_time"]


def test_update_event_rejects_end_before_start(created_event):
    event, headers = created_event
    response = client.put(
        f"/events/{event['id']}",
        json={"end_time": "2026-01-01T00:00:00Z"},
        headers=headers,
    )
    assert response.status_code == 422


def test_update_event_not_found_returns_404(auth_headers):
    response = client.put(f"/events/{uuid.uuid4()}", json={"title": "no existe"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_event_ok(auth_headers):
    created = client.post("/events", json=VALID_PAYLOAD, headers=auth_headers).json()

    response = client.delete(f"/events/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    assert client.get(f"/events/{created['id']}", headers=auth_headers).status_code == 404


def test_delete_event_not_found_returns_404(auth_headers):
    response = client.delete(f"/events/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_cannot_access_another_users_event(created_event, other_user_headers):
    event, _owner_headers = created_event
    assert client.get(f"/events/{event['id']}", headers=other_user_headers).status_code == 404
    assert (
        client.put(
            f"/events/{event['id']}", json={"title": "hackeado"}, headers=other_user_headers
        ).status_code
        == 404
    )
    assert client.delete(f"/events/{event['id']}", headers=other_user_headers).status_code == 404
    ids = [e["id"] for e in client.get("/events", headers=other_user_headers).json()]
    assert event["id"] not in ids

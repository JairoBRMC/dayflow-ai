import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from models import ChatMessage
from tests.conftest import TestSessionLocal

client = TestClient(app)


@pytest.fixture
def created_conversation(auth_headers):
    """Crea una conversación real contra la base de datos y la borra al terminar el test."""
    response = client.post("/conversations", json={"title": "Charla de test"}, headers=auth_headers)
    assert response.status_code == 200
    conversation = response.json()
    yield conversation, auth_headers
    client.delete(f"/conversations/{conversation['id']}", headers=auth_headers)


def _insert_message(conversation_id: str, role: str, content: str) -> None:
    """Inserta un ChatMessage directamente en la DB -- todavía no hay endpoint para
    crear mensajes (eso llega con la integración de Groq), así que para probar que
    GET /conversations/{id} los devuelve bien hace falta meterlos a mano."""
    db = TestSessionLocal()
    try:
        db.add(ChatMessage(conversation_id=uuid.UUID(conversation_id), role=role, content=content))
        db.commit()
    finally:
        db.close()


def test_create_conversation_requires_auth():
    response = client.post("/conversations", json={"title": "sin token"})
    assert response.status_code == 401


def test_create_conversation_with_title_ok(created_conversation):
    conversation, _headers = created_conversation
    assert conversation["title"] == "Charla de test"
    assert "id" in conversation
    assert "created_at" in conversation


def test_create_conversation_without_title_ok(auth_headers):
    response = client.post("/conversations", json={}, headers=auth_headers)
    assert response.status_code == 200
    conversation = response.json()
    assert conversation["title"] is None
    client.delete(f"/conversations/{conversation['id']}", headers=auth_headers)


def test_list_conversations_includes_created(created_conversation):
    conversation, headers = created_conversation
    response = client.get("/conversations", headers=headers)
    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert conversation["id"] in ids


def test_list_conversations_ordered_by_most_recent(auth_headers):
    first = client.post("/conversations", json={"title": "primera"}, headers=auth_headers).json()
    second = client.post("/conversations", json={"title": "segunda"}, headers=auth_headers).json()
    try:
        ids = [c["id"] for c in client.get("/conversations", headers=auth_headers).json()]
        assert ids.index(second["id"]) < ids.index(first["id"])
    finally:
        client.delete(f"/conversations/{first['id']}", headers=auth_headers)
        client.delete(f"/conversations/{second['id']}", headers=auth_headers)


def test_get_conversation_requires_auth(created_conversation):
    conversation, _headers = created_conversation
    response = client.get(f"/conversations/{conversation['id']}")
    assert response.status_code == 401


def test_get_conversation_starts_with_no_messages(created_conversation):
    conversation, headers = created_conversation
    response = client.get(f"/conversations/{conversation['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["messages"] == []


def test_get_conversation_returns_messages_in_order(created_conversation):
    conversation, headers = created_conversation
    _insert_message(conversation["id"], "user", "hola")
    _insert_message(conversation["id"], "assistant", "¿en qué te ayudo?")

    response = client.get(f"/conversations/{conversation['id']}", headers=headers)
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert [m["content"] for m in messages] == ["hola", "¿en qué te ayudo?"]


def test_get_conversation_not_found_returns_404(auth_headers):
    response = client.get(f"/conversations/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_conversation_ok(auth_headers):
    created = client.post("/conversations", json={"title": "para borrar"}, headers=auth_headers).json()

    response = client.delete(f"/conversations/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    assert client.get(f"/conversations/{created['id']}", headers=auth_headers).status_code == 404


def test_delete_conversation_also_deletes_its_messages(auth_headers):
    """ondelete=CASCADE en chat_messages.conversation_id debe llevarse los mensajes."""
    created = client.post("/conversations", json={"title": "con mensajes"}, headers=auth_headers).json()
    _insert_message(created["id"], "user", "hola")

    client.delete(f"/conversations/{created['id']}", headers=auth_headers)

    db = TestSessionLocal()
    try:
        remaining = db.query(ChatMessage).filter(ChatMessage.conversation_id == uuid.UUID(created["id"])).count()
        assert remaining == 0
    finally:
        db.close()


def test_delete_conversation_not_found_returns_404(auth_headers):
    response = client.delete(f"/conversations/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_cannot_access_another_users_conversation(created_conversation, other_user_headers):
    conversation, _owner_headers = created_conversation
    assert client.get(f"/conversations/{conversation['id']}", headers=other_user_headers).status_code == 404
    assert client.delete(f"/conversations/{conversation['id']}", headers=other_user_headers).status_code == 404
    ids = [c["id"] for c in client.get("/conversations", headers=other_user_headers).json()]
    assert conversation["id"] not in ids

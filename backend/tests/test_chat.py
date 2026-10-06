import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from groq import APIError as GroqAPIError

import main

client = TestClient(main.app)


@pytest.fixture
def fake_groq(monkeypatch):
    """Sustituye la llamada real a Groq por un doble determinista y sin red: los
    tests de este archivo no deben depender de la API externa ni gastar cuota.
    La conectividad real con Groq se comprueba aparte (ver groq_client.py), no en
    la suite automatizada."""
    calls = []

    def _fake(messages):
        calls.append(messages)
        return "respuesta simulada"

    monkeypatch.setattr(main, "get_chat_completion", _fake)
    return calls


@pytest.fixture
def created_conversation(auth_headers):
    response = client.post("/conversations", json={"title": "chat de test"}, headers=auth_headers)
    assert response.status_code == 200
    conversation = response.json()
    yield conversation, auth_headers
    client.delete(f"/conversations/{conversation['id']}", headers=auth_headers)


def test_chat_requires_auth(created_conversation):
    conversation, _headers = created_conversation
    response = client.post(f"/conversations/{conversation['id']}/chat", json={"message": "hola"})
    assert response.status_code == 401


def test_chat_not_found_returns_404(auth_headers, fake_groq):
    response = client.post(
        f"/conversations/{uuid.uuid4()}/chat", json={"message": "hola"}, headers=auth_headers
    )
    assert response.status_code == 404
    assert fake_groq == []  # ni se debería haber llamado a Groq


def test_chat_rejects_empty_message(created_conversation, fake_groq):
    conversation, headers = created_conversation
    response = client.post(f"/conversations/{conversation['id']}/chat", json={"message": ""}, headers=headers)
    assert response.status_code == 422
    assert fake_groq == []


def test_chat_saves_and_returns_assistant_reply(created_conversation, fake_groq):
    conversation, headers = created_conversation
    response = client.post(
        f"/conversations/{conversation['id']}/chat", json={"message": "hola"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert body["content"] == "respuesta simulada"

    detail = client.get(f"/conversations/{conversation['id']}", headers=headers).json()
    assert [(m["role"], m["content"]) for m in detail["messages"]] == [
        ("user", "hola"),
        ("assistant", "respuesta simulada"),
    ]


def test_chat_sends_full_history_to_groq(created_conversation, fake_groq):
    conversation, headers = created_conversation
    client.post(f"/conversations/{conversation['id']}/chat", json={"message": "primero"}, headers=headers)
    client.post(f"/conversations/{conversation['id']}/chat", json={"message": "segundo"}, headers=headers)

    # en la segunda llamada, Groq debería recibir los 3 mensajes previos (user,
    # assistant, user) para "recordar" la conversación, no solo el último mensaje
    second_call_messages = fake_groq[1]
    assert [m["role"] for m in second_call_messages] == ["user", "assistant", "user"]
    assert [m["content"] for m in second_call_messages] == ["primero", "respuesta simulada", "segundo"]


def test_chat_cannot_use_another_users_conversation(created_conversation, other_user_headers, fake_groq):
    conversation, _owner_headers = created_conversation
    response = client.post(
        f"/conversations/{conversation['id']}/chat", json={"message": "hola"}, headers=other_user_headers
    )
    assert response.status_code == 404
    assert fake_groq == []


def test_chat_returns_502_when_groq_fails(created_conversation, monkeypatch):
    conversation, headers = created_conversation

    def _broken(messages):
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        raise GroqAPIError("boom", request, body=None)

    monkeypatch.setattr(main, "get_chat_completion", _broken)

    response = client.post(f"/conversations/{conversation['id']}/chat", json={"message": "hola"}, headers=headers)
    assert response.status_code == 502

    # el mensaje del usuario sí debe quedar guardado aunque Groq falle
    detail = client.get(f"/conversations/{conversation['id']}", headers=headers).json()
    assert [(m["role"], m["content"]) for m in detail["messages"]] == [("user", "hola")]

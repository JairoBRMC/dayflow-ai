import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import User

client = TestClient(app)

TEST_PASSWORD = "testpassword123"


def register_and_login(email: str | None = None) -> tuple[dict, str]:
    """Registra un usuario nuevo, hace login y devuelve (headers, email).
    No limpia nada -- quien lo llame es responsable de borrar el usuario."""
    email = email or f"test-{uuid.uuid4()}@example.com"

    register_response = client.post("/auth/register", json={"email": email, "password": TEST_PASSWORD})
    assert register_response.status_code == 201

    login_response = client.post("/auth/login", data={"username": email, "password": TEST_PASSWORD})
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def delete_test_user(email: str) -> None:
    """Borra un usuario de test directamente en la DB (no hay endpoint DELETE /users).
    El ondelete=CASCADE de la FK se lleva por delante sus tasks/events."""
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def registered_user():
    """Un usuario de test recién registrado: (headers, email). Se borra (y sus
    tasks/events en cascada) al terminar."""
    headers, email = register_and_login()
    yield headers, email
    delete_test_user(email)


@pytest.fixture
def auth_headers(registered_user):
    headers, _email = registered_user
    return headers


@pytest.fixture
def registered_email(registered_user):
    _headers, email = registered_user
    return email


@pytest.fixture
def other_user_headers():
    """Un segundo usuario de test, independiente de auth_headers/registered_user --
    para probar que nadie puede acceder a los recursos de otro usuario."""
    headers, email = register_and_login()
    yield headers
    delete_test_user(email)

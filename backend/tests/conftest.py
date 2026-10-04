import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from models import User

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Los tests NUNCA tocan la base de datos de desarrollo (DATABASE_URL): usan su propia
# Postgres (servicio db_test en docker-compose.yml), vacía desde cero.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL no está definida. Copia backend/.env.example a backend/.env, "
        "arranca el servicio db_test (docker-compose up -d db_test) y vuelve a intentarlo."
    )

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Cualquier endpoint que dependa de get_db (prácticamente todos) usa la sesión de test
# en vez de la de main.py mientras corre pytest.
app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_database():
    """Deja la DB de test en head antes del primer test. alembic/env.py lee
    DATABASE_URL de el entorno, así que apuntamos esa variable a TEST_DATABASE_URL
    solo durante esta llamada -- la DB de desarrollo no se toca."""
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url


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
    """Borra un usuario de test directamente en la DB de test (no hay endpoint
    DELETE /users). El ondelete=CASCADE de la FK se lleva por delante sus tasks/events."""
    db = TestSessionLocal()
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

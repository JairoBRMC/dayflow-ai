import uuid

from fastapi.testclient import TestClient

from main import app
from tests.conftest import delete_test_user

client = TestClient(app)

TEST_PASSWORD = "testpassword123"


def test_register_ok():
    email = f"test-{uuid.uuid4()}@example.com"
    response = client.post("/auth/register", json={"email": email, "password": TEST_PASSWORD})
    try:
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == email
        assert "id" in body
        assert "password" not in body
        assert "hashed_password" not in body
    finally:
        delete_test_user(email)


def test_register_rejects_short_password():
    email = f"test-{uuid.uuid4()}@example.com"
    response = client.post("/auth/register", json={"email": email, "password": "short"})
    assert response.status_code == 422


def test_register_rejects_duplicate_email(auth_headers, registered_email):
    response = client.post("/auth/register", json={"email": registered_email, "password": TEST_PASSWORD})
    assert response.status_code == 400


def test_login_ok(registered_email):
    response = client.post("/auth/login", data={"username": registered_email, "password": TEST_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password(registered_email):
    response = client.post("/auth/login", data={"username": registered_email, "password": "wrong-password"})
    assert response.status_code == 401


def test_login_unknown_email():
    response = client.post(
        "/auth/login", data={"username": f"noexiste-{uuid.uuid4()}@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401


def test_protected_endpoint_without_token_returns_401():
    response = client.get("/tasks")
    assert response.status_code == 401


def test_protected_endpoint_with_invalid_token_returns_401():
    response = client.get("/tasks", headers={"Authorization": "Bearer no-soy-un-jwt-valido"})
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token_ok(auth_headers):
    response = client.get("/tasks", headers=auth_headers)
    assert response.status_code == 200


def test_refresh_token_issues_new_access_token(registered_email):
    login_response = client.post("/auth/login", data={"username": registered_email, "password": TEST_PASSWORD})
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]

    me_check = client.get("/tasks", headers={"Authorization": f"Bearer {new_access_token}"})
    assert me_check.status_code == 200


def test_refresh_rejects_an_access_token_as_refresh_token(auth_headers):
    # auth_headers trae un access token; no debe servir como refresh token
    access_token = auth_headers["Authorization"].removeprefix("Bearer ")
    response = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_refresh_rejects_garbage_token():
    response = client.post("/auth/refresh", json={"refresh_token": "no-soy-un-jwt-valido"})
    assert response.status_code == 401

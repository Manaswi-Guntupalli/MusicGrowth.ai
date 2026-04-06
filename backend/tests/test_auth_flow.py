from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_login_and_me(test_client: TestClient):
    payload = {"name": "Alice", "email": "alice@example.com", "password": "Passw0rd!"}

    register = test_client.post("/api/auth/register", json=payload)
    assert register.status_code == 200
    body = register.json()
    assert "access_token" in body
    assert body["user"]["email"] == payload["email"]

    duplicate = test_client.post("/api/auth/register", json=payload)
    assert duplicate.status_code == 400

    login = test_client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = test_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == payload["email"]
    assert me_body["name"] == payload["name"]


def test_login_invalid_password(test_client: TestClient):
    payload = {"name": "Bob", "email": "bob@example.com", "password": "Passw0rd!"}
    test_client.post("/api/auth/register", json=payload)

    bad = test_client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": "wrong-pass"},
    )
    assert bad.status_code == 401

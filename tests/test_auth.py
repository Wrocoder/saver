from decimal import Decimal

from fastapi.testclient import TestClient


def test_register_returns_tokens_and_bearer_token_scopes_goals(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "auth-user@example.com",
            "password": "correct-password",
            "name": "Auth User",
            "base_currency": "USD",
        },
    )

    assert register_response.status_code == 201
    auth_payload = register_response.json()
    assert auth_payload["token_type"] == "bearer"
    assert auth_payload["access_token"]
    assert auth_payload["refresh_token"]
    assert auth_payload["user"]["email"] == "auth-user@example.com"

    goal_response = client.post(
        "/api/goals",
        headers={"Authorization": f"Bearer {auth_payload['access_token']}"},
        json={
            "title": "Emergency fund",
            "target_amount": "1500",
            "current_amount": "300",
            "currency": "USD",
        },
    )

    assert goal_response.status_code == 201

    goals_response = client.get(
        "/api/goals",
        headers={"Authorization": f"Bearer {auth_payload['access_token']}"},
    )
    assert goals_response.status_code == 200
    goals = goals_response.json()
    assert len(goals) == 1
    assert Decimal(goals[0]["current_amount"]) == Decimal("300")


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "wrong-password@example.com",
            "password": "correct-password",
            "base_currency": "USD",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "wrong-password",
        },
    )

    assert login_response.status_code == 401


def test_refresh_rotates_token_and_rejects_reuse(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "correct-password",
            "base_currency": "USD",
        },
    )
    original_refresh_token = register_response.json()["refresh_token"]

    refresh_response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )

    assert refresh_response.status_code == 200
    rotated_payload = refresh_response.json()
    assert rotated_payload["access_token"]
    assert rotated_payload["refresh_token"] != original_refresh_token

    reuse_response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    assert reuse_response.status_code == 401


def test_delete_account_revokes_access_and_refresh_and_allows_email_reuse(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "delete-me@example.com",
            "password": "correct-password",
            "base_currency": "USD",
        },
    )
    payload = register_response.json()
    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    client.post(
        "/api/goals",
        headers=headers,
        json={"title": "Private goal", "target_amount": "1000", "currency": "USD"},
    )

    delete_response = client.delete("/api/me", headers=headers)

    assert delete_response.status_code == 204
    assert client.get("/api/me", headers=headers).status_code == 401
    assert client.get("/api/goals", headers=headers).status_code == 401
    assert client.post(
        "/api/auth/refresh",
        json={"refresh_token": payload["refresh_token"]},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "delete-me@example.com", "password": "correct-password"},
    ).status_code == 401

    re_register_response = client.post(
        "/api/auth/register",
        json={
            "email": "delete-me@example.com",
            "password": "correct-password",
            "base_currency": "USD",
        },
    )
    assert re_register_response.status_code == 201


def test_delete_account_requires_bearer_token(client: TestClient) -> None:
    response = client.delete("/api/me")

    assert response.status_code == 401

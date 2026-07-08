from fastapi.testclient import TestClient


def register_user(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-password", "base_currency": "USD"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_audit_log_lists_current_user_actions_only(client: TestClient) -> None:
    first_headers = register_user(client, "audit-one@example.com")
    second_headers = register_user(client, "audit-two@example.com")

    client.patch(
        "/api/me/profile",
        headers=first_headers,
        json={"monthly_available_amount": "450"},
    )
    client.post(
        "/api/goals",
        headers=first_headers,
        json={"title": "Laptop", "target_amount": "1200", "currency": "USD"},
    )
    client.post(
        "/api/goals",
        headers=second_headers,
        json={"title": "Hidden", "target_amount": "500", "currency": "USD"},
    )

    response = client.get("/api/audit-log", headers=first_headers)

    assert response.status_code == 200
    entries = response.json()
    assert {entry["entity_type"] for entry in entries} >= {"user_profile", "financial_goal"}
    assert {entry["action"] for entry in entries} >= {"update", "create"}
    assert all(entry["actor_user_id"] is not None for entry in entries)
    assert not any(entry["after_json"] and entry["after_json"].get("title") == "Hidden" for entry in entries)


def test_audit_log_can_filter_by_entity_type(client: TestClient) -> None:
    headers = register_user(client, "audit-filter@example.com")
    client.patch(
        "/api/me/profile",
        headers=headers,
        json={"monthly_available_amount": "700"},
    )
    client.post(
        "/api/goals",
        headers=headers,
        json={"title": "Phone", "target_amount": "900", "currency": "USD"},
    )

    response = client.get("/api/audit-log?entity_type=financial_goal", headers=headers)

    assert response.status_code == 200
    entries = response.json()
    assert entries
    assert {entry["entity_type"] for entry in entries} == {"financial_goal"}

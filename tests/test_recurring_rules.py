from decimal import Decimal

from fastapi.testclient import TestClient


def test_recurring_rule_can_be_applied_to_goal(client: TestClient) -> None:
    goal_response = client.post(
        "/api/goals",
        json={
            "title": "Emergency fund",
            "target_amount": "1000",
            "current_amount": "100",
            "currency": "USD",
        },
    )
    goal_id = goal_response.json()["id"]

    create_response = client.post(
        "/api/recurring-rules",
        json={
            "goal_id": goal_id,
            "title": "Salary auto-save",
            "amount": "150",
            "currency": "USD",
            "frequency": "monthly",
            "day_of_month": 10,
            "source": "salary",
            "next_run_on": "2026-07-10",
        },
    )

    assert create_response.status_code == 201
    rule = create_response.json()
    assert rule["title"] == "Salary auto-save"
    assert rule["next_run_on"] == "2026-07-10"

    apply_response = client.post(f"/api/recurring-rules/{rule['id']}/apply?occurred_at=2026-07-10")

    assert apply_response.status_code == 200
    contribution = apply_response.json()
    assert contribution["source"] == "salary"
    assert Decimal(contribution["amount"]) == Decimal("150")

    updated_goal = client.get(f"/api/goals/{goal_id}").json()
    assert Decimal(updated_goal["current_amount"]) == Decimal("250")

    updated_rule = client.get("/api/recurring-rules").json()[0]
    assert updated_rule["last_run_on"] == "2026-07-10"
    assert updated_rule["next_run_on"] == "2026-08-10"


def test_recurring_rule_update_pause_and_delete(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={
            "title": "Phone",
            "target_amount": "900",
            "current_amount": "0",
            "currency": "USD",
        },
    ).json()["id"]
    rule_id = client.post(
        "/api/recurring-rules",
        json={
            "goal_id": goal_id,
            "title": "Weekly save",
            "amount": "25",
            "currency": "USD",
            "frequency": "weekly",
        },
    ).json()["id"]

    pause_response = client.patch(f"/api/recurring-rules/{rule_id}", json={"is_active": False})
    assert pause_response.status_code == 200
    assert pause_response.json()["is_active"] is False

    apply_response = client.post(f"/api/recurring-rules/{rule_id}/apply")
    assert apply_response.status_code == 400

    delete_response = client.delete(f"/api/recurring-rules/{rule_id}")
    assert delete_response.status_code == 204
    assert client.get("/api/recurring-rules").json() == []


def test_recurring_rule_rejects_goal_from_other_user(client: TestClient) -> None:
    first_user = client.post(
        "/api/users",
        json={"email": "rules-first@example.com", "name": "First", "base_currency": "USD"},
    ).json()
    second_user = client.post(
        "/api/users",
        json={"email": "rules-second@example.com", "name": "Second", "base_currency": "USD"},
    ).json()
    goal_id = client.post(
        "/api/goals",
        headers={"X-User-Id": first_user["id"]},
        json={"title": "Car", "target_amount": "4000", "currency": "USD"},
    ).json()["id"]

    response = client.post(
        "/api/recurring-rules",
        headers={"X-User-Id": second_user["id"]},
        json={
            "goal_id": goal_id,
            "title": "Wrong user rule",
            "amount": "100",
            "currency": "USD",
            "frequency": "monthly",
        },
    )

    assert response.status_code == 404

from decimal import Decimal

from fastapi.testclient import TestClient


def test_price_history_update_changes_goal_target(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={
            "title": "Camera",
            "target_amount": "1000",
            "current_amount": "200",
            "currency": "USD",
        },
    ).json()["id"]

    price_response = client.post(
        f"/api/goals/{goal_id}/price-history",
        json={
            "new_amount": "900",
            "currency": "USD",
            "source": "store",
            "note": "Discount",
            "changed_at": "2026-07-05",
        },
    )

    assert price_response.status_code == 201
    price_record = price_response.json()
    assert Decimal(price_record["previous_amount"]) == Decimal("1000")
    assert Decimal(price_record["new_amount"]) == Decimal("900")
    assert price_record["note"] == "Discount"

    goal = client.get(f"/api/goals/{goal_id}").json()
    assert Decimal(goal["target_amount"]) == Decimal("900")

    history = client.get(f"/api/goals/{goal_id}/price-history").json()
    assert len(history) == 1
    assert history[0]["source"] == "store"


def test_goal_patch_records_price_history_when_target_changes(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={"title": "Phone", "target_amount": "800", "currency": "USD"},
    ).json()["id"]

    patch_response = client.patch(f"/api/goals/{goal_id}", json={"target_amount": "850"})

    assert patch_response.status_code == 200
    history = client.get(f"/api/goals/{goal_id}/price-history").json()
    assert len(history) == 1
    assert history[0]["source"] == "goal_update"
    assert Decimal(history[0]["previous_amount"]) == Decimal("800")
    assert Decimal(history[0]["new_amount"]) == Decimal("850")


def test_price_history_is_scoped_to_goal_owner(client: TestClient) -> None:
    first_user = client.post(
        "/api/users",
        json={"email": "price-first@example.com", "name": "First", "base_currency": "USD"},
    ).json()
    second_user = client.post(
        "/api/users",
        json={"email": "price-second@example.com", "name": "Second", "base_currency": "USD"},
    ).json()
    goal_id = client.post(
        "/api/goals",
        headers={"X-User-Id": first_user["id"]},
        json={"title": "Car", "target_amount": "5000", "currency": "USD"},
    ).json()["id"]

    response = client.post(
        f"/api/goals/{goal_id}/price-history",
        headers={"X-User-Id": second_user["id"]},
        json={"new_amount": "5200"},
    )

    assert response.status_code == 404

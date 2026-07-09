from decimal import Decimal

from fastapi.testclient import TestClient


def test_create_goal_and_recalculate_plan(client: TestClient) -> None:

    response = client.post(
        "/api/goals",
        json={
            "title": "iPhone",
            "target_amount": "1000",
            "current_amount": "200",
            "currency": "USD",
            "priority": 1,
        },
    )

    assert response.status_code == 201
    goal = response.json()
    assert goal["title"] == "iPhone"
    assert Decimal(goal["current_amount"]) == Decimal("200")

    plan_response = client.get("/api/plan")
    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert Decimal(plan["monthly_available_amount"]) == Decimal("300")
    assert Decimal(plan["goals"][0]["remaining_amount"]) == Decimal("800")
    assert plan["goals"][0]["status"] == "on_track"


def test_contribution_updates_goal_amount(client: TestClient) -> None:
    goal_response = client.post(
        "/api/goals",
        json={
            "title": "Laptop",
            "target_amount": "1200",
            "current_amount": "100",
            "currency": "USD",
        },
    )
    goal_id = goal_response.json()["id"]

    contribution_response = client.post(
        f"/api/goals/{goal_id}/contributions",
        json={
            "type": "add",
            "amount": "250",
            "source": "salary",
        },
    )
    assert contribution_response.status_code == 201

    updated_goal = client.get(f"/api/goals/{goal_id}").json()
    assert Decimal(updated_goal["current_amount"]) == Decimal("350")


def test_archive_goal_hides_it_from_lists_and_plan(client: TestClient) -> None:
    goal_response = client.post(
        "/api/goals",
        json={
            "title": "Camera",
            "target_amount": "900",
            "current_amount": "100",
            "currency": "USD",
        },
    )
    goal_id = goal_response.json()["id"]

    delete_response = client.delete(f"/api/goals/{goal_id}")

    assert delete_response.status_code == 204
    assert client.get(f"/api/goals/{goal_id}").status_code == 404
    assert client.get("/api/goals").json() == []
    assert client.get("/api/plan").json()["goals"] == []


def test_reverse_contribution_restores_goal_amount(client: TestClient) -> None:
    goal_response = client.post(
        "/api/goals",
        json={
            "title": "Laptop",
            "target_amount": "1200",
            "current_amount": "100",
            "currency": "USD",
        },
    )
    goal_id = goal_response.json()["id"]
    contribution_response = client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"type": "add", "amount": "250"},
    )
    contribution_id = contribution_response.json()["id"]

    reverse_response = client.post(f"/api/contributions/{contribution_id}/reverse")

    assert reverse_response.status_code == 200
    assert reverse_response.json()["reversed_at"] is not None

    updated_goal = client.get(f"/api/goals/{goal_id}").json()
    assert Decimal(updated_goal["current_amount"]) == Decimal("100")

    second_reverse_response = client.post(f"/api/contributions/{contribution_id}/reverse")
    assert second_reverse_response.status_code == 400


def test_update_priorities_reorders_goals(client: TestClient) -> None:
    first_goal = client.post(
        "/api/goals",
        json={"title": "Phone", "target_amount": "1000", "currency": "USD", "priority": 1},
    ).json()
    second_goal = client.post(
        "/api/goals",
        json={"title": "Car", "target_amount": "8000", "currency": "USD", "priority": 2},
    ).json()

    response = client.post(
        "/api/priorities",
        json={"ordered_goal_ids": [second_goal["id"], first_goal["id"]]},
    )

    assert response.status_code == 200
    reordered_titles = [goal["title"] for goal in response.json()]
    assert reordered_titles == ["Car", "Phone"]

    listed_titles = [goal["title"] for goal in client.get("/api/goals").json()]
    assert listed_titles == ["Car", "Phone"]


def test_update_and_get_plan_strategy(client: TestClient) -> None:
    first_goal = client.post(
        "/api/goals",
        json={"title": "Phone", "target_amount": "1000", "currency": "USD", "priority": 1},
    ).json()
    second_goal = client.post(
        "/api/goals",
        json={"title": "Vacation", "target_amount": "2000", "currency": "USD", "priority": 2},
    ).json()

    update_response = client.post(
        "/api/plan/strategy",
        json={
            "type": "proportional",
            "weights": {first_goal["id"]: "70", second_goal["id"]: "30"},
            "fixed_amounts": {},
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["strategy"] == "proportional"

    strategy_response = client.get("/api/plan/strategy")
    assert strategy_response.status_code == 200
    strategy = strategy_response.json()
    assert strategy["type"] == "proportional"
    assert Decimal(strategy["weights"][first_goal["id"]]) == Decimal("70")
    assert Decimal(strategy["weights"][second_goal["id"]]) == Decimal("30")


def test_update_plan_strategy_supports_custom_fixed_amounts(client: TestClient) -> None:
    first_goal = client.post(
        "/api/goals",
        json={"title": "Emergency fund", "target_amount": "1000", "currency": "USD", "priority": 1},
    ).json()
    second_goal = client.post(
        "/api/goals",
        json={"title": "Trip", "target_amount": "800", "currency": "USD", "priority": 2},
    ).json()

    update_response = client.post(
        "/api/plan/strategy",
        json={
            "type": "custom",
            "weights": {},
            "fixed_amounts": {first_goal["id"]: "200", second_goal["id"]: "80"},
        },
    )

    assert update_response.status_code == 200
    plan = update_response.json()
    assert plan["strategy"] == "custom"
    assert Decimal(plan["monthly_schedule"][0]["allocations"][first_goal["id"]]) == Decimal("200")
    assert Decimal(plan["monthly_schedule"][0]["allocations"][second_goal["id"]]) == Decimal("80")

    strategy_response = client.get("/api/plan/strategy")
    assert strategy_response.status_code == 200
    strategy = strategy_response.json()
    assert strategy["type"] == "custom"
    assert Decimal(strategy["fixed_amounts"][first_goal["id"]]) == Decimal("200")
    assert Decimal(strategy["fixed_amounts"][second_goal["id"]]) == Decimal("80")


def test_custom_fixed_amount_strategy_rejects_unknown_goal_ids(client: TestClient) -> None:
    response = client.post(
        "/api/plan/strategy",
        json={
            "type": "custom",
            "weights": {},
            "fixed_amounts": {"missing-goal": "50"},
        },
    )

    assert response.status_code == 400
    assert "Unknown goal ids in fixed_amounts" in response.json()["detail"]


def test_one_time_inflow_scenario_adds_extra_funds_to_selected_month(client: TestClient) -> None:
    goal = client.post(
        "/api/goals",
        json={"title": "Emergency fund", "target_amount": "1000", "currency": "USD", "priority": 1},
    ).json()

    response = client.post(
        "/api/scenarios/one-time-inflow",
        json={
            "scenario_name": "bonus",
            "amount": "500",
            "month_index": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_name"] == "bonus"
    assert payload["base"]["strategy"] == payload["scenario"]["strategy"]
    assert Decimal(payload["base"]["monthly_schedule"][1]["allocations"][goal["id"]]) == Decimal("300")
    assert Decimal(payload["scenario"]["monthly_schedule"][1]["allocations"][goal["id"]]) == Decimal("700")
    assert payload["scenario"]["goals"][0]["expected_completion_date"] < payload["base"]["goals"][0]["expected_completion_date"]


def test_skipped_months_scenario_removes_regular_funding_for_period(client: TestClient) -> None:
    goal = client.post(
        "/api/goals",
        json={"title": "Laptop", "target_amount": "900", "currency": "USD", "priority": 1},
    ).json()

    response = client.post(
        "/api/scenarios/skipped-months",
        json={
            "scenario_name": "missed_salary",
            "start_month": 1,
            "month_count": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_name"] == "missed_salary"
    assert Decimal(payload["base"]["monthly_schedule"][0]["allocations"][goal["id"]]) == Decimal("300")
    assert payload["scenario"]["monthly_schedule"][0]["month_index"] == 2
    assert Decimal(payload["scenario"]["monthly_schedule"][0]["allocations"][goal["id"]]) == Decimal("300")
    assert payload["scenario"]["goals"][0]["allocated_first_month"] == "0"
    assert payload["scenario"]["goals"][0]["expected_completion_date"] > payload["base"]["goals"][0]["expected_completion_date"]


def test_goal_ownership_is_scoped_by_user_header(client: TestClient) -> None:
    first_user = client.post(
        "/api/users",
        json={"email": "first@example.com", "name": "First", "base_currency": "USD"},
    ).json()
    second_user = client.post(
        "/api/users",
        json={"email": "second@example.com", "name": "Second", "base_currency": "USD"},
    ).json()

    goal_response = client.post(
        "/api/goals",
        headers={"X-User-Id": first_user["id"]},
        json={
            "title": "Car",
            "target_amount": "5000",
            "current_amount": "1000",
            "currency": "USD",
        },
    )

    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    forbidden_lookup = client.get(
        f"/api/goals/{goal_id}",
        headers={"X-User-Id": second_user["id"]},
    )
    assert forbidden_lookup.status_code == 404

    second_user_goals = client.get(
        "/api/goals",
        headers={"X-User-Id": second_user["id"]},
    ).json()
    assert second_user_goals == []

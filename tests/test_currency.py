from decimal import Decimal

from fastapi.testclient import TestClient


def auth_headers(client: TestClient, email: str = "currency@example.com") -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct-password",
            "base_currency": "USD",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_rate(
    client: TestClient,
    base_currency: str,
    quote_currency: str,
    rate: str,
) -> dict:
    response = client.post(
        "/api/exchange-rates",
        json={
            "base_currency": base_currency,
            "quote_currency": quote_currency,
            "rate": rate,
            "source": "test",
            "rate_date": "2026-07-04",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_financial_summary_converts_non_base_currency_when_rate_exists(
    client: TestClient,
) -> None:
    headers = auth_headers(client)
    add_rate(client, "EUR", "USD", "1.20")

    income_response = client.post(
        "/api/incomes",
        headers=headers,
        json={
            "amount": "1000",
            "currency": "EUR",
            "frequency": "monthly",
        },
    )
    assert income_response.status_code == 201

    summary = client.get("/api/financial-summary", headers=headers).json()

    assert Decimal(summary["total_monthly_income"]) == Decimal("1200.0000000000")
    assert Decimal(summary["calculated_monthly_available_amount"]) == Decimal("1200.0000000000")
    assert summary["warnings"] == []


def test_contribution_in_goal_foreign_currency_uses_exchange_rate_and_reverses(
    client: TestClient,
) -> None:
    headers = auth_headers(client, "goal-currency@example.com")
    add_rate(client, "EUR", "USD", "1.20")

    goal = client.post(
        "/api/goals",
        headers=headers,
        json={
            "title": "Camera",
            "target_amount": "1000",
            "current_amount": "100",
            "currency": "USD",
        },
    ).json()

    contribution_response = client.post(
        f"/api/goals/{goal['id']}/contributions",
        headers=headers,
        json={
            "type": "add",
            "amount": "100",
            "currency": "EUR",
        },
    )

    assert contribution_response.status_code == 201
    contribution = contribution_response.json()
    assert Decimal(contribution["amount"]) == Decimal("100")
    assert Decimal(contribution["amount_in_goal_currency"]) == Decimal("120.0000000000")
    assert Decimal(contribution["amount_in_base_currency"]) == Decimal("120.0000000000")

    updated_goal = client.get(f"/api/goals/{goal['id']}", headers=headers).json()
    assert Decimal(updated_goal["current_amount"]) == Decimal("220.0000")

    reverse_response = client.post(
        f"/api/contributions/{contribution['id']}/reverse",
        headers=headers,
    )
    assert reverse_response.status_code == 200

    restored_goal = client.get(f"/api/goals/{goal['id']}", headers=headers).json()
    assert Decimal(restored_goal["current_amount"]) == Decimal("100.0000")


def test_plan_converts_foreign_currency_goal_to_base_currency(
    client: TestClient,
) -> None:
    headers = auth_headers(client, "plan-currency@example.com")
    add_rate(client, "EUR", "USD", "1.20")
    client.patch(
        "/api/me/profile",
        headers=headers,
        json={"monthly_available_amount": "600"},
    )
    client.post(
        "/api/goals",
        headers=headers,
        json={
            "title": "Trip",
            "target_amount": "1000",
            "current_amount": "0",
            "currency": "EUR",
        },
    )

    plan_response = client.get("/api/plan", headers=headers)

    assert plan_response.status_code == 200
    projection = plan_response.json()["goals"][0]
    assert projection["currency"] == "USD"
    assert Decimal(projection["target_amount"]) == Decimal("1200.0000000000")
    assert Decimal(projection["allocated_first_month"]) == Decimal("600")


def test_plan_skips_foreign_currency_goal_without_rate_without_blocking_other_data(
    client: TestClient,
) -> None:
    headers = auth_headers(client, "missing-plan-rate@example.com")
    client.patch(
        "/api/me/profile",
        headers=headers,
        json={"monthly_available_amount": "500"},
    )
    client.post(
        "/api/goals",
        headers=headers,
        json={
            "title": "Phone",
            "target_amount": "1000",
            "current_amount": "0",
            "currency": "USD",
            "priority": 1,
        },
    )
    client.post(
        "/api/goals",
        headers=headers,
        json={
            "title": "Trip",
            "target_amount": "2000",
            "current_amount": "0",
            "currency": "PLN",
            "priority": 2,
        },
    )

    plan_response = client.get("/api/plan", headers=headers)
    goals_response = client.get("/api/goals", headers=headers)
    summary_response = client.get("/api/financial-summary", headers=headers)

    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert [goal["title"] for goal in plan["goals"]] == ["Phone"]
    assert any("PLN->USD" in conflict for conflict in plan["conflicts"])
    assert {goal["title"] for goal in goals_response.json()} == {"Phone", "Trip"}
    assert summary_response.status_code == 200
    assert Decimal(summary_response.json()["effective_monthly_available_amount"]) == Decimal("500")

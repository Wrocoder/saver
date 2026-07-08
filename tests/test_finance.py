from decimal import Decimal

from fastapi.testclient import TestClient


def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "finance@example.com",
            "password": "correct-password",
            "base_currency": "USD",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_financial_summary_calculates_safe_monthly_capacity(client: TestClient) -> None:
    headers = auth_headers(client)

    client.patch(
        "/api/me/profile",
        headers=headers,
        json={"monthly_available_amount": "2000"},
    )
    client.post(
        "/api/incomes",
        headers=headers,
        json={
            "amount": "3000",
            "currency": "USD",
            "frequency": "monthly",
            "source": "salary",
        },
    )
    client.post(
        "/api/expenses",
        headers=headers,
        json={
            "amount": "1200",
            "currency": "USD",
            "category": "rent_and_bills",
            "frequency": "monthly",
            "is_mandatory": True,
        },
    )
    client.post(
        "/api/debts",
        headers=headers,
        json={
            "type": "loan",
            "creditor": "Bank",
            "balance": "5000",
            "currency": "USD",
            "min_monthly_payment": "400",
            "status": "active",
        },
    )
    client.put(
        "/api/emergency-fund",
        headers=headers,
        json={
            "target_months": 3,
            "target_amount": "3000",
            "current_amount": "1000",
            "monthly_contribution": "200",
            "currency": "USD",
        },
    )

    response = client.get("/api/financial-summary", headers=headers)

    assert response.status_code == 200
    summary = response.json()
    assert Decimal(summary["total_monthly_income"]) == Decimal("3000")
    assert Decimal(summary["total_monthly_expenses"]) == Decimal("1200")
    assert Decimal(summary["total_monthly_debt_payments"]) == Decimal("400")
    assert Decimal(summary["emergency_fund_monthly_reserve"]) == Decimal("200")
    assert Decimal(summary["calculated_monthly_available_amount"]) == Decimal("1200")
    assert Decimal(summary["effective_monthly_available_amount"]) == Decimal("1200")
    assert "lower value" in " ".join(summary["warnings"])


def test_plan_uses_financial_summary_effective_amount(client: TestClient) -> None:
    headers = auth_headers(client)

    client.patch(
        "/api/me/profile",
        headers=headers,
        json={"monthly_available_amount": "2000"},
    )
    client.post(
        "/api/incomes",
        headers=headers,
        json={"amount": "2000", "currency": "USD", "frequency": "monthly"},
    )
    client.post(
        "/api/expenses",
        headers=headers,
        json={"amount": "800", "currency": "USD", "category": "bills", "frequency": "monthly"},
    )
    client.post(
        "/api/goals",
        headers=headers,
        json={
            "title": "Laptop",
            "target_amount": "2400",
            "current_amount": "0",
            "currency": "USD",
        },
    )

    plan_response = client.get("/api/plan", headers=headers)

    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert Decimal(plan["monthly_available_amount"]) == Decimal("1200")
    assert Decimal(plan["goals"][0]["allocated_first_month"]) == Decimal("1200")


def test_non_base_currency_inputs_are_excluded_until_rates_exist(client: TestClient) -> None:
    headers = auth_headers(client)

    client.post(
        "/api/incomes",
        headers=headers,
        json={"amount": "3000", "currency": "USD", "frequency": "monthly"},
    )
    client.post(
        "/api/expenses",
        headers=headers,
        json={"amount": "1000", "currency": "EUR", "category": "rent", "frequency": "monthly"},
    )

    summary = client.get("/api/financial-summary", headers=headers).json()

    assert Decimal(summary["total_monthly_income"]) == Decimal("3000")
    assert Decimal(summary["total_monthly_expenses"]) == Decimal("0")
    assert summary["warnings"]


def test_update_and_delete_financial_inputs_recalculate_summary(client: TestClient) -> None:
    headers = auth_headers(client)

    income = client.post(
        "/api/incomes",
        headers=headers,
        json={"amount": "3000", "currency": "USD", "frequency": "monthly"},
    ).json()
    expense = client.post(
        "/api/expenses",
        headers=headers,
        json={"amount": "1000", "currency": "USD", "category": "rent", "frequency": "monthly"},
    ).json()
    debt = client.post(
        "/api/debts",
        headers=headers,
        json={
            "type": "credit_card",
            "balance": "1000",
            "currency": "USD",
            "min_monthly_payment": "100",
            "status": "active",
        },
    ).json()

    update_expense_response = client.patch(
        f"/api/expenses/{expense['id']}",
        headers=headers,
        json={"amount": "1200"},
    )
    assert update_expense_response.status_code == 200

    update_debt_response = client.patch(
        f"/api/debts/{debt['id']}",
        headers=headers,
        json={"status": "paid"},
    )
    assert update_debt_response.status_code == 200

    summary = client.get("/api/financial-summary", headers=headers).json()
    assert Decimal(summary["total_monthly_income"]) == Decimal("3000")
    assert Decimal(summary["total_monthly_expenses"]) == Decimal("1200")
    assert Decimal(summary["total_monthly_debt_payments"]) == Decimal("0")
    assert Decimal(summary["calculated_monthly_available_amount"]) == Decimal("1800")

    delete_income_response = client.delete(f"/api/incomes/{income['id']}", headers=headers)
    assert delete_income_response.status_code == 204

    summary_after_delete = client.get("/api/financial-summary", headers=headers).json()
    assert Decimal(summary_after_delete["total_monthly_income"]) == Decimal("0")
    assert Decimal(summary_after_delete["calculated_monthly_available_amount"]) == Decimal("0")

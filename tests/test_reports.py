from decimal import Decimal

from fastapi.testclient import TestClient


def test_monthly_report_aggregates_goal_contributions(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={
            "title": "Vacation",
            "target_amount": "1500",
            "current_amount": "100",
            "currency": "USD",
        },
    ).json()["id"]

    client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"type": "add", "amount": "250", "source": "salary", "occurred_at": "2026-07-10"},
    )
    client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"type": "subtract", "amount": "50", "source": "correction", "occurred_at": "2026-07-12"},
    )
    client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"type": "add", "amount": "999", "source": "outside", "occurred_at": "2026-08-01"},
    )

    response = client.get("/api/reports/monthly?year=2026&month=7")

    assert response.status_code == 200
    report = response.json()
    assert report["period_start"] == "2026-07-01"
    assert report["period_end"] == "2026-08-01"
    assert Decimal(report["total_added"]) == Decimal("250")
    assert Decimal(report["total_removed"]) == Decimal("50")
    assert Decimal(report["net_saved"]) == Decimal("200")
    assert report["contributions_count"] == 2
    assert report["goal_reports"][0]["title"] == "Vacation"
    assert Decimal(report["goal_reports"][0]["net_amount"]) == Decimal("200")
    assert report["plan_recommendations"]


def test_monthly_report_ignores_reversed_contributions(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={"title": "Laptop", "target_amount": "1200", "currency": "USD"},
    ).json()["id"]
    contribution_id = client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"type": "add", "amount": "300", "occurred_at": "2026-07-10"},
    ).json()["id"]
    client.post(f"/api/contributions/{contribution_id}/reverse")

    report = client.get("/api/reports/monthly?year=2026&month=7").json()

    assert Decimal(report["net_saved"]) == Decimal("0")
    assert report["reversed_contributions_count"] == 1
    assert report["goal_reports"] == []


def test_monthly_report_validates_period(client: TestClient) -> None:
    invalid_month = client.get("/api/reports/monthly?year=2026&month=13")
    invalid_year = client.get("/api/reports/monthly?year=1800&month=1")

    assert invalid_month.status_code == 400
    assert invalid_year.status_code == 400

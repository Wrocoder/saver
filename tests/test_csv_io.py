import csv
import io
from decimal import Decimal

from fastapi.testclient import TestClient


def test_export_goals_csv_contains_user_goals(client: TestClient) -> None:
    client.post(
        "/api/goals",
        json={
            "title": "Laptop",
            "category": "work",
            "target_amount": "1500",
            "current_amount": "250",
            "currency": "USD",
            "desired_date": "2026-12-31",
        },
    )

    response = client.get("/api/export/goals.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["title"] == "Laptop"
    assert Decimal(rows[0]["target_amount"]) == Decimal("1500.0000")
    assert rows[0]["desired_date"] == "2026-12-31"


def test_export_contributions_csv_contains_goal_operations(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={"title": "Trip", "target_amount": "900", "currency": "USD"},
    ).json()["id"]
    client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"amount": "100", "currency": "USD", "source": "salary"},
    )

    response = client.get("/api/export/contributions.csv")

    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["goal_id"] == goal_id
    assert rows[0]["goal_title"] == "Trip"
    assert rows[0]["source"] == "salary"
    assert Decimal(rows[0]["amount"]) == Decimal("100.0000")


def test_export_contributions_csv_filters_by_period(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={"title": "Trip", "target_amount": "900", "currency": "USD"},
    ).json()["id"]
    client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"amount": "100", "currency": "USD", "source": "june", "occurred_at": "2026-06-30"},
    )
    client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"amount": "200", "currency": "USD", "source": "july", "occurred_at": "2026-07-15"},
    )
    client.post(
        f"/api/goals/{goal_id}/contributions",
        json={"amount": "300", "currency": "USD", "source": "august", "occurred_at": "2026-08-01"},
    )

    response = client.get("/api/export/contributions.csv?from_date=2026-07-01&to_date=2026-07-31")

    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["source"] == "july"
    assert rows[0]["occurred_at"] == "2026-07-15"


def test_export_contributions_csv_rejects_invalid_period(client: TestClient) -> None:
    response = client.get("/api/export/contributions.csv?from_date=2026-08-01&to_date=2026-07-01")

    assert response.status_code == 400
    assert response.json()["detail"] == "from_date must be earlier than or equal to to_date"


def test_goals_import_template_csv_contains_importable_columns(client: TestClient) -> None:
    response = client.get("/api/import/goals-template.csv")

    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows
    assert "title" in rows[0]
    assert "target_amount" in rows[0]
    assert "created_at" not in rows[0]
    assert rows[0]["title"] == "Emergency fund"


def test_contributions_import_template_csv_contains_importable_columns(client: TestClient) -> None:
    response = client.get("/api/import/contributions-template.csv")

    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows
    assert "goal_id" in rows[0]
    assert "goal_title" in rows[0]
    assert "amount" in rows[0]
    assert "created_at" not in rows[0]
    assert rows[0]["type"] == "add"


def test_import_goals_csv_creates_valid_rows_and_reports_errors(client: TestClient) -> None:
    csv_text = "\n".join(
        [
            "title,category,target_amount,currency,current_amount,desired_date,priority,deadline_type",
            "Emergency fund,safety,3000,USD,500,2026-11-30,1,hard",
            "Bad row,shopping,not-a-number,USD,0,,2,flexible",
            "",
        ]
    )

    response = client.post("/api/import/goals.csv", json={"csv_text": csv_text})

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 1
    assert payload["skipped_count"] == 1
    assert len(payload["errors"]) == 1
    assert "target_amount must be a decimal number" in payload["errors"][0]
    assert payload["error_details"] == [
        {
            "row_number": 3,
            "field": "target_amount",
            "value": "not-a-number",
            "message": "target_amount must be a decimal number",
        }
    ]
    assert payload["created_goals"][0]["title"] == "Emergency fund"

    goals = client.get("/api/goals").json()
    assert len(goals) == 1
    assert goals[0]["title"] == "Emergency fund"


def test_import_contributions_csv_creates_historical_operations(client: TestClient) -> None:
    goal_id = client.post(
        "/api/goals",
        json={
            "title": "Vacation",
            "target_amount": "1200",
            "current_amount": "100",
            "currency": "USD",
        },
    ).json()["id"]
    csv_text = "\n".join(
        [
            "goal_id,goal_title,type,amount,currency,source,comment,occurred_at",
            f"{goal_id},,add,250,USD,bonus,summer bonus,2026-07-10",
            ",Vacation,subtract,50,USD,correction,bank fee,2026-07-11",
            "missing,,add,not-a-number,USD,bad,bad row,2026-07-12",
        ]
    )

    response = client.post("/api/import/contributions.csv", json={"csv_text": csv_text})

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 2
    assert payload["skipped_count"] == 1
    assert len(payload["errors"]) == 1
    assert payload["error_details"] == [
        {
            "row_number": 4,
            "field": "goal_id",
            "value": "missing",
            "message": "goal_id does not match an active goal",
        }
    ]
    assert payload["created_contributions"][0]["source"] == "bonus"
    assert payload["created_contributions"][1]["type"] == "subtract"

    goal = client.get(f"/api/goals/{goal_id}").json()
    assert Decimal(goal["current_amount"]) == Decimal("300")

    contributions = client.get(f"/api/goals/{goal_id}/contributions").json()
    assert len(contributions) == 2
    assert {item["occurred_at"] for item in contributions} == {"2026-07-10", "2026-07-11"}

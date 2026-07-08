import csv
import io
from decimal import Decimal

from fastapi.testclient import TestClient


def test_authenticated_goal_contribution_and_csv_roundtrip_smoke(client: TestClient) -> None:
    auth_response = client.post(
        "/api/auth/register",
        json={
            "email": "e2e-smoke@example.com",
            "password": "correct-password",
            "name": "E2E Smoke",
            "base_currency": "USD",
        },
    )
    assert auth_response.status_code == 201
    headers = {"Authorization": f"Bearer {auth_response.json()['access_token']}"}

    goal_response = client.post(
        "/api/goals",
        headers=headers,
        json={
            "title": "Emergency fund",
            "target_amount": "3000",
            "current_amount": "500",
            "currency": "USD",
            "desired_date": "2026-12-31",
            "priority": 1,
        },
    )
    assert goal_response.status_code == 201
    emergency_goal_id = goal_response.json()["id"]

    contribution_response = client.post(
        f"/api/goals/{emergency_goal_id}/contributions",
        headers=headers,
        json={
            "amount": "250",
            "currency": "USD",
            "source": "salary",
            "comment": "first monthly transfer",
            "occurred_at": "2026-07-10",
        },
    )
    assert contribution_response.status_code == 201

    goals_export = client.get("/api/export/goals.csv", headers=headers)
    assert goals_export.status_code == 200
    goal_rows = list(csv.DictReader(io.StringIO(goals_export.text)))
    assert [row["title"] for row in goal_rows] == ["Emergency fund"]
    assert Decimal(goal_rows[0]["current_amount"]) == Decimal("750.0000")

    contributions_export = client.get("/api/export/contributions.csv", headers=headers)
    assert contributions_export.status_code == 200
    contribution_rows = list(csv.DictReader(io.StringIO(contributions_export.text)))
    assert len(contribution_rows) == 1
    assert contribution_rows[0]["goal_id"] == emergency_goal_id
    assert contribution_rows[0]["source"] == "salary"

    imported_goals_csv = "\n".join(
        [
            "title,category,target_amount,currency,current_amount,desired_date,priority,deadline_type",
            "Laptop,work,1800,USD,200,2027-01-31,2,flexible",
            "",
        ]
    )
    import_goals_response = client.post(
        "/api/import/goals.csv",
        headers=headers,
        json={"csv_text": imported_goals_csv},
    )
    assert import_goals_response.status_code == 200
    imported_goal_payload = import_goals_response.json()
    assert imported_goal_payload["created_count"] == 1
    assert imported_goal_payload["skipped_count"] == 0
    laptop_goal_id = imported_goal_payload["created_goals"][0]["id"]

    imported_contributions_csv = "\n".join(
        [
            "goal_id,goal_title,type,amount,currency,source,comment,occurred_at",
            ",Laptop,add,150,USD,bonus,imported historical contribution,2026-07-11",
            "",
        ]
    )
    import_contributions_response = client.post(
        "/api/import/contributions.csv",
        headers=headers,
        json={"csv_text": imported_contributions_csv},
    )
    assert import_contributions_response.status_code == 200
    imported_contribution_payload = import_contributions_response.json()
    assert imported_contribution_payload["created_count"] == 1
    assert imported_contribution_payload["skipped_count"] == 0

    goals_response = client.get("/api/goals", headers=headers)
    assert goals_response.status_code == 200
    goals_by_title = {goal["title"]: goal for goal in goals_response.json()}
    assert set(goals_by_title) == {"Emergency fund", "Laptop"}
    assert Decimal(goals_by_title["Emergency fund"]["current_amount"]) == Decimal("750.0000")
    assert Decimal(goals_by_title["Laptop"]["current_amount"]) == Decimal("350.0000")

    laptop_contributions = client.get(f"/api/goals/{laptop_goal_id}/contributions", headers=headers)
    assert laptop_contributions.status_code == 200
    assert laptop_contributions.json()[0]["source"] == "bonus"

    final_contributions_export = client.get("/api/export/contributions.csv", headers=headers)
    assert final_contributions_export.status_code == 200
    final_contribution_rows = list(csv.DictReader(io.StringIO(final_contributions_export.text)))
    assert {row["source"] for row in final_contribution_rows} == {"salary", "bonus"}

    plan_response = client.get("/api/plan", headers=headers)
    assert plan_response.status_code == 200
    assert [goal["title"] for goal in plan_response.json()["goals"]] == ["Emergency fund", "Laptop"]

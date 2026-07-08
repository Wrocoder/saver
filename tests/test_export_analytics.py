from fastapi.testclient import TestClient


def test_record_and_list_product_event(client: TestClient) -> None:
    event_response = client.post(
        "/api/analytics/events",
        json={
            "name": "goal_created",
            "source": "web",
            "properties": {"currency": "USD", "count": 1},
        },
    )

    assert event_response.status_code == 201
    event = event_response.json()
    assert event["name"] == "goal_created"
    assert event["properties"] == {"currency": "USD", "count": 1}

    list_response = client.get("/api/analytics/events")
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "goal_created"


def test_analytics_summary_counts_mvp_events(client: TestClient) -> None:
    for name in [
        "goal_created",
        "goal_created",
        "contribution_added",
        "scenario_run",
        "csv_goals_imported",
    ]:
        response = client.post(
            "/api/analytics/events",
            json={"name": name, "source": "web", "properties": {}},
        )
        assert response.status_code == 201

    summary_response = client.get("/api/analytics/summary")

    assert summary_response.status_code == 200
    payload = summary_response.json()
    assert payload["total_events"] == 5
    assert payload["events_last_7_days"] == 5
    assert payload["events_last_30_days"] == 5
    assert payload["active_days_last_30"] == 1
    assert payload["key_metrics"]["goals_created"] == 2
    assert payload["key_metrics"]["contributions_added"] == 1
    assert payload["key_metrics"]["scenarios_run"] == 1
    assert payload["key_metrics"]["csv_imports"] == 1
    assert payload["event_counts"][0] == {"name": "goal_created", "count": 2}
    assert len(payload["recent_events"]) == 5


def test_export_user_data_includes_financial_records_without_auth_secrets(client: TestClient) -> None:
    auth_response = client.post(
        "/api/auth/register",
        json={
            "email": "export@example.com",
            "password": "long-password",
            "name": "Export User",
            "base_currency": "USD",
        },
    )
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    goal_response = client.post(
        "/api/goals",
        headers=headers,
        json={
            "title": "Vacation",
            "target_amount": "1500",
            "current_amount": "200",
            "currency": "USD",
        },
    )
    goal_id = goal_response.json()["id"]
    client.post(
        f"/api/goals/{goal_id}/contributions",
        headers=headers,
        json={"type": "add", "amount": "100", "source": "salary"},
    )

    export_response = client.get("/api/export/user-data", headers=headers)

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/json")
    assert export_response.headers["content-disposition"] == 'attachment; filename="money-saver-export.json"'
    payload = export_response.json()
    assert payload["user"]["email"] == "export@example.com"
    assert "password_hash" not in payload["user"]
    assert payload["profile"]["name"] == "Export User"
    assert payload["goals"][0]["title"] == "Vacation"
    assert payload["goal_contributions"][0]["source"] == "salary"
    assert "refresh" not in str(payload).lower()

    events_response = client.get("/api/analytics/events", headers=headers)
    assert any(event["name"] == "data_exported" for event in events_response.json())

from datetime import date, timedelta

from fastapi.testclient import TestClient


def test_generate_notifications_from_plan_and_mark_read(client: TestClient) -> None:
    goal_response = client.post(
        "/api/goals",
        json={
            "title": "Tuition",
            "target_amount": "3000",
            "current_amount": "100",
            "currency": "USD",
            "desired_date": (date.today() + timedelta(days=7)).isoformat(),
            "deadline_type": "hard",
        },
    )
    assert goal_response.status_code == 201

    generate_response = client.post("/api/notifications/generate")

    assert generate_response.status_code == 201
    notifications = generate_response.json()
    assert any(item["severity"] == "warning" for item in notifications)

    duplicate_response = client.post("/api/notifications/generate")
    assert duplicate_response.status_code == 201
    assert duplicate_response.json() == []

    list_response = client.get("/api/notifications?status_filter=unread")
    assert list_response.status_code == 200
    unread = list_response.json()
    assert len(unread) >= 1

    read_response = client.post(f"/api/notifications/{unread[0]['id']}/read")
    assert read_response.status_code == 200
    assert read_response.json()["status"] == "read"

    dismiss_response = client.post(f"/api/notifications/{unread[0]['id']}/dismiss")
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["status"] == "dismissed"


def test_list_notifications_runs_daily_scheduler_once(client: TestClient) -> None:
    goal_response = client.post(
        "/api/goals",
        json={
            "title": "School",
            "target_amount": "4000",
            "current_amount": "100",
            "currency": "USD",
            "desired_date": (date.today() + timedelta(days=10)).isoformat(),
            "deadline_type": "hard",
        },
    )
    assert goal_response.status_code == 201

    first_list_response = client.get("/api/notifications?status_filter=unread")

    assert first_list_response.status_code == 200
    first_notifications = first_list_response.json()
    assert any(item["severity"] == "warning" for item in first_notifications)

    second_list_response = client.get("/api/notifications?status_filter=unread")

    assert second_list_response.status_code == 200
    assert len(second_list_response.json()) == len(first_notifications)


def test_notification_settings_can_disable_generation(client: TestClient) -> None:
    settings_response = client.get("/api/notification-settings")
    assert settings_response.status_code == 200
    assert settings_response.json()["in_app_enabled"] is True
    assert settings_response.json()["in_app_frequency"] == "daily"
    assert settings_response.json()["email_frequency"] == "weekly"

    update_response = client.patch(
        "/api/notification-settings",
        json={
            "in_app_enabled": False,
            "plan_warnings": False,
            "email_enabled": True,
            "in_app_frequency": "weekly",
            "email_frequency": "monthly",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["in_app_enabled"] is False
    assert update_response.json()["plan_warnings"] is False
    assert update_response.json()["email_enabled"] is True
    assert update_response.json()["in_app_frequency"] == "weekly"
    assert update_response.json()["email_frequency"] == "monthly"

    client.post(
        "/api/goals",
        json={
            "title": "Car",
            "target_amount": "5000",
            "current_amount": "0",
            "currency": "USD",
        },
    )

    generate_response = client.post("/api/notifications/generate")
    assert generate_response.status_code == 201
    assert generate_response.json() == []


def test_notification_settings_reject_invalid_frequency(client: TestClient) -> None:
    response = client.patch(
        "/api/notification-settings",
        json={"in_app_frequency": "hourly"},
    )

    assert response.status_code == 422

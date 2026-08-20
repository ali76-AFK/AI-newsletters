from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def create_schedule(enabled: bool) -> int:
    response = client.post(
        "/api/schedules",
        json={
            "email": unique_email("schedule"),
            "name": "Schedule Test",
            "topics": ["ai_news"],
            "sources": ["Spiegel"],
            "weekdays": [0],
            "delivery_time": "18:00",
            "timezone": "Europe/Berlin",
            "enabled": enabled,
        },
    )
    assert response.status_code == 201
    return response.json()["schedule"]["id"]


def test_disabled_schedule_cannot_run_now():
    schedule_id = create_schedule(enabled=False)

    response = client.post(
        f"/api/schedules/{schedule_id}/run-now"
    )

    assert response.status_code == 400
    assert "disabled" in response.json()["detail"]


def test_enabled_schedule_run_now_records_run():
    email = unique_email("scheduled-subscriber")

    subscribe = client.post(
        "/api/subscribers",
        json={
            "email": email,
            "name": "Scheduled Subscriber",
            "topics": ["ai_news"],
        },
    )
    assert subscribe.status_code == 201

    schedule_id = create_schedule(enabled=True)

    response = client.post(
        f"/api/schedules/{schedule_id}/run-now"
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["schedule_id"] == schedule_id
    assert payload["run"]["schedule_id"] == schedule_id
    assert payload["run"]["run_key"].startswith(
        f"manual-{schedule_id}-"
    )
    assert payload["run"]["status"] in {
        "sent",
        "pending_review",
        "skipped_no_new_articles",
    }

    runs = client.get(
        f"/api/schedules/{schedule_id}/runs"
    )
    assert runs.status_code == 200
    assert len(runs.json()["runs"]) == 1

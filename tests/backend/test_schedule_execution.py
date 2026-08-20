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


def test_due_scan_creates_one_run_and_second_scan_is_idempotent():
    from datetime import datetime, timezone

    from backend.app.db import get_session
    from backend.app.schedule_service import scan_due_schedules_once
    from backend.app.models import NewsletterSchedule

    schedule_id = create_schedule(enabled=True)

    with get_session() as db:
        schedule = db.get(NewsletterSchedule, schedule_id)
        assert schedule is not None

        schedule.weekdays_json = "[0]"
        schedule.delivery_time = "18:00"
        schedule.timezone = "Europe/Berlin"

    due_time = datetime(
        2026,
        8,
        17,
        16,
        0,
        tzinfo=timezone.utc,
    )

    with get_session() as db:
        first = scan_due_schedules_once(db, due_time)

    assert first["due_schedule_count"] >= 1

    with get_session() as db:
        second = scan_due_schedules_once(db, due_time)

    matching = [
        item
        for item in second["results"]
        if item["schedule_id"] == schedule_id
    ]

    assert len(matching) == 1
    assert matching[0]["status"] == "already_processed"


def test_due_scan_ignores_not_due_schedule():
    from datetime import datetime, timezone

    from backend.app.db import get_session
    from backend.app.schedule_service import scan_due_schedules_once
    from backend.app.models import NewsletterSchedule

    schedule_id = create_schedule(enabled=True)

    with get_session() as db:
        schedule = db.get(NewsletterSchedule, schedule_id)
        assert schedule is not None

        schedule.weekdays_json = "[0]"
        schedule.delivery_time = "18:00"
        schedule.timezone = "Europe/Berlin"

    not_due_time = datetime(
        2026,
        8,
        17,
        16,
        1,
        tzinfo=timezone.utc,
    )

    with get_session() as db:
        result = scan_due_schedules_once(db, not_due_time)

    matching = [
        item
        for item in result["results"]
        if item["schedule_id"] == schedule_id
    ]

    assert matching == []

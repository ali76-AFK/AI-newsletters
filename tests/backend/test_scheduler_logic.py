from __future__ import annotations

from datetime import datetime, timezone

from backend.app.models import NewsletterSchedule
from backend.app.scheduler_logic import (
    is_schedule_due,
    schedule_delivery_window_key,
    schedule_local_time,
)


def make_schedule(
    *,
    enabled: bool = True,
    weekdays_json: str = "[0]",
    delivery_time: str = "18:00",
    timezone_name: str = "Europe/Berlin",
) -> NewsletterSchedule:
    return NewsletterSchedule(
        id=42,
        email="scheduler-test@example.com",
        topics_json='["ai_news"]',
        sources_json='["Spiegel"]',
        weekdays_json=weekdays_json,
        delivery_time=delivery_time,
        timezone=timezone_name,
        enabled=enabled,
    )


def test_due_when_local_weekday_and_time_match():
    schedule = make_schedule(
        weekdays_json="[0]",
        delivery_time="18:00",
    )

    now_utc = datetime(2026, 8, 17, 16, 0, tzinfo=timezone.utc)

    assert is_schedule_due(schedule, now_utc) is True


def test_not_due_when_minute_does_not_match():
    schedule = make_schedule(
        weekdays_json="[0]",
        delivery_time="18:00",
    )

    now_utc = datetime(2026, 8, 17, 16, 1, tzinfo=timezone.utc)

    assert is_schedule_due(schedule, now_utc) is False


def test_not_due_when_schedule_is_disabled():
    schedule = make_schedule(
        enabled=False,
        weekdays_json="[0]",
        delivery_time="18:00",
    )

    now_utc = datetime(2026, 8, 17, 16, 0, tzinfo=timezone.utc)

    assert is_schedule_due(schedule, now_utc) is False


def test_utc_schedule_uses_utc_time():
    schedule = make_schedule(
        weekdays_json="[0]",
        delivery_time="16:00",
        timezone_name="UTC",
    )

    now_utc = datetime(2026, 8, 17, 16, 0, tzinfo=timezone.utc)

    assert is_schedule_due(schedule, now_utc) is True


def test_delivery_window_key_is_local_timezone_based():
    schedule = make_schedule(
        weekdays_json="[0]",
        delivery_time="18:00",
        timezone_name="Europe/Berlin",
    )

    now_utc = datetime(2026, 8, 17, 16, 0, tzinfo=timezone.utc)

    local_now = schedule_local_time(schedule, now_utc)
    key = schedule_delivery_window_key(schedule, now_utc)

    assert local_now.hour == 18
    assert key == "schedule-42-2026-08-17-1800-Europe/Berlin"

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import NewsletterSchedule


class ScheduleTimezoneError(ValueError):
    pass


def schedule_local_time(
    schedule: NewsletterSchedule,
    now_utc: datetime,
) -> datetime:
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    try:
        timezone_info = ZoneInfo(schedule.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ScheduleTimezoneError(
            f"Unsupported schedule timezone: {schedule.timezone}"
        ) from exc

    return now_utc.astimezone(timezone_info)


def parse_delivery_time(delivery_time: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = delivery_time.split(":")
        hour = int(hour_text)
        minute = int(minute_text)
    except (AttributeError, ValueError) as exc:
        raise ValueError(
            f"Invalid delivery time: {delivery_time!r}"
        ) from exc

    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(
            f"Invalid delivery time: {delivery_time!r}"
        )

    return hour, minute


def schedule_delivery_window_key(
    schedule: NewsletterSchedule,
    now_utc: datetime,
) -> str:
    local_now = schedule_local_time(schedule, now_utc)
    hour, minute = parse_delivery_time(schedule.delivery_time)

    return (
        f"schedule-{schedule.id}-"
        f"{local_now.date().isoformat()}-"
        f"{hour:02d}{minute:02d}-"
        f"{schedule.timezone}"
    )


def is_schedule_due(
    schedule: NewsletterSchedule,
    now_utc: datetime,
) -> bool:
    if not schedule.enabled:
        return False

    local_now = schedule_local_time(schedule, now_utc)
    hour, minute = parse_delivery_time(schedule.delivery_time)

    try:
        weekdays = {
            int(day)
            for day in schedule.weekdays_json.strip("[]").split(",")
            if day.strip()
        }
    except ValueError as exc:
        raise ValueError(
            f"Invalid weekdays configuration for schedule #{schedule.id}"
        ) from exc

    return (
        local_now.weekday() in weekdays
        and local_now.hour == hour
        and local_now.minute == minute
    )

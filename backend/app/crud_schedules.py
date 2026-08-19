from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import NewsletterSchedule
from .schemas import NewsletterScheduleCreate


def _serialize_schedule(schedule: NewsletterSchedule) -> dict:
    return {
        "id": schedule.id,
        "email": schedule.email,
        "name": schedule.name,
        "topics": json.loads(schedule.topics_json),
        "sources": json.loads(schedule.sources_json),
        "weekdays": json.loads(schedule.weekdays_json),
        "delivery_time": schedule.delivery_time,
        "timezone": schedule.timezone,
        "enabled": schedule.enabled,
        "last_run_at": (
            schedule.last_run_at.isoformat()
            if schedule.last_run_at
            else None
        ),
        "next_run_at": (
            schedule.next_run_at.isoformat()
            if schedule.next_run_at
            else None
        ),
        "created_at": schedule.created_at.isoformat(),
        "updated_at": schedule.updated_at.isoformat(),
    }


def create_schedule(
    db: Session,
    payload: NewsletterScheduleCreate,
) -> NewsletterSchedule:
    schedule = NewsletterSchedule(
        email=str(payload.email),
        name=payload.name,
        topics_json=json.dumps(payload.topics),
        sources_json=json.dumps(payload.sources),
        weekdays_json=json.dumps(payload.weekdays),
        delivery_time=payload.delivery_time,
        timezone=payload.timezone,
        enabled=payload.enabled,
    )

    db.add(schedule)
    db.flush()
    return schedule


def list_schedules(db: Session) -> list[NewsletterSchedule]:
    result = db.execute(
        select(NewsletterSchedule).order_by(
            NewsletterSchedule.created_at.desc()
        )
    )
    return list(result.scalars().all())


def get_schedule(
    db: Session,
    schedule_id: int,
) -> NewsletterSchedule | None:
    return db.get(NewsletterSchedule, schedule_id)


def serialize_schedule(schedule: NewsletterSchedule) -> dict:
    return _serialize_schedule(schedule)

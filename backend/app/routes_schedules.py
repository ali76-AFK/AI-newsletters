from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .crud_schedules import (
    create_schedule,
    get_schedule,
    list_schedules,
    serialize_schedule,
)
from .db import get_session
from .schemas import NewsletterScheduleCreate


router = APIRouter(prefix="/api/schedules", tags=["schedules"])


def get_db():
    with get_session() as session:
        yield session


@router.get("")
def get_schedules(db: Session = Depends(get_db)) -> dict:
    schedules = list_schedules(db)

    return {
        "schedules": [
            serialize_schedule(schedule)
            for schedule in schedules
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_newsletter_schedule(
    payload: NewsletterScheduleCreate,
    db: Session = Depends(get_db),
) -> dict:
    schedule = create_schedule(db, payload)

    return {
        "status": "ok",
        "message": "Newsletter delivery schedule saved.",
        "schedule": serialize_schedule(schedule),
    }


@router.post("/{schedule_id}/enable")
def enable_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> dict:
    schedule = get_schedule(db, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} was not found.",
        )

    schedule.enabled = True
    db.flush()

    return {
        "status": "ok",
        "schedule": serialize_schedule(schedule),
    }


@router.post("/{schedule_id}/disable")
def disable_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> dict:
    schedule = get_schedule(db, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} was not found.",
        )

    schedule.enabled = False
    db.flush()

    return {
        "status": "ok",
        "schedule": serialize_schedule(schedule),
    }

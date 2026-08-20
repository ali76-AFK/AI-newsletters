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
from .models import ScheduleRun
from .schedule_service import (
    ScheduleExecutionError,
    run_schedule_now,
)
from .schemas import NewsletterScheduleCreate


router = APIRouter(prefix="/api/schedules", tags=["schedules"])


def get_db():
    with get_session() as session:
        yield session


def serialize_run(run: ScheduleRun) -> dict:
    return {
        "id": run.id,
        "schedule_id": run.schedule_id,
        "run_key": run.run_key,
        "status": run.status,
        "newsletter_id": run.newsletter_id,
        "message": run.message,
        "started_at": run.started_at.isoformat(),
        "completed_at": (
            run.completed_at.isoformat()
            if run.completed_at
            else None
        ),
    }


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


@router.post("/{schedule_id}/run-now")
def run_schedule_immediately(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> dict:
    schedule = get_schedule(db, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} was not found.",
        )

    try:
        return run_schedule_now(db, schedule)
    except ScheduleExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{schedule_id}/runs")
def get_schedule_runs(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> dict:
    schedule = get_schedule(db, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} was not found.",
        )

    runs = (
        db.query(ScheduleRun)
        .filter(ScheduleRun.schedule_id == schedule_id)
        .order_by(ScheduleRun.started_at.desc())
        .all()
    )

    return {
        "schedule_id": schedule_id,
        "runs": [serialize_run(run) for run in runs],
    }


@router.post("/scan-due")
def scan_due_schedules(
    db: Session = Depends(get_db),
) -> dict:
    from .schedule_service import scan_due_schedules_once

    return scan_due_schedules_once(db)

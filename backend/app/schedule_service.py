from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from .ai_newsletter_service import AIServiceError, classify_newsletter_text
from .crud_newsletters import (
    create_newsletter,
    create_workflow_execution_for_newsletter,
)
from .models import Newsletter, NewsletterSchedule, ScheduleRun
from .news_ingestion import NewsArticle, get_articles
from .routes_workflows import run_newsletter_workflow
from .scheduler_logic import (
    is_schedule_due,
    schedule_delivery_window_key,
)
from .schemas import NewsletterCreate


REVIEW_REQUIRED_RISK_LEVELS = {"high", "critical"}


class ScheduleExecutionError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _schedule_values(
    schedule: NewsletterSchedule,
) -> tuple[list[str], list[str]]:
    try:
        topics = json.loads(schedule.topics_json)
        sources = json.loads(schedule.sources_json)
    except json.JSONDecodeError as exc:
        raise ScheduleExecutionError(
            f"Schedule #{schedule.id} has invalid JSON configuration."
        ) from exc

    if not isinstance(topics, list) or not topics:
        raise ScheduleExecutionError(
            f"Schedule #{schedule.id} has no configured topics."
        )

    if not isinstance(sources, list) or not sources:
        raise ScheduleExecutionError(
            f"Schedule #{schedule.id} has no configured sources."
        )

    return topics, sources


def _article_already_processed(
    db: Session,
    article: NewsArticle,
) -> bool:
    existing = (
        db.query(Newsletter)
        .filter(
            Newsletter.source == article.source,
            Newsletter.source_external_id == article.external_id,
        )
        .first()
    )

    if existing is not None:
        return True

    return (
        db.query(Newsletter)
        .filter(Newsletter.content_hash == article.content_hash)
        .first()
        is not None
    )


def _first_unseen_article(
    db: Session,
    sources: list[str],
    topics: list[str],
) -> NewsArticle | None:
    for source in sources:
        for topic in topics:
            for article in get_articles(
                source=source,
                topic=topic,
            ):
                if not _article_already_processed(db, article):
                    return article

    return None


def _serialize_run(run: ScheduleRun) -> dict:
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


def _existing_run_for_key(
    db: Session,
    run_key: str,
) -> ScheduleRun | None:
    return (
        db.query(ScheduleRun)
        .filter(ScheduleRun.run_key == run_key)
        .first()
    )


def _create_run(
    db: Session,
    schedule: NewsletterSchedule,
    run_key: str,
    message: str,
) -> ScheduleRun:
    run = ScheduleRun(
        schedule_id=schedule.id,
        run_key=run_key,
        status="running",
        message=message,
    )
    db.add(run)
    db.flush()
    return run


def _run_schedule(
    db: Session,
    schedule: NewsletterSchedule,
    run_key: str,
    now_utc: datetime,
    started_message: str,
) -> dict:
    run = _create_run(
        db,
        schedule,
        run_key,
        started_message,
    )

    try:
        topics, sources = _schedule_values(schedule)
        article = _first_unseen_article(db, sources, topics)

        if article is None:
            run.status = "skipped_no_relevant_articles"
            run.message = (
                "No unseen relevant articles are available for this "
                "schedule's configured sources and topics."
            )
            run.completed_at = _utc_now()
            schedule.last_run_at = now_utc
            db.flush()

            return {
                "status": run.status,
                "schedule_id": schedule.id,
                "run": _serialize_run(run),
                "newsletter": None,
            }

        payload = NewsletterCreate(
            title=article.title,
            topic=article.topic,
            body=article.body,
            source=article.source,
            source_external_id=article.external_id,
            source_url=article.url,
            content_hash=article.content_hash,
        )

        newsletter = create_newsletter(db, payload)
        create_workflow_execution_for_newsletter(db, newsletter)

        try:
            classification = classify_newsletter_text(
                newsletter.title,
                newsletter.body,
            )
        except AIServiceError as exc:
            raise ScheduleExecutionError(
                f"Classification failed: {exc}"
            ) from exc

        newsletter.risk_level = classification["risk_level"]
        newsletter.risk_reason = classification["reason"]
        run.newsletter_id = newsletter.id
        schedule.last_run_at = now_utc

        if newsletter.risk_level in REVIEW_REQUIRED_RISK_LEVELS:
            newsletter.status = "pending_review"
            newsletter.approved = False
            run.status = "pending_review"
            run.message = (
                f"Newsletter #{newsletter.id} requires human review: "
                f"{newsletter.risk_reason}"
            )
            run.completed_at = _utc_now()
            db.flush()

            return {
                "status": run.status,
                "schedule_id": schedule.id,
                "run": _serialize_run(run),
                "newsletter": {
                    "id": newsletter.id,
                    "title": newsletter.title,
                    "risk_level": newsletter.risk_level,
                    "approved": newsletter.approved,
                    "status": newsletter.status,
                },
            }

        newsletter.status = "approved"
        newsletter.approved = True
        db.flush()

        workflow_result = run_newsletter_workflow(
            newsletter.id,
            db=db,
        )

        run.status = "sent"
        run.message = (
            f"Newsletter #{newsletter.id} was sent through "
            "the bounded schedule workflow."
        )
        run.completed_at = _utc_now()
        db.flush()

        return {
            "status": run.status,
            "schedule_id": schedule.id,
            "run": _serialize_run(run),
            "newsletter": {
                "id": newsletter.id,
                "title": newsletter.title,
                "risk_level": newsletter.risk_level,
                "approved": newsletter.approved,
                "status": newsletter.status,
            },
            "workflow_result": workflow_result,
        }

    except Exception as exc:
        run.status = "failed"
        run.message = str(exc)
        run.completed_at = _utc_now()
        db.flush()
        raise


def run_schedule_now(
    db: Session,
    schedule: NewsletterSchedule,
) -> dict:
    if not schedule.enabled:
        raise ScheduleExecutionError(
            f"Schedule #{schedule.id} is disabled."
        )

    run_key = f"manual-{schedule.id}-{uuid4().hex}"

    return _run_schedule(
        db=db,
        schedule=schedule,
        run_key=run_key,
        now_utc=_utc_now(),
        started_message="Manual schedule execution started.",
    )


def scan_due_schedules_once(
    db: Session,
    now_utc: datetime | None = None,
) -> dict:
    if now_utc is None:
        now_utc = _utc_now()

    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    schedules = (
        db.query(NewsletterSchedule)
        .filter(NewsletterSchedule.enabled.is_(True))
        .order_by(NewsletterSchedule.id.asc())
        .all()
    )

    results: list[dict] = []

    for schedule in schedules:
        if not is_schedule_due(schedule, now_utc):
            continue

        run_key = schedule_delivery_window_key(schedule, now_utc)
        existing_run = _existing_run_for_key(db, run_key)

        if existing_run is not None:
            results.append(
                {
                    "status": "already_processed",
                    "schedule_id": schedule.id,
                    "run": _serialize_run(existing_run),
                }
            )
            continue

        try:
            result = _run_schedule(
                db=db,
                schedule=schedule,
                run_key=run_key,
                now_utc=now_utc,
                started_message="Scheduled delivery window started.",
            )
        except ScheduleExecutionError as exc:
            results.append(
                {
                    "status": "failed",
                    "schedule_id": schedule.id,
                    "message": str(exc),
                }
            )
            continue

        results.append(result)

    return {
        "scanned_at": now_utc.isoformat(),
        "due_schedule_count": len(results),
        "results": results,
    }

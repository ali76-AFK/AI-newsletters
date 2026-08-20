from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from .ai_newsletter_service import AIServiceError, classify_newsletter_text
from .crud_newsletters import (
    create_newsletter,
    create_workflow_execution_for_newsletter,
)
from .models import Newsletter, NewsletterSchedule, ScheduleRun
from .news_ingestion import NewsArticle, get_stub_articles
from .routes_workflows import run_newsletter_workflow
from .schemas import NewsletterCreate


REVIEW_REQUIRED_RISK_LEVELS = {"high", "critical"}


class ScheduleExecutionError(Exception):
    pass


def _schedule_values(schedule: NewsletterSchedule) -> tuple[list[str], list[str]]:
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
            for article in get_stub_articles(
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


def run_schedule_now(
    db: Session,
    schedule: NewsletterSchedule,
) -> dict:
    if not schedule.enabled:
        raise ScheduleExecutionError(
            f"Schedule #{schedule.id} is disabled."
        )

    run_key = f"manual-{schedule.id}-{uuid4().hex}"

    run = ScheduleRun(
        schedule_id=schedule.id,
        run_key=run_key,
        status="running",
        message="Manual schedule execution started.",
    )
    db.add(run)
    db.flush()

    now = datetime.utcnow()

    try:
        topics, sources = _schedule_values(schedule)
        article = _first_unseen_article(db, sources, topics)

        if article is None:
            run.status = "skipped_no_new_articles"
            run.message = (
                "No unseen local articles are available for this "
                "schedule's configured sources and topics."
            )
            run.completed_at = now
            schedule.last_run_at = now
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
        schedule.last_run_at = now

        if newsletter.risk_level in REVIEW_REQUIRED_RISK_LEVELS:
            newsletter.status = "pending_review"
            newsletter.approved = False

            run.status = "pending_review"
            run.message = (
                f"Newsletter #{newsletter.id} requires human review: "
                f"{newsletter.risk_reason}"
            )
            run.completed_at = datetime.utcnow()
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
        run.completed_at = datetime.utcnow()
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
        run.completed_at = datetime.utcnow()
        db.flush()
        raise

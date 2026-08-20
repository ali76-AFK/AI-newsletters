from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .ai_newsletter_service import AIServiceError, classify_newsletter_text
from .crud_automation import (
    MAX_AUTOMATED_SENDS_PER_DAY,
    can_run_automation_tick,
    get_or_create_automation_state,
    halt_automation_for_review,
    record_automated_send,
    start_automation as start_automation_state,
    stop_automation as stop_automation_state,
)
from .crud_newsletters import (
    create_newsletter,
    create_workflow_execution_for_newsletter,
)
from .crud_subscribers import ALLOWED_TOPICS
from .db import get_session
from .models import Newsletter
from .news_ingestion import (
    NewsArticle,
    NewsIngestionError,
    build_stub_newsletter_content,
    get_articles,
)
from .routes_workflows import run_newsletter_workflow
from .schemas import NewsletterCreate


router = APIRouter(prefix="/api/automation", tags=["automation"])


def get_db():
    with get_session() as session:
        yield session


class AutomationCreateRequest(BaseModel):
    source: str
    topic: str


def _automation_state_response(state) -> dict:
    if state.halted_for_review:
        status_label = "halted_for_review"
    elif state.enabled:
        status_label = "running"
    else:
        status_label = "stopped"

    return {
        "status": status_label,
        "enabled": state.enabled,
        "halted_for_review": state.halted_for_review,
        "halt_reason": state.halt_reason,
        "last_run_at": state.last_run_at.isoformat() if state.last_run_at else None,
        "last_newsletter_id": state.last_newsletter_id,
        "daily_send_count": state.daily_send_count,
        "daily_send_limit": MAX_AUTOMATED_SENDS_PER_DAY,
    }


def _article_already_processed(db: Session, article: NewsArticle) -> bool:
    """
    Return True if the article identity or its content hash already exists.

    External IDs are the primary deduplication key. Content hash catches
    identical text under a changed external ID.
    """
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

    if article.content_hash:
        same_content = (
            db.query(Newsletter)
            .filter(Newsletter.content_hash == article.content_hash)
            .first()
        )
        if same_content is not None:
            return True

    return False


def _find_next_unseen_article(
    db: Session,
    source: str,
    topic: str,
) -> NewsArticle | None:
    for article in get_articles(source=source, topic=topic):
        if not _article_already_processed(db, article):
            return article

    return None


def _create_newsletter_from_content(
    content: dict[str, str],
    topic: str,
    db: Session,
) -> dict:
    newsletter_payload = NewsletterCreate(
        title=content["title"],
        topic=topic,
        body=content["body"],
        source=content.get("source"),
        source_external_id=content.get("source_external_id"),
        source_url=content.get("source_url"),
        content_hash=content.get("content_hash"),
    )

    newsletter = create_newsletter(db, newsletter_payload)
    create_workflow_execution_for_newsletter(db, newsletter)

    try:
        classification = classify_newsletter_text(
            newsletter.title,
            newsletter.body,
        )
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {exc}",
        ) from exc

    newsletter.risk_level = classification["risk_level"]
    newsletter.risk_reason = classification["reason"]
    db.flush()

    auto_approved = newsletter.risk_level in ("low", "medium")

    if auto_approved:
        newsletter.approved = True
        db.flush()
        workflow_result = run_newsletter_workflow(newsletter.id, db=db)
    else:
        workflow_result = {
            "status": "blocked_for_review",
            "reason": (
                f"Newsletter risk level '{newsletter.risk_level}' "
                "requires human review before sending."
            ),
        }

    return {
        "newsletter_id": newsletter.id,
        "title": newsletter.title,
        "topic": newsletter.topic,
        "source": newsletter.source,
        "source_external_id": newsletter.source_external_id,
        "source_url": newsletter.source_url,
        "content_hash": newsletter.content_hash,
        "risk_level": newsletter.risk_level,
        "risk_reason": newsletter.risk_reason,
        "auto_approved": auto_approved,
        "workflow_result": workflow_result,
    }


def _create_newsletter_from_source(
    source: str,
    topic: str,
    db: Session,
) -> dict:
    """
    Create one newsletter using the first local article for a source/topic.

    This preserves the existing manual source endpoint. The /tick endpoint
    below chooses the next unseen article instead.
    """
    if topic not in ALLOWED_TOPICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid topic '{topic}'. Allowed topics: {ALLOWED_TOPICS}",
        )

    try:
        content = build_stub_newsletter_content(source, topic)
    except NewsIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    article = NewsArticle(
        source=content["source"],
        external_id=content["source_external_id"],
        url=content["source_url"],
        published_at=content["published_at"],
        topic=topic,
        title=content["title"],
        body=content["body"],
    )

    if _article_already_processed(db, article):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Duplicate prevention: this article identity or content "
                "was already processed."
            ),
        )

    return _create_newsletter_from_content(content, topic, db)


@router.post(
    "/create_newsletter_from_source",
    status_code=status.HTTP_200_OK,
)
def create_newsletter_from_source(
    payload: AutomationCreateRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Create and run one manual newsletter automation cycle."""
    return _create_newsletter_from_source(
        source=payload.source,
        topic=payload.topic,
        db=db,
    )


@router.get("/status")
def get_automation_status(db: Session = Depends(get_db)) -> dict:
    state = get_or_create_automation_state(db)
    return _automation_state_response(state)


@router.post("/start")
def start_automation(db: Session = Depends(get_db)) -> dict:
    state = start_automation_state(db)
    return _automation_state_response(state)


@router.post("/stop")
def stop_automation(db: Session = Depends(get_db)) -> dict:
    state = stop_automation_state(db)
    return _automation_state_response(state)


@router.post("/tick")
def run_automation_tick(db: Session = Depends(get_db)) -> dict:
    """
    Run one safe cycle using the next unseen local article.

    This endpoint does not schedule itself. A future scheduler may call it
    periodically, but only while the persistent enabled flag is true.
    """
    state = get_or_create_automation_state(db)
    now = datetime.utcnow()

    if state.halted_for_review:
        return {
            "status": "halted_for_review",
            "message": "Automation is paused until a human reviews the alert.",
            "automation": _automation_state_response(state),
        }

    if not state.enabled:
        return {
            "status": "skipped",
            "message": "Automation is stopped. Start it before running a tick.",
            "automation": _automation_state_response(state),
        }

    allowed, reason = can_run_automation_tick(state, now)

    if not allowed:
        state = halt_automation_for_review(
            db,
            reason or "Automation safety limit reached.",
        )
        return {
            "status": "halted_for_review",
            "message": reason,
            "automation": _automation_state_response(state),
        }

    source = "Spiegel"
    topic = "ai_news"

    article = _find_next_unseen_article(db, source=source, topic=topic)

    if article is None:
        return {
            "status": "skipped_no_new_articles",
            "message": (
                "No unseen local articles are available for this source and topic."
            ),
            "automation": _automation_state_response(state),
        }

    content = {
        "title": article.title,
        "body": article.body,
        "source": article.source,
        "source_external_id": article.external_id,
        "source_url": article.url,
        "content_hash": article.content_hash,
        "published_at": article.published_at,
    }

    result = _create_newsletter_from_content(content, topic, db)

    state.last_run_at = now
    state.last_newsletter_id = result["newsletter_id"]

    if result["auto_approved"]:
        record_automated_send(state, now)

    db.flush()

    if result["risk_level"] in ("high", "critical"):
        reason = (
            f"Newsletter #{result['newsletter_id']} from {source} was halted "
            f"for review: {result['risk_reason']}"
        )
        state = halt_automation_for_review(db, reason)

        return {
            "status": "halted_for_review",
            "message": "High-risk newsletter created but not sent.",
            "newsletter": result,
            "automation": _automation_state_response(state),
        }

    return {
        "status": "ok",
        "message": "One automation tick completed using a new article.",
        "newsletter": result,
        "automation": _automation_state_response(state),
    }

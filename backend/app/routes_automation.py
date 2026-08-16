from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from datetime import datetime, timedelta
from sqlalchemy import desc

from .db import get_session
from .news_ingestion import build_stub_newsletter_content, NewsIngestionError
from .crud_newsletters import (
    create_newsletter,
    create_workflow_execution_for_newsletter,
)
from .crud_subscribers import ALLOWED_TOPICS
from .models import Newsletter
from .schemas import NewsletterCreate
from .ai_newsletter_service import classify_newsletter_text, AIServiceError
from .routes_workflows import run_newsletter_workflow
from pydantic import BaseModel

from .crud_automation import (
    AUTOMATION_COOLDOWN_SECONDS,
    MAX_AUTOMATED_SENDS_PER_DAY,
    can_run_automation_tick,
    get_or_create_automation_state,
    halt_automation_for_review,
    record_automated_send,
    start_automation as start_automation_state,
    stop_automation as stop_automation_state,
)

router = APIRouter(prefix="/api/automation", tags=["automation"])


def get_db():
    with get_session() as session:
        yield session


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


def _recent_duplicate_exists(
    db: Session,
    *,
    title: str,
    topic: str,
    now: datetime,
) -> bool:
    """
    Treat an identical title/topic created within 24 hours as a duplicate.

    Later, replace title matching with a real article URL/hash from the news API.
    """
    cutoff = now - timedelta(hours=30)

    duplicate = (
        db.query(Newsletter)
        .filter(
            Newsletter.title == title,
            Newsletter.topic == topic,
            Newsletter.created_at >= cutoff,
        )
        .order_by(desc(Newsletter.created_at))
        .first()
    )

    return duplicate is not None


def _create_newsletter_from_source(
    source: str,
    topic: str,
    db: Session,
) -> dict:
    """
    Execute exactly one newsletter cycle.

    The function is used by the existing manual endpoint and later by /tick.
    It does not manage the automation-state flag itself.
    """
    if topic not in ALLOWED_TOPICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid topic '{topic}'. Allowed topics: {ALLOWED_TOPICS}",
        )

    try:
        content = build_stub_newsletter_content(source, topic)
        now = datetime.utcnow()

        if _recent_duplicate_exists(
            db,
            title=content["title"],
            topic=topic,
            now=now,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Duplicate prevention: an identical newsletter title and topic "
                    "already exist from the previous 24 hours."
                ),
            )
    except NewsIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    newsletter_payload = NewsletterCreate(
        title=content["title"],
        topic=topic,
        body=content["body"],
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
        "risk_level": newsletter.risk_level,
        "risk_reason": newsletter.risk_reason,
        "auto_approved": auto_approved,
        "workflow_result": workflow_result,
    }

class AutomationCreateRequest(BaseModel):
    source: str
    topic: str




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
    """Return persistent start/stop/review-halt state."""
    state = get_or_create_automation_state(db)
    return _automation_state_response(state)


@router.post("/start")
def start_automation(db: Session = Depends(get_db)) -> dict:
    """
    Enable scheduled automation.

    This currently changes state only. A future scheduler or /tick endpoint
    will read this flag before it runs an automation cycle.
    """
    state = start_automation_state(db)
    return _automation_state_response(state)


@router.post("/stop")
def stop_automation(db: Session = Depends(get_db)) -> dict:
    """
    Disable scheduled automation.

    This does not delete newsletters or drafts; it prevents future ticks
    from starting new work.
    """
    state = stop_automation_state(db)
    return _automation_state_response(state)



@router.post("/tick")
def run_automation_tick(db: Session = Depends(get_db)) -> dict:
    """
    Run one safe automation cycle.

    This endpoint does not schedule itself. A future cron task or scheduler
    may call it periodically, but only while enabled remains true.
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
        state = halt_automation_for_review(db, reason or "Automation safety limit reached.")
        return {
            "status": "halted_for_review",
            "message": reason,
            "automation": _automation_state_response(state),
        }



    # Fixed demo configuration. Later this comes from saved user settings.
    source = "Spiegel"
    topic = "ai_news"

    try:
        result = _create_newsletter_from_source(
            source=source,
            topic=topic,
            db=db,
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_409_CONFLICT:
            return {
                "status": "skipped_duplicate",
                "message": exc.detail,
                "automation": _automation_state_response(state),
            }
        raise

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
        "message": "One automation tick completed.",
        "newsletter": result,
        "automation": _automation_state_response(state),
    }
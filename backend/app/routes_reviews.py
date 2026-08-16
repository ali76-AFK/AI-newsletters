from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .crud_automation import get_or_create_automation_state
from .db import get_session
from .models import Newsletter
from .routes_workflows import run_newsletter_workflow


router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def get_db():
    with get_session() as session:
        yield session


class ReviewDecisionRequest(BaseModel):
    review_note: str | None = None


def _serialize_newsletter(newsletter: Newsletter) -> dict:
    return {
        "id": newsletter.id,
        "title": newsletter.title,
        "topic": newsletter.topic,
        "body": newsletter.body,
        "status": newsletter.status,
        "risk_level": newsletter.risk_level,
        "risk_reason": newsletter.risk_reason,
        "approved": newsletter.approved,
        "review_decision": newsletter.review_decision,
        "review_note": newsletter.review_note,
        "reviewed_at": (
            newsletter.reviewed_at.isoformat()
            if newsletter.reviewed_at
            else None
        ),
        "created_at": newsletter.created_at.isoformat(),
    }


def _get_pending_review_or_404(db: Session, newsletter_id: int) -> Newsletter:
    newsletter = db.get(Newsletter, newsletter_id)

    if newsletter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Newsletter {newsletter_id} was not found.",
        )

    if newsletter.risk_level not in ("high", "critical"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only high or critical newsletters require this review action.",
        )

    if newsletter.review_decision is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Newsletter already reviewed as '{newsletter.review_decision}'.",
        )

    return newsletter


@router.get("/pending")
def list_pending_reviews(db: Session = Depends(get_db)) -> dict:
    pending = (
        db.query(Newsletter)
        .filter(
            Newsletter.risk_level.in_(("high", "critical")),
            Newsletter.approved.is_(False),
            Newsletter.review_decision.is_(None),
        )
        .order_by(Newsletter.created_at.asc())
        .all()
    )

    return {
        "pending_reviews": [_serialize_newsletter(item) for item in pending],
        "count": len(pending),
    }


@router.post("/newsletters/{newsletter_id}/approve-and-send")
def approve_and_send(
    newsletter_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    newsletter = _get_pending_review_or_404(db, newsletter_id)

    newsletter.approved = True
    newsletter.review_decision = "approved_and_sent"
    newsletter.review_note = payload.review_note
    newsletter.reviewed_at = datetime.utcnow()
    db.flush()

    workflow_result = run_newsletter_workflow(newsletter.id, db=db)

    return {
        "status": "ok",
        "message": f"Newsletter {newsletter.id} was approved and sent.",
        "newsletter": _serialize_newsletter(newsletter),
        "workflow_result": workflow_result,
    }


@router.post("/newsletters/{newsletter_id}/reject")
def reject_newsletter(
    newsletter_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> dict:
    newsletter = _get_pending_review_or_404(db, newsletter_id)

    newsletter.approved = False
    newsletter.review_decision = "rejected"
    newsletter.review_note = payload.review_note
    newsletter.reviewed_at = datetime.utcnow()
    newsletter.status = "rejected"
    db.flush()

    return {
        "status": "ok",
        "message": f"Newsletter {newsletter.id} was rejected and will not be sent.",
        "newsletter": _serialize_newsletter(newsletter),
    }


@router.post("/resume-automation")
def resume_automation(db: Session = Depends(get_db)) -> dict:
    pending_count = (
        db.query(Newsletter)
        .filter(
            Newsletter.risk_level.in_(("high", "critical")),
            Newsletter.approved.is_(False),
            Newsletter.review_decision.is_(None),
        )
        .count()
    )

    if pending_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot resume automation: {pending_count} pending review "
                "item(s) remain."
            ),
        )

    automation = get_or_create_automation_state(db)
    automation.enabled = True
    automation.halted_for_review = False
    automation.halt_reason = None
    db.flush()

    return {
        "status": "ok",
        "message": "Automation resumed after review.",
        "automation": {
            "enabled": automation.enabled,
            "halted_for_review": automation.halted_for_review,
            "halt_reason": automation.halt_reason,
        },
    }

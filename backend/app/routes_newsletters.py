from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_session
from .crud_newsletters import (
    create_basic_draft_for_newsletter,
    create_newsletter,
    create_workflow_execution_for_newsletter,
    list_newsletters,
)
from .crud_subscribers import ALLOWED_TOPICS
from .schemas import (
    NewsletterCreate,
    NewsletterListResponse,
    NewsletterResponse,
)
from .models import Newsletter
from .ai_newsletter_service import classify_newsletter_text, AIServiceError

router = APIRouter(prefix="/api/newsletters", tags=["newsletters"])


def get_db():
    with get_session() as session:
        yield session


@router.get("/topics", response_model=List[str])
def newsletter_topics() -> List[str]:
    return ALLOWED_TOPICS


@router.post(
    "",
    response_model=NewsletterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_newsletter_endpoint(
    payload: NewsletterCreate,
    db: Session = Depends(get_db),
) -> NewsletterResponse:
    if payload.topic not in ALLOWED_TOPICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid topic",
        )

    newsletter = create_newsletter(db, payload)
    create_workflow_execution_for_newsletter(db, newsletter)
    create_basic_draft_for_newsletter(db, newsletter)

    return NewsletterResponse(
        id=newsletter.id,
        title=newsletter.title,
        topic=newsletter.topic,
        status=newsletter.status,
        risk_level=newsletter.risk_level,
        approved=newsletter.approved,
    )


@router.get(
    "",
    response_model=NewsletterListResponse,
)
def list_newsletters_endpoint(
    db: Session = Depends(get_db),
) -> NewsletterListResponse:
    newsletters = list_newsletters(db)
    items: List[NewsletterResponse] = [
        NewsletterResponse(
            id=n.id,
            title=n.title,
            topic=n.topic,
            status=n.status,
            risk_level=n.risk_level,
            approved=n.approved,
        )
        for n in newsletters
    ]
    return NewsletterListResponse(newsletters=items)


@router.post(
    "/{newsletter_id}/classify-and-store",
    status_code=status.HTTP_200_OK,
)
def classify_and_store_newsletter(
    newsletter_id: int,
    db: Session = Depends(get_db),
) -> dict:
    newsletter = db.get(Newsletter, newsletter_id)
    if newsletter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Newsletter not found",
        )

    try:
        result = classify_newsletter_text(newsletter.title, newsletter.body)
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    newsletter.risk_level = result["risk_level"]
    newsletter.risk_reason = result["reason"]
    db.flush()

    return {"classification": result}


@router.post(
    "/{newsletter_id}/approve",
    status_code=status.HTTP_200_OK,
)
def approve_newsletter(
    newsletter_id: int,
    db: Session = Depends(get_db),
) -> dict:
    newsletter = db.get(Newsletter, newsletter_id)
    if newsletter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Newsletter not found",
        )

    # Policy: only low or medium risk can be auto-approved.
    if newsletter.risk_level == "high":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="High-risk newsletters require manual review and cannot be auto-approved.",
        )

    newsletter.approved = True
    db.flush()

    return {"status": "ok", "approved": True}

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .ai_newsletter_service import (
    AIServiceError,
    classify_newsletter_text,
    summarize_newsletter_text,
    refine_newsletter_draft,
)
from .db import get_session
from .models import Newsletter, DraftEmail, Subscriber

router = APIRouter(prefix="/api/ai", tags=["ai"])


def get_db():
    with get_session() as session:
        yield session


@router.post(
    "/newsletters/{newsletter_id}/classify",
    status_code=status.HTTP_200_OK,
)
def ai_classify_newsletter(
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

    return {"classification": result}


@router.post(
    "/newsletters/{newsletter_id}/summarize",
    status_code=status.HTTP_200_OK,
)
def ai_summarize_newsletter(
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
        summary = summarize_newsletter_text(newsletter.title, newsletter.body)
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return {"summary": summary}


@router.post(
    "/drafts/{draft_id}/refine",
    status_code=status.HTTP_200_OK,
)
def ai_refine_draft(
    draft_id: int,
    db: Session = Depends(get_db),
) -> dict:
    draft = db.get(DraftEmail, draft_id)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    subscriber = None
    if draft.subscriber_id:
        subscriber = db.get(Subscriber, draft.subscriber_id)

    name = subscriber.name if subscriber else None

    try:
        result = refine_newsletter_draft(
            base_subject=draft.subject,
            base_body=draft.body,
            subscriber_name=name,
        )
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    # For now, do not auto-save; just return suggestion
    return {"refined": result}

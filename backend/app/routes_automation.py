from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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

router = APIRouter(prefix="/api/automation", tags=["automation"])


def get_db():
    with get_session() as session:
        yield session


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
    source = payload.source
    topic = payload.topic

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

    # ... rest of your existing logic: create newsletter, classify, approve, run workflow, return dict

    payload = NewsletterCreate(
        title=content["title"],
        topic=topic,
        body=content["body"],
    )

    # Create newsletter and workflow execution
    newsletter = create_newsletter(db, payload)
    create_workflow_execution_for_newsletter(db, newsletter)

    # Classify risk
    try:
        cls = classify_newsletter_text(newsletter.title, newsletter.body)
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {exc}",
        ) from exc

    newsletter.risk_level = cls["risk_level"]
    newsletter.risk_reason = cls["reason"]
    db.flush()

    # Auto-approve if low or medium risk
    auto_approved = False
    if newsletter.risk_level in ("low", "medium"):
        newsletter.approved = True
        auto_approved = True
        db.flush()

    # Run workflow
    workflow_result = run_newsletter_workflow(newsletter.id, db=db)

    return {
        "newsletter_id": newsletter.id,
        "title": newsletter.title,
        "topic": newsletter.topic,
        "risk_level": newsletter.risk_level,
        "risk_reason": newsletter.risk_reason,
        "auto_approved": auto_approved,
        "workflow_result": workflow_result,
    }

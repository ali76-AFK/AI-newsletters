from __future__ import annotations

from typing import List
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DraftEmail, Newsletter, WorkflowExecution
from .schemas import NewsletterCreate


def create_newsletter(
    db: Session,
    payload: NewsletterCreate,
) -> Newsletter:
    newsletter = Newsletter(
        title=payload.title,
        topic=payload.topic,
        body=payload.body,
        status="created",
        source=payload.source,
        source_external_id=payload.source_external_id,
        source_url=payload.source_url,
        content_hash=payload.content_hash,
    )
    db.add(newsletter)
    db.flush()
    return newsletter


def create_workflow_execution_for_newsletter(
    db: Session,
    newsletter: Newsletter,
) -> WorkflowExecution:
    corr_id = str(uuid4())
    wf = WorkflowExecution(
        newsletter_id=newsletter.id,
        state="created",
        correlation_id=corr_id,
    )
    db.add(wf)
    db.flush()
    return wf


def create_basic_draft_for_newsletter(
    db: Session,
    newsletter: Newsletter,
) -> DraftEmail:
    subject = newsletter.title
    body = newsletter.body  # deterministic: copy body as-is for now
    draft = DraftEmail(
        newsletter_id=newsletter.id,
        subscriber_id=None,
        subject=subject,
        body=body,
        status="draft",
    )
    db.add(draft)
    db.flush()
    return draft


def list_newsletters(db: Session) -> List[Newsletter]:
    result = db.execute(select(Newsletter).order_by(Newsletter.created_at.desc()))
    return list(result.scalars().all())

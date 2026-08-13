from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DraftEmail, Newsletter, Subscriber, SubscriberTopic, WorkflowExecution


class WorkflowError(Exception):
    """Generic workflow error."""
    pass


def _get_newsletter(db: Session, newsletter_id: int) -> Newsletter:
    stmt = select(Newsletter).where(Newsletter.id == newsletter_id)
    newsletter = db.execute(stmt).scalar_one_or_none()
    if not newsletter:
        raise WorkflowError(f"Newsletter {newsletter_id} not found")
    return newsletter


def _get_workflow_execution(db: Session, newsletter_id: int) -> WorkflowExecution:
    stmt = select(WorkflowExecution).where(
        WorkflowExecution.newsletter_id == newsletter_id,
    ).order_by(WorkflowExecution.started_at.desc())
    wf = db.execute(stmt).scalar_one_or_none()
    if not wf:
        raise WorkflowError(f"No workflow execution found for newsletter {newsletter_id}")
    return wf


def _get_active_subscribers_for_topic(
    db: Session,
    topic: str,
) -> List[Subscriber]:
    stmt = (
        select(Subscriber)
        .join(SubscriberTopic)
        .where(
            Subscriber.is_active.is_(True),
            SubscriberTopic.topic == topic,
        )
        .order_by(Subscriber.created_at.desc())
    )
    result = db.execute(stmt)
    return list(result.scalars().all())


def _create_drafts_for_subscribers(
    db: Session,
    newsletter: Newsletter,
    subscribers: List[Subscriber],
) -> List[DraftEmail]:
    drafts: List[DraftEmail] = []
    for sub in subscribers:
        subject = newsletter.title
        body = f"Hello {sub.name or 'subscriber'},\n\n{newsletter.body}\n\nBest regards,\nYour AI Newsletter"
        draft = DraftEmail(
            newsletter_id=newsletter.id,
            subscriber_id=sub.id,
            subject=subject,
            body=body,
            status="draft",
        )
        db.add(draft)
        drafts.append(draft)

    db.flush()
    return drafts


def run_deterministic_workflow(
    db: Session,
    newsletter_id: int,
) -> dict:
    """
    Deterministic workflow stub:

    1. Load newsletter.
    2. Load latest workflow execution.
    3. Load active subscribers for newsletter.topic.
    4. Create per-subscriber drafts.
    5. Update workflow execution state.
    """
    newsletter = _get_newsletter(db, newsletter_id)
    wf = _get_workflow_execution(db, newsletter_id)
    subscribers = _get_active_subscribers_for_topic(db, newsletter.topic)

    if not subscribers:
        raise WorkflowError("No active subscribers for this topic")

    # Mark workflow as running
    wf.state = "running"
    db.flush()

    drafts = _create_drafts_for_subscribers(db, newsletter, subscribers)

    wf.state = "completed"
    wf.completed_at = datetime.utcnow()
    newsletter.status = "drafting"
    db.flush()

    return {
        "newsletter_id": newsletter.id,
        "workflow_id": wf.id,
        "created_drafts": len(drafts),
        "subscriber_count": len(subscribers),
    }

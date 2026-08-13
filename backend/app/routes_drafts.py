from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session
from .models import DraftEmail, Subscriber


router = APIRouter(prefix="/api/drafts", tags=["drafts"])


def get_db():
    with get_session() as session:
        yield session


@router.get(
    "/newsletter/{newsletter_id}",
    status_code=status.HTTP_200_OK,
)
def list_drafts_for_newsletter(
    newsletter_id: int,
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(DraftEmail, Subscriber)
        .join(Subscriber, DraftEmail.subscriber_id == Subscriber.id, isouter=True)
        .where(DraftEmail.newsletter_id == newsletter_id)
        .order_by(DraftEmail.created_at.desc())
    )
    result = db.execute(stmt)

    drafts: List[dict] = []
    for draft, subscriber in result.all():
        drafts.append(
            {
                "id": draft.id,
                "newsletter_id": draft.newsletter_id,
                "subscriber_id": draft.subscriber_id,
                "subscriber_email": getattr(subscriber, "email", None),
                "status": draft.status,
                "subject": draft.subject,
            },
        )

    if not drafts:
        return {"drafts": []}

    return {"drafts": drafts}

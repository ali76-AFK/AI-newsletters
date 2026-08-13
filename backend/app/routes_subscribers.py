from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_session
from .crud_subscribers import (
    ALLOWED_TOPICS,
    create_or_update_subscriber,
    get_subscribers,
    unsubscribe_by_email,
)
from .schemas import (
    SubscriberCreate,
    SubscriberListResponse,
    SubscriberResponse,
    UnsubscribeRequest,
)

router = APIRouter(prefix="/api/subscribers", tags=["subscribers"])


def get_db():
    with get_session() as session:
        yield session


@router.get(
    "/topics",
    response_model=List[str],
)
def list_topics() -> List[str]:
    return ALLOWED_TOPICS


@router.post(
    "",
    response_model=SubscriberResponse,
    status_code=status.HTTP_201_CREATED,
)
def subscribe(
    payload: SubscriberCreate,
    db: Session = Depends(get_db),
) -> SubscriberResponse:
    subscriber = create_or_update_subscriber(db, payload)
    topics = [t.topic for t in subscriber.topics]
    return SubscriberResponse(
        id=subscriber.id,
        email=subscriber.email,
        name=subscriber.name,
        is_active=subscriber.is_active,
        topics=topics,
    )


@router.get(
    "",
    response_model=SubscriberListResponse,
)
def list_subscribers(
    db: Session = Depends(get_db),
) -> SubscriberListResponse:
    subscribers = get_subscribers(db)
    items: List[SubscriberResponse] = []
    for s in subscribers:
        topics = [t.topic for t in s.topics]
        items.append(
            SubscriberResponse(
                id=s.id,
                email=s.email,
                name=s.name,
                is_active=s.is_active,
                topics=topics,
            ),
        )
    return SubscriberListResponse(subscribers=items)


@router.post(
    "/unsubscribe",
    status_code=status.HTTP_200_OK,
)
def unsubscribe(
    payload: UnsubscribeRequest,
    db: Session = Depends(get_db),
) -> dict:
    ok = unsubscribe_by_email(db, payload.email)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber not found",
        )
    return {"status": "ok"}

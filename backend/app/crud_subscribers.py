from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Subscriber, SubscriberTopic
from .schemas import SubscriberCreate


# For now, define allowed topics as a constant list.
ALLOWED_TOPICS: List[str] = [
    "ai_news",
    "robotics",
    "data_eng",
    "devops",
    "llm_workflows",
]


def create_or_update_subscriber(
    db: Session,
    payload: SubscriberCreate,
) -> Subscriber:
    email_lower = payload.email.lower()
    subscriber = db.execute(
        select(Subscriber).where(Subscriber.email == email_lower),
    ).scalar_one_or_none()

    if subscriber is None:
        subscriber = Subscriber(email=email_lower, name=payload.name)
        db.add(subscriber)
        db.flush()
    else:
        if payload.name:
            subscriber.name = payload.name
        subscriber.is_active = True

    # Clear existing topics and re-add based on payload
    subscriber.topics.clear()

    for t in payload.topics:
        topic = t.strip().lower()
        if topic not in ALLOWED_TOPICS:
            continue
        subscriber.topics.append(SubscriberTopic(topic=topic))

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise

    return subscriber


def get_subscribers(db: Session) -> List[Subscriber]:
    result = db.execute(select(Subscriber).order_by(Subscriber.created_at.desc()))
    return list(result.scalars().all())


def unsubscribe_by_email(db: Session, email: str) -> bool:
    email_lower = email.lower()
    subscriber = db.execute(
        select(Subscriber).where(Subscriber.email == email_lower),
    ).scalar_one_or_none()
    if not subscriber:
        return False
    subscriber.is_active = False
    db.flush()
    return True

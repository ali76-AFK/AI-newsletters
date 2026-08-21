from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Subscriber, SubscriberTopic
from .schemas import SubscriberCreate


ALLOWED_TOPICS: List[str] = [
    "ai_news",
    "robotics",
    "data_eng",
    "devops",
    "llm_workflows",
    "technology_science",
    "business",
    "world_news",
]


def create_or_update_subscriber(
    db: Session,
    payload: SubscriberCreate,
) -> Subscriber:
    email_lower = str(payload.email).strip().lower()
    normalized_topics = sorted(
        {
            topic.strip().lower()
            for topic in payload.topics
            if topic and topic.strip()
        }
    )

    invalid_topics = [
        topic
        for topic in normalized_topics
        if topic not in ALLOWED_TOPICS
    ]

    if invalid_topics:
        raise ValueError(
            f"Invalid topic(s): {', '.join(invalid_topics)}"
        )

    subscriber = db.execute(
        select(Subscriber).where(
            Subscriber.email == email_lower
        )
    ).scalar_one_or_none()

    if subscriber is None:
        subscriber = Subscriber(
            email=email_lower,
            name=payload.name,
            is_active=True,
        )
        db.add(subscriber)
        db.flush()
    else:
        subscriber.name = payload.name
        subscriber.is_active = True

    db.query(SubscriberTopic).filter(
        SubscriberTopic.subscriber_id == subscriber.id
    ).delete(synchronize_session=False)

    for topic in normalized_topics:
        db.add(
            SubscriberTopic(
                subscriber_id=subscriber.id,
                topic=topic,
            )
        )

    db.flush()
    return subscriber


def get_subscribers(db: Session) -> List[Subscriber]:
    result = db.execute(
        select(Subscriber).order_by(
            Subscriber.created_at.desc()
        )
    )
    return list(result.scalars().all())


def unsubscribe_by_email(
    db: Session,
    email: str,
) -> bool:
    email_lower = email.strip().lower()

    subscriber = db.execute(
        select(Subscriber).where(
            Subscriber.email == email_lower
        )
    ).scalar_one_or_none()

    if subscriber is None:
        return False

    subscriber.is_active = False
    db.flush()
    return True

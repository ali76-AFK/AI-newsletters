from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    topics = relationship(
        "SubscriberTopic",
        back_populates="subscriber",
        cascade="all, delete-orphan",
    )

    draft_emails = relationship("DraftEmail", back_populates="subscriber")


class SubscriberTopic(Base):
    __tablename__ = "subscriber_topics"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(
        Integer,
        ForeignKey("subscribers.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic = Column(String(100), nullable=False)

    subscriber = relationship("Subscriber", back_populates="topics")

    __table_args__ = (
        UniqueConstraint(
            "subscriber_id",
            "topic",
            name="uq_subscriber_topic",
        ),
    )


class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(32), default="created", nullable=False)
    # Risk and approval
    risk_level = Column(String(16), default="unknown", nullable=False)
    risk_reason = Column(Text, nullable=True)
    approved = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    workflow_executions = relationship(
        "WorkflowExecution",
        back_populates="newsletter",
        cascade="all, delete-orphan",
    )
    drafts = relationship(
        "DraftEmail",
        back_populates="newsletter",
        cascade="all, delete-orphan",
    )


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    newsletter_id = Column(
        Integer,
        ForeignKey("newsletters.id", ondelete="CASCADE"),
        nullable=False,
    )
    state = Column(String(32), nullable=False, default="created")
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    correlation_id = Column(String(64), nullable=False, index=True)

    newsletter = relationship("Newsletter", back_populates="workflow_executions")


class DraftEmail(Base):
    __tablename__ = "draft_emails"

    id = Column(Integer, primary_key=True, index=True)
    newsletter_id = Column(
        Integer,
        ForeignKey("newsletters.id", ondelete="CASCADE"),
        nullable=False,
    )
    subscriber_id = Column(
        Integer,
        ForeignKey("subscribers.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(
        String(32),
        default="draft",
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    newsletter = relationship("Newsletter", back_populates="drafts")
    subscriber = relationship("Subscriber", back_populates="draft_emails")

    __table_args__ = (
        UniqueConstraint(
            "newsletter_id",
            "subscriber_id",
            name="uq_newsletter_subscriber_draft",
        ),
    )

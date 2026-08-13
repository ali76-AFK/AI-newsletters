from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class SubscriberState(BaseModel):
    id: int
    email: str
    name: Optional[str] = None


class DraftSummary(BaseModel):
    id: int
    subscriber_id: Optional[int] = None
    subject: str


class SendSummary(BaseModel):
    sender: str
    recipients: List[str]
    subject: str
    count: int


class WorkflowState(BaseModel):
    newsletter_id: int
    workflow_id: int
    topic: Optional[str] = None
    subscribers: List[SubscriberState] = []
    created_drafts: List[DraftSummary] = []
    send_summary: Optional[SendSummary] = None

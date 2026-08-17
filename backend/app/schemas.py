from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class SubscriberCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    topics: List[str] = Field(default_factory=list)

    @field_validator("topics", mode="before")
    @classmethod
    def normalize_topics(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class SubscriberResponse(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str]
    is_active: bool
    topics: List[str]

    class Config:
        from_attributes = True


class SubscriberListResponse(BaseModel):
    subscribers: List[SubscriberResponse]


class UnsubscribeRequest(BaseModel):
    email: EmailStr


class NewsletterCreate(BaseModel):
    title: str
    topic: str
    body: str
    source: str | None = None
    source_external_id: str | None = None
    source_url: str | None = None
    content_hash: str | None = None

class NewsletterResponse(BaseModel):
    id: int
    title: str
    topic: str
    status: str
    risk_level: str = "unknown"
    approved: bool

    class Config:
        from_attributes = True


class NewsletterListResponse(BaseModel):
    newsletters: List[NewsletterResponse]

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


class NewsletterScheduleCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None

    topics: List[str] = Field(min_length=1)
    sources: List[str] = Field(min_length=1)
    weekdays: List[int] = Field(min_length=1)

    delivery_time: str
    timezone: str = "Europe/Berlin"
    enabled: bool = False

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: List[int]) -> List[int]:
        unique_days = sorted(set(value))

        if any(day < 0 or day > 6 for day in unique_days):
            raise ValueError("weekdays must contain only values from 0 to 6")

        return unique_days

    @field_validator("delivery_time")
    @classmethod
    def validate_delivery_time(cls, value: str) -> str:
        try:
            hour_text, minute_text = value.split(":")
            hour = int(hour_text)
            minute = int(minute_text)
        except (ValueError, AttributeError) as exc:
            raise ValueError("delivery_time must use HH:MM format") from exc

        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("delivery_time must be a valid 24-hour time")

        return f"{hour:02d}:{minute:02d}"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        allowed = {"Europe/Berlin", "UTC"}

        if value not in allowed:
            raise ValueError(
                f"timezone must be one of: {', '.join(sorted(allowed))}"
            )

        return value


class NewsletterScheduleResponse(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str]

    topics: List[str]
    sources: List[str]
    weekdays: List[int]

    delivery_time: str
    timezone: str
    enabled: bool

    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    created_at: str
    updated_at: str


class NewsletterScheduleListResponse(BaseModel):
    schedules: List[NewsletterScheduleResponse]
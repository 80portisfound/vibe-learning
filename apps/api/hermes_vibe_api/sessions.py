from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CodingSession(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    goal: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    archived_at: datetime | None = None


class CodingSessionCreate(BaseModel):
    title: str
    goal: str = ""


class CodingSessionUpdate(BaseModel):
    title: str | None = None
    goal: str | None = None

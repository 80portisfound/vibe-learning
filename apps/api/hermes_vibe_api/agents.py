from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentProfile(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    role: str = ""
    system_prompt: str = ""
    provider: str | None = None
    model: str | None = None
    skills: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    archived_at: datetime | None = None


class AgentProfileCreate(BaseModel):
    name: str
    role: str = ""
    system_prompt: str = ""
    provider: str | None = None
    model: str | None = None
    skills: list[str] = Field(default_factory=list)


class AgentProfileUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    system_prompt: str | None = None
    provider: str | None = None
    model: str | None = None
    skills: list[str] | None = None

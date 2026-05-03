from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str
    type: str
    payload: dict
    source: str
    created_at: datetime = Field(default_factory=utc_now)


class ConceptNote(BaseModel):
    concept: str
    short_summary: str


class ImplementationSummary(BaseModel):
    current_goal: str = ""
    completed_changes: list[str] = Field(default_factory=list)
    in_progress_changes: list[str] = Field(default_factory=list)
    touched_files: list[str] = Field(default_factory=list)
    important_decisions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    test_status: str = "unknown"
    next_steps: list[str] = Field(default_factory=list)


class DecisionTrace(BaseModel):
    user_request: str = ""
    agent_reasoning_summary: str = ""
    tool_calls: list[str] = Field(default_factory=list)
    code_changes: list[str] = Field(default_factory=list)
    resulting_files: list[str] = Field(default_factory=list)
    outcome: str = ""


class BeforeAfterExplanation(BaseModel):
    file_path: str
    before_summary: str
    after_summary: str
    behavior_change: str = ""
    risk_level: str = "unknown"
    related_concepts: list[str] = Field(default_factory=list)


class ErrorLearningLog(BaseModel):
    error_message: str
    where_it_happened: str = ""
    root_cause_summary: str = ""
    fix_summary: str = ""
    files_changed: list[str] = Field(default_factory=list)
    prevention_note: str = ""
    related_concepts: list[str] = Field(default_factory=list)


class RuntimeActivityItem(BaseModel):
    kind: str
    summary: str
    stream: str = ""
    tool: str = ""


class DashboardOverview(BaseModel):
    status: str = "idle"
    progress_percent: int = 0
    completed_count: int = 0
    in_progress_count: int = 0
    touched_file_count: int = 0
    blocker_count: int = 0
    concept_count: int = 0
    decision_count: int = 0
    next_action: str = ""
    last_activity: str = ""


class DashboardProjection(BaseModel):
    overview: DashboardOverview = Field(default_factory=DashboardOverview)
    implementation: ImplementationSummary = Field(default_factory=ImplementationSummary)
    activity: list[RuntimeActivityItem] = Field(default_factory=list)
    concepts: list[ConceptNote] = Field(default_factory=list)
    decisions: list[DecisionTrace] = Field(default_factory=list)
    before_after: list[BeforeAfterExplanation] = Field(default_factory=list)
    errors: list[ErrorLearningLog] = Field(default_factory=list)

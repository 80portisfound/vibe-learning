from hermes_vibe_api.dashboard.schemas import DashboardEvent


CONCEPT_KEYWORDS = {
    "cors": ("CORS", "Browser policy for cross-origin API requests."),
    "fastapi": ("FastAPI", "Python API framework used by the Hermes Vibe backend."),
    "react": ("React", "Renderer UI library used by the desktop app."),
    "electron": ("Electron", "Desktop shell that hosts the React renderer."),
    "pytest": ("pytest", "Python test runner used for backend regression tests."),
    "sse": ("SSE", "Server-sent event stream for live backend events."),
    "sqlite": ("SQLite", "Local database used for dashboard event storage."),
    "honcho": ("honcho", "Hermes user/project modeling state stored in Hermes home."),
    "hermes": ("Hermes", "Agent runtime embedded by the desktop app."),
}


def analyze_successful_turn(
    session_id: str,
    message,
    assistant_content: str,
    tool_name: str,
) -> list[DashboardEvent]:
    outcome = assistant_content.splitlines()[0].strip() if assistant_content.strip() else "Hermes completed the turn."
    events = [
        DashboardEvent(
            session_id=session_id,
            type="implementation.summary.updated",
            payload={
                "current_goal": message.content,
                "in_progress_changes": [],
                "next_steps": ["Review Hermes response and continue the coding loop."],
            },
            source="dashboard.analyzer",
        ),
        DashboardEvent(
            session_id=session_id,
            type="decision.trace.created",
            payload={
                "user_request": message.content,
                "agent_reasoning_summary": "Hermes generated a response through the configured runtime adapter.",
                "tool_calls": [tool_name],
                "code_changes": [],
                "resulting_files": [],
                "outcome": outcome,
            },
            source="dashboard.analyzer",
        ),
    ]
    events.extend(_concept_events(session_id, f"{message.content}\n{assistant_content}"))
    return events


def analyze_failed_turn(
    session_id: str,
    message,
    error_message: str,
    where_it_happened: str,
) -> list[DashboardEvent]:
    return [
        DashboardEvent(
            session_id=session_id,
            type="implementation.blocker.detected",
            payload={"summary": f"Hermes could not complete: {error_message}"},
            source="dashboard.analyzer",
        ),
        DashboardEvent(
            session_id=session_id,
            type="error.learning_log.created",
            payload={
                "error_message": error_message,
                "where_it_happened": where_it_happened,
                "root_cause_summary": "Hermes runtime returned an error before completing the turn.",
                "fix_summary": "Check the runtime configuration, selected model, credentials, or Hermes CLI output.",
                "files_changed": [],
                "prevention_note": f"Validate {where_it_happened} configuration before launching the turn.",
                "related_concepts": [],
            },
            source="dashboard.analyzer",
        ),
    ]


def _concept_events(session_id: str, text: str) -> list[DashboardEvent]:
    lowered = text.lower()
    events = []
    seen = set()
    for keyword, (concept, summary) in CONCEPT_KEYWORDS.items():
        if keyword in lowered and concept not in seen:
            seen.add(concept)
            events.append(
                DashboardEvent(
                    session_id=session_id,
                    type="concept.detected",
                    payload={"concept": concept, "summary": summary},
                    source="dashboard.analyzer",
                )
            )
    return events

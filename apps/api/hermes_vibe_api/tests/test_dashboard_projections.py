from hermes_vibe_api.dashboard.projections import build_dashboard_projection
from hermes_vibe_api.dashboard.schemas import DashboardEvent


def event(event_type: str, payload: dict) -> DashboardEvent:
    return DashboardEvent(session_id="s1", type=event_type, payload=payload, source="test")


def test_projection_builds_implementation_summary_from_events():
    projection = build_dashboard_projection(
        [
            event(
                "implementation.summary.updated",
                {
                    "current_goal": "Wire Hermes dashboard events",
                    "in_progress_changes": ["Normalize Hermes turn output"],
                    "next_steps": ["Expose live activity"],
                },
            ),
            event("implementation.changed", {"file_path": "src/auth.py", "summary": "Added login guard"}),
            event("implementation.blocker.detected", {"summary": "Token refresh fails"}),
            event("test.run.failed", {"summary": "auth tests failing"}),
        ]
    )

    assert projection.implementation.current_goal == "Wire Hermes dashboard events"
    assert projection.implementation.in_progress_changes == ["Normalize Hermes turn output"]
    assert projection.implementation.next_steps == ["Expose live activity"]
    assert projection.implementation.touched_files == ["src/auth.py"]
    assert projection.implementation.completed_changes == ["Added login guard"]
    assert projection.implementation.blockers == ["Token refresh fails"]
    assert projection.implementation.test_status == "failed: auth tests failing"


def test_projection_collects_learning_and_debug_records():
    projection = build_dashboard_projection(
        [
            event("concept.detected", {"concept": "JWT", "summary": "Signed token for auth"}),
            event("decision.trace.created", {"user_request": "Add auth", "outcome": "Created guard"}),
            event(
                "code.before_after.created",
                {"file_path": "src/auth.py", "before_summary": "No guard", "after_summary": "Guard added"},
            ),
            event("error.learning_log.created", {"error_message": "401", "root_cause_summary": "Missing token"}),
        ]
    )

    assert projection.concepts[0].concept == "JWT"
    assert projection.decisions[0].outcome == "Created guard"
    assert projection.before_after[0].after_summary == "Guard added"
    assert projection.errors[0].root_cause_summary == "Missing token"


def test_projection_collects_runtime_activity_timeline():
    projection = build_dashboard_projection(
        [
            event("agent.tool.started", {"tool": "hermes.oneshot"}),
            event("agent.log.chunk", {"tool": "hermes.oneshot", "stream": "stdout", "content": "partial answer"}),
            event("agent.log.chunk", {"tool": "hermes.oneshot", "stream": "stderr", "content": "warning"}),
            event("agent.tool.completed", {"tool": "hermes.oneshot", "returncode": 0}),
        ]
    )

    assert [item.kind for item in projection.activity] == [
        "tool.started",
        "log.stdout",
        "log.stderr",
        "tool.completed",
    ]
    assert projection.activity[1].summary == "partial answer"
    assert projection.activity[3].summary == "hermes.oneshot completed with 0"


def test_projection_builds_dashboard_overview_cards():
    projection = build_dashboard_projection(
        [
            event("implementation.summary.updated", {"current_goal": "Ship dashboard", "next_steps": ["Polish cards"]}),
            event("implementation.changed", {"file_path": "src/a.ts", "summary": "Added card"}),
            event("implementation.changed", {"file_path": "src/b.ts", "summary": "Added summary"}),
            event("concept.detected", {"concept": "Projection", "summary": "Derived UI state"}),
            event("decision.trace.created", {"user_request": "Improve UX", "outcome": "Added overview"}),
            event("test.run.passed", {"summary": "unit tests"}),
            event("agent.tool.completed", {"tool": "hermes.oneshot", "returncode": 0}),
        ]
    )

    assert projection.overview.status == "healthy"
    assert projection.overview.progress_percent == 67
    assert projection.overview.completed_count == 2
    assert projection.overview.touched_file_count == 2
    assert projection.overview.concept_count == 1
    assert projection.overview.decision_count == 1
    assert projection.overview.next_action == "Polish cards"
    assert projection.overview.last_activity == "hermes.oneshot completed with 0"


def test_projection_overview_marks_blocked_and_failed_states():
    projection = build_dashboard_projection(
        [
            event("implementation.summary.updated", {"in_progress_changes": ["Fix runtime"]}),
            event("implementation.blocker.detected", {"summary": "Hermes failed"}),
            event("test.run.failed", {"summary": "runtime tests"}),
        ]
    )

    assert projection.overview.status == "blocked"
    assert projection.overview.progress_percent == 0
    assert projection.overview.blocker_count == 1

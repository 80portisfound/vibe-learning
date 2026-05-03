from hermes_vibe_api.dashboard.analyzer import (
    analyze_failed_turn,
    analyze_successful_turn,
)
from hermes_vibe_api.hermes.runtime import RuntimeMessage


def test_successful_turn_creates_dashboard_learning_events():
    events = analyze_successful_turn(
        session_id="s1",
        message=RuntimeMessage(role="user", content="Fix the FastAPI CORS bug"),
        assistant_content="Updated FastAPI middleware and added a pytest regression test.",
        tool_name="hermes.oneshot",
    )

    assert [event.type for event in events] == [
        "implementation.summary.updated",
        "decision.trace.created",
        "concept.detected",
        "concept.detected",
        "concept.detected",
    ]
    assert events[0].payload["current_goal"] == "Fix the FastAPI CORS bug"
    assert events[1].payload["tool_calls"] == ["hermes.oneshot"]
    assert {event.payload["concept"] for event in events[2:]} == {"FastAPI", "CORS", "pytest"}


def test_failed_turn_creates_blocker_and_error_learning_log():
    events = analyze_failed_turn(
        session_id="s1",
        message=RuntimeMessage(role="user", content="Run Hermes"),
        error_message="missing model",
        where_it_happened="hermes.oneshot",
    )

    assert [event.type for event in events] == [
        "implementation.blocker.detected",
        "error.learning_log.created",
    ]
    assert events[0].payload["summary"] == "Hermes could not complete: missing model"
    assert events[1].payload["root_cause_summary"] == "Hermes runtime returned an error before completing the turn."

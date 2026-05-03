from .schemas import (
    BeforeAfterExplanation,
    ConceptNote,
    DashboardEvent,
    DashboardProjection,
    DecisionTrace,
    ErrorLearningLog,
    RuntimeActivityItem,
)


def build_dashboard_projection(events: list[DashboardEvent]) -> DashboardProjection:
    projection = DashboardProjection()

    for event in events:
        payload = event.payload
        if event.type == "implementation.summary.updated":
            projection.implementation.current_goal = str(payload.get("current_goal", "")).strip()
            projection.implementation.in_progress_changes = [
                str(item) for item in payload.get("in_progress_changes", []) if str(item).strip()
            ]
            projection.implementation.next_steps = [
                str(item) for item in payload.get("next_steps", []) if str(item).strip()
            ]
        elif event.type == "implementation.changed":
            summary = str(payload.get("summary", "")).strip()
            file_path = str(payload.get("file_path", "")).strip()
            if summary:
                projection.implementation.completed_changes.append(summary)
            if file_path and file_path not in projection.implementation.touched_files:
                projection.implementation.touched_files.append(file_path)
        elif event.type == "implementation.blocker.detected":
            summary = str(payload.get("summary", "")).strip()
            if summary:
                projection.implementation.blockers.append(summary)
        elif event.type == "test.run.failed":
            summary = str(payload.get("summary", "")).strip()
            projection.implementation.test_status = f"failed: {summary}" if summary else "failed"
        elif event.type == "test.run.passed":
            summary = str(payload.get("summary", "")).strip()
            projection.implementation.test_status = f"passed: {summary}" if summary else "passed"
        elif event.type == "concept.detected":
            projection.concepts.append(
                ConceptNote(
                    concept=str(payload.get("concept", "")),
                    short_summary=str(payload.get("summary", "")),
                )
            )
        elif event.type == "decision.trace.created":
            projection.decisions.append(DecisionTrace(**payload))
        elif event.type == "code.before_after.created":
            projection.before_after.append(BeforeAfterExplanation(**payload))
        elif event.type == "error.learning_log.created":
            projection.errors.append(ErrorLearningLog(**payload))
        elif event.type == "agent.tool.started":
            tool = str(payload.get("tool", "")).strip()
            projection.activity.append(
                RuntimeActivityItem(kind="tool.started", summary=f"{tool} started", tool=tool)
            )
        elif event.type == "agent.log.chunk":
            stream = str(payload.get("stream", "")).strip()
            content = str(payload.get("content", "")).strip()
            tool = str(payload.get("tool", "")).strip()
            if content:
                projection.activity.append(
                    RuntimeActivityItem(kind=f"log.{stream}", summary=content, stream=stream, tool=tool)
                )
        elif event.type == "agent.tool.completed":
            tool = str(payload.get("tool", "")).strip()
            returncode = payload.get("returncode", "")
            projection.activity.append(
                RuntimeActivityItem(
                    kind="tool.completed",
                    summary=f"{tool} completed with {returncode}",
                    tool=tool,
                )
            )

    projection.overview = build_overview(projection)
    return projection


def build_overview(projection: DashboardProjection):
    completed_count = len(projection.implementation.completed_changes)
    in_progress_count = len(projection.implementation.in_progress_changes)
    blocker_count = len(projection.implementation.blockers) + len(projection.errors)
    next_step_count = 1 if projection.implementation.next_steps else 0
    total_work = completed_count + in_progress_count + blocker_count + next_step_count
    if total_work:
        progress_percent = round((completed_count / total_work) * 100)
    else:
        progress_percent = 0

    if blocker_count:
        status = "blocked"
    elif projection.implementation.test_status.startswith("failed"):
        status = "failing"
    elif completed_count or projection.implementation.test_status.startswith("passed"):
        status = "healthy"
    elif in_progress_count:
        status = "active"
    else:
        status = "idle"

    projection.overview.status = status
    projection.overview.progress_percent = progress_percent
    projection.overview.completed_count = completed_count
    projection.overview.in_progress_count = in_progress_count
    projection.overview.touched_file_count = len(projection.implementation.touched_files)
    projection.overview.blocker_count = blocker_count
    projection.overview.concept_count = len(projection.concepts)
    projection.overview.decision_count = len(projection.decisions)
    projection.overview.next_action = projection.implementation.next_steps[0] if projection.implementation.next_steps else ""
    projection.overview.last_activity = projection.activity[-1].summary if projection.activity else ""
    return projection.overview

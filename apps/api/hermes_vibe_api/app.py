import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from hermes_vibe_api.agents import AgentProfile, AgentProfileCreate, AgentProfileUpdate, utc_now
from hermes_vibe_api.dashboard.projections import build_dashboard_projection
from hermes_vibe_api.dashboard.schemas import DashboardEvent
from hermes_vibe_api.hermes.fork import read_fork_metadata
from hermes_vibe_api.hermes.home import bootstrap_hermes_home, detect_hermes_home
from hermes_vibe_api.hermes.runtime import HermesCLIBackedRuntime, HermesRuntime, RuntimeMessage
from hermes_vibe_api.hermes.snapshots import SnapshotStore, write_text_with_snapshot
from hermes_vibe_api.models.providers import ModelRegistry
from hermes_vibe_api.sessions import CodingSession, CodingSessionCreate, CodingSessionUpdate
from hermes_vibe_api.sessions import utc_now as session_utc_now
from hermes_vibe_api.storage.sqlite_store import SQLiteEventStore


def create_app(
    hermes_home: str | None = None,
    database_path: str | Path | None = None,
    fork_metadata_path: str | Path | None = None,
    runtime: HermesRuntime | None = None,
) -> FastAPI:
    requested_home = hermes_home or os.environ.get("HERMES_HOME")
    if requested_home and os.environ.get("HERMES_VIBE_BOOTSTRAP_HOME") == "1":
        linked_home = bootstrap_hermes_home(requested_home)
    else:
        linked_home = detect_hermes_home(requested_home, bootstrap_honcho=True)
    requested_fork_metadata_path = fork_metadata_path or os.environ.get("HERMES_VIBE_FORK_METADATA_PATH")
    fork_metadata = read_fork_metadata(requested_fork_metadata_path)
    db_path = Path(database_path) if database_path else Path.home() / ".hermes-vibe" / "app.db"
    store = SQLiteEventStore(db_path)
    snapshot_store = SnapshotStore(db_path.parent / "snapshots")
    model_registry = ModelRegistry.with_defaults()
    active_runtime = runtime or HermesCLIBackedRuntime(
        hermes_home=linked_home.path,
        workspace_path=Path.cwd(),
    )

    app = FastAPI(title="Hermes Vibe API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "hermes_home": {"path": str(linked_home.path)},
        }

    @app.get("/models/providers")
    def list_model_providers() -> list[dict]:
        return [provider.model_dump() for provider in model_registry.list_providers()]

    @app.get("/hermes/fork")
    def hermes_fork() -> dict:
        return fork_metadata.model_dump(mode="json")

    @app.get("/hermes/home")
    def hermes_home_status() -> dict:
        return hermes_home_status_payload(linked_home)

    @app.put("/hermes/home")
    def update_hermes_home(payload: dict) -> dict:
        nonlocal linked_home, active_runtime
        requested_path = str(payload.get("path", "")).strip()
        if not requested_path:
            raise HTTPException(status_code=400, detail="Hermes home path is required")
        try:
            if bool(payload.get("bootstrap", False)):
                next_home = bootstrap_hermes_home(requested_path)
            else:
                next_home = detect_hermes_home(requested_path, bootstrap_honcho=True)
        except RuntimeError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        linked_home = next_home
        if runtime is None:
            active_runtime = HermesCLIBackedRuntime(
                hermes_home=linked_home.path,
                workspace_path=Path.cwd(),
            )
        return hermes_home_status_payload(linked_home)

    def hermes_home_status_payload(home) -> dict:
        paths = {
            "config.yaml": home.config_path,
            "memories": home.memories_path,
            "skills": home.skills_path,
            "sessions": home.sessions_path,
            "honcho": home.honcho_path,
        }
        return {
            "path": str(home.path),
            "paths": {name: path_status(path) for name, path in paths.items()},
        }

    @app.get("/hermes/config")
    def read_hermes_config() -> dict:
        return {
            "path": "config.yaml",
            "content": linked_home.config_path.read_text(encoding="utf-8"),
        }

    @app.put("/hermes/config")
    def write_hermes_config(payload: dict) -> dict:
        snapshot = write_text_with_snapshot(
            target_path=linked_home.config_path,
            new_content=str(payload.get("content", "")),
            hermes_home=linked_home.path,
            snapshot_store=snapshot_store,
            reason=str(payload.get("reason", "Hermes config edit")),
        )
        return {
            "path": "config.yaml",
            "snapshot": {
                "snapshot_path": str(snapshot.snapshot_path),
                "relative_path": snapshot.relative_path,
                "reason": snapshot.reason,
                "created_at": snapshot.created_at,
            },
        }

    @app.get("/honcho/status")
    def honcho_status() -> dict:
        return build_honcho_status(linked_home.honcho_path, db_path)

    @app.get("/memory/files")
    def list_memory_files() -> list[dict]:
        files = []
        for path in linked_home.memories_path.rglob("*"):
            if path.is_file() and not path.name.endswith(".lock"):
                relative = path.relative_to(linked_home.memories_path)
                files.append({"path": str(relative), "size": path.stat().st_size})
        return sorted(files, key=lambda item: item["path"])

    @app.get("/memory/files/{relative_path:path}")
    def read_memory_file(relative_path: str) -> dict:
        path = resolve_memory_file(relative_path, linked_home.memories_path)
        if path is None or not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Memory file not found")
        return {"path": relative_path, "content": path.read_text(encoding="utf-8")}

    @app.put("/memory/files/{relative_path:path}")
    def write_memory_file(relative_path: str, payload: dict) -> dict:
        path = resolve_memory_file(relative_path, linked_home.memories_path)
        if path is None or not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Memory file not found")
        snapshot = write_text_with_snapshot(
            target_path=path,
            new_content=str(payload.get("content", "")),
            hermes_home=linked_home.path,
            snapshot_store=snapshot_store,
            reason=str(payload.get("reason", "memory edit")),
        )
        return {
            "path": relative_path,
            "snapshot": {
                "snapshot_path": str(snapshot.snapshot_path),
                "relative_path": snapshot.relative_path,
                "reason": snapshot.reason,
                "created_at": snapshot.created_at,
            },
        }

    @app.get("/skills/files")
    def list_skill_files() -> list[dict]:
        files = []
        for path in linked_home.skills_path.rglob("*"):
            if path.is_file() and is_editable_skill_file(path):
                relative = path.relative_to(linked_home.skills_path)
                files.append({"path": str(relative), "size": path.stat().st_size})
        return sorted(files, key=lambda item: item["path"])

    @app.get("/skills/files/{relative_path:path}")
    def read_skill_file(relative_path: str) -> dict:
        path = resolve_scoped_file(relative_path, linked_home.skills_path)
        if path is None or not path.exists() or not path.is_file() or not is_editable_skill_file(path):
            raise HTTPException(status_code=404, detail="Skill file not found")
        return {"path": relative_path, "content": path.read_text(encoding="utf-8")}

    @app.put("/skills/files/{relative_path:path}")
    def write_skill_file(relative_path: str, payload: dict) -> dict:
        path = resolve_scoped_file(relative_path, linked_home.skills_path)
        if path is None or not path.exists() or not path.is_file() or not is_editable_skill_file(path):
            raise HTTPException(status_code=404, detail="Skill file not found")
        snapshot = write_text_with_snapshot(
            target_path=path,
            new_content=str(payload.get("content", "")),
            hermes_home=linked_home.path,
            snapshot_store=snapshot_store,
            reason=str(payload.get("reason", "skill edit")),
        )
        return {
            "path": relative_path,
            "snapshot": {
                "snapshot_path": str(snapshot.snapshot_path),
                "relative_path": snapshot.relative_path,
                "reason": snapshot.reason,
                "created_at": snapshot.created_at,
            },
        }

    @app.get("/agents")
    def list_agents(include_archived: bool = False) -> list[dict]:
        return [agent.model_dump(mode="json") for agent in store.list_agents(include_archived=include_archived)]

    @app.post("/agents")
    def create_agent(profile: AgentProfileCreate) -> dict:
        agent = store.save_agent(AgentProfile(**profile.model_dump()))
        return agent.model_dump(mode="json")

    @app.patch("/agents/{agent_id}")
    def update_agent(agent_id: str, update: AgentProfileUpdate) -> dict:
        existing = store.get_agent(agent_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Agent profile not found")
        data = update.model_dump(exclude_unset=True)
        agent = existing.model_copy(update={**data, "updated_at": utc_now()})
        return store.save_agent(agent).model_dump(mode="json")

    @app.post("/agents/{agent_id}/archive")
    def archive_agent(agent_id: str) -> dict:
        existing = store.get_agent(agent_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Agent profile not found")
        archived = existing.model_copy(update={"archived_at": utc_now(), "updated_at": utc_now()})
        return store.save_agent(archived).model_dump(mode="json")

    @app.post("/agents/{agent_id}/restore")
    def restore_agent(agent_id: str) -> dict:
        existing = store.get_agent(agent_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Agent profile not found")
        restored = existing.model_copy(update={"archived_at": None, "updated_at": utc_now()})
        return store.save_agent(restored).model_dump(mode="json")

    @app.delete("/agents/{agent_id}")
    def delete_agent(agent_id: str) -> dict:
        if not store.delete_agent(agent_id):
            raise HTTPException(status_code=404, detail="Agent profile not found")
        return {"deleted": True, "id": agent_id}

    @app.get("/sessions")
    def list_sessions(include_archived: bool = False) -> list[dict]:
        return [session.model_dump(mode="json") for session in store.list_sessions(include_archived=include_archived)]

    @app.post("/sessions/deduplicate")
    def deduplicate_sessions() -> dict:
        sessions = store.list_sessions()
        groups: dict[tuple[str, str], list[CodingSession]] = {}
        for session in sessions:
            key = (normalize_duplicate_key(session.title), normalize_duplicate_key(session.goal))
            groups.setdefault(key, []).append(session)

        result_groups = []
        archived_count = 0
        for candidates in groups.values():
            if len(candidates) < 2:
                continue
            keep = sorted(candidates, key=lambda item: item.updated_at, reverse=True)[0]
            archived_ids = []
            for duplicate in candidates:
                if duplicate.id == keep.id:
                    continue
                now = session_utc_now()
                store.save_session(duplicate.model_copy(update={"archived_at": now, "updated_at": now}))
                archived_ids.append(duplicate.id)
            if archived_ids:
                archived_count += len(archived_ids)
                result_groups.append(
                    {
                        "key": {"title": keep.title.strip(), "goal": keep.goal.strip()},
                        "keep_session_id": keep.id,
                        "archived_session_ids": archived_ids,
                    }
                )

        return {"archived_count": archived_count, "groups": result_groups}

    @app.post("/sessions")
    def create_session(payload: CodingSessionCreate) -> dict:
        session = store.save_session(CodingSession(**payload.model_dump()))
        return session.model_dump(mode="json")

    @app.patch("/sessions/{session_id}")
    def update_session(session_id: str, payload: CodingSessionUpdate) -> dict:
        existing = store.get_session(session_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Session not found")
        data = payload.model_dump(exclude_unset=True)
        session = existing.model_copy(update={**data, "updated_at": session_utc_now()})
        return store.save_session(session).model_dump(mode="json")

    @app.post("/sessions/{session_id}/archive")
    def archive_session(session_id: str) -> dict:
        existing = store.get_session(session_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Session not found")
        now = session_utc_now()
        session = existing.model_copy(update={"archived_at": now, "updated_at": now})
        return store.save_session(session).model_dump(mode="json")

    @app.post("/sessions/{session_id}/restore")
    def restore_session(session_id: str) -> dict:
        existing = store.get_session(session_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Session not found")
        session = existing.model_copy(update={"archived_at": None, "updated_at": session_utc_now()})
        return store.save_session(session).model_dump(mode="json")

    @app.delete("/sessions/{session_id}")
    def delete_session(session_id: str) -> dict:
        if not store.delete_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return {"deleted": True, "id": session_id}

    @app.post("/events")
    def add_event(event: DashboardEvent) -> dict:
        return store.add_event(event).model_dump(mode="json")

    def touch_session(session_id: str, message_content: str) -> None:
        existing = store.get_session(session_id)
        if existing is None:
            store.save_session(CodingSession(id=session_id, title=title_from_message(message_content)))
            return
        store.save_session(existing.model_copy(update={"updated_at": session_utc_now()}))

    def ensure_session_can_receive_message(session_id: str) -> None:
        existing = store.get_session(session_id)
        if existing is not None and existing.archived_at is not None:
            raise HTTPException(status_code=409, detail="Archived session cannot receive new messages")

    def enrich_message_from_agent_profile(message: RuntimeMessage) -> RuntimeMessage:
        if not message.agent_id:
            return message
        agent = store.get_agent(message.agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent profile not found")
        if agent.archived_at is not None:
            raise HTTPException(status_code=409, detail="Archived agent cannot receive new messages")
        return message.model_copy(
            update={
                "agent_name": message.agent_name or agent.name,
                "system_prompt": message.system_prompt or agent.system_prompt or None,
                "provider": message.provider or agent.provider,
                "model": message.model or agent.model,
            }
        )

    @app.post("/sessions/{session_id}/messages")
    async def send_message(session_id: str, message: RuntimeMessage) -> dict:
        ensure_session_can_receive_message(session_id)
        runtime_message = enrich_message_from_agent_profile(message)
        touch_session(session_id, message.content)
        user_event = store.add_event(user_message_event(session_id, runtime_message))
        events = [user_event]
        async for event in active_runtime.send_message(session_id, runtime_message):
            events.append(store.add_event(event))
        return {"events": [event.model_dump(mode="json") for event in events]}

    @app.post("/sessions/{session_id}/messages/stream")
    def send_message_stream(session_id: str, message: RuntimeMessage) -> StreamingResponse:
        async def stream_runtime_events():
            ensure_session_can_receive_message(session_id)
            runtime_message = enrich_message_from_agent_profile(message)
            touch_session(session_id, message.content)
            user_event = store.add_event(user_message_event(session_id, runtime_message))
            user_payload = json.dumps(user_event.model_dump(mode="json"))
            yield f"event: {user_event.type}\ndata: {user_payload}\n\n"
            async for event in active_runtime.send_message(session_id, runtime_message):
                saved_event = store.add_event(event)
                payload = json.dumps(saved_event.model_dump(mode="json"))
                yield f"event: {saved_event.type}\ndata: {payload}\n\n"

        return StreamingResponse(stream_runtime_events(), media_type="text/event-stream")

    @app.get("/sessions/{session_id}/events")
    def list_events(session_id: str) -> list[dict]:
        return [event.model_dump(mode="json") for event in store.list_events(session_id)]

    @app.get("/sessions/{session_id}/dashboard")
    def dashboard(session_id: str) -> dict:
        events = store.list_events(session_id)
        return build_dashboard_projection(events).model_dump(mode="json")

    @app.get("/sessions/{session_id}/events/stream")
    def event_stream(session_id: str) -> StreamingResponse:
        def stream_existing_events():
            for event in store.list_events(session_id):
                payload = json.dumps(event.model_dump(mode="json"))
                yield f"event: {event.type}\ndata: {payload}\n\n"

        return StreamingResponse(stream_existing_events(), media_type="text/event-stream")

    return app


def user_message_event(session_id: str, message: RuntimeMessage) -> DashboardEvent:
    return DashboardEvent(
        session_id=session_id,
        type="chat.message.user",
        payload={
            "role": "user",
            "content": message.content,
            "agent_id": message.agent_id,
            "agent_name": message.agent_name,
            "provider": message.provider,
            "model": message.model,
        },
        source="hermes-vibe.user",
    )


def title_from_message(content: str) -> str:
    first_line = content.strip().splitlines()[0] if content.strip() else "Untitled session"
    return first_line[:60]


def normalize_duplicate_key(value: str) -> str:
    return " ".join(value.casefold().split())


def resolve_memory_file(relative_path: str, memories_path: Path) -> Path | None:
    return resolve_scoped_file(relative_path, memories_path)


def resolve_scoped_file(relative_path: str, root: Path) -> Path | None:
    try:
        path = (root / relative_path).resolve()
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def is_editable_skill_file(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json"} and not path.name.endswith(".lock")


def path_status(path: Path) -> dict:
    if path.is_dir():
        kind = "directory"
    elif path.is_file():
        kind = "file"
    else:
        kind = "missing"
    return {
        "path": str(path),
        "exists": path.exists(),
        "kind": kind,
    }


def build_honcho_status(honcho_path: Path, database_path: Path) -> dict:
    files = [path for path in honcho_path.rglob("*") if path.is_file()] if honcho_path.exists() else []
    recent_files = sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:8]
    return {
        "path": str(honcho_path),
        "exists": honcho_path.exists(),
        "file_count": len(files),
        "total_size": sum(path.stat().st_size for path in files),
        "recent_files": [
            {
                "path": str(path.relative_to(honcho_path)),
                "size": path.stat().st_size,
                "modified_at": path.stat().st_mtime,
            }
            for path in recent_files
        ],
        "app_database_path": str(database_path),
    }

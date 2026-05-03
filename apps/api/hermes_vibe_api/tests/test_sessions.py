from pathlib import Path

from fastapi.testclient import TestClient

from hermes_vibe_api.app import create_app
from hermes_vibe_api.dashboard.schemas import DashboardEvent
from hermes_vibe_api.hermes.runtime import HermesRuntime, RuntimeMessage


def make_valid_home(root: Path) -> Path:
    home = root / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "honcho").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    return home


class FakeRuntime(HermesRuntime):
    async def send_message(self, session_id: str, message: RuntimeMessage):
        yield DashboardEvent(
            session_id=session_id,
            type="chat.message.completed",
            payload={"role": "assistant", "content": f"echo: {message.content}"},
            source="test.runtime",
        )


def test_sessions_can_be_created_listed_and_updated(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    created = client.post("/sessions", json={"title": "Dashboard work", "goal": "Track learning"})

    assert created.status_code == 200
    session = created.json()
    assert session["id"]
    assert session["title"] == "Dashboard work"

    listed = client.get("/sessions")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [session["id"]]

    updated = client.patch(f"/sessions/{session['id']}", json={"goal": "Track implementation context"})

    assert updated.status_code == 200
    assert updated.json()["goal"] == "Track implementation context"


def test_streaming_message_records_user_event_and_touches_session(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        runtime=FakeRuntime(),
    )
    client = TestClient(app)

    response = client.post("/sessions", json={"title": "Chat log", "goal": ""})
    session_id = response.json()["id"]

    with client.stream(
        "POST",
        f"/sessions/{session_id}/messages/stream",
        json={"role": "user", "content": "hello"},
    ) as stream_response:
        body = "".join(stream_response.iter_text())

    assert stream_response.status_code == 200
    assert "event: chat.message.user" in body
    events = client.get(f"/sessions/{session_id}/events").json()
    assert [event["type"] for event in events] == ["chat.message.user", "chat.message.completed"]


def test_session_can_be_archived_and_deleted_with_events(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        runtime=FakeRuntime(),
    )
    client = TestClient(app)
    created = client.post("/sessions", json={"title": "Temp", "goal": ""}).json()
    client.post(f"/sessions/{created['id']}/messages", json={"role": "user", "content": "hello"})

    archived = client.post(f"/sessions/{created['id']}/archive")

    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get("/sessions").json() == []
    assert client.get("/sessions?include_archived=true").json()[0]["id"] == created["id"]

    deleted = client.delete(f"/sessions/{created['id']}")

    assert deleted.status_code == 200
    assert client.get("/sessions?include_archived=true").json() == []
    assert client.get(f"/sessions/{created['id']}/events").json() == []


def test_archived_session_can_be_restored(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        runtime=FakeRuntime(),
    )
    client = TestClient(app)
    created = client.post("/sessions", json={"title": "Restorable", "goal": ""}).json()
    client.post(f"/sessions/{created['id']}/archive")

    restored = client.post(f"/sessions/{created['id']}/restore")

    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert client.get("/sessions").json()[0]["id"] == created["id"]


def test_archived_session_rejects_new_messages(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        runtime=FakeRuntime(),
    )
    client = TestClient(app)
    created = client.post("/sessions", json={"title": "Frozen", "goal": ""}).json()
    client.post(f"/sessions/{created['id']}/archive")

    response = client.post(f"/sessions/{created['id']}/messages", json={"role": "user", "content": "hello"})

    assert response.status_code == 409
    assert client.get(f"/sessions/{created['id']}/events").json() == []


def test_duplicate_sessions_can_be_archived_while_keeping_latest(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)
    first = client.post("/sessions", json={"title": "  Duplicate Work  ", "goal": "Same goal"}).json()
    second = client.post("/sessions", json={"title": "duplicate   work", "goal": " Same goal "}).json()
    unique = client.post("/sessions", json={"title": "Unique Work", "goal": "Same goal"}).json()
    client.patch(f"/sessions/{first['id']}", json={"goal": "Same goal, older"})
    client.patch(f"/sessions/{first['id']}", json={"goal": "Same goal"})

    result = client.post("/sessions/deduplicate")

    assert result.status_code == 200
    body = result.json()
    assert body["archived_count"] == 1
    assert body["groups"][0]["keep_session_id"] == first["id"]
    assert body["groups"][0]["archived_session_ids"] == [second["id"]]
    active_ids = [item["id"] for item in client.get("/sessions").json()]
    assert first["id"] in active_ids
    assert unique["id"] in active_ids
    assert second["id"] not in active_ids
    archived_ids = [
        item["id"]
        for item in client.get("/sessions?include_archived=true").json()
        if item["archived_at"] is not None
    ]
    assert archived_ids == [second["id"]]

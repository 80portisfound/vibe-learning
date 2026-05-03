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
    def __init__(self):
        self.messages: list[RuntimeMessage] = []

    async def send_message(self, session_id: str, message: RuntimeMessage):
        self.messages.append(message)
        yield DashboardEvent(
            session_id=session_id,
            type="chat.message.completed",
            payload={"role": "assistant", "content": f"echo: {message.content}"},
            source="test.runtime",
        )


def test_message_endpoint_runs_runtime_and_stores_events(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        fork_metadata_path=Path(__file__).parents[4] / "packages" / "hermes" / "HERMES_VIBE_FORK.json",
        runtime=FakeRuntime(),
    )
    client = TestClient(app)

    response = client.post(
        "/sessions/s1/messages",
        json={"role": "user", "content": "hello"},
    )

    assert response.status_code == 200
    assert response.json()["events"][1]["payload"]["content"] == "echo: hello"
    stored = client.get("/sessions/s1/events").json()
    assert [event["type"] for event in stored] == ["chat.message.user", "chat.message.completed"]


def test_message_endpoint_enriches_runtime_message_from_agent_profile(tmp_path):
    home = make_valid_home(tmp_path)
    runtime = FakeRuntime()
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        fork_metadata_path=Path(__file__).parents[4] / "packages" / "hermes" / "HERMES_VIBE_FORK.json",
        runtime=runtime,
    )
    client = TestClient(app)
    agent = client.post(
        "/agents",
        json={
            "name": "Docs Pair",
            "role": "Documentation partner",
            "system_prompt": "Keep release notes concrete.",
            "provider": "openai",
            "model": "gpt-5.4",
            "skills": ["docs"],
        },
    ).json()

    response = client.post(
        "/sessions/s1/messages",
        json={"role": "user", "content": "write the release notes", "agent_id": agent["id"]},
    )

    assert response.status_code == 200
    assert runtime.messages[0].agent_id == agent["id"]
    assert runtime.messages[0].agent_name == "Docs Pair"
    assert runtime.messages[0].system_prompt == "Keep release notes concrete."
    assert runtime.messages[0].provider == "openai"
    assert runtime.messages[0].model == "gpt-5.4"


def test_message_endpoint_rejects_archived_agent_profile(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        fork_metadata_path=Path(__file__).parents[4] / "packages" / "hermes" / "HERMES_VIBE_FORK.json",
        runtime=FakeRuntime(),
    )
    client = TestClient(app)
    agent = client.post("/agents", json={"name": "Old Agent"}).json()
    client.post(f"/agents/{agent['id']}/archive")

    response = client.post(
        "/sessions/s1/messages",
        json={"role": "user", "content": "hello", "agent_id": agent["id"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Archived agent cannot receive new messages"


def test_message_stream_endpoint_streams_and_stores_runtime_events(tmp_path):
    home = make_valid_home(tmp_path)
    runtime = FakeRuntime()
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        fork_metadata_path=Path(__file__).parents[4] / "packages" / "hermes" / "HERMES_VIBE_FORK.json",
        runtime=runtime,
    )
    client = TestClient(app)
    agent = client.post(
        "/agents",
        json={
            "name": "Streaming Pair",
            "system_prompt": "Stream concise updates.",
            "provider": "anthropic",
            "model": "claude-sonnet-4.5",
        },
    ).json()

    with client.stream(
        "POST",
        "/sessions/s1/messages/stream",
        json={"role": "user", "content": "hello", "agent_id": agent["id"]},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: chat.message.user" in body
    assert "event: chat.message.completed" in body
    assert '"content": "echo: hello"' in body
    assert runtime.messages[0].agent_name == "Streaming Pair"
    assert runtime.messages[0].system_prompt == "Stream concise updates."
    assert runtime.messages[0].provider == "anthropic"
    assert runtime.messages[0].model == "claude-sonnet-4.5"
    stored = client.get("/sessions/s1/events").json()
    assert [event["type"] for event in stored] == ["chat.message.user", "chat.message.completed"]

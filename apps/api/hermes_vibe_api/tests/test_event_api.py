from pathlib import Path

from fastapi.testclient import TestClient

from hermes_vibe_api.app import create_app


def make_valid_home(root: Path) -> Path:
    home = root / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "honcho").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    return home


def test_health_reports_linked_hermes_home(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["hermes_home"]["path"] == str(home.resolve())


def test_events_can_be_added_and_projected(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.post(
        "/events",
        json={
            "session_id": "s1",
            "type": "concept.detected",
            "payload": {"concept": "Embedding", "summary": "Vector representation"},
            "source": "test",
        },
    )

    assert response.status_code == 200
    projection = client.get("/sessions/s1/dashboard").json()
    assert projection["concepts"][0]["concept"] == "Embedding"


def test_event_stream_endpoint_is_sse(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    with client.stream("GET", "/sessions/s1/events/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

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


def test_honcho_status_reports_storage_summary(tmp_path):
    home = make_valid_home(tmp_path)
    (home / "honcho" / "memory.json").write_text('{"ok": true}\n', encoding="utf-8")
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/honcho/status")

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == str((home / "honcho").resolve())
    assert body["exists"] is True
    assert body["file_count"] == 1
    assert body["total_size"] == len('{"ok": true}\n')
    assert body["recent_files"][0]["path"] == "memory.json"
    assert body["app_database_path"] == str(tmp_path / "app.db")


def test_empty_honcho_status_is_reported_as_empty(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/honcho/status")

    assert response.status_code == 200
    assert response.json()["file_count"] == 0
    assert response.json()["recent_files"] == []

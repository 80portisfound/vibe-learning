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


def test_memory_files_can_be_listed_read_and_saved_with_snapshot(tmp_path):
    home = make_valid_home(tmp_path)
    memory_file = home / "memories" / "USER.md"
    memory_file.write_text("old memory\n", encoding="utf-8")
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    listed = client.get("/memory/files")

    assert listed.status_code == 200
    assert listed.json()[0]["path"] == "USER.md"

    read = client.get("/memory/files/USER.md")
    assert read.status_code == 200
    assert read.json()["content"] == "old memory\n"

    saved = client.put(
        "/memory/files/USER.md",
        json={"content": "new memory\n", "reason": "test edit"},
    )

    assert saved.status_code == 200
    assert memory_file.read_text(encoding="utf-8") == "new memory\n"
    assert saved.json()["snapshot"]["relative_path"] == "memories/USER.md"


def test_memory_file_paths_cannot_escape_memory_dir(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/memory/files/../config.yaml")

    assert response.status_code == 404

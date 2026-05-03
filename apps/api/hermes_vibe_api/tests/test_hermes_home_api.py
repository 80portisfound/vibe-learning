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


def test_hermes_home_status_reports_required_paths(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/hermes/home")

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == str(home.resolve())
    assert body["paths"]["config.yaml"]["exists"] is True
    assert body["paths"]["memories"]["kind"] == "directory"
    assert body["paths"]["honcho"]["exists"] is True


def test_hermes_home_can_be_repointed(tmp_path):
    first_home = make_valid_home(tmp_path / "first")
    second_home = make_valid_home(tmp_path / "second")
    (second_home / "config.yaml").write_text("default_model: second-model\n", encoding="utf-8")
    app = create_app(hermes_home=str(first_home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.put("/hermes/home", json={"path": str(second_home)})

    assert response.status_code == 200
    assert response.json()["path"] == str(second_home.resolve())
    assert client.get("/health").json()["hermes_home"]["path"] == str(second_home.resolve())
    assert client.get("/hermes/config").json()["content"] == "default_model: second-model\n"


def test_hermes_home_can_be_bootstrapped_and_repointed(tmp_path):
    first_home = make_valid_home(tmp_path / "first")
    new_home = tmp_path / "new-home"
    app = create_app(hermes_home=str(first_home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.put("/hermes/home", json={"path": str(new_home), "bootstrap": True})

    assert response.status_code == 200
    assert response.json()["path"] == str(new_home.resolve())
    assert (new_home / "config.yaml").read_text(encoding="utf-8") == "default_model: test-model\n"
    assert (new_home / "memories").is_dir()
    assert (new_home / "skills").is_dir()
    assert (new_home / "sessions").is_dir()
    assert (new_home / "honcho").is_dir()


def test_hermes_config_can_be_read_and_saved_with_snapshot(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    read = client.get("/hermes/config")

    assert read.status_code == 200
    assert read.json()["content"] == "default_model: test-model\n"

    saved = client.put(
        "/hermes/config",
        json={"content": "default_model: edited-model\n", "reason": "test config edit"},
    )

    assert saved.status_code == 200
    assert (home / "config.yaml").read_text(encoding="utf-8") == "default_model: edited-model\n"
    assert saved.json()["snapshot"]["relative_path"] == "config.yaml"

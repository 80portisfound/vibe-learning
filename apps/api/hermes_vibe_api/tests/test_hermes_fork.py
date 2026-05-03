import json
import os

from fastapi.testclient import TestClient

from hermes_vibe_api.app import create_app
from hermes_vibe_api.hermes.fork import read_fork_metadata


def make_valid_home(root):
    home = root / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "honcho").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    return home


def test_read_fork_metadata_from_json(tmp_path):
    metadata_path = tmp_path / "HERMES_VIBE_FORK.json"
    metadata_path.write_text(
        json.dumps(
            {
                "upstream_repository": "https://github.com/NousResearch/hermes-agent.git",
                "upstream_commit": "abc123",
                "import_date": "2026-05-01",
                "import_type": "hard-fork-vendored-source",
                "local_integration_notes": ["note"],
            }
        ),
        encoding="utf-8",
    )

    metadata = read_fork_metadata(metadata_path)

    assert metadata.upstream_commit == "abc123"
    assert metadata.local_integration_notes == ["note"]


def test_api_exposes_hermes_fork_metadata(tmp_path):
    home = make_valid_home(tmp_path)
    metadata_path = tmp_path / "HERMES_VIBE_FORK.json"
    metadata_path.write_text(
        json.dumps(
            {
                "upstream_repository": "https://github.com/NousResearch/hermes-agent.git",
                "upstream_commit": "abc123",
                "import_date": "2026-05-01",
                "import_type": "hard-fork-vendored-source",
                "local_integration_notes": ["note"],
            }
        ),
        encoding="utf-8",
    )
    app = create_app(
        hermes_home=str(home),
        database_path=tmp_path / "app.db",
        fork_metadata_path=metadata_path,
    )
    client = TestClient(app)

    response = client.get("/hermes/fork")

    assert response.status_code == 200
    assert response.json()["upstream_commit"] == "abc123"


def test_api_reads_fork_metadata_path_from_environment(tmp_path, monkeypatch):
    home = make_valid_home(tmp_path)
    metadata_path = tmp_path / "HERMES_VIBE_FORK.json"
    metadata_path.write_text(
        json.dumps(
            {
                "upstream_repository": "https://github.com/NousResearch/hermes-agent.git",
                "upstream_commit": "env123",
                "import_date": "2026-05-01",
                "import_type": "hard-fork-vendored-source",
                "local_integration_notes": ["note"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setitem(os.environ, "HERMES_VIBE_FORK_METADATA_PATH", str(metadata_path))
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/hermes/fork")

    assert response.status_code == 200
    assert response.json()["upstream_commit"] == "env123"

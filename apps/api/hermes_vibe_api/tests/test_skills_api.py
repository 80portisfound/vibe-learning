from pathlib import Path

from fastapi.testclient import TestClient

from hermes_vibe_api.app import create_app


def make_valid_home(root: Path) -> Path:
    home = root / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills" / "software-development" / "tdd").mkdir(parents=True)
    (home / "sessions").mkdir()
    (home / "honcho").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    return home


def test_skill_files_can_be_listed_read_and_saved_with_snapshot(tmp_path):
    home = make_valid_home(tmp_path)
    skill_file = home / "skills" / "software-development" / "tdd" / "SKILL.md"
    skill_file.write_text("# TDD\n\nWrite tests first.\n", encoding="utf-8")
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    listed = client.get("/skills/files")

    assert listed.status_code == 200
    assert listed.json()[0]["path"] == "software-development/tdd/SKILL.md"

    read = client.get("/skills/files/software-development/tdd/SKILL.md")
    assert read.status_code == 200
    assert read.json()["content"] == "# TDD\n\nWrite tests first.\n"

    saved = client.put(
        "/skills/files/software-development/tdd/SKILL.md",
        json={"content": "# TDD\n\nRed green refactor.\n", "reason": "test edit"},
    )

    assert saved.status_code == 200
    assert skill_file.read_text(encoding="utf-8") == "# TDD\n\nRed green refactor.\n"
    assert saved.json()["snapshot"]["relative_path"] == "skills/software-development/tdd/SKILL.md"


def test_skill_file_paths_cannot_escape_skills_dir(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/skills/files/../config.yaml")

    assert response.status_code == 404

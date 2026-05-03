from fastapi.testclient import TestClient

from hermes_vibe_api.app import create_app


def make_valid_home(root):
    home = root / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "honcho").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    return home


def test_agent_profiles_can_be_created_listed_and_updated(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    created = client.post(
        "/agents",
        json={
            "name": "Frontend Pair",
            "role": "React implementation partner",
            "system_prompt": "Focus on compact, testable React changes.",
            "provider": "openai",
            "model": "gpt-5.2",
            "skills": ["react", "debugging"],
        },
    )

    assert created.status_code == 200
    agent = created.json()
    assert agent["id"]
    assert agent["name"] == "Frontend Pair"
    assert agent["skills"] == ["react", "debugging"]

    listed = client.get("/agents")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [agent["id"]]

    updated = client.patch(
        f"/agents/{agent['id']}",
        json={"role": "Dashboard-focused React partner", "skills": ["react", "dashboard"]},
    )

    assert updated.status_code == 200
    assert updated.json()["role"] == "Dashboard-focused React partner"
    assert updated.json()["skills"] == ["react", "dashboard"]


def test_unknown_agent_profile_returns_404(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.patch("/agents/missing", json={"name": "Nobody"})

    assert response.status_code == 404


def test_agent_profile_can_be_archived_and_deleted(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)
    created = client.post(
        "/agents",
        json={
            "name": "Temp",
            "role": "",
            "system_prompt": "",
            "skills": [],
        },
    ).json()

    archived = client.post(f"/agents/{created['id']}/archive")

    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get("/agents").json() == []
    assert client.get("/agents?include_archived=true").json()[0]["id"] == created["id"]

    deleted = client.delete(f"/agents/{created['id']}")

    assert deleted.status_code == 200
    assert client.get("/agents?include_archived=true").json() == []


def test_archived_agent_profile_can_be_restored(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)
    created = client.post(
        "/agents",
        json={
            "name": "Restorable",
            "role": "",
            "system_prompt": "",
            "skills": [],
        },
    ).json()
    client.post(f"/agents/{created['id']}/archive")

    restored = client.post(f"/agents/{created['id']}/restore")

    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert client.get("/agents").json()[0]["id"] == created["id"]

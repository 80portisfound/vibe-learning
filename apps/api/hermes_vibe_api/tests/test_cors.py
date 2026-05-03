from fastapi.testclient import TestClient

from hermes_vibe_api.app import create_app


def test_dev_desktop_origin_can_call_api(tmp_path):
    home = tmp_path / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"

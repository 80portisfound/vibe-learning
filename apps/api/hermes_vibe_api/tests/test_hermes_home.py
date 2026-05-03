from pathlib import Path

from hermes_vibe_api.hermes.home import HermesHome, HermesHomeError, detect_hermes_home


def make_valid_home(root: Path) -> Path:
    home = root / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "honcho").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    return home


def test_detect_hermes_home_from_explicit_path(tmp_path):
    home = make_valid_home(tmp_path)

    detected = detect_hermes_home(str(home))

    assert detected == HermesHome(
        path=home,
        config_path=home / "config.yaml",
        memories_path=home / "memories",
        skills_path=home / "skills",
        sessions_path=home / "sessions",
        honcho_path=home / "honcho",
    )


def test_detect_hermes_home_rejects_missing_required_paths(tmp_path):
    home = tmp_path / ".hermes"
    home.mkdir()

    try:
        detect_hermes_home(str(home))
    except HermesHomeError as exc:
        assert "missing required Hermes paths" in str(exc)
        assert "config.yaml" in str(exc)
        assert "memories" in str(exc)
    else:
        raise AssertionError("detect_hermes_home should reject incomplete Hermes homes")


def test_detect_hermes_home_can_bootstrap_missing_honcho_path(tmp_path):
    home = tmp_path / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")

    detected = detect_hermes_home(str(home), bootstrap_honcho=True)

    assert detected.honcho_path == home / "honcho"
    assert detected.honcho_path.is_dir()

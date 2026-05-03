from dataclasses import dataclass
from pathlib import Path


class HermesHomeError(RuntimeError):
    pass


@dataclass(frozen=True)
class HermesHome:
    path: Path
    config_path: Path
    memories_path: Path
    skills_path: Path
    sessions_path: Path
    honcho_path: Path


DEFAULT_CONFIG = "default_model: test-model\n"


def bootstrap_hermes_home(explicit_path: str) -> HermesHome:
    root = Path(explicit_path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ("memories", "skills", "sessions", "honcho"):
        (root / name).mkdir(exist_ok=True)
    config_path = root / "config.yaml"
    if not config_path.exists():
        config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    return detect_hermes_home(str(root), bootstrap_honcho=True)


def detect_hermes_home(explicit_path: str | None = None, bootstrap_honcho: bool = False) -> HermesHome:
    root = Path(explicit_path).expanduser() if explicit_path else Path.home() / ".hermes"
    root = root.resolve()

    config_path = root / "config.yaml"
    memories_path = root / "memories"
    skills_path = root / "skills"
    sessions_path = root / "sessions"
    honcho_path = root / "honcho"

    if bootstrap_honcho and not honcho_path.exists():
        honcho_path.mkdir(parents=True)

    required = [config_path, memories_path, skills_path, sessions_path, honcho_path]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        joined = ", ".join(missing)
        raise HermesHomeError(f"{root} is missing required Hermes paths: {joined}")

    return HermesHome(
        path=root,
        config_path=config_path,
        memories_path=memories_path,
        skills_path=skills_path,
        sessions_path=sessions_path,
        honcho_path=honcho_path,
    )

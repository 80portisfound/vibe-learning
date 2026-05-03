import json
from pathlib import Path

from pydantic import BaseModel


class HermesForkMetadata(BaseModel):
    upstream_repository: str
    upstream_commit: str
    import_date: str
    import_type: str
    local_integration_notes: list[str]


def default_fork_metadata_path() -> Path:
    return Path(__file__).resolve().parents[4] / "packages" / "hermes" / "HERMES_VIBE_FORK.json"


def read_fork_metadata(metadata_path: str | Path | None = None) -> HermesForkMetadata:
    path = Path(metadata_path) if metadata_path is not None else default_fork_metadata_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    return HermesForkMetadata(**data)

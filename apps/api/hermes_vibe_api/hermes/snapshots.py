from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class SnapshotRecord:
    snapshot_path: Path
    original_path: Path
    relative_path: str
    reason: str
    created_at: str


class SnapshotStore:
    def __init__(self, root: Path):
        self.root = root

    def create_snapshot(self, target_path: Path, hermes_home: Path, reason: str) -> SnapshotRecord:
        hermes_home = hermes_home.resolve()
        target_path = target_path.resolve()
        try:
            relative = target_path.relative_to(hermes_home)
        except ValueError as exc:
            raise ValueError(f"{target_path} is outside Hermes home {hermes_home}") from exc

        created_at = datetime.now(timezone.utc).isoformat()
        snapshot_dir = self.root / datetime.now(timezone.utc).strftime("%Y%m%d")
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        safe_name = "__".join(relative.parts)
        snapshot_path = snapshot_dir / f"{uuid4().hex}_{safe_name}"
        snapshot_path.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")
        return SnapshotRecord(
            snapshot_path=snapshot_path,
            original_path=target_path,
            relative_path=str(relative),
            reason=reason,
            created_at=created_at,
        )


def write_text_with_snapshot(
    target_path: Path,
    new_content: str,
    hermes_home: Path,
    snapshot_store: SnapshotStore,
    reason: str,
) -> SnapshotRecord:
    snapshot = snapshot_store.create_snapshot(target_path, hermes_home, reason)
    target_path.write_text(new_content, encoding="utf-8")
    return snapshot

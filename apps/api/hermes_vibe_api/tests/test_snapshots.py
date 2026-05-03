from pathlib import Path

from hermes_vibe_api.hermes.snapshots import SnapshotStore, write_text_with_snapshot


def test_write_text_with_snapshot_preserves_original_content(tmp_path):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    target = hermes_home / "config.yaml"
    target.write_text("model: old\n", encoding="utf-8")
    snapshot_store = SnapshotStore(tmp_path / "snapshots")

    snapshot = write_text_with_snapshot(
        target_path=target,
        new_content="model: new\n",
        hermes_home=hermes_home,
        snapshot_store=snapshot_store,
        reason="test update",
    )

    assert target.read_text(encoding="utf-8") == "model: new\n"
    assert snapshot.snapshot_path.read_text(encoding="utf-8") == "model: old\n"
    assert snapshot.relative_path == "config.yaml"
    assert snapshot.reason == "test update"


def test_write_text_with_snapshot_rejects_paths_outside_hermes_home(tmp_path):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("old\n", encoding="utf-8")
    snapshot_store = SnapshotStore(tmp_path / "snapshots")

    try:
        write_text_with_snapshot(
            target_path=target,
            new_content="new\n",
            hermes_home=hermes_home,
            snapshot_store=snapshot_store,
            reason="unsafe",
        )
    except ValueError as exc:
        assert "outside Hermes home" in str(exc)
    else:
        raise AssertionError("writes outside Hermes home should be rejected")

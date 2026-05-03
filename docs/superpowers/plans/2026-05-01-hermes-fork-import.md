# Hermes Fork Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the upstream Hermes Agent source into `packages/hermes`, record fork metadata, and expose fork status through the Python backend.

**Architecture:** The upstream source is vendored as a hard fork under `packages/hermes` without relying on a nested git repo. A small backend metadata reader parses `packages/hermes/HERMES_VIBE_FORK.json` and exposes the imported repository URL, commit SHA, import date, and local integration notes through a health-style endpoint.

**Tech Stack:** Python 3.12+/FastAPI/Pydantic/pytest, vendored upstream GitHub source.

---

## File Structure

```text
packages/hermes/
  HERMES_VIBE_FORK.json
  HERMES_VIBE_FORK.md
  <upstream Hermes source files>

apps/api/hermes_vibe_api/hermes/
  fork.py

apps/api/hermes_vibe_api/tests/
  test_hermes_fork.py
```

## Task 1: Import Upstream Hermes Source

**Files:**
- Create/replace: `packages/hermes/*`
- Create: `packages/hermes/HERMES_VIBE_FORK.json`
- Create: `packages/hermes/HERMES_VIBE_FORK.md`

- [ ] **Step 1: Clone upstream into a temporary directory**

Run:

```bash
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git /private/tmp/hermes-agent-upstream
```

Expected: clone succeeds.

- [ ] **Step 2: Copy upstream source into `packages/hermes`**

Run:

```bash
rsync -a --delete --exclude .git /private/tmp/hermes-agent-upstream/ packages/hermes/
```

Expected: `packages/hermes` contains upstream Hermes source files and no nested `.git`.

- [ ] **Step 3: Add fork metadata**

Create `packages/hermes/HERMES_VIBE_FORK.json`:

```json
{
  "upstream_repository": "https://github.com/NousResearch/hermes-agent.git",
  "upstream_commit": "75e1339d4cdb32652e560eccc3930cc9264ac67b",
  "import_date": "2026-05-01",
  "import_type": "hard-fork-vendored-source",
  "local_integration_notes": [
    "Initial import for Hermes Vibe Desktop runtime integration.",
    "Backend currently uses apps/api/hermes_vibe_api/hermes/runtime.py stub until adapter work lands.",
    "Future local changes should emit app-standard DashboardEvent records."
  ]
}
```

Create `packages/hermes/HERMES_VIBE_FORK.md`:

```markdown
# Hermes Vibe Fork Metadata

This directory contains a hard-forked vendored copy of Nous Research Hermes Agent.

- Upstream repository: https://github.com/NousResearch/hermes-agent.git
- Upstream commit: `75e1339d4cdb32652e560eccc3930cc9264ac67b`
- Import date: 2026-05-01
- Import type: hard-fork-vendored-source

Runtime integration starts in `apps/api/hermes_vibe_api/hermes/runtime.py`.
Future fork edits should expose app-standard `DashboardEvent` records.
```

- [ ] **Step 4: Verify import metadata and source**

Run:

```bash
test -f packages/hermes/HERMES_VIBE_FORK.json
test -f packages/hermes/HERMES_VIBE_FORK.md
test ! -d packages/hermes/.git
```

Expected: all commands exit 0.

## Task 2: Backend Fork Metadata Reader

**Files:**
- Create: `apps/api/hermes_vibe_api/tests/test_hermes_fork.py`
- Create: `apps/api/hermes_vibe_api/hermes/fork.py`
- Modify: `apps/api/hermes_vibe_api/hermes/__init__.py`
- Modify: `apps/api/hermes_vibe_api/app.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/hermes_vibe_api/tests/test_hermes_fork.py`:

```python
import json

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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd apps/api && /private/tmp/hermes-vibe-api-venv/bin/pytest hermes_vibe_api/tests/test_hermes_fork.py -v
```

Expected: fail with missing `hermes_vibe_api.hermes.fork`.

- [ ] **Step 3: Implement metadata reader and endpoint**

Create `apps/api/hermes_vibe_api/hermes/fork.py` and update `app.py` so `create_app` accepts `fork_metadata_path`.

- [ ] **Step 4: Run focused and full tests**

Run:

```bash
cd apps/api && /private/tmp/hermes-vibe-api-venv/bin/pytest hermes_vibe_api/tests/test_hermes_fork.py -v
cd apps/api && /private/tmp/hermes-vibe-api-venv/bin/pytest -v
```

Expected: focused tests pass and full backend tests pass.

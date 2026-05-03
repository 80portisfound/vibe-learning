# Hermes Vibe Desktop Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable foundation for an Electron + React + Python FastAPI desktop app that links to local Hermes state, exposes model/profile/runtime contracts, streams dashboard events, and shows a live coding/learning dashboard shell.

**Architecture:** This plan creates a monorepo-style foundation without importing the Hermes fork yet. The backend defines stable app-facing contracts and a stubbed Hermes runtime adapter so the UI and dashboard can be developed before the hard fork lands in `packages/hermes`. Local Hermes state is linked through `~/.hermes` or a configured test path, and writes are guarded by snapshots.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, SQLite, Electron, Vite, React, TypeScript.

---

## File Structure

Create this structure:

```text
apps/
  api/
    hermes_vibe_api/
      __init__.py
      app.py
      config.py
      dashboard/
        __init__.py
        projections.py
        schemas.py
      hermes/
        __init__.py
        home.py
        runtime.py
        snapshots.py
      models/
        __init__.py
        providers.py
      storage/
        __init__.py
        sqlite_store.py
      tests/
        test_dashboard_projections.py
        test_event_api.py
        test_hermes_home.py
        test_model_registry.py
        test_snapshots.py
    requirements.txt
    pytest.ini
  desktop/
    package.json
    tsconfig.json
    vite.config.ts
    index.html
    electron/
      main.ts
      preload.ts
    src/
      App.tsx
      api.ts
      styles.css
      components/
        ChatPanel.tsx
        DashboardPanel.tsx
        HermesHomePanel.tsx
        ModelSelector.tsx
packages/
  hermes/
    README.md
```

Responsibilities:

- `apps/api/hermes_vibe_api/app.py`: FastAPI app factory, REST endpoints, SSE event stream endpoint.
- `apps/api/hermes_vibe_api/hermes/home.py`: detect and validate linked Hermes home.
- `apps/api/hermes_vibe_api/hermes/snapshots.py`: snapshot-before-write support for local Hermes files.
- `apps/api/hermes_vibe_api/hermes/runtime.py`: app-facing Hermes runtime interface and stub implementation.
- `apps/api/hermes_vibe_api/dashboard/schemas.py`: canonical dashboard event and projection models.
- `apps/api/hermes_vibe_api/dashboard/projections.py`: derive implementation, concept, decision, before/after, and error summaries from events.
- `apps/api/hermes_vibe_api/models/providers.py`: model provider registry and session override logic.
- `apps/api/hermes_vibe_api/storage/sqlite_store.py`: small SQLite event store for the MVP foundation.
- `apps/desktop`: Electron + React shell that talks to the FastAPI backend.
- `packages/hermes/README.md`: placeholder documenting where the hard-forked Hermes source will be imported.

---

### Task 1: Backend Package And Test Harness

**Files:**
- Create: `apps/api/requirements.txt`
- Create: `apps/api/pytest.ini`
- Create: `apps/api/hermes_vibe_api/__init__.py`
- Create: `apps/api/hermes_vibe_api/config.py`
- Create: `apps/api/hermes_vibe_api/tests/test_hermes_home.py`
- Create: `apps/api/hermes_vibe_api/hermes/__init__.py`
- Create: `apps/api/hermes_vibe_api/hermes/home.py`

- [ ] **Step 1: Write the failing Hermes home tests**

Create `apps/api/hermes_vibe_api/tests/test_hermes_home.py`:

```python
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
```

- [ ] **Step 2: Add backend dependency files**

Create `apps/api/requirements.txt`:

```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
pytest>=8.2.0
httpx>=0.27.0
```

Create `apps/api/pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = hermes_vibe_api/tests
```

Create `apps/api/hermes_vibe_api/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `apps/api/hermes_vibe_api/hermes/__init__.py`:

```python
from .home import HermesHome, HermesHomeError, detect_hermes_home

__all__ = ["HermesHome", "HermesHomeError", "detect_hermes_home"]
```

Create `apps/api/hermes_vibe_api/config.py`:

```python
from pathlib import Path
from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    hermes_home: Path | None = None
    app_data_dir: Path = Field(default_factory=lambda: Path.home() / ".hermes-vibe")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_hermes_home.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `detect_hermes_home`.

- [ ] **Step 4: Implement Hermes home detection**

Create `apps/api/hermes_vibe_api/hermes/home.py`:

```python
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


def detect_hermes_home(explicit_path: str | None = None) -> HermesHome:
    root = Path(explicit_path).expanduser() if explicit_path else Path.home() / ".hermes"
    root = root.resolve()

    config_path = root / "config.yaml"
    memories_path = root / "memories"
    skills_path = root / "skills"
    sessions_path = root / "sessions"
    honcho_path = root / "honcho"

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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_hermes_home.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

If this directory has been initialized as a git repo, run:

```bash
git add apps/api
git commit -m "feat: add Hermes home detection foundation"
```

If it is not a git repo, skip the commit and note that commit was unavailable.

---

### Task 2: Snapshot-Before-Write Safety

**Files:**
- Create: `apps/api/hermes_vibe_api/tests/test_snapshots.py`
- Create: `apps/api/hermes_vibe_api/hermes/snapshots.py`
- Modify: `apps/api/hermes_vibe_api/hermes/__init__.py`

- [ ] **Step 1: Write the failing snapshot tests**

Create `apps/api/hermes_vibe_api/tests/test_snapshots.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_snapshots.py -v
```

Expected: FAIL with missing `hermes_vibe_api.hermes.snapshots`.

- [ ] **Step 3: Implement snapshot support**

Create `apps/api/hermes_vibe_api/hermes/snapshots.py`:

```python
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
```

Modify `apps/api/hermes_vibe_api/hermes/__init__.py`:

```python
from .home import HermesHome, HermesHomeError, detect_hermes_home
from .snapshots import SnapshotRecord, SnapshotStore, write_text_with_snapshot

__all__ = [
    "HermesHome",
    "HermesHomeError",
    "SnapshotRecord",
    "SnapshotStore",
    "detect_hermes_home",
    "write_text_with_snapshot",
]
```

- [ ] **Step 4: Run snapshot tests**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_snapshots.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run all backend tests so far**

Run:

```bash
cd apps/api && pytest -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/hermes_vibe_api/hermes apps/api/hermes_vibe_api/tests/test_snapshots.py
git commit -m "feat: add snapshot-before-write safety"
```

Skip commit if git is unavailable.

---

### Task 3: Model Provider Registry

**Files:**
- Create: `apps/api/hermes_vibe_api/tests/test_model_registry.py`
- Create: `apps/api/hermes_vibe_api/models/__init__.py`
- Create: `apps/api/hermes_vibe_api/models/providers.py`

- [ ] **Step 1: Write the failing model registry tests**

Create `apps/api/hermes_vibe_api/tests/test_model_registry.py`:

```python
from hermes_vibe_api.models.providers import ModelChoice, ModelRegistry


def test_registry_lists_default_providers_and_models():
    registry = ModelRegistry.with_defaults()

    providers = registry.list_providers()

    assert [provider.id for provider in providers] == ["openai", "anthropic", "local"]
    assert registry.list_models("openai")[0].id == "gpt-5.4"


def test_session_override_replaces_agent_default_model():
    registry = ModelRegistry.with_defaults()
    default = ModelChoice(provider="openai", model="gpt-5.4")
    override = ModelChoice(provider="anthropic", model="claude-sonnet-4.5")

    selected = registry.resolve_choice(default_choice=default, session_override=override)

    assert selected == override


def test_unknown_model_is_rejected():
    registry = ModelRegistry.with_defaults()

    try:
        registry.validate_choice(ModelChoice(provider="openai", model="missing-model"))
    except ValueError as exc:
        assert "Unknown model" in str(exc)
    else:
        raise AssertionError("Unknown model should be rejected")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_model_registry.py -v
```

Expected: FAIL with missing `hermes_vibe_api.models`.

- [ ] **Step 3: Implement the model registry**

Create `apps/api/hermes_vibe_api/models/__init__.py`:

```python
from .providers import ModelChoice, ModelInfo, ModelProvider, ModelRegistry

__all__ = ["ModelChoice", "ModelInfo", "ModelProvider", "ModelRegistry"]
```

Create `apps/api/hermes_vibe_api/models/providers.py`:

```python
from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    display_name: str
    context_window: int | None = None


class ModelProvider(BaseModel):
    id: str
    display_name: str
    auth_status: str = "unknown"
    models: list[ModelInfo]


class ModelChoice(BaseModel):
    provider: str
    model: str
    reasoning_effort: str | None = None
    temperature: float | None = None


class ModelRegistry:
    def __init__(self, providers: list[ModelProvider]):
        self._providers = {provider.id: provider for provider in providers}

    @classmethod
    def with_defaults(cls) -> "ModelRegistry":
        return cls(
            providers=[
                ModelProvider(
                    id="openai",
                    display_name="OpenAI",
                    models=[
                        ModelInfo(id="gpt-5.4", display_name="GPT-5.4"),
                        ModelInfo(id="gpt-5.4-mini", display_name="GPT-5.4 Mini"),
                    ],
                ),
                ModelProvider(
                    id="anthropic",
                    display_name="Anthropic",
                    models=[ModelInfo(id="claude-sonnet-4.5", display_name="Claude Sonnet 4.5")],
                ),
                ModelProvider(
                    id="local",
                    display_name="Local",
                    models=[ModelInfo(id="custom-local", display_name="Custom Local Model")],
                ),
            ]
        )

    def list_providers(self) -> list[ModelProvider]:
        return list(self._providers.values())

    def list_models(self, provider_id: str) -> list[ModelInfo]:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        return self._providers[provider_id].models

    def validate_choice(self, choice: ModelChoice) -> ModelChoice:
        models = self.list_models(choice.provider)
        if choice.model not in {model.id for model in models}:
            raise ValueError(f"Unknown model for {choice.provider}: {choice.model}")
        return choice

    def resolve_choice(
        self,
        default_choice: ModelChoice,
        session_override: ModelChoice | None = None,
    ) -> ModelChoice:
        choice = session_override or default_choice
        return self.validate_choice(choice)
```

- [ ] **Step 4: Run model registry tests**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_model_registry.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run all backend tests**

Run:

```bash
cd apps/api && pytest -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/hermes_vibe_api/models apps/api/hermes_vibe_api/tests/test_model_registry.py
git commit -m "feat: add model provider registry"
```

Skip commit if git is unavailable.

---

### Task 4: Dashboard Event Schemas And Projections

**Files:**
- Create: `apps/api/hermes_vibe_api/tests/test_dashboard_projections.py`
- Create: `apps/api/hermes_vibe_api/dashboard/__init__.py`
- Create: `apps/api/hermes_vibe_api/dashboard/schemas.py`
- Create: `apps/api/hermes_vibe_api/dashboard/projections.py`

- [ ] **Step 1: Write the failing projection tests**

Create `apps/api/hermes_vibe_api/tests/test_dashboard_projections.py`:

```python
from hermes_vibe_api.dashboard.projections import build_dashboard_projection
from hermes_vibe_api.dashboard.schemas import DashboardEvent


def event(event_type: str, payload: dict) -> DashboardEvent:
    return DashboardEvent(session_id="s1", type=event_type, payload=payload, source="test")


def test_projection_builds_implementation_summary_from_events():
    projection = build_dashboard_projection(
        [
            event("implementation.changed", {"file_path": "src/auth.py", "summary": "Added login guard"}),
            event("implementation.blocker.detected", {"summary": "Token refresh fails"}),
            event("test.run.failed", {"summary": "auth tests failing"}),
        ]
    )

    assert projection.implementation.touched_files == ["src/auth.py"]
    assert projection.implementation.completed_changes == ["Added login guard"]
    assert projection.implementation.blockers == ["Token refresh fails"]
    assert projection.implementation.test_status == "failed: auth tests failing"


def test_projection_collects_learning_and_debug_records():
    projection = build_dashboard_projection(
        [
            event("concept.detected", {"concept": "JWT", "summary": "Signed token for auth"}),
            event("decision.trace.created", {"user_request": "Add auth", "outcome": "Created guard"}),
            event("code.before_after.created", {"file_path": "src/auth.py", "before_summary": "No guard", "after_summary": "Guard added"}),
            event("error.learning_log.created", {"error_message": "401", "root_cause_summary": "Missing token"}),
        ]
    )

    assert projection.concepts[0].concept == "JWT"
    assert projection.decisions[0].outcome == "Created guard"
    assert projection.before_after[0].after_summary == "Guard added"
    assert projection.errors[0].root_cause_summary == "Missing token"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_dashboard_projections.py -v
```

Expected: FAIL with missing dashboard modules.

- [ ] **Step 3: Implement dashboard schemas**

Create `apps/api/hermes_vibe_api/dashboard/__init__.py`:

```python
from .projections import build_dashboard_projection
from .schemas import (
    BeforeAfterExplanation,
    ConceptNote,
    DashboardEvent,
    DashboardProjection,
    DecisionTrace,
    ErrorLearningLog,
    ImplementationSummary,
)

__all__ = [
    "BeforeAfterExplanation",
    "ConceptNote",
    "DashboardEvent",
    "DashboardProjection",
    "DecisionTrace",
    "ErrorLearningLog",
    "ImplementationSummary",
    "build_dashboard_projection",
]
```

Create `apps/api/hermes_vibe_api/dashboard/schemas.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str
    type: str
    payload: dict
    source: str
    created_at: datetime = Field(default_factory=utc_now)


class ConceptNote(BaseModel):
    concept: str
    short_summary: str


class ImplementationSummary(BaseModel):
    current_goal: str = ""
    completed_changes: list[str] = Field(default_factory=list)
    in_progress_changes: list[str] = Field(default_factory=list)
    touched_files: list[str] = Field(default_factory=list)
    important_decisions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    test_status: str = "unknown"
    next_steps: list[str] = Field(default_factory=list)


class DecisionTrace(BaseModel):
    user_request: str = ""
    agent_reasoning_summary: str = ""
    tool_calls: list[str] = Field(default_factory=list)
    code_changes: list[str] = Field(default_factory=list)
    resulting_files: list[str] = Field(default_factory=list)
    outcome: str = ""


class BeforeAfterExplanation(BaseModel):
    file_path: str
    before_summary: str
    after_summary: str
    behavior_change: str = ""
    risk_level: str = "unknown"
    related_concepts: list[str] = Field(default_factory=list)


class ErrorLearningLog(BaseModel):
    error_message: str
    where_it_happened: str = ""
    root_cause_summary: str = ""
    fix_summary: str = ""
    files_changed: list[str] = Field(default_factory=list)
    prevention_note: str = ""
    related_concepts: list[str] = Field(default_factory=list)


class DashboardProjection(BaseModel):
    implementation: ImplementationSummary = Field(default_factory=ImplementationSummary)
    concepts: list[ConceptNote] = Field(default_factory=list)
    decisions: list[DecisionTrace] = Field(default_factory=list)
    before_after: list[BeforeAfterExplanation] = Field(default_factory=list)
    errors: list[ErrorLearningLog] = Field(default_factory=list)
```

- [ ] **Step 4: Implement dashboard projections**

Create `apps/api/hermes_vibe_api/dashboard/projections.py`:

```python
from .schemas import (
    BeforeAfterExplanation,
    ConceptNote,
    DashboardEvent,
    DashboardProjection,
    DecisionTrace,
    ErrorLearningLog,
)


def build_dashboard_projection(events: list[DashboardEvent]) -> DashboardProjection:
    projection = DashboardProjection()

    for event in events:
        payload = event.payload
        if event.type == "implementation.changed":
            summary = str(payload.get("summary", "")).strip()
            file_path = str(payload.get("file_path", "")).strip()
            if summary:
                projection.implementation.completed_changes.append(summary)
            if file_path and file_path not in projection.implementation.touched_files:
                projection.implementation.touched_files.append(file_path)
        elif event.type == "implementation.blocker.detected":
            summary = str(payload.get("summary", "")).strip()
            if summary:
                projection.implementation.blockers.append(summary)
        elif event.type == "test.run.failed":
            summary = str(payload.get("summary", "")).strip()
            projection.implementation.test_status = f"failed: {summary}" if summary else "failed"
        elif event.type == "test.run.passed":
            summary = str(payload.get("summary", "")).strip()
            projection.implementation.test_status = f"passed: {summary}" if summary else "passed"
        elif event.type == "concept.detected":
            projection.concepts.append(
                ConceptNote(
                    concept=str(payload.get("concept", "")),
                    short_summary=str(payload.get("summary", "")),
                )
            )
        elif event.type == "decision.trace.created":
            projection.decisions.append(DecisionTrace(**payload))
        elif event.type == "code.before_after.created":
            projection.before_after.append(BeforeAfterExplanation(**payload))
        elif event.type == "error.learning_log.created":
            projection.errors.append(ErrorLearningLog(**payload))

    return projection
```

- [ ] **Step 5: Run projection tests**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_dashboard_projections.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Run all backend tests**

Run:

```bash
cd apps/api && pytest -v
```

Expected: 9 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/hermes_vibe_api/dashboard apps/api/hermes_vibe_api/tests/test_dashboard_projections.py
git commit -m "feat: add dashboard event projections"
```

Skip commit if git is unavailable.

---

### Task 5: SQLite Event Store And FastAPI Endpoints

**Files:**
- Create: `apps/api/hermes_vibe_api/tests/test_event_api.py`
- Create: `apps/api/hermes_vibe_api/storage/__init__.py`
- Create: `apps/api/hermes_vibe_api/storage/sqlite_store.py`
- Create: `apps/api/hermes_vibe_api/app.py`

- [ ] **Step 1: Write failing API tests**

Create `apps/api/hermes_vibe_api/tests/test_event_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from hermes_vibe_api.app import create_app


def make_valid_home(root: Path) -> Path:
    home = root / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "sessions").mkdir()
    (home / "honcho").mkdir()
    (home / "config.yaml").write_text("default_model: test-model\n", encoding="utf-8")
    return home


def test_health_reports_linked_hermes_home(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["hermes_home"]["path"] == str(home.resolve())


def test_events_can_be_added_and_projected(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.post(
        "/events",
        json={
            "session_id": "s1",
            "type": "concept.detected",
            "payload": {"concept": "Embedding", "summary": "Vector representation"},
            "source": "test",
        },
    )

    assert response.status_code == 200
    projection = client.get("/sessions/s1/dashboard").json()
    assert projection["concepts"][0]["concept"] == "Embedding"


def test_event_stream_endpoint_is_sse(tmp_path):
    home = make_valid_home(tmp_path)
    app = create_app(hermes_home=str(home), database_path=tmp_path / "app.db")
    client = TestClient(app)

    with client.stream("GET", "/sessions/s1/events/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
```

- [ ] **Step 2: Run API tests to verify they fail**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_event_api.py -v
```

Expected: FAIL with missing `hermes_vibe_api.app`.

- [ ] **Step 3: Implement SQLite event store**

Create `apps/api/hermes_vibe_api/storage/__init__.py`:

```python
from .sqlite_store import SQLiteEventStore

__all__ = ["SQLiteEventStore"]
```

Create `apps/api/hermes_vibe_api/storage/sqlite_store.py`:

```python
import json
import sqlite3
from pathlib import Path

from hermes_vibe_api.dashboard.schemas import DashboardEvent


class SQLiteEventStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dashboard_events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add_event(self, event: DashboardEvent) -> DashboardEvent:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_events (id, session_id, type, payload, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.session_id,
                    event.type,
                    json.dumps(event.payload),
                    event.source,
                    event.created_at.isoformat(),
                ),
            )
        return event

    def list_events(self, session_id: str) -> list[DashboardEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, type, payload, source, created_at
                FROM dashboard_events
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()

        return [
            DashboardEvent(
                id=row[0],
                session_id=row[1],
                type=row[2],
                payload=json.loads(row[3]),
                source=row[4],
                created_at=row[5],
            )
            for row in rows
        ]
```

- [ ] **Step 4: Implement FastAPI app**

Create `apps/api/hermes_vibe_api/app.py`:

```python
import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from hermes_vibe_api.dashboard.projections import build_dashboard_projection
from hermes_vibe_api.dashboard.schemas import DashboardEvent
from hermes_vibe_api.hermes.home import detect_hermes_home
from hermes_vibe_api.models.providers import ModelRegistry
from hermes_vibe_api.storage.sqlite_store import SQLiteEventStore


def create_app(hermes_home: str | None = None, database_path: str | Path | None = None) -> FastAPI:
    requested_home = hermes_home or os.environ.get("HERMES_HOME")
    linked_home = detect_hermes_home(requested_home)
    db_path = Path(database_path) if database_path else Path.home() / ".hermes-vibe" / "app.db"
    store = SQLiteEventStore(db_path)
    model_registry = ModelRegistry.with_defaults()

    app = FastAPI(title="Hermes Vibe API")

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "hermes_home": {"path": str(linked_home.path)},
        }

    @app.get("/models/providers")
    def list_model_providers() -> list[dict]:
        return [provider.model_dump() for provider in model_registry.list_providers()]

    @app.post("/events")
    def add_event(event: DashboardEvent) -> dict:
        return store.add_event(event).model_dump(mode="json")

    @app.get("/sessions/{session_id}/events")
    def list_events(session_id: str) -> list[dict]:
        return [event.model_dump(mode="json") for event in store.list_events(session_id)]

    @app.get("/sessions/{session_id}/dashboard")
    def dashboard(session_id: str) -> dict:
        events = store.list_events(session_id)
        return build_dashboard_projection(events).model_dump(mode="json")

    @app.get("/sessions/{session_id}/events/stream")
    def event_stream(session_id: str) -> StreamingResponse:
        def stream_existing_events():
            for event in store.list_events(session_id):
                payload = json.dumps(event.model_dump(mode="json"))
                yield f"event: {event.type}\ndata: {payload}\n\n"

        return StreamingResponse(stream_existing_events(), media_type="text/event-stream")

    return app
```

- [ ] **Step 5: Run API tests**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_event_api.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Run all backend tests**

Run:

```bash
cd apps/api && pytest -v
```

Expected: 12 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/hermes_vibe_api/app.py apps/api/hermes_vibe_api/storage apps/api/hermes_vibe_api/tests/test_event_api.py
git commit -m "feat: add event API and dashboard endpoint"
```

Skip commit if git is unavailable.

---

### Task 6: Hermes Runtime Interface Stub

**Files:**
- Create: `apps/api/hermes_vibe_api/hermes/runtime.py`
- Create: `apps/api/hermes_vibe_api/tests/test_runtime.py`
- Modify: `apps/api/hermes_vibe_api/hermes/__init__.py`

- [ ] **Step 1: Write failing runtime tests**

Create `apps/api/hermes_vibe_api/tests/test_runtime.py`:

```python
import pytest

from hermes_vibe_api.hermes.runtime import InProcessHermesRuntime, RuntimeMessage


@pytest.mark.asyncio
async def test_stub_runtime_streams_user_message_echo_events():
    runtime = InProcessHermesRuntime()

    events = [
        event
        async for event in runtime.send_message(
            session_id="s1",
            message=RuntimeMessage(role="user", content="hello"),
        )
    ]

    assert [event.type for event in events] == ["chat.message.delta", "chat.message.completed"]
    assert events[0].payload["content"] == "Hermes stub received: hello"
```

- [ ] **Step 2: Add pytest-asyncio dependency**

Modify `apps/api/requirements.txt`:

```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

- [ ] **Step 3: Run runtime tests to verify they fail**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_runtime.py -v
```

Expected: FAIL with missing `hermes_vibe_api.hermes.runtime`.

- [ ] **Step 4: Implement runtime interface and stub**

Create `apps/api/hermes_vibe_api/hermes/runtime.py`:

```python
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel

from hermes_vibe_api.dashboard.schemas import DashboardEvent


class RuntimeMessage(BaseModel):
    role: str
    content: str


class HermesRuntime(ABC):
    @abstractmethod
    async def send_message(
        self,
        session_id: str,
        message: RuntimeMessage,
    ) -> AsyncIterator[DashboardEvent]:
        pass


class InProcessHermesRuntime(HermesRuntime):
    async def send_message(
        self,
        session_id: str,
        message: RuntimeMessage,
    ) -> AsyncIterator[DashboardEvent]:
        content = f"Hermes stub received: {message.content}"
        yield DashboardEvent(
            session_id=session_id,
            type="chat.message.delta",
            payload={"role": "assistant", "content": content},
            source="hermes.stub",
        )
        yield DashboardEvent(
            session_id=session_id,
            type="chat.message.completed",
            payload={"role": "assistant", "content": content},
            source="hermes.stub",
        )
```

Modify `apps/api/hermes_vibe_api/hermes/__init__.py`:

```python
from .home import HermesHome, HermesHomeError, detect_hermes_home
from .runtime import HermesRuntime, InProcessHermesRuntime, RuntimeMessage
from .snapshots import SnapshotRecord, SnapshotStore, write_text_with_snapshot

__all__ = [
    "HermesHome",
    "HermesHomeError",
    "HermesRuntime",
    "InProcessHermesRuntime",
    "RuntimeMessage",
    "SnapshotRecord",
    "SnapshotStore",
    "detect_hermes_home",
    "write_text_with_snapshot",
]
```

- [ ] **Step 5: Run runtime tests**

Run:

```bash
cd apps/api && pytest hermes_vibe_api/tests/test_runtime.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Run all backend tests**

Run:

```bash
cd apps/api && pytest -v
```

Expected: 13 passed.

- [ ] **Step 7: Commit**

```bash
git add apps/api/requirements.txt apps/api/hermes_vibe_api/hermes apps/api/hermes_vibe_api/tests/test_runtime.py
git commit -m "feat: add Hermes runtime interface stub"
```

Skip commit if git is unavailable.

---

### Task 7: Desktop React Shell

**Files:**
- Create: `apps/desktop/package.json`
- Create: `apps/desktop/tsconfig.json`
- Create: `apps/desktop/vite.config.ts`
- Create: `apps/desktop/index.html`
- Create: `apps/desktop/src/api.ts`
- Create: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/styles.css`
- Create: `apps/desktop/src/components/ChatPanel.tsx`
- Create: `apps/desktop/src/components/DashboardPanel.tsx`
- Create: `apps/desktop/src/components/HermesHomePanel.tsx`
- Create: `apps/desktop/src/components/ModelSelector.tsx`

- [ ] **Step 1: Create desktop package files**

Create `apps/desktop/package.json`:

```json
{
  "name": "hermes-vibe-desktop",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0"
  }
}
```

Create `apps/desktop/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

Create `apps/desktop/vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
```

Create `apps/desktop/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hermes Vibe</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/App.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Create API client**

Create `apps/desktop/src/api.ts`:

```typescript
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export type HealthResponse = {
  status: string;
  hermes_home: { path: string };
};

export type ModelProvider = {
  id: string;
  display_name: string;
  auth_status: string;
  models: { id: string; display_name: string; context_window?: number | null }[];
};

export type DashboardProjection = {
  implementation: {
    completed_changes: string[];
    touched_files: string[];
    blockers: string[];
    test_status: string;
  };
  concepts: { concept: string; short_summary: string }[];
  decisions: { user_request: string; outcome: string }[];
  before_after: { file_path: string; before_summary: string; after_summary: string }[];
  errors: { error_message: string; root_cause_summary: string }[];
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return response.json();
}

export async function getModelProviders(): Promise<ModelProvider[]> {
  const response = await fetch(`${API_BASE}/models/providers`);
  if (!response.ok) throw new Error(`Model providers failed: ${response.status}`);
  return response.json();
}

export async function getDashboard(sessionId: string): Promise<DashboardProjection> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/dashboard`);
  if (!response.ok) throw new Error(`Dashboard failed: ${response.status}`);
  return response.json();
}
```

- [ ] **Step 3: Create React components**

Create `apps/desktop/src/components/HermesHomePanel.tsx`:

```tsx
import { HardDrive } from 'lucide-react';
import type { HealthResponse } from '../api';

export function HermesHomePanel({ health }: { health: HealthResponse | null }) {
  return (
    <section className="panel">
      <div className="panel-title"><HardDrive size={16} /> Hermes Home</div>
      <div className="mono">{health?.hermes_home.path ?? 'Not connected'}</div>
      <div className="muted">Linked mode uses local Hermes state directly.</div>
    </section>
  );
}
```

Create `apps/desktop/src/components/ModelSelector.tsx`:

```tsx
import { Cpu } from 'lucide-react';
import type { ModelProvider } from '../api';

export function ModelSelector({ providers }: { providers: ModelProvider[] }) {
  const firstProvider = providers[0];
  const firstModel = firstProvider?.models[0];

  return (
    <section className="panel">
      <div className="panel-title"><Cpu size={16} /> Model</div>
      <select className="select" defaultValue={firstProvider && firstModel ? `${firstProvider.id}:${firstModel.id}` : ''}>
        {providers.flatMap((provider) =>
          provider.models.map((model) => (
            <option key={`${provider.id}:${model.id}`} value={`${provider.id}:${model.id}`}>
              {provider.display_name} / {model.display_name}
            </option>
          )),
        )}
      </select>
    </section>
  );
}
```

Create `apps/desktop/src/components/ChatPanel.tsx`:

```tsx
import { MessageSquare } from 'lucide-react';

export function ChatPanel() {
  return (
    <section className="chat">
      <div className="panel-title"><MessageSquare size={16} /> Hermes Chat</div>
      <div className="chat-log">
        <div className="message assistant">Hermes runtime foundation is ready for connection.</div>
      </div>
      <div className="composer">
        <input placeholder="Message Hermes..." />
        <button>Send</button>
      </div>
    </section>
  );
}
```

Create `apps/desktop/src/components/DashboardPanel.tsx`:

```tsx
import { Activity, BookOpen, Bug, GitBranch } from 'lucide-react';
import type { DashboardProjection } from '../api';

export function DashboardPanel({ dashboard }: { dashboard: DashboardProjection | null }) {
  return (
    <aside className="dashboard">
      <section className="panel">
        <div className="panel-title"><Activity size={16} /> Implementation</div>
        <div className="muted">Test status: {dashboard?.implementation.test_status ?? 'unknown'}</div>
        <ul>
          {(dashboard?.implementation.completed_changes ?? []).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-title"><BookOpen size={16} /> Concepts</div>
        <ul>
          {(dashboard?.concepts ?? []).map((item) => <li key={item.concept}>{item.concept}: {item.short_summary}</li>)}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-title"><GitBranch size={16} /> Before / After</div>
        <ul>
          {(dashboard?.before_after ?? []).map((item) => <li key={item.file_path}>{item.file_path}: {item.after_summary}</li>)}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-title"><Bug size={16} /> Error Learning</div>
        <ul>
          {(dashboard?.errors ?? []).map((item) => <li key={item.error_message}>{item.error_message}: {item.root_cause_summary}</li>)}
        </ul>
      </section>
    </aside>
  );
}
```

- [ ] **Step 4: Create app and styles**

Create `apps/desktop/src/App.tsx`:

```tsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import { getDashboard, getHealth, getModelProviders, type DashboardProjection, type HealthResponse, type ModelProvider } from './api';
import { ChatPanel } from './components/ChatPanel';
import { DashboardPanel } from './components/DashboardPanel';
import { HermesHomePanel } from './components/HermesHomePanel';
import { ModelSelector } from './components/ModelSelector';
import './styles.css';

function App() {
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [providers, setProviders] = React.useState<ModelProvider[]>([]);
  const [dashboard, setDashboard] = React.useState<DashboardProjection | null>(null);
  const [error, setError] = React.useState<string>('');

  React.useEffect(() => {
    Promise.all([getHealth(), getModelProviders(), getDashboard('demo')])
      .then(([healthResponse, providerResponse, dashboardResponse]) => {
        setHealth(healthResponse);
        setProviders(providerResponse);
        setDashboard(dashboardResponse);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <main className="app">
      <nav className="rail">
        <div className="brand">Hermes Vibe</div>
        <button className="rail-button active">Chat</button>
        <button className="rail-button">Agents</button>
        <button className="rail-button">Dashboard</button>
        <button className="rail-button">Memory</button>
        <button className="rail-button">Skills</button>
        <button className="rail-button">Hermes Home</button>
      </nav>
      <section className="main">
        {error && <div className="error">{error}</div>}
        <div className="topbar">
          <HermesHomePanel health={health} />
          <ModelSelector providers={providers} />
        </div>
        <ChatPanel />
      </section>
      <DashboardPanel dashboard={dashboard} />
    </main>
  );
}

createRoot(document.getElementById('root') as HTMLElement).render(<App />);
```

Create `apps/desktop/src/styles.css`:

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #101214; color: #eef2f4; }
button, input, select { font: inherit; }
.app { min-height: 100vh; display: grid; grid-template-columns: 180px minmax(420px, 1fr) 360px; }
.rail { border-right: 1px solid #252a30; padding: 18px 12px; background: #15181c; }
.brand { font-weight: 800; margin-bottom: 18px; }
.rail-button { display: block; width: 100%; margin-bottom: 6px; padding: 9px 10px; color: #b8c0c7; background: transparent; border: 1px solid transparent; text-align: left; border-radius: 6px; }
.rail-button.active, .rail-button:hover { color: #ffffff; background: #20252b; border-color: #303741; }
.main { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.topbar { display: grid; grid-template-columns: 1fr 280px; gap: 12px; }
.panel, .chat { border: 1px solid #29313a; background: #171b20; border-radius: 8px; padding: 14px; }
.panel-title { display: flex; align-items: center; gap: 8px; font-weight: 750; margin-bottom: 10px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: #9dd5ff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.muted { color: #8f9aa5; font-size: 13px; }
.select { width: 100%; color: #eef2f4; background: #101214; border: 1px solid #303741; border-radius: 6px; padding: 8px; }
.chat { flex: 1; display: flex; flex-direction: column; min-height: 520px; }
.chat-log { flex: 1; padding: 10px 0; }
.message { max-width: 70%; padding: 10px 12px; border-radius: 8px; background: #222932; color: #dce6ee; }
.composer { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
.composer input { color: #eef2f4; background: #101214; border: 1px solid #303741; border-radius: 6px; padding: 10px; }
.composer button { color: #101214; background: #7cc7ff; border: 0; border-radius: 6px; padding: 10px 14px; font-weight: 750; }
.dashboard { border-left: 1px solid #252a30; padding: 18px 14px; background: #13161a; overflow-y: auto; }
.dashboard .panel { margin-bottom: 12px; }
.dashboard ul { margin: 0; padding-left: 18px; color: #c9d3dc; font-size: 13px; }
.error { border: 1px solid #7a3333; background: #2a1717; color: #ffb4b4; border-radius: 8px; padding: 10px 12px; }
```

- [ ] **Step 5: Run TypeScript build**

Run:

```bash
cd apps/desktop && npm install && npm run build
```

Expected: Vite build succeeds.

If network access blocks `npm install`, request approval to run the install with network access, then rerun.

- [ ] **Step 6: Commit**

```bash
git add apps/desktop
git commit -m "feat: add React desktop shell"
```

Skip commit if git is unavailable.

---

### Task 8: Electron Main Process Skeleton

**Files:**
- Modify: `apps/desktop/package.json`
- Create: `apps/desktop/tsconfig.electron.json`
- Create: `apps/desktop/electron/main.ts`
- Create: `apps/desktop/electron/preload.ts`

- [ ] **Step 1: Update desktop dependencies and scripts**

Modify `apps/desktop/package.json`:

```json
{
  "name": "hermes-vibe-desktop",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "dist-electron/main.js",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "build:electron": "tsc -p tsconfig.electron.json",
    "desktop": "npm run build:electron && electron dist-electron/main.js"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "lucide-react": "^0.468.0",
    "electron": "^33.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0"
  }
}
```

Create `apps/desktop/tsconfig.electron.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist-electron",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "types": ["node"]
  },
  "include": ["electron/**/*.ts"]
}
```

- [ ] **Step 2: Create Electron preload**

Create `apps/desktop/electron/preload.ts`:

```typescript
import { contextBridge } from 'electron';

contextBridge.exposeInMainWorld('hermesVibe', {
  platform: process.platform,
});
```

- [ ] **Step 3: Create Electron main process**

Create `apps/desktop/electron/main.ts`:

```typescript
import { app, BrowserWindow } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 760,
    backgroundColor: '#101214',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    void window.loadURL(devUrl);
  } else {
    void window.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
```

- [ ] **Step 4: Build Electron TypeScript**

Run:

```bash
cd apps/desktop && npm run build:electron
```

Expected: TypeScript compiles into `dist-electron`.

- [ ] **Step 5: Build desktop app**

Run:

```bash
cd apps/desktop && npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 6: Commit**

```bash
git add apps/desktop
git commit -m "feat: add Electron desktop shell"
```

Skip commit if git is unavailable.

---

### Task 9: Hermes Fork Placeholder And Developer Docs

**Files:**
- Create: `packages/hermes/README.md`
- Modify: `README.md`

- [ ] **Step 1: Create Hermes fork placeholder**

Create `packages/hermes/README.md`:

```markdown
# Hermes Fork

This directory is reserved for the hard-forked Hermes Agent source.

The implementation plan intentionally builds the app-facing runtime contract first:

- `apps/api/hermes_vibe_api/hermes/runtime.py`
- `apps/api/hermes_vibe_api/dashboard/schemas.py`
- `apps/api/hermes_vibe_api/dashboard/projections.py`

When the upstream Hermes source is imported, record:

- upstream repository URL
- upstream commit SHA
- import date
- local changes needed for event emission and GUI integration
```

- [ ] **Step 2: Add README section**

Append this section to `README.md`:

````markdown
## Hermes Vibe Desktop Direction

The next app direction is an Electron + React + Python FastAPI desktop app that embeds a hard-forked Hermes Agent runtime.

Planned structure:

```text
apps/api      Python FastAPI backend and Hermes runtime host
apps/desktop  Electron + React desktop UI
packages/hermes  hard-forked Hermes Agent source
```

The app links directly to local Hermes state at `~/.hermes` by default. The backend validates that path and snapshots files before app-initiated writes.

Foundation commands:

```bash
cd apps/api
pip install -r requirements.txt
pytest -v

cd ../desktop
npm install
npm run build
```
````

- [ ] **Step 3: Verify docs mention core decisions**

Run:

```bash
rg -n "Electron|FastAPI|packages/hermes|~/.hermes|snapshot" README.md packages/hermes/README.md
```

Expected: output includes all five terms.

- [ ] **Step 4: Commit**

```bash
git add README.md packages/hermes/README.md
git commit -m "docs: document Hermes Vibe desktop foundation"
```

Skip commit if git is unavailable.

---

## Final Verification

- [ ] **Run backend tests**

```bash
cd apps/api && pytest -v
```

Expected: all backend tests pass.

- [ ] **Run desktop build**

```bash
cd apps/desktop && npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Run Electron TypeScript build**

```bash
cd apps/desktop && npm run build:electron
```

Expected: Electron main/preload compile.

- [ ] **Manual smoke test**

Create a temporary Hermes home:

```bash
mkdir -p /tmp/hermes-vibe-test/.hermes/{memories,skills,sessions,honcho}
printf "default_model: test-model\n" > /tmp/hermes-vibe-test/.hermes/config.yaml
```

Start backend:

```bash
cd apps/api
HERMES_HOME=/tmp/hermes-vibe-test/.hermes uvicorn hermes_vibe_api.app:create_app --factory --reload
```

Start renderer:

```bash
cd apps/desktop
npm run dev
```

Open the Vite URL and confirm:

- the Hermes Home panel shows a linked path when the backend is configured with a valid Hermes home
- the model selector lists default models
- the dashboard shell renders implementation, concepts, before/after, and error learning panels

## Notes For Next Plan

The next implementation plan should import the upstream Hermes source into `packages/hermes` and replace `InProcessHermesRuntime` stub behavior with the real hard-forked Hermes runtime event adapter.

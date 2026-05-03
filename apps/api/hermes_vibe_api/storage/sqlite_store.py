import json
import sqlite3
from pathlib import Path

from hermes_vibe_api.agents import AgentProfile
from hermes_vibe_api.dashboard.schemas import DashboardEvent
from hermes_vibe_api.sessions import CodingSession


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    skills TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS coding_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT
                )
                """
            )
            self._ensure_column(conn, "agent_profiles", "archived_at", "TEXT")
            self._ensure_column(conn, "coding_sessions", "archived_at", "TEXT")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

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

    def save_agent(self, agent: AgentProfile) -> AgentProfile:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_profiles (
                    id, name, role, system_prompt, provider, model, skills, created_at, updated_at, archived_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    system_prompt = excluded.system_prompt,
                    provider = excluded.provider,
                    model = excluded.model,
                    skills = excluded.skills,
                    updated_at = excluded.updated_at,
                    archived_at = excluded.archived_at
                """,
                (
                    agent.id,
                    agent.name,
                    agent.role,
                    agent.system_prompt,
                    agent.provider,
                    agent.model,
                    json.dumps(agent.skills),
                    agent.created_at.isoformat(),
                    agent.updated_at.isoformat(),
                    agent.archived_at.isoformat() if agent.archived_at else None,
                ),
            )
        return agent

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, role, system_prompt, provider, model, skills, created_at, updated_at, archived_at
                FROM agent_profiles
                WHERE id = ?
                """,
                (agent_id,),
            ).fetchone()
        return self._agent_from_row(row) if row else None

    def list_agents(self, include_archived: bool = False) -> list[AgentProfile]:
        where = "" if include_archived else "WHERE archived_at IS NULL"
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, name, role, system_prompt, provider, model, skills, created_at, updated_at, archived_at
                FROM agent_profiles
                {where}
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._agent_from_row(row) for row in rows]

    def delete_agent(self, agent_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM agent_profiles WHERE id = ?", (agent_id,))
        return cursor.rowcount > 0

    def _agent_from_row(self, row) -> AgentProfile:
        return AgentProfile(
            id=row[0],
            name=row[1],
            role=row[2],
            system_prompt=row[3],
            provider=row[4],
            model=row[5],
            skills=json.loads(row[6]),
            created_at=row[7],
            updated_at=row[8],
            archived_at=row[9],
        )

    def save_session(self, session: CodingSession) -> CodingSession:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO coding_sessions (id, title, goal, created_at, updated_at, archived_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    goal = excluded.goal,
                    updated_at = excluded.updated_at,
                    archived_at = excluded.archived_at
                """,
                (
                    session.id,
                    session.title,
                    session.goal,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.archived_at.isoformat() if session.archived_at else None,
                ),
            )
        return session

    def get_session(self, session_id: str) -> CodingSession | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, title, goal, created_at, updated_at, archived_at
                FROM coding_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        return self._session_from_row(row) if row else None

    def list_sessions(self, include_archived: bool = False) -> list[CodingSession]:
        where = "" if include_archived else "WHERE archived_at IS NULL"
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, title, goal, created_at, updated_at, archived_at
                FROM coding_sessions
                {where}
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._session_from_row(row) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        with self._connect() as conn:
            conn.execute("DELETE FROM dashboard_events WHERE session_id = ?", (session_id,))
            cursor = conn.execute("DELETE FROM coding_sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0

    def _session_from_row(self, row) -> CodingSession:
        return CodingSession(
            id=row[0],
            title=row[1],
            goal=row[2],
            created_at=row[3],
            updated_at=row[4],
            archived_at=row[5],
        )

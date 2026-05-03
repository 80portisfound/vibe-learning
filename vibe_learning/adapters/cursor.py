import os
import sqlite3
import glob
from ..schema import UniversalContext, Session, PromptContext, CodeChange, Metadata
from .base import BaseAdapter


class CursorAdapter(BaseAdapter):
    """Extracts from .cursor/ composer chat logs and .cursorrules."""

    def extract(self, project_root: str) -> UniversalContext:
        prompts = []
        rules = []
        changes = []

        cursor_dir = os.path.join(project_root, ".cursor")
        if os.path.isdir(cursor_dir):
            # Try to find composer chat DB
            db_paths = glob.glob(os.path.join(cursor_dir, "*.db"))
            if db_paths:
                try:
                    prompts = self._read_composer_db(db_paths[0])
                except Exception:
                    prompts = []

        cursorrules = os.path.join(project_root, ".cursorrules")
        if os.path.isfile(cursorrules):
            try:
                with open(cursorrules, "r", encoding="utf-8") as f:
                    rules = [f.read()]
            except Exception:
                rules = []

        session = Session(source_tool="cursor")
        prompt_ctx = PromptContext(original_prompts=prompts, system_rules=rules)
        meta = Metadata()
        return UniversalContext(
            session=session,
            prompt_context=prompt_ctx,
            code_changes=changes,
            metadata=meta,
        )

    def _read_composer_db(self, db_path: str) -> list:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        prompts = []
        try:
            # Composer DB schema may vary; attempt common patterns
            cursor.execute(
                "SELECT content FROM chat_messages WHERE role='user' ORDER BY createdAt DESC LIMIT 10"
            )
            rows = cursor.fetchall()
            prompts = [r[0] for r in rows if r[0]]
        except Exception:
            pass
        finally:
            conn.close()
        return prompts

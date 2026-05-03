import os
import glob
import json
from ..schema import UniversalContext, Session, PromptContext, CodeChange, Metadata
from .base import BaseAdapter


class KimiCodeAdapter(BaseAdapter):
    """Extracts from .kimi/ session files and API response logs."""

    def extract(self, project_root: str) -> UniversalContext:
        prompts = []
        rules = []
        changes = []

        kimi_dir = os.path.join(project_root, ".kimi")
        if os.path.isdir(kimi_dir):
            session_files = sorted(
                glob.glob(os.path.join(kimi_dir, "*.json")),
                key=os.path.getmtime,
                reverse=True,
            )
            if session_files:
                try:
                    with open(session_files[0], "r", encoding="utf-8") as f:
                        data = json.load(f)
                    prompts = self._extract_prompts(data)
                except Exception:
                    prompts = []

        session = Session(source_tool="kimi-code")
        prompt_ctx = PromptContext(original_prompts=prompts, system_rules=rules)
        meta = Metadata()
        return UniversalContext(
            session=session,
            prompt_context=prompt_ctx,
            code_changes=changes,
            metadata=meta,
        )

    def _extract_prompts(self, data: dict) -> list:
        msgs = data.get("messages", data if isinstance(data, list) else [])
        prompts = []
        for m in msgs:
            if isinstance(m, dict) and m.get("role") == "user":
                content = m.get("content", "")
                if content:
                    prompts.append(content)
        return prompts

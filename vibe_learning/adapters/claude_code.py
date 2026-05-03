import os
import glob
import json
from ..schema import UniversalContext, Session, PromptContext, CodeChange, Metadata
from .base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    """Extracts from .claude/ conversation logs and CLAUDE.md rules."""

    def extract(self, project_root: str) -> UniversalContext:
        prompts = []
        rules = []
        changes = []

        claude_dir = os.path.join(project_root, ".claude")
        if os.path.isdir(claude_dir):
            # Try to read latest conversation log
            log_files = sorted(
                glob.glob(os.path.join(claude_dir, "*.json")),
                key=os.path.getmtime,
                reverse=True,
            )
            if log_files:
                try:
                    with open(log_files[0], "r", encoding="utf-8") as f:
                        log = json.load(f)
                    prompts = self._extract_prompts(log)
                except Exception:
                    prompts = []

        claude_md = os.path.join(project_root, "CLAUDE.md")
        if os.path.isfile(claude_md):
            try:
                with open(claude_md, "r", encoding="utf-8") as f:
                    rules = [f.read()]
            except Exception:
                rules = []

        session = Session(source_tool="claude-code")
        prompt_ctx = PromptContext(original_prompts=prompts, system_rules=rules)
        meta = Metadata()
        return UniversalContext(
            session=session,
            prompt_context=prompt_ctx,
            code_changes=changes,
            metadata=meta,
        )

    def _extract_prompts(self, log: dict) -> list:
        msgs = log.get("messages", log if isinstance(log, list) else [])
        prompts = []
        for m in msgs:
            if isinstance(m, dict) and m.get("role") == "user":
                content = m.get("content", "")
                if content:
                    prompts.append(content)
        return prompts

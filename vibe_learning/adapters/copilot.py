import os
import glob
import json
from ..schema import UniversalContext, Session, PromptContext, CodeChange, Metadata
from .base import BaseAdapter


class CopilotAdapter(BaseAdapter):
    """Extracts from VS Code extension logs and inline chat history."""

    def extract(self, project_root: str) -> UniversalContext:
        prompts = []
        rules = []
        changes = []

        # VS Code stores copilot history in various locations; try common paths
        vscode_dir = os.path.join(project_root, ".vscode")
        copilot_logs = []
        if os.path.isdir(vscode_dir):
            copilot_logs = glob.glob(os.path.join(vscode_dir, "copilot*.json"))

        if copilot_logs:
            try:
                with open(sorted(copilot_logs, key=os.path.getmtime, reverse=True)[0], "r", encoding="utf-8") as f:
                    data = json.load(f)
                prompts = self._extract_prompts(data)
            except Exception:
                prompts = []

        session = Session(source_tool="copilot")
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

import os
import subprocess
from ..schema import UniversalContext, Session, PromptContext, CodeChange, Metadata
from .base import BaseAdapter


class GenericAdapter(BaseAdapter):
    """Fallback adapter using git diff and filesystem events.
    Works with any editor as long as the project is a git repo.
    """

    def extract(self, project_root: str) -> UniversalContext:
        diff = self._get_git_diff(project_root)
        changes = self._parse_diff(diff)
        session = Session(source_tool="generic")
        prompt_ctx = PromptContext(
            original_prompts=["(generic: no prompt log available, inferred from diff)"]
        )
        meta = Metadata(framework_hints=[])
        return UniversalContext(
            session=session,
            prompt_context=prompt_ctx,
            code_changes=changes,
            metadata=meta,
        )

    def _get_git_diff(self, project_root: str) -> str:
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout or ""
        except Exception:
            return ""

    def _parse_diff(self, diff: str) -> list:
        if not diff.strip():
            return []
        # Naive diff parser: split by file
        changes = []
        current_file = None
        current_diff_lines = []
        for line in diff.splitlines():
            if line.startswith("diff --git"):
                if current_file and current_diff_lines:
                    changes.append(
                        CodeChange(
                            file_path=current_file,
                            change_type="modified",
                            diff="\n".join(current_diff_lines),
                            language="python",
                        )
                    )
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[-2][2:]  # b/path
                else:
                    current_file = "unknown"
                current_diff_lines = []
            else:
                current_diff_lines.append(line)
        if current_file and current_diff_lines:
            changes.append(
                CodeChange(
                    file_path=current_file,
                    change_type="modified",
                    diff="\n".join(current_diff_lines),
                    language="python",
                )
            )
        return changes

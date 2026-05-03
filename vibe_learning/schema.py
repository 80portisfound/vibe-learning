from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid


@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_tool: str = "generic"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class PromptContext:
    original_prompts: List[str] = field(default_factory=list)
    system_rules: List[str] = field(default_factory=list)
    conversation_summary: Optional[str] = None


@dataclass
class CodeChange:
    file_path: str = ""
    change_type: str = "modified"  # created|modified|deleted
    diff: str = ""
    language: str = "python"


@dataclass
class Metadata:
    model_used: Optional[str] = None
    framework_hints: List[str] = field(default_factory=list)


@dataclass
class UniversalContext:
    session: Session = field(default_factory=Session)
    prompt_context: PromptContext = field(default_factory=PromptContext)
    code_changes: List[CodeChange] = field(default_factory=list)
    metadata: Metadata = field(default_factory=Metadata)

    @classmethod
    def from_dict(cls, d: dict) -> "UniversalContext":
        session = Session(**d.get("session", {}))
        prompt = PromptContext(**d.get("prompt_context", {}))
        changes = [CodeChange(**c) for c in d.get("code_changes", [])]
        meta = Metadata(**d.get("metadata", {}))
        return cls(session=session, prompt_context=prompt, code_changes=changes, metadata=meta)

    def to_dict(self) -> dict:
        return {
            "session": {
                "id": self.session.id,
                "source_tool": self.session.source_tool,
                "timestamp": self.session.timestamp,
            },
            "prompt_context": {
                "original_prompts": self.prompt_context.original_prompts,
                "system_rules": self.prompt_context.system_rules,
                "conversation_summary": self.prompt_context.conversation_summary,
            },
            "code_changes": [
                {
                    "file_path": c.file_path,
                    "change_type": c.change_type,
                    "diff": c.diff,
                    "language": c.language,
                }
                for c in self.code_changes
            ],
            "metadata": {
                "model_used": self.metadata.model_used,
                "framework_hints": self.metadata.framework_hints,
            },
        }

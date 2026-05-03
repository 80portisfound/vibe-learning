from typing import Dict, Optional
from ..schema import UniversalContext
from .code_scanner import CodeScanner
from .shape_tracker import ShapeTracker
from .concept_linker import ConceptLinker
from .note_architect import NoteArchitect
from .recall_agent import RecallAgent


class Orchestrator:
    """Controls the full pipeline without stopping on failure.
    If an agent fails, pass empty values to the next stage.
    """

    def __init__(self, recall_db_path: str = ".vibe-learning/chroma_db"):
        self.scanner = CodeScanner()
        self.tracker = ShapeTracker()
        self.linker = ConceptLinker()
        self.architect = NoteArchitect()
        self.recall = RecallAgent(db_path=recall_db_path)

    def run(
        self,
        context: UniversalContext,
        user_feeling: str = "",
        user_confusion: str = "",
    ) -> Dict:
        print("[Orchestrator] Pipeline started")

        # Stage 1: Code Scanner
        all_blocks = []
        try:
            for change in context.code_changes:
                blocks = self.scanner.scan(change.diff, change.file_path)
                all_blocks.extend(blocks)
            print(f"[Orchestrator] CodeScanner: {len(all_blocks)} blocks found")
        except Exception as e:
            print(f"[Orchestrator] CodeScanner failed: {e}")
            all_blocks = []

        # Stage 2: Shape Tracker
        tracked = []
        try:
            tracked = self.tracker.track(all_blocks)
            print(f"[Orchestrator] ShapeTracker: {len(tracked)} tracked")
        except Exception as e:
            print(f"[Orchestrator] ShapeTracker failed: {e}")
            tracked = []

        # Stage 3: Concept Linker
        linked = []
        try:
            linked = self.linker.link(tracked)
            print(f"[Orchestrator] ConceptLinker: {len(linked)} linked")
        except Exception as e:
            print(f"[Orchestrator] ConceptLinker failed: {e}")
            linked = []

        # Stage 4: Note Architect
        note = ""
        note_path = ""
        try:
            note = self.architect.build(
                linked_concepts=linked,
                context=context.to_dict(),
                user_feeling=user_feeling,
                user_confusion=user_confusion,
            )
            note_path = self.architect.save(note, out_dir=".vibe-learning/concepts")
            print(f"[Orchestrator] NoteArchitect: saved to {note_path}")
        except Exception as e:
            print(f"[Orchestrator] NoteArchitect failed: {e}")
            note = ""

        # Stage 5: Recall Agent
        indexed = False
        try:
            if note and note_path:
                meta = {
                    "session_id": context.session.id,
                    "source_tool": context.session.source_tool,
                    "concept": linked[0]["concept"] if linked else "Unknown",
                }
                indexed = self.recall.index_note(note_path, note, meta)
                print(f"[Orchestrator] RecallAgent: indexed={indexed}")
        except Exception as e:
            print(f"[Orchestrator] RecallAgent failed: {e}")

        print("[Orchestrator] Pipeline finished")
        return {
            "blocks": all_blocks,
            "tracked": tracked,
            "linked": linked,
            "note": note,
            "note_path": note_path,
            "indexed": indexed,
        }

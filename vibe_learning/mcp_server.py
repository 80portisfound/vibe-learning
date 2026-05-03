import os
import json
from typing import Optional

from .schema import UniversalContext
from .agents import Orchestrator
from .agents.recall_agent import RecallAgent

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except Exception:
    HAS_MCP = False
    FastMCP = None

mcp: Optional[FastMCP] = None
if HAS_MCP:
    mcp = FastMCP("vibe_learning")


class MCPServer:
    """Exposes vibe_decode, vibe_recall, vibe_experiment via MCP protocol."""

    def __init__(self):
        self.orchestrator = Orchestrator()
        self.recall = RecallAgent()

    def run(self):
        if not HAS_MCP or mcp is None:
            print("[MCP] mcp package not installed. Run: pip install mcp")
            return

        @mcp.tool()
        def vibe_decode(context_json: str) -> str:
            """Analyze vibe coding results and create a concept note."""
            try:
                data = json.loads(context_json)
                context = UniversalContext.from_dict(data)
                result = self.orchestrator.run(context)
                return json.dumps(
                    {
                        "note_path": result.get("note_path"),
                        "indexed": result.get("indexed"),
                    },
                    ensure_ascii=False,
                )
            except Exception as e:
                return json.dumps({"error": str(e)})

        @mcp.tool()
        def vibe_recall(query: str) -> str:
            """Search previously recorded concept notes."""
            try:
                results = self.recall.recall(query)
                return json.dumps(results, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)})

        @mcp.tool()
        def vibe_experiment(concept: str) -> str:
            """Generate a 5-minute experiment for a given concept."""
            try:
                from .agents.concept_linker import ConceptLinker
                linker = ConceptLinker()
                exp = linker._generate_experiment(concept)
                return json.dumps({"concept": concept, "experiment": exp}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)})

        mcp.run()


def main():
    server = MCPServer()
    server.run()

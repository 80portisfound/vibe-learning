# Vibe Coding Learning Agent Swarm v3.0

Multi-IDE AI code reverse-parsing and concept auto-recording system.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize directories
python main.py init

# 3. Watch inbox (runs continuously)
python main.py watch

# 4. Process a session JSON manually
python main.py process -f .vibe-learning/inbox/session_001.json

# 5. Search your knowledge
python main.py recall "embedding"

# 6. Use a specific IDE adapter
python main.py adapter claude --feeling "wow this works" --confusion "why 768?"
```

## Architecture

```
User Layer (Any IDE)
  |
  |-- Adapter Layer (IDE-specific extractors)
  |-- MCP Gateway (optional)
  |-- File Watcher (fallback)
          |
          v
  Universal Context Schema (JSON)
          |
          v
  Orchestrator -> Code Scanner -> Shape Tracker -> Concept Linker -> Note Architect -> Recall Agent
```

## Agents

- **Orchestrator**: Pipeline flow control, never stops on failure.
- **Code Scanner**: AST-based unknown keyword extraction.
- **Shape Tracker**: Tensor/data shape tracking in Python list perspective.
- **Concept Linker**: Links to SWE concepts + generates 5-min experiments.
- **Note Architect**: Auto-generates markdown notes.
- **Recall Agent**: ChromaDB + sentence-transformers vector search.

## Project Structure

```
vibe-learning/
├── main.py
├── requirements.txt
├── vibe_learning/
│   ├── schema.py
│   ├── adapters/
│   │   ├── base.py
│   │   ├── generic.py
│   │   ├── claude_code.py
│   │   ├── cursor.py
│   │   ├── kimi_code.py
│   │   └── copilot.py
│   ├── agents/
│   │   ├── code_scanner.py
│   │   ├── shape_tracker.py
│   │   ├── concept_linker.py
│   │   ├── note_architect.py
│   │   ├── recall_agent.py
│   │   └── orchestrator.py
│   ├── watcher.py
│   └── mcp_server.py
└── .vibe-learning/
    ├── inbox/
    ├── processed/
    └── concepts/
```

## Universal Context Schema Example

Drop a file like this into `.vibe-learning/inbox/` to trigger processing:

```json
{
  "session": {
    "id": "abc123",
    "source_tool": "claude-code",
    "timestamp": "2026-04-30T21:41:00Z"
  },
  "prompt_context": {
    "original_prompts": ["RAG chatbot please"],
    "system_rules": [],
    "conversation_summary": null
  },
  "code_changes": [
    {
      "file_path": "src/rag.py",
      "change_type": "created",
      "diff": "+ def encode(docs):\n+     return model.encode(docs)",
      "language": "python"
    }
  ],
  "metadata": {
    "model_used": "claude-sonnet-4",
    "framework_hints": ["chromadb", "sentence-transformers"]
  }
}
```

## 4-Week MVP Roadmap

| Week | Focus | Output |
|---|---|---|
| 1 | Code Scanner + Shape Tracker | 5 notes + Recall demo |
| 2 | Concept Linker | 5 notes (attention, QKV) |
| 3 | Note Architect automation | 10 notes + auto pipeline |
| 4 | Recall Agent + Adapter Layer | ChromaDB personal knowledge engine |

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

Desktop packaging, release notes, and install guidance live in `apps/desktop/README.md`.

Full Korean manual for execution, applying Hermes Vibe to other projects, dashboard behavior, and features:

- `docs/hermes-vibe-manual.md`
- `docs/reverse-learning-guide.md`

#!/usr/bin/env python3
"""
vibe-learning CLI
Multi-IDE vibe coding learning agent swarm.
"""

import argparse
import json
import os
import sys

from vibe_learning.schema import UniversalContext, Session, PromptContext, CodeChange, Metadata
from vibe_learning.agents import Orchestrator
from vibe_learning.adapters import GenericAdapter
from vibe_learning.watcher import start_watcher
from vibe_learning.mcp_server import main as mcp_main


def cmd_init(args):
    dirs = [
        ".vibe-learning/inbox",
        ".vibe-learning/processed",
        ".vibe-learning/concepts",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("[init] Created vibe-learning directories:")
    for d in dirs:
        print(f"  - {d}")


def cmd_process(args):
    adapter = GenericAdapter()
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
        context = UniversalContext.from_dict(data)
    else:
        context = adapter.extract(args.project_root)
    orch = Orchestrator()
    result = orch.run(context, user_feeling=args.feeling, user_confusion=args.confusion)
    print(f"[process] Note: {result.get('note_path')}")
    print(f"[process] Indexed: {result.get('indexed')}")


def cmd_watch(args):
    start_watcher(project_root=args.project_root)


def cmd_recall(args):
    from vibe_learning.agents.recall_agent import RecallAgent
    recall = RecallAgent()
    results = recall.recall(args.query, n_results=args.n)
    if not results:
        print("[recall] No results found.")
        return
    for r in results:
        print(f"--- {r['id']} (distance={r['distance']:.4f}) ---")
        print(r["content"][:500])
        print()


def cmd_mcp(args):
    mcp_main()


def cmd_dashboard(args):
    from vibe_learning.dashboard import build_dashboard
    import subprocess
    import platform
    path = build_dashboard(args.project_root)
    print(f"[dashboard] Generated: {path}")
    if args.open:
        if platform.system() == "Darwin":
            subprocess.run(["open", path])
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", path])
        else:
            os.startfile(path)


def cmd_adapter(args):
    from vibe_learning.adapters import (
        ClaudeCodeAdapter,
        CursorAdapter,
        KimiCodeAdapter,
        CopilotAdapter,
        GenericAdapter,
    )
    mapping = {
        "claude": ClaudeCodeAdapter(),
        "cursor": CursorAdapter(),
        "kimi": KimiCodeAdapter(),
        "copilot": CopilotAdapter(),
        "generic": GenericAdapter(),
    }
    adapter = mapping.get(args.tool, GenericAdapter())
    context = adapter.extract(args.project_root)
    orch = Orchestrator()
    result = orch.run(context, user_feeling=args.feeling, user_confusion=args.confusion)
    print(f"[{args.tool}] Note: {result.get('note_path')}")
    print(f"[{args.tool}] Indexed: {result.get('indexed')}")


def main():
    parser = argparse.ArgumentParser(
        description="Vibe Coding Learning Agent Swarm v3.0"
    )
    parser.add_argument("--project-root", default=".", help="Project root path")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize .vibe-learning directories")
    p_init.set_defaults(func=cmd_init)

    p_process = sub.add_parser("process", help="Process a session JSON or git diff")
    p_process.add_argument("--file", "-f", help="Path to Universal Context JSON")
    p_process.add_argument("--feeling", default="", help="User feeling (discovery moment)")
    p_process.add_argument("--confusion", default="", help="User confusion")
    p_process.set_defaults(func=cmd_process)

    p_watch = sub.add_parser("watch", help="Watch inbox for new JSON files")
    p_watch.set_defaults(func=cmd_watch)

    p_recall = sub.add_parser("recall", help="Search notes via vector DB")
    p_recall.add_argument("query", help="Natural language query")
    p_recall.add_argument("-n", type=int, default=3, help="Number of results")
    p_recall.set_defaults(func=cmd_recall)

    p_mcp = sub.add_parser("mcp", help="Run MCP server")
    p_mcp.set_defaults(func=cmd_mcp)

    p_dashboard = sub.add_parser("dashboard", help="Generate learning dashboard HTML")
    p_dashboard.add_argument("--open", action="store_true", help="Open in browser after generation")
    p_dashboard.set_defaults(func=cmd_dashboard)

    p_adapter = sub.add_parser("adapter", help="Use a specific IDE adapter")
    p_adapter.add_argument(
        "tool",
        choices=["claude", "cursor", "kimi", "copilot", "generic"],
        help="IDE tool name",
    )
    p_adapter.add_argument("--feeling", default="", help="User feeling")
    p_adapter.add_argument("--confusion", default="", help="User confusion")
    p_adapter.set_defaults(func=cmd_adapter)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

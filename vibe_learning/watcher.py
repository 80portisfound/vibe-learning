import os
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .schema import UniversalContext
from .agents import Orchestrator


class VibeInboxHandler(FileSystemEventHandler):
    """Watchdog handler that triggers the pipeline when a new JSON lands in inbox."""

    def __init__(self, orchestrator: Orchestrator, inbox_dir: str, processed_dir: str):
        self.orchestrator = orchestrator
        self.inbox_dir = inbox_dir
        self.processed_dir = processed_dir
        os.makedirs(self.processed_dir, exist_ok=True)

    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".json"):
            return
        print(f"[Watcher] New file detected: {event.src_path}")
        try:
            with open(event.src_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            context = UniversalContext.from_dict(data)
            self.orchestrator.run(context)
            # Move to processed
            basename = os.path.basename(event.src_path)
            processed_path = os.path.join(self.processed_dir, basename)
            os.rename(event.src_path, processed_path)
            print(f"[Watcher] Moved to processed: {processed_path}")
        except Exception as e:
            print(f"[Watcher] Failed to process {event.src_path}: {e}")


def start_watcher(
    project_root: str = ".",
    inbox: str = ".vibe-learning/inbox",
    processed: str = ".vibe-learning/processed",
):
    inbox_path = os.path.join(project_root, inbox)
    processed_path = os.path.join(project_root, processed)
    os.makedirs(inbox_path, exist_ok=True)
    os.makedirs(processed_path, exist_ok=True)

    orch = Orchestrator()
    handler = VibeInboxHandler(orch, inbox_path, processed_path)
    observer = Observer()
    observer.schedule(handler, inbox_path, recursive=False)
    observer.start()
    print(f"[Watcher] Watching {inbox_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

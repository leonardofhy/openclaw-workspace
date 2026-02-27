"""Shared JSONL storage — single implementation for all trackers.

Usage:
    from shared.jsonl_store import JsonlStore
    store = JsonlStore("memory/experiments/experiments.jsonl", prefix="EXP")
    store.append({"name": "test"})       # auto-assigns ID, writes to file
    items = store.load()                 # read all
    store.update("EXP-001", {"status": "done"})  # update + atomic rewrite
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def find_workspace() -> Path:
    """Find workspace root via git or fallback to known path."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: known workspace path
        return Path.home() / ".openclaw" / "workspace"


WORKSPACE = find_workspace()


class JsonlStore:
    """Append-only JSONL store with atomic rewrite for updates."""

    def __init__(self, rel_path: str, prefix: str = "ID"):
        self.path = WORKSPACE / rel_path
        self.prefix = prefix

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        items = []
        for i, line in enumerate(self.path.read_text().strip().splitlines(), 1):
            if not line.strip():
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"⚠️ {self.path.name}:{i}: skipping malformed line", file=sys.stderr)
        return items

    def next_id(self, items: list[dict] | None = None) -> str:
        if items is None:
            items = self.load()
        if not items:
            return f"{self.prefix}-001"
        max_num = 0
        for item in items:
            try:
                num = int(item["id"].split("-")[1])
                max_num = max(max_num, num)
            except (KeyError, IndexError, ValueError):
                pass
        return f"{self.prefix}-{max_num + 1:03d}"

    def append(self, item: dict) -> dict:
        """Append item with auto-assigned ID. Returns the item with ID."""
        items = self.load()
        if "id" not in item:
            item["id"] = self.next_id(items)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item

    def update(self, item_id: str, updates: dict) -> dict | None:
        """Update an item by ID. Uses atomic rewrite."""
        items = self.load()
        target = None
        for item in items:
            if item.get("id") == item_id:
                item.update(updates)
                target = item
                break
        if target is None:
            return None
        self._atomic_rewrite(items)
        return target

    def find(self, item_id: str) -> dict | None:
        for item in self.load():
            if item.get("id") == item_id:
                return item
        return None

    def filter(self, **kwargs) -> list[dict]:
        """Filter items by field values. Example: store.filter(status="success", machine="lab")"""
        items = self.load()
        for key, val in kwargs.items():
            items = [i for i in items if i.get(key) == val]
        return items

    def _atomic_rewrite(self, items: list[dict]):
        """Write to temp file then rename — survives crashes."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=self.path.parent,
            suffix=".tmp",
            prefix=self.path.stem
        )
        try:
            with os.fdopen(fd, "w") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            os.replace(tmp_path, self.path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

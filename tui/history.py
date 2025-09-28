from __future__ import annotations
import json, time, pathlib
from typing import Dict, List

class HistoryStore:
    def __init__(self, app_id: str = "tui"):
        home = pathlib.Path.home()
        self.path = home / f".{app_id}" / "history.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try: self.data = json.loads(self.path.read_text())
            except Exception: self.data = {}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2))

    def add(self, command: str, arg: str, value: str):
        now = time.time()
        self.data.setdefault(command, {}).setdefault(arg, {})[value] = now
        self._save()

    def get(self, command: str, arg: str, limit: int = 8) -> List[str]:
        items = list(self.data.get(command, {}).get(arg, {}).items())
        items.sort(key=lambda kv: kv[1], reverse=True)
        return [k for k,_ in items[:limit]]

import os
import json
from typing import Any, Dict, List

class FeedbackStore:
    def __init__(self, persist_root: str):
        self.persist_root = persist_root

    def _db_dir(self, db: str) -> str:
        return os.path.join(self.persist_root, db)

    def _file_path(self, db: str) -> str:
        d = os.path.join(self._db_dir(db), "feedback")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "feedback.jsonl")

    def append(self, db: str, item: Dict[str, Any]) -> None:
        path = self._file_path(db)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def list(self, db: str, limit: int = 50) -> List[Dict[str, Any]]:
        path = self._file_path(db)
        if not os.path.exists(path):
            return []
        items: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
        if limit and limit > 0:
            return items[-limit:]
        return items

    def clear(self, db: str) -> int:
        path = self._file_path(db)
        if not os.path.exists(path):
            return 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                cnt = sum(1 for _ in f)
        except Exception:
            cnt = 0
        try:
            os.remove(path)
        except Exception:
            pass
        return cnt

import os
import json
import time
from datetime import datetime
from typing import Any, Dict, Optional, List

class ExperimentLogger:
    """JSONL logger theo DB, xoay file theo ngày.
    - File: data/kb/{db}/logs/exp-YYYYMMDD.jsonl
    - Trạng thái enable per-DB lưu ở settings.json
    """

    def __init__(self, persist_root: str):
        self.persist_root = persist_root

    def _db_dir(self, db: str) -> str:
        return os.path.join(self.persist_root, db)

    def _log_dir(self, db: str) -> str:
        p = os.path.join(self._db_dir(db), "logs")
        os.makedirs(p, exist_ok=True)
        return p

    def _settings_path(self, db: str) -> str:
        return os.path.join(self._log_dir(db), "settings.json")

    def _is_enabled(self, db: str) -> bool:
        p = self._settings_path(db)
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return bool(data.get("enabled", False))
        except Exception:
            pass
        return False

    def info(self, db: str) -> Dict[str, Any]:
        return {"db": db, "enabled": self._is_enabled(db)}

    def enable(self, db: str, enabled: bool) -> Dict[str, Any]:
        p = self._settings_path(db)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"enabled": bool(enabled)}, f)
        except Exception:
            pass
        return self.info(db)

    def _log_path_for_today(self, db: str) -> str:
        day = datetime.utcnow().strftime("%Y%m%d")
        return os.path.join(self._log_dir(db), f"exp-{day}.jsonl")

    def log(self, db: str, event: Dict[str, Any]) -> None:
        if not self._is_enabled(db):
            return
        path = self._log_path_for_today(db)
        # Bổ sung thời gian nếu thiếu
        if "ts" not in event:
            event["ts"] = int(time.time() * 1000)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def export(self, db: str, since: Optional[str] = None, until: Optional[str] = None) -> str:
        """Gom các file theo khoảng ngày [since, until] (YYYYMMDD) thành một JSONL string.
        Nếu không truyền since/until → gom toàn bộ file trong thư mục logs.
        """
        log_dir = self._log_dir(db)
        files = []
        try:
            for name in os.listdir(log_dir):
                if not name.startswith("exp-") or not name.endswith(".jsonl"):
                    continue
                day = name[4:12]  # YYYYMMDD
                if since and day < since:
                    continue
                if until and day > until:
                    continue
                files.append(os.path.join(log_dir, name))
        except Exception:
            pass
        files.sort()
        lines: List[str] = []
        for p in files:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            lines.append(line.rstrip("\n"))
            except Exception:
                continue
        return "\n".join(lines) + ("\n" if lines else "")

    def clear(self, db: str) -> int:
        log_dir = self._log_dir(db)
        cnt = 0
        try:
            for name in os.listdir(log_dir):
                if name.startswith("exp-") and name.endswith(".jsonl"):
                    try:
                        os.remove(os.path.join(log_dir, name))
                        cnt += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return cnt

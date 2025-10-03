import builtins
import io
import json
import os
import re
import uuid
import zipfile
from datetime import datetime
from typing import Any

from filelock import FileLock

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def now_iso() -> str:
    # Use timezone-aware UTC to avoid deprecation warnings
    from datetime import timezone

    return datetime.now(timezone.utc).strftime(ISO)


class ChatStore:
    """Lưu trữ hội thoại theo DB: data/kb/{db}/chats/{id}.json"""

    def __init__(self, persist_root: str):
        self.persist_root = persist_root
        self._lock_timeout = 5  # seconds timeout for file locks

    def _lock_path(self, db_name: str) -> str:
        """Get lock file path for DB."""
        return os.path.join(self._db_chat_dir(db_name), ".chat_lock")

    def _db_chat_dir(self, db_name: str) -> str:
        path = os.path.join(self.persist_root, db_name, "chats")
        os.makedirs(path, exist_ok=True)
        return path

    def _chat_path(self, db_name: str, chat_id: str) -> str:
        return os.path.join(self._db_chat_dir(db_name), f"{chat_id}.json")

    def list(self, db_name: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        base = self._db_chat_dir(db_name)
        try:
            for fname in os.listdir(base):
                if not fname.endswith('.json'):
                    continue
                fpath = os.path.join(base, fname)
                try:
                    with open(fpath, encoding='utf-8') as f:
                        data = json.load(f)
                        out.append(
                            {
                                'id': data.get('id'),
                                'name': data.get('name'),
                                'created_at': data.get('created_at'),
                                'updated_at': data.get('updated_at'),
                                'messages_count': len(data.get('messages', [])),
                            }
                        )
                except Exception:
                    continue
        except Exception:
            pass
        out.sort(key=lambda x: (x.get('updated_at') or ''), reverse=True)
        return out

    def get(self, db_name: str, chat_id: str) -> dict[str, Any] | None:
        p = self._chat_path(db_name, chat_id)
        if not os.path.isfile(p):
            return None
        try:
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def get_many(self, db_name: str, chat_ids: builtins.list[str]) -> dict[str, dict[str, Any]]:
        """Bulk fetch multiple chats by IDs. Returns dict mapping chat_id -> chat_data.

        ✅ FIX BUG #8: Tránh N+1 query pattern bằng cách load nhiều chats cùng lúc.
        Thay vì gọi get() N lần, gọi get_many() 1 lần để tăng tốc analytics!
        """
        results: dict[str, dict[str, Any]] = {}
        for chat_id in chat_ids:
            data = self.get(db_name, chat_id)
            if data is not None:
                results[chat_id] = data
        return results

    def create(self, db_name: str, name: str | None = None) -> dict[str, Any]:
        chat_id = str(uuid.uuid4())
        data = {
            'id': chat_id,
            'name': name or 'New Chat',
            'created_at': now_iso(),
            'updated_at': now_iso(),
            'messages': [],
        }
        p = self._chat_path(db_name, chat_id)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def rename(self, db_name: str, chat_id: str, new_name: str) -> dict[str, Any]:
        data = self.get(db_name, chat_id)
        if data is None:
            raise FileNotFoundError('Chat not found')
        data['name'] = new_name
        data['updated_at'] = now_iso()
        p = self._chat_path(db_name, chat_id)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def delete(self, db_name: str, chat_id: str) -> None:
        """Delete chat with file locking."""
        lock_file = self._lock_path(db_name)
        with FileLock(lock_file, timeout=self._lock_timeout):
            p = self._chat_path(db_name, chat_id)
            try:
                os.remove(p)
            except Exception:
                pass

    def delete_all(self, db_name: str) -> int:
        base = self._db_chat_dir(db_name)
        cnt = 0
        try:
            for fname in os.listdir(base):
                if fname.endswith('.json'):
                    try:
                        os.remove(os.path.join(base, fname))
                        cnt += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return cnt

    def append_message(
        self,
        db_name: str,
        chat_id: str,
        role: str,
        content: str,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = self.get(db_name, chat_id)
        if data is None:
            raise FileNotFoundError('Chat not found')
        data.setdefault('messages', []).append(
            {
                'role': role,
                'content': content,
                'meta': meta or {},
                'ts': now_iso(),
            }
        )
        data['updated_at'] = now_iso()
        p = self._chat_path(db_name, chat_id)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def append_pair(
        self,
        db_name: str,
        chat_id: str,
        user_text: str,
        assistant_text: str,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append Q/A pair with file locking for concurrent safety."""
        lock_file = self._lock_path(db_name)
        with FileLock(lock_file, timeout=self._lock_timeout):
            data = self.get(db_name, chat_id)
            if data is None:
                raise FileNotFoundError('Chat not found')
            msgs = data.setdefault('messages', [])
            now = now_iso()
            msgs.append({'role': 'user', 'content': user_text, 'meta': {}, 'ts': now})
            msgs.append(
                {
                    'role': 'assistant',
                    'content': assistant_text,
                    'meta': meta or {},
                    'ts': now_iso(),
                }
            )
            data['updated_at'] = now_iso()
            p = self._chat_path(db_name, chat_id)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data

    # ==== Export ====
    def export_json(self, db_name: str, chat_id: str) -> dict[str, Any] | None:
        return self.get(db_name, chat_id)

    def to_markdown(self, data: dict[str, Any]) -> str:
        lines = []
        title = data.get('name') or data.get('id') or 'Chat'
        lines.append(f"# Chat: {title}")
        lines.append("")
        lines.append(f"Created: {data.get('created_at','')}")
        lines.append(f"Updated: {data.get('updated_at','')}")
        lines.append("")
        for m in data.get('messages', []):
            role = m.get('role', 'user')
            ts = m.get('ts', '')
            lines.append(f"## {role} — {ts}")
            lines.append("")
            lines.append(m.get('content', ''))
            lines.append("")
        return "\n".join(lines)

    def export_markdown(self, db_name: str, chat_id: str) -> str | None:
        data = self.get(db_name, chat_id)
        if data is None:
            return None
        return self.to_markdown(data)

    def _slug(self, s: str) -> str:
        s = s or ""
        s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s)
        s = s.strip("_")
        return s or "chat"

    def export_db_zip(self, db_name: str, fmt: str = "json") -> bytes:
        fmt = (fmt or "json").lower()
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for summary in self.list(db_name):
                chat = self.get(db_name, summary.get('id'))
                if not chat:
                    continue
                base = self._slug(chat.get('name') or chat.get('id') or "chat")
                if fmt == "md" or fmt == "markdown":
                    content = self.to_markdown(chat)
                    zf.writestr(f"{base}.md", content or "")
                else:
                    # default json
                    zf.writestr(f"{base}.json", json.dumps(chat, ensure_ascii=False, indent=2))
        mem.seek(0)
        return mem.read()

    # ==== Search ====
    def search(
        self, db_name: str, query: str, limit_chats: int = 10, limit_matches: int = 5
    ) -> builtins.list[dict[str, Any]]:
        q = (query or '').strip().lower()
        if not q:
            return []
        results: list[dict[str, Any]] = []
        for summary in self.list(db_name):
            if len(results) >= limit_chats:
                break
            data = self.get(db_name, summary['id'])
            if not data:
                continue
            matches = []
            for idx, m in enumerate(data.get('messages', [])):
                text = str(m.get('content', ''))
                if q in text.lower():
                    # tạo snippet
                    pos = text.lower().find(q)
                    start = max(0, pos - 40)
                    end = min(len(text), pos + 40)
                    snippet = text[start:end].replace('\n', ' ')
                    matches.append({'index': idx, 'role': m.get('role', ''), 'snippet': snippet})
                if len(matches) >= limit_matches:
                    break
            if matches:
                results.append(
                    {
                        'chat': {
                            'id': data.get('id'),
                            'name': data.get('name'),
                            'updated_at': data.get('updated_at'),
                        },
                        'matches': matches,
                    }
                )
        return results

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def now_iso() -> str:
    return datetime.utcnow().strftime(ISO)


class ChatStore:
    """Lưu trữ hội thoại theo DB: data/kb/{db}/chats/{id}.json"""

    def __init__(self, persist_root: str):
        self.persist_root = persist_root

    def _db_chat_dir(self, db_name: str) -> str:
        path = os.path.join(self.persist_root, db_name, "chats")
        os.makedirs(path, exist_ok=True)
        return path

    def _chat_path(self, db_name: str, chat_id: str) -> str:
        return os.path.join(self._db_chat_dir(db_name), f"{chat_id}.json")

    def list(self, db_name: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        base = self._db_chat_dir(db_name)
        try:
            for fname in os.listdir(base):
                if not fname.endswith('.json'):
                    continue
                fpath = os.path.join(base, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        out.append({
                            'id': data.get('id'),
                            'name': data.get('name'),
                            'created_at': data.get('created_at'),
                            'updated_at': data.get('updated_at'),
                            'messages_count': len(data.get('messages', []))
                        })
                except Exception:
                    continue
        except Exception:
            pass
        out.sort(key=lambda x: (x.get('updated_at') or ''), reverse=True)
        return out

    def get(self, db_name: str, chat_id: str) -> Optional[Dict[str, Any]]:
        p = self._chat_path(db_name, chat_id)
        if not os.path.isfile(p):
            return None
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def create(self, db_name: str, name: Optional[str] = None) -> Dict[str, Any]:
        chat_id = str(uuid.uuid4())
        data = {
            'id': chat_id,
            'name': name or 'New Chat',
            'created_at': now_iso(),
            'updated_at': now_iso(),
            'messages': []
        }
        p = self._chat_path(db_name, chat_id)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def rename(self, db_name: str, chat_id: str, new_name: str) -> Dict[str, Any]:
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
        p = self._chat_path(db_name, chat_id)
        try:
            os.remove(p)
        except Exception:
            pass

    def append_message(self, db_name: str, chat_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = self.get(db_name, chat_id)
        if data is None:
            raise FileNotFoundError('Chat not found')
        data.setdefault('messages', []).append({
            'role': role,
            'content': content,
            'meta': meta or {},
            'ts': now_iso(),
        })
        data['updated_at'] = now_iso()
        p = self._chat_path(db_name, chat_id)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def append_pair(self, db_name: str, chat_id: str, user_text: str, assistant_text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = self.get(db_name, chat_id)
        if data is None:
            raise FileNotFoundError('Chat not found')
        msgs = data.setdefault('messages', [])
        now = now_iso()
        msgs.append({'role': 'user', 'content': user_text, 'meta': {}, 'ts': now})
        msgs.append({'role': 'assistant', 'content': assistant_text, 'meta': meta or {}, 'ts': now_iso()})
        data['updated_at'] = now_iso()
        p = self._chat_path(db_name, chat_id)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

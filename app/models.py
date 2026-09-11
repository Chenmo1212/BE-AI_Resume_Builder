"""
models.py — In-memory stores for stateless pipeline runner.
All data lives only for the lifetime of the process (ephemeral).
MongoDB is no longer required.
"""
from __future__ import annotations
import threading
from datetime import datetime
from typing import Optional, Dict, Any


def _new_id() -> str:
    import uuid
    return str(uuid.uuid4())


class _InMemoryStore:
    """Thread-safe in-memory key-value store with soft-delete support."""

    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, data: dict) -> str:
        doc_id = data.get('id') or _new_id()
        now = datetime.now()
        doc = {**data, 'id': doc_id, 'create_time': now, 'update_time': now, 'is_delete': False}
        with self._lock:
            self._data[doc_id] = doc
        return doc_id

    def update(self, doc_id: str, update_data: dict) -> int:
        with self._lock:
            doc = self._data.get(doc_id)
            if doc is None or doc.get('is_delete'):
                return 0
            doc.update({k: v for k, v in update_data.items() if k != 'id'})
            doc['update_time'] = datetime.now()
        return 1

    def delete(self, doc_id: str) -> int:
        with self._lock:
            doc = self._data.get(doc_id)
            if doc is None or doc.get('is_delete'):
                return 0
            doc['is_delete'] = True
            doc['delete_time'] = datetime.now()
        return 1

    def get(self, doc_id: str) -> Optional[dict]:
        with self._lock:
            doc = self._data.get(doc_id)
            if doc is None or doc.get('is_delete'):
                return None
            return dict(doc)

    def query(self, **kwargs) -> Optional[dict]:
        with self._lock:
            for doc in self._data.values():
                if doc.get('is_delete'):
                    continue
                if all(doc.get(k) == v for k, v in kwargs.items()):
                    return dict(doc)
        return None

    def get_by_ids(self, ids) -> list:
        with self._lock:
            return [dict(self._data[i]) for i in ids if i in self._data and not self._data[i].get('is_delete')]

    def list(self) -> list:
        with self._lock:
            return [dict(doc) for doc in self._data.values() if not doc.get('is_delete')]


# Module-level singletons — one per logical collection
_resume_store = _InMemoryStore()
_job_store = _InMemoryStore()
_task_store = _InMemoryStore()
_prompt_template_store = _InMemoryStore()


class ResumeManager:
    def create(self, data: dict) -> str:
        data.setdefault('is_raw', True)
        data.setdefault('raw_id', '')
        data.setdefault('job_id', '')
        return _resume_store.create(data)

    def update(self, doc_id: str, data: dict) -> int:
        return _resume_store.update(doc_id, data)

    def delete(self, doc_id: str) -> int:
        return _resume_store.delete(doc_id)

    def get(self, doc_id: str) -> Optional[dict]:
        return _resume_store.get(doc_id)

    def get_by_ids(self, ids) -> list:
        return _resume_store.get_by_ids(list(ids))

    def list(self) -> list:
        return _resume_store.list()


class JobManager:
    def create(self, data: dict) -> str:
        return _job_store.create(data)

    def update(self, doc_id: str, data: dict) -> int:
        return _job_store.update(doc_id, data)

    def delete(self, doc_id: str) -> int:
        return _job_store.delete(doc_id)

    def get(self, doc_id: str) -> Optional[dict]:
        return _job_store.get(doc_id)

    def get_by_ids(self, ids) -> list:
        return _job_store.get_by_ids(list(ids))

    def list(self) -> list:
        return _job_store.list()


class TaskManager:
    def create(self, data: dict) -> str:
        return _task_store.create(data)

    def update(self, doc_id: str, data: dict) -> int:
        return _task_store.update(doc_id, data)

    def get(self, doc_id: str) -> Optional[dict]:
        return _task_store.get(doc_id)

    def query(self, **kwargs) -> Optional[dict]:
        return _task_store.query(**kwargs)

    def list(self) -> list:
        return _task_store.list()


class PromptTemplateManager:
    """Minimal stub — prompt templates are now managed client-side.
    Kept for backwards-compat with any remaining route references."""

    def get(self, doc_id: str) -> Optional[dict]:
        return _prompt_template_store.get(doc_id)

    def list_all(self) -> list:
        return _prompt_template_store.list()

    def update_with_history(self, template_id: str, new_messages: list) -> int:
        doc = _prompt_template_store.get(template_id)
        if not doc:
            return 0
        new_version = doc.get('version', 1) + 1
        _prompt_template_store.update(template_id, {'messages': new_messages, 'version': new_version})
        return new_version

"""
In-memory session store.

A "session" bundles:
  - a per-session FAISS vector store (so sources from different users
    never mix)
  - the list of loaded SourceMeta records
  - the running chat history (for multi-turn memory)

For this assignment scope an in-memory store is appropriate and explicitly
called out as a simplification in the README. Swapping this for
Redis/Supabase later only requires changing this module.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from app.config import get_settings
from app.schemas import ChatMessage, SourceMeta
from app.services.vector_store import VectorStore

_settings = get_settings()


@dataclass
class Session:
    session_id: str
    vector_store: VectorStore = field(default_factory=VectorStore)
    sources: dict[str, SourceMeta] = field(default_factory=dict)
    history: list[ChatMessage] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)

    def touch(self):
        self.last_active = time.time()

    def source_titles(self) -> dict[str, str]:
        return {sid: meta.title for sid, meta in self.sources.items()}


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session:
            session.touch()
        return session

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id:
            existing = self.get(session_id)
            if existing:
                return existing
        return self.create()

    def cleanup_expired(self):
        cutoff = time.time() - _settings.session_ttl_minutes * 60
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.last_active < cutoff]
            for sid in expired:
                del self._sessions[sid]


# Single process-wide instance
session_store = SessionStore()

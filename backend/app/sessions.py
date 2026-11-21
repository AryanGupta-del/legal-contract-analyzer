"""In-memory, expiring document sessions. Nothing is written to disk."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from .engine.analysis import Document
from .engine.schemas import Chunk, KeyTerms, RiskReport


@dataclass
class Session:
    id: str
    doc: Document
    pdf: bytes
    touched: float = field(default_factory=time.time)
    terms: KeyTerms | None = None
    risks: RiskReport | None = None
    risk_src: dict[int, Chunk] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


class SessionStore:
    def __init__(self, ttl_s: int, max_sessions: int):
        self.ttl_s, self.max_sessions = ttl_s, max_sessions
        self._items: dict[str, Session] = {}
        self._lock = threading.Lock()

    def add(self, doc: Document, pdf: bytes) -> Session:
        with self._lock:
            self._purge()
            sid = uuid.uuid4().hex
            self._items[sid] = Session(sid, doc, pdf)
            return self._items[sid]

    def get(self, sid: str) -> Session | None:
        with self._lock:
            self._purge()
            s = self._items.get(sid)
            if s:
                s.touched = time.time()
            return s

    def _purge(self) -> None:
        now = time.time()
        for k in [k for k, s in self._items.items() if now - s.touched > self.ttl_s]:
            del self._items[k]
        while len(self._items) >= self.max_sessions:  # evict least recently used
            del self._items[min(self._items, key=lambda k: self._items[k].touched)]

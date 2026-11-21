"""Shared singletons, exposed as FastAPI dependencies so tests can override them."""
from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from .config import settings
from .engine.llm import LLM, resolve_api_key
from .engine.retrieval import Embedder, load_embedder
from .sessions import SessionStore

store = SessionStore(settings.session_ttl_s, settings.max_sessions)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return load_embedder()


@lru_cache(maxsize=1)
def _llm() -> LLM | None:
    key = resolve_api_key()
    return LLM(key) if key else None


def get_llm() -> LLM:
    llm = _llm()
    if llm is None:
        raise HTTPException(503, "The server has no GROQ_API_KEY configured.")
    return llm


def get_store() -> SessionStore:
    return store

"""Tiny sliding-window rate limiter keyed by client IP. Protects the public demo's LLM quota."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def make_limiter(per_minute: int):
    def limiter(request: Request) -> None:
        q, now = _hits[client_ip(request)], time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= per_minute:
            raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
        q.append(now)

    return limiter

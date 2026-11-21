"""FastAPI entry point:  uvicorn app.main:app --reload"""
from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .deps import get_embedder
from .routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=get_embedder, daemon=True).start()  # warm the model off the request path
    yield


app = FastAPI(title="Legal Contract Analyzer API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health(embedder=Depends(get_embedder)):
    return {"status": "ok", "embedder": type(embedder).__name__}

"""Settings from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()])
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    session_ttl_s: int = int(os.getenv("SESSION_TTL_S", "3600"))
    max_sessions: int = int(os.getenv("MAX_SESSIONS", "50"))
    llm_calls_per_min: int = int(os.getenv("LLM_CALLS_PER_MIN", "20"))
    samples_dir: Path = ROOT / "samples"


settings = Settings()

"""Request / response models for the HTTP API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .engine.schemas import KeyTerms, Risk


class DocInfo(BaseModel):
    id: str
    name: str
    pages: int
    clauses: int


class ClauseOut(BaseModel):
    page: int
    label: str
    text: str


class RiskOut(Risk):
    clause: ClauseOut | None = None


class OverviewOut(BaseModel):
    key_terms: KeyTerms
    summary: str
    score: int
    counts: dict[str, int]
    risks: list[RiskOut]


class Turn(BaseModel):
    q: str = Field(max_length=500)
    a: str = Field(max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    history: list[Turn] = Field(default_factory=list, max_length=6)


class SourceOut(BaseModel):
    n: int
    page: int
    label: str
    text: str


class AskOut(BaseModel):
    answer: str
    found: bool
    sources: list[SourceOut]


class CompareIn(BaseModel):
    doc_a: str
    doc_b: str
    aspects: list[str] = Field(default_factory=list, max_length=10)

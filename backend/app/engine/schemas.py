"""Typed data models: document chunks and the structured LLM outputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


@dataclass(frozen=True)
class Chunk:
    id: int
    text: str
    page: int
    clause_ref: Optional[str] = None  # e.g. "5.2" or "Article IV"
    heading: Optional[str] = None  # e.g. "Termination for Convenience"

    @property
    def label(self) -> str:
        parts = []
        if self.clause_ref:
            parts.append(f"§{self.clause_ref}" if self.clause_ref[0].isdigit() else self.clause_ref)
        if self.heading:
            parts.append(self.heading)
        return " ".join(parts) if parts else "Preamble"

    @property
    def embed_text(self) -> str:
        return f"{self.heading}. {self.text}" if self.heading else self.text


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


# ---------- structured LLM outputs ----------

Severity = Literal["high", "medium", "low"]


class Risk(BaseModel):
    title: str
    category: str = "Other"
    severity: Severity = "medium"
    party_affected: str = "Unclear"
    explanation: str
    recommendation: str = ""
    source_id: int = Field(description="Number of the source passage the risk comes from")

    @field_validator("severity", mode="before")
    @classmethod
    def _norm_severity(cls, v):
        v = str(v).strip().lower()
        return v if v in {"high", "medium", "low"} else "medium"


class RiskReport(BaseModel):
    summary: str = ""
    risks: list[Risk] = Field(default_factory=list)

    @property
    def score(self) -> int:
        """0-100 heuristic exposure score (higher = riskier)."""
        weights = {"high": 25, "medium": 10, "low": 3}
        return min(100, sum(weights[r.severity] for r in self.risks))

    @property
    def counts(self) -> dict[str, int]:
        out = {"high": 0, "medium": 0, "low": 0}
        for r in self.risks:
            out[r.severity] += 1
        return out


class QAResult(BaseModel):
    answer: str
    found: bool = True
    sources_used: list[int] = Field(default_factory=list)


class KeyTerms(BaseModel):
    parties: list[str] = Field(default_factory=list)
    effective_date: str = "Not specified"
    term: str = "Not specified"
    renewal: str = "Not specified"
    termination: str = "Not specified"
    notice_period: str = "Not specified"
    payment_terms: str = "Not specified"
    liability_cap: str = "Not specified"
    governing_law: str = "Not specified"

    @field_validator("*", mode="before")
    @classmethod
    def _none_to_default(cls, v, info):
        if v is None:
            return [] if info.field_name == "parties" else "Not specified"
        return v


class ComparisonRow(BaseModel):
    aspect: str
    contract_a: str
    contract_b: str
    riskier: Literal["a", "b", "similar"] = "similar"
    note: str = ""

    @field_validator("riskier", mode="before")
    @classmethod
    def _norm(cls, v):
        v = str(v).strip().lower()
        return v if v in {"a", "b", "similar"} else "similar"


class Comparison(BaseModel):
    rows: list[ComparisonRow] = Field(default_factory=list)
    verdict: str = ""

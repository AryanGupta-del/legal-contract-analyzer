"""Question answering, risk analysis, key-term extraction and comparison.

Every function takes the LLM and a `Document`, returns validated Pydantic objects, and keeps
the source passages so the UI can show citations.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .ingest import chunk_pages, extract_pages, Page
from .llm import LLM
from .retrieval import Embedder, HybridIndex
from .schemas import (Chunk, Comparison, Hit, KeyTerms, QAResult, Risk, RiskReport)


@dataclass
class Document:
    name: str
    pages: list[Page]
    chunks: list[Chunk]
    index: HybridIndex
    digest: str = ""

    @property
    def n_pages(self) -> int:
        return len(self.pages)


def load_document(name: str, data: bytes, embedder: Embedder, reranker=None) -> Document:
    pages = extract_pages(data)
    chunks = chunk_pages(pages)
    return Document(name, pages, chunks, HybridIndex(chunks, embedder, reranker),
                    hashlib.sha256(data).hexdigest()[:16])


def _format_sources(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{i}] (page {h.chunk.page}, {h.chunk.label})\n{h.chunk.text}"
                       for i, h in enumerate(hits, 1))


# ---------------------------------------------------------------- Q&A

@dataclass
class Answer:
    text: str
    found: bool
    sources: list[tuple[int, Hit]] = field(default_factory=list)  # (citation number, passage) actually cited


def answer_question(llm: LLM, doc: Document, question: str,
                    history: list[tuple[str, str]] | None = None, k: int = 5) -> Answer:
    query = question
    if history and len(question.split()) < 6:  # short follow-up: borrow context for retrieval
        query = f"{history[-1][0]} {question}"
    hits = doc.index.search(query, k=k)
    convo = "".join(f"User: {q}\nAssistant: {a}\n" for q, a in (history or [])[-3:])
    prompt = (
        f"Answer the question using ONLY the numbered passages from the contract.\n"
        f"Cite passages inline like [1] or [2][3]. If the passages do not contain the answer, "
        f'set "found" to false and say so plainly.\n\n'
        f"Previous conversation:\n{convo or '(none)'}\n\nPassages:\n{_format_sources(hits)}\n\n"
        f"Question: {question}\n\n"
        f'JSON schema: {{"answer": string, "found": boolean, "sources_used": [int]}}'
    )
    res = llm.complete_json(prompt, QAResult)
    used = [n for n in dict.fromkeys(res.sources_used) if 1 <= n <= len(hits)]
    return Answer(res.answer, res.found, [(n, hits[n - 1]) for n in used] if res.found else [])


# ---------------------------------------------------------------- risks

RISK_CATEGORIES: dict[str, list[str]] = {
    "Liability": ["liable", "liability", "damages", "consequential", "limitation of"],
    "Indemnity": ["indemnify", "indemnification", "hold harmless"],
    "Termination": ["terminate", "termination", "cancel"],
    "Auto-renewal": ["auto-renew", "automatically renew", "automatic renewal", "renewal term"],
    "Penalties": ["penalty", "penalties", "liquidated damages", "late fee", "forfeit"],
    "Payment": ["non-refundable", "nonrefundable", "interest on", "fees are"],
    "Non-compete": ["non-compete", "noncompete", "exclusive", "exclusivity", "non-solicit"],
    "Dispute resolution": ["arbitration", "jurisdiction", "venue", "waive", "class action"],
    "IP & data": ["intellectual property", "assigns", "work product", "personal data"],
    "Confidentiality": ["confidential"],
}


def candidate_risk_chunks(chunks: list[Chunk], limit: int = 10) -> list[Chunk]:
    """Cheap keyword pre-filter so the LLM only reads the clauses that matter."""
    scored = []
    for c in chunks:
        low = c.embed_text.lower()
        score = sum(any(kw in low for kw in kws) for kws in RISK_CATEGORIES.values())
        if score:
            scored.append((score, c))
    scored.sort(key=lambda sc: (-sc[0], sc[1].id))
    return sorted((c for _, c in scored[:limit]), key=lambda c: c.id)


def analyze_risks(llm: LLM, doc: Document) -> tuple[RiskReport, dict[int, Chunk]]:
    """Returns the report and a map source_id -> Chunk so the UI can quote the clause."""
    cands = candidate_risk_chunks(doc.chunks)
    if not cands:
        return RiskReport(summary="No risk-bearing clauses were detected."), {}
    src = {i: c for i, c in enumerate(cands, 1)}
    body = "\n\n".join(f"[{i}] (page {c.page}, {c.label})\n{c.text}" for i, c in src.items())
    prompt = (
        "You review contracts for the party who is about to SIGN them (the customer/recipient "
        "unless the text clearly says otherwise). From the numbered passages, list genuine risks: "
        "one-sided terms, uncapped or unlimited liability, hard-to-exit termination, automatic "
        "renewal, penalties, broad indemnities, unusual dispute clauses. Skip boilerplate that is "
        "standard and balanced. Rate severity honestly: high = could cause major financial/legal "
        "harm, medium = worth negotiating, low = minor.\n\n"
        f"Passages:\n{body}\n\n"
        'JSON schema: {"summary": string (2 sentences), "risks": [{"title": string, '
        '"category": string, "severity": "high"|"medium"|"low", "party_affected": string, '
        '"explanation": string (plain English, 1-2 sentences), "recommendation": string '
        '(what to negotiate), "source_id": int}]}'
    )
    report = llm.complete_json(prompt, RiskReport, max_tokens=6000)
    report.risks = [r for r in report.risks if r.source_id in src]
    order = {"high": 0, "medium": 1, "low": 2}
    report.risks.sort(key=lambda r: order[r.severity])
    return report, src


# ---------------------------------------------------------------- key terms

_TERM_QUERIES = [
    "parties to this agreement effective date",
    "term duration renewal",
    "termination notice period",
    "payment fees invoices",
    "limitation of liability cap",
    "governing law jurisdiction",
]


def extract_key_terms(llm: LLM, doc: Document) -> KeyTerms:
    seen: dict[int, Hit] = {}
    for q in _TERM_QUERIES:
        for h in doc.index.search(q, k=2):
            seen.setdefault(h.chunk.id, h)
    hits = sorted(seen.values(), key=lambda h: h.chunk.id)
    prompt = (
        "Extract key terms from the passages. Use short, concrete values (e.g. '12 months, "
        "auto-renews yearly', '30 days written notice'). Use \"Not specified\" when absent.\n\n"
        f"Passages:\n{_format_sources(hits)}\n\n"
        'JSON schema: {"parties": [string], "effective_date": string, "term": string, '
        '"renewal": string, "termination": string, "notice_period": string, '
        '"payment_terms": string, "liability_cap": string, "governing_law": string}'
    )
    return llm.complete_json(prompt, KeyTerms)


# ---------------------------------------------------------------- comparison

DEFAULT_ASPECTS = [
    "Term and renewal",
    "Termination and notice period",
    "Limitation of liability",
    "Indemnification",
    "Payment terms and fees",
    "Confidentiality",
    "Governing law and dispute resolution",
]


def compare_documents(llm: LLM, a: Document, b: Document,
                      aspects: list[str] | None = None) -> Comparison:
    aspects = aspects or DEFAULT_ASPECTS
    blocks = []
    for asp in aspects:
        pa = _format_sources(a.index.search(asp, k=2))
        pb = _format_sources(b.index.search(asp, k=2))
        blocks.append(f"### {asp}\nCONTRACT A passages:\n{pa}\n\nCONTRACT B passages:\n{pb}")
    prompt = (
        f"Compare Contract A ({a.name}) and Contract B ({b.name}) on each aspect, using only the "
        "passages. For each aspect give a one-sentence summary per contract, say which is riskier "
        "for the signing party, and add a short note. If a contract is silent, say so.\n\n"
        + "\n\n".join(blocks)
        + '\n\nJSON schema: {"rows": [{"aspect": string, "contract_a": string, "contract_b": '
        'string, "riskier": "a"|"b"|"similar", "note": string}], "verdict": string (2-3 sentences)}'
    )
    return llm.complete_json(prompt, Comparison, max_tokens=6000)

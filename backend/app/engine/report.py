"""Markdown export of an analysis."""
from __future__ import annotations

from .analysis import Document
from .schemas import Chunk, KeyTerms, RiskReport

DISCLAIMER = "_Automated analysis for information only. This is not legal advice._"


def to_markdown(doc: Document, terms: KeyTerms | None, report: RiskReport | None,
                sources: dict[int, Chunk] | None = None) -> str:
    out = [f"# Contract analysis: {doc.name}", "", f"{doc.n_pages} pages · {len(doc.chunks)} clauses indexed", ""]
    if terms:
        out += ["## Key terms", "",
                f"- **Parties:** {', '.join(terms.parties) or 'Not specified'}",
                f"- **Effective date:** {terms.effective_date}",
                f"- **Term:** {terms.term}",
                f"- **Renewal:** {terms.renewal}",
                f"- **Termination:** {terms.termination}",
                f"- **Notice period:** {terms.notice_period}",
                f"- **Payment:** {terms.payment_terms}",
                f"- **Liability cap:** {terms.liability_cap}",
                f"- **Governing law:** {terms.governing_law}", ""]
    if report:
        out += [f"## Risk review (exposure score {report.score}/100)", "", report.summary, ""]
        for r in report.risks:
            chunk = (sources or {}).get(r.source_id)
            where = f" (page {chunk.page}, {chunk.label})" if chunk else ""
            out += [f"### [{r.severity.upper()}] {r.title}{where}",
                    f"- **Affects:** {r.party_affected}",
                    f"- **Why:** {r.explanation}",
                    f"- **Suggested action:** {r.recommendation}", ""]
    out.append(DISCLAIMER)
    return "\n".join(out)

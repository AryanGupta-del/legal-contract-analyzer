from pathlib import Path

import pytest

from app.engine.analysis import (analyze_risks, answer_question, candidate_risk_chunks,
                               compare_documents, load_document)
from app.engine.ingest import ExtractionError, Page, chunk_pages, extract_pages
from app.engine.retrieval import HashingEmbedder
from app.engine.schemas import Risk, RiskReport

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def sample(name):
    return (SAMPLES / name).read_bytes()


class FakeLLM:
    """Returns canned JSON keyed on a marker in the prompt."""
    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, prompt, schema, **kw):
        return schema.model_validate(self.payload)


def test_clause_chunking_keeps_structure():
    chunks = chunk_pages(extract_pages(sample("sample_saas_agreement_A.pdf")))
    refs = [c.clause_ref for c in chunks if c.clause_ref]
    assert refs == [str(i) for i in range(1, 9)]
    term = next(c for c in chunks if c.heading == "Term")
    assert "ninety (90) days" in term.text and term.page == 1


def test_long_clause_is_windowed_with_same_ref():
    text = "1. Scope. " + "word " * 500 + "\n2. Term. short\n3. Fees. short\n4. Law. short"
    chunks = chunk_pages([Page(1, text.replace(". ", ".\n", 0))], max_words=100, overlap=10)
    scope = [c for c in chunks if c.clause_ref == "1"]
    assert len(scope) > 3


def test_unstructured_text_falls_back_to_windows():
    chunks = chunk_pages([Page(1, "plain prose " * 400), Page(2, "more prose " * 50)])
    assert chunks and all(c.clause_ref is None for c in chunks)
    assert {c.page for c in chunks} == {1, 2}


def test_scanned_pdf_rejected():
    import pymupdf
    doc = pymupdf.open(); doc.new_page()
    with pytest.raises(ExtractionError):
        extract_pages(doc.tobytes())


def test_garbage_bytes_rejected():
    with pytest.raises(ExtractionError):
        extract_pages(b"not a pdf")


def test_hybrid_search_finds_lexical_match():
    doc = load_document("a.pdf", sample("sample_saas_agreement_A.pdf"), HashingEmbedder())
    top = doc.index.search("arbitration Singapore class action", k=1)[0]
    assert top.chunk.heading == "Governing Law and Disputes"


def test_risk_prefilter_picks_risky_clauses():
    doc = load_document("a.pdf", sample("sample_saas_agreement_A.pdf"), HashingEmbedder())
    labels = {c.heading for c in candidate_risk_chunks(doc.chunks)}
    assert {"Termination", "Limitation of Liability", "Indemnification"} <= labels


def test_risk_report_scoring_and_invalid_source_dropped():
    doc = load_document("a.pdf", sample("sample_saas_agreement_A.pdf"), HashingEmbedder())
    llm = FakeLLM({"summary": "s", "risks": [
        {"title": "t", "severity": "HIGH", "explanation": "e", "source_id": 1},
        {"title": "ghost", "severity": "low", "explanation": "e", "source_id": 999},
    ]})
    report, src = analyze_risks(llm, doc)
    assert [r.title for r in report.risks] == ["t"]
    assert report.score == 25 and report.counts["high"] == 1


def test_score_is_capped():
    r = Risk(title="x", severity="high", explanation="e", source_id=1)
    assert RiskReport(risks=[r] * 10).score == 100


def test_answer_maps_citations_and_drops_bad_ids():
    doc = load_document("a.pdf", sample("sample_saas_agreement_A.pdf"), HashingEmbedder())
    llm = FakeLLM({"answer": "90 days [1]", "found": True, "sources_used": [1, 1, 42]})
    ans = answer_question(llm, doc, "renewal notice period?")
    assert len(ans.sources) == 1 and ans.sources[0][0] == 1


def test_not_found_answer_has_no_sources():
    doc = load_document("a.pdf", sample("sample_saas_agreement_A.pdf"), HashingEmbedder())
    llm = FakeLLM({"answer": "Not in contract", "found": False, "sources_used": [1]})
    assert answer_question(llm, doc, "pet policy?").sources == []


def test_compare_normalises_bad_riskier_value():
    a = load_document("a.pdf", sample("sample_saas_agreement_A.pdf"), HashingEmbedder())
    b = load_document("b.pdf", sample("sample_saas_agreement_B.pdf"), HashingEmbedder())
    llm = FakeLLM({"rows": [{"aspect": "Term", "contract_a": "x", "contract_b": "y",
                             "riskier": "Contract A"}], "verdict": "v"})
    assert compare_documents(llm, a, b, ["Term"]).rows[0].riskier == "similar"


def test_llm_does_not_retry_on_missing_model(monkeypatch):
    import groq, httpx
    from app.engine.llm import LLM, LLMError

    calls = []

    class Boom:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls.append(kw)
                    req = httpx.Request("POST", "https://api.groq.com/x")
                    raise groq.NotFoundError("model not found", response=httpx.Response(404, request=req), body=None)

    llm = LLM.__new__(LLM)
    llm.client, llm.model = Boom, "gone-model"
    with pytest.raises(LLMError, match="gone-model"):
        llm.complete("hi")
    assert len(calls) == 1

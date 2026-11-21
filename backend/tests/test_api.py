"""API tests with the LLM and embedder swapped for fakes."""
import pytest
from fastapi.testclient import TestClient

from app import deps
from app.engine.retrieval import HashingEmbedder
from app.main import app
from app.ratelimit import _hits

PAYLOADS = {
    "RiskReport": {"summary": "Two one-sided terms.", "risks": [
        {"title": "Uncapped customer liability", "category": "Liability", "severity": "high",
         "party_affected": "Customer", "explanation": "No cap.", "recommendation": "Ask for a cap.",
         "source_id": 1}]},
    "KeyTerms": {"parties": ["Nimbus", "Acme"], "term": "12 months"},
    "QAResult": {"answer": "90 days [1]", "found": True, "sources_used": [1]},
    "Comparison": {"rows": [{"aspect": "Term", "contract_a": "auto-renews", "contract_b": "no renewal",
                             "riskier": "a", "note": ""}], "verdict": "A is riskier."},
}


class FakeLLM:
    calls = 0

    def complete_json(self, prompt, schema, **kw):
        FakeLLM.calls += 1
        return schema.model_validate(PAYLOADS[schema.__name__])


@pytest.fixture()
def client():
    _hits.clear()
    FakeLLM.calls = 0
    app.dependency_overrides[deps.get_llm] = lambda: FakeLLM()
    app.dependency_overrides[deps.get_embedder] = lambda: HashingEmbedder()
    yield TestClient(app)
    app.dependency_overrides.clear()


def sample(client, key="a"):
    r = client.post(f"/api/documents/sample/{key}")
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_sample_overview_and_pdf(client):
    doc = sample(client)
    assert doc["pages"] == 1 and doc["clauses"] == 9
    ov = client.get(f"/api/documents/{doc['id']}/overview").json()
    assert ov["score"] == 25 and ov["counts"]["high"] == 1
    assert ov["risks"][0]["clause"]["page"] == 1
    pdf = client.get(f"/api/documents/{doc['id']}/pdf")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")


def test_overview_is_cached(client):
    doc = sample(client)
    client.get(f"/api/documents/{doc['id']}/overview")
    before = FakeLLM.calls
    client.get(f"/api/documents/{doc['id']}/overview")
    assert FakeLLM.calls == before


def test_ask_returns_cited_sources(client):
    doc = sample(client)
    r = client.post(f"/api/documents/{doc['id']}/ask", json={"question": "Notice period?"})
    body = r.json()
    assert r.status_code == 200 and body["found"] and body["sources"][0]["n"] == 1


def test_compare(client):
    a, b = sample(client, "a"), sample(client, "b")
    r = client.post("/api/compare", json={"doc_a": a["id"], "doc_b": b["id"], "aspects": ["Term"]})
    assert r.json()["rows"][0]["riskier"] == "a"


def test_rejects_non_pdf_and_oversize(client):
    r = client.post("/api/documents", files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert r.status_code == 415
    big = b"%PDF" + b"0" * (10 * 1024 * 1024 + 10)
    assert client.post("/api/documents", files={"file": ("x.pdf", big)}).status_code == 413


def test_scanned_pdf_gives_422(client):
    import pymupdf
    d = pymupdf.open(); d.new_page()
    r = client.post("/api/documents", files={"file": ("s.pdf", d.tobytes())})
    assert r.status_code == 422 and "scanned" in r.json()["detail"].lower()


def test_unknown_session_404(client):
    assert client.get("/api/documents/nope/overview").status_code == 404


def test_validation_and_rate_limit(client):
    doc = sample(client)
    assert client.post(f"/api/documents/{doc['id']}/ask", json={"question": "x"}).status_code == 422
    codes = [client.post(f"/api/documents/{doc['id']}/ask", json={"question": "notice period?"}).status_code
             for _ in range(25)]
    assert 429 in codes


def test_report_download(client):
    doc = sample(client)
    r = client.get(f"/api/documents/{doc['id']}/report")
    assert "attachment" in r.headers["content-disposition"] and "Key terms" in r.text

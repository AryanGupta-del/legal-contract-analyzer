from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response

from .config import settings
from .deps import get_embedder, get_llm, get_store
from .engine.analysis import (analyze_risks, answer_question, compare_documents,
                              extract_key_terms, load_document)
from .engine.ingest import ExtractionError
from .engine.llm import LLM, LLMError
from .engine.report import to_markdown
from .engine.schemas import Comparison
from .models import (AskIn, AskOut, ClauseOut, CompareIn, DocInfo, OverviewOut, RiskOut,
                     SourceOut)
from .ratelimit import make_limiter
from .sessions import Session, SessionStore

router = APIRouter(prefix="/api")
llm_limit = make_limiter(settings.llm_calls_per_min)
upload_limit = make_limiter(30)


def _session(store: SessionStore, sid: str) -> Session:
    s = store.get(sid)
    if s is None:
        raise HTTPException(404, "This session expired. Please upload the contract again.")
    return s


def _create(store: SessionStore, embedder, name: str, data: bytes) -> DocInfo:
    try:
        doc = load_document(name, data, embedder)
    except ExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc
    s = store.add(doc, data)
    return DocInfo(id=s.id, name=name, pages=doc.n_pages, clauses=len(doc.chunks))


# ---------------------------------------------------------------- documents

@router.post("/documents", response_model=DocInfo, dependencies=[Depends(upload_limit)])
def upload_document(file: UploadFile, store: SessionStore = Depends(get_store),
                    embedder=Depends(get_embedder)):
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "Only PDF files are supported.")
    return _create(store, embedder, (file.filename or "contract.pdf")[:120], data)


@router.post("/documents/sample/{key}", response_model=DocInfo, dependencies=[Depends(upload_limit)])
def sample_document(key: str, store: SessionStore = Depends(get_store), embedder=Depends(get_embedder)):
    if key not in {"a", "b"}:
        raise HTTPException(404, "Unknown sample.")
    name = f"sample_saas_agreement_{key.upper()}.pdf"
    return _create(store, embedder, name, (settings.samples_dir / name).read_bytes())


@router.get("/documents/{sid}", response_model=DocInfo)
def get_document(sid: str, store: SessionStore = Depends(get_store)):
    s = _session(store, sid)
    return DocInfo(id=s.id, name=s.doc.name, pages=s.doc.n_pages, clauses=len(s.doc.chunks))


@router.get("/documents/{sid}/pdf")
def get_pdf(sid: str, store: SessionStore = Depends(get_store)):
    s = _session(store, sid)
    return Response(s.pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "inline", "Cache-Control": "private, max-age=600"})


# ---------------------------------------------------------------- analysis

def _ensure_overview(s: Session, llm: LLM) -> None:
    with s.lock:  # a double-click must not run the LLM twice
        if s.risks is not None and s.terms is not None:
            return
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_risk = pool.submit(analyze_risks, llm, s.doc)
                f_terms = pool.submit(extract_key_terms, llm, s.doc)
                (s.risks, s.risk_src), s.terms = f_risk.result(), f_terms.result()
        except LLMError as exc:
            raise HTTPException(502, str(exc)) from exc


@router.get("/documents/{sid}/overview", response_model=OverviewOut, dependencies=[Depends(llm_limit)])
def overview(sid: str, store: SessionStore = Depends(get_store), llm: LLM = Depends(get_llm)):
    s = _session(store, sid)
    _ensure_overview(s, llm)
    risks = []
    for r in s.risks.risks:
        c = s.risk_src.get(r.source_id)
        risks.append(RiskOut(**r.model_dump(),
                             clause=ClauseOut(page=c.page, label=c.label, text=c.text) if c else None))
    return OverviewOut(key_terms=s.terms, summary=s.risks.summary, score=s.risks.score,
                       counts=s.risks.counts, risks=risks)


@router.post("/documents/{sid}/ask", response_model=AskOut, dependencies=[Depends(llm_limit)])
def ask(sid: str, body: AskIn, store: SessionStore = Depends(get_store), llm: LLM = Depends(get_llm)):
    s = _session(store, sid)
    try:
        ans = answer_question(llm, s.doc, body.question, [(t.q, t.a) for t in body.history])
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from exc
    return AskOut(answer=ans.text, found=ans.found,
                  sources=[SourceOut(n=n, page=h.chunk.page, label=h.chunk.label, text=h.chunk.text)
                           for n, h in ans.sources])


@router.post("/compare", response_model=Comparison, dependencies=[Depends(llm_limit)])
def compare(body: CompareIn, store: SessionStore = Depends(get_store), llm: LLM = Depends(get_llm)):
    a, b = _session(store, body.doc_a), _session(store, body.doc_b)
    aspects = [x.strip()[:120] for x in body.aspects if x.strip()] or None
    try:
        return compare_documents(llm, a.doc, b.doc, aspects)
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/documents/{sid}/report", dependencies=[Depends(llm_limit)])
def report(sid: str, store: SessionStore = Depends(get_store), llm: LLM = Depends(get_llm)):
    s = _session(store, sid)
    _ensure_overview(s, llm)
    md = to_markdown(s.doc, s.terms, s.risks, s.risk_src)
    return PlainTextResponse(md, media_type="text/markdown",
                             headers={"Content-Disposition": 'attachment; filename="contract_analysis.md"'})

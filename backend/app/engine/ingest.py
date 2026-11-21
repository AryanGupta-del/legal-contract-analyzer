"""PDF text extraction and clause-aware chunking.

Contracts are structured documents, so instead of cutting fixed windows we first split on
clause headings ("5.2 Termination", "ARTICLE IV") and only window-split clauses that are
too long. Every chunk keeps its page number and clause reference for citations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import Chunk

MAX_PAGES = 80
MIN_CHARS = 200  # below this the PDF is almost certainly scanned images


class ExtractionError(ValueError):
    """Raised when a PDF cannot be turned into usable text."""


@dataclass(frozen=True)
class Page:
    number: int
    text: str


HEADING_RE = re.compile(
    r"""^\s*(?:
        (?P<art>(?:ARTICLE|Article|SECTION|Section)\s+(?:\d+|[IVXLC]+))[.:\-–]?\s*(?P<t1>.*)
        |
        (?P<num>\d{1,2}(?:\.\d{1,2}){1,3}\.?|\d{1,2}[.)])\s+(?P<t2>[A-Z].*)
    )$""",
    re.VERBOSE,
)
_NOISE_RE = re.compile(r"^(?:page\s+\d+(?:\s+of\s+\d+)?|\d{1,3})$", re.IGNORECASE)


def extract_pages(data: bytes) -> list[Page]:
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24.3
    except ImportError:
        import fitz

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # corrupt / not a PDF
        raise ExtractionError("This file could not be opened as a PDF.") from exc
    if doc.page_count > MAX_PAGES:
        raise ExtractionError(f"Contract has {doc.page_count} pages; the limit is {MAX_PAGES}.")
    pages = [Page(i + 1, p.get_text("text")) for i, p in enumerate(doc)]
    if sum(len(p.text.strip()) for p in pages) < MIN_CHARS:
        raise ExtractionError(
            "No readable text found. This looks like a scanned PDF; run OCR on it first."
        )
    return pages


def _split_title(rest: str) -> tuple[str, str]:
    m = re.match(r"^([^.]{2,70})\.\s*(.*)$", rest)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    if len(rest) <= 80:
        return rest.strip(), ""
    return "", rest.strip()


def split_clauses(pages: list[Page]) -> list[dict]:
    """Group lines into clauses; each carries the page where it starts."""
    clauses: list[dict] = []
    cur = {"ref": None, "heading": None, "page": 1, "lines": []}

    def flush():
        text = " ".join(cur["lines"]).strip()
        if text or cur["heading"]:
            clauses.append({**cur, "text": text})

    for page in pages:
        for raw in page.text.splitlines():
            line = raw.strip()
            if not line or _NOISE_RE.match(line):
                continue
            m = HEADING_RE.match(line)
            if m:
                flush()
                ref = (m.group("art") or m.group("num")).rstrip(".)")
                title, body = _split_title(m.group("t1") if m.group("art") else m.group("t2"))
                cur = {"ref": ref, "heading": title or None, "page": page.number,
                       "lines": [body] if body else []}
            else:
                if not cur["lines"] and cur["ref"] is None and not clauses:
                    cur["page"] = page.number
                cur["lines"].append(line)
    flush()
    return clauses


def _window(words: list[str], size: int, overlap: int) -> list[str]:
    if len(words) <= size:
        return [" ".join(words)]
    out, step = [], max(1, size - overlap)
    for start in range(0, len(words), step):
        out.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return out


def chunk_pages(pages: list[Page], max_words: int = 180, overlap: int = 30) -> list[Chunk]:
    """Clause-aware chunking with a plain sliding-window fallback for unstructured text."""
    clauses = split_clauses(pages)
    structured = sum(1 for c in clauses if c["ref"]) >= 3
    if not structured:
        clauses = [{"ref": None, "heading": None, "page": p.number,
                    "text": " ".join(p.text.split())} for p in pages if p.text.strip()]

    chunks: list[Chunk] = []
    for c in clauses:
        words = c["text"].split()
        if not words:
            continue
        for piece in _window(words, max_words, overlap):
            chunks.append(Chunk(id=len(chunks), text=piece, page=c["page"],
                                clause_ref=c["ref"], heading=c["heading"]))
    return chunks

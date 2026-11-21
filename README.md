# ⚖️ Legal Contract Analyzer

A full-stack app that turns a contract PDF into **key terms, a severity-rated risk review and cited answers in plain English**, with the original PDF beside the analysis so every claim can be checked. It can also compare two contracts clause by clause.

**React + TypeScript + Tailwind** frontend · **FastAPI** backend · hybrid retrieval (BM25 + dense vectors) · LLM output validated with Pydantic

**[Live demo](#)** · **[API docs](#)** `/docs` <!-- replace both after deploying -->

<!-- Screenshots: docs/screenshots/overview.png, risks.png, ask.png, compare.png -->

## Features

- **Cited answers.** Each answer carries `[n]` markers. Click one and the PDF pane jumps to that page.
- **Risk review.** Clauses are pre-filtered, then the LLM returns schema-validated risks: severity, affected party, plain-English explanation and a negotiation tip.
- **Key terms and exposure score.** Parties, term, renewal, notice period, liability cap, governing law.
- **Compare.** Two contracts, chosen aspects, a "which is riskier" table and a verdict.
- **Export** the analysis as Markdown.

## Architecture

```
┌─────────────── frontend (React, Vite, Tailwind) ───────────────┐
│ Landing → Workspace: PDF pane │ Overview · Risks · Ask · Compare │
└───────────────────────────────┬─────────────────────────────────┘
                                │ JSON over HTTP  (/api/*)
┌───────────────────────────────▼─────────────────────────────────┐
│ FastAPI   sessions (in-memory, TTL) · rate limit · validation    │
│   └─ engine/                                                      │
│      ingest     PyMuPDF → clause splitter (§ / ARTICLE), page kept │
│      retrieval  BM25 + FAISS cosine → Reciprocal Rank Fusion       │
│      analysis   Q&A · risks · key terms · compare                  │
│      llm        Groq, JSON mode, retries, Pydantic validation      │
└──────────────────────────────────────────────────────────────────┘
```

### Design decisions

- **Clause-aware chunking.** Contracts are structured, so a clause is the natural unit for retrieval and for citation. Long clauses are windowed; unstructured text falls back to plain windows.
- **Hybrid retrieval.** Legal text has exact terms ("indemnify", "90 days") where BM25 wins and paraphrased questions where embeddings win. RRF fuses both without score tuning.
- **Validated structured output.** The model must return JSON matching Pydantic models. Invalid output is retried once, and citations pointing at passages that don't exist are dropped.
- **Prompt-injection guard.** Contract text is treated as data in the system prompt.
- **Public-demo safety.** Per-IP rate limiting protects the LLM quota. Uploads are checked for type, magic bytes and size. Sessions live in memory, expire after an hour, and nothing is written to disk.
- **Light embeddings.** ONNX (fastembed) instead of PyTorch keeps the backend image small and cold starts fast. It falls back to sentence-transformers, then to a hashing embedder, so the app always starts.
- **Parallel LLM calls.** Risks and key terms are computed concurrently and cached per session.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/documents` | Upload a PDF (multipart `file`) |
| POST | `/api/documents/sample/{a\|b}` | Load a bundled sample contract |
| GET | `/api/documents/{id}/pdf` | The original PDF (for the viewer) |
| GET | `/api/documents/{id}/overview` | Key terms, risks, exposure score |
| POST | `/api/documents/{id}/ask` | Cited answer to a question |
| POST | `/api/compare` | Compare two uploaded contracts |
| GET | `/api/documents/{id}/report` | Markdown report download |
| GET | `/health` | Liveness and active embedder |

Interactive docs are served at `/docs`.

## Run locally

You need Python 3.11+, Node 20+ and a free [Groq API key](https://console.groq.com).

```bash
# terminal 1: API
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                   # add GROQ_API_KEY
uvicorn app.main:app --reload                          # http://localhost:8000/docs

# terminal 2: UI
cd frontend
npm install
npm run dev                                            # http://localhost:5173
```

Or with Docker: put your key in `backend/.env`, then `docker compose up --build` and open http://localhost:8080.

## Deploy

**Backend → Render (free tier works)**
1. New → Web Service → connect this repo, runtime **Docker**, root directory `backend`.
2. Environment: `GROQ_API_KEY`, and `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`.
3. The free tier sleeps when idle, so the first request after a break takes ~30 s.

**Frontend → Vercel**
1. Import the repo, root directory `frontend`, framework Vite.
2. Environment: `VITE_API_URL=https://<your-render-service>.onrender.com`.

## Evaluation

```bash
python eval/run_eval.py            # BM25 vs dense vs hybrid: hit@1, hit@3, MRR
```

`eval/golden.json` has 20 paraphrased questions over the two sample contracts, each labelled with the clause that answers it. Run it with the real embedder installed (`pip install fastembed`) and paste the numbers here:

| Method | hit@1 | hit@3 | MRR |
|---|---|---|---|
| BM25 | | | |
| Dense (bge-small) | | | |
| Hybrid (RRF) | | | |

## Tests

```bash
cd backend && pytest -q        # 23 tests: ingest, retrieval, risk scoring, citations, API, rate limiting
cd frontend && npm run build   # type-checks the whole UI
```

CI (`.github/workflows/ci.yml`) runs both on every push.

## Project layout

```
backend/
  app/
    main.py  routes.py  models.py  deps.py  sessions.py  ratelimit.py  config.py
    engine/   ingest · retrieval · llm · analysis · schemas · report
  samples/    two fictional contracts (+ generator)
  tests/      engine + API tests (LLM and embedder faked)
frontend/
  src/
    App.tsx  api.ts  types.ts
    components/   Landing · Workspace · PdfPane · Overview · Risks · Ask · Compare · ui
eval/         golden questions + retrieval benchmark
docker-compose.yml · .github/workflows/ci.yml · Makefile
```

## Limitations

- Text PDFs only. Scanned documents need OCR first (the API says so clearly).
- The exposure score is a heuristic, not a legal assessment.
- Sessions are in memory, so a restart clears them. Fine for a demo; a production version would use Redis and object storage.
- Information only. **Not legal advice.**

## License

MIT

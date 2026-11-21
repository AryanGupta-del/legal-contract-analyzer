"""Retrieval evaluation: hit@k and MRR for BM25-only, dense-only and hybrid search.

    python eval/run_eval.py            # from the repo root; uses the best embedder available
    python eval/run_eval.py --rerank   # adds the cross-encoder reranker

Questions are paraphrased on purpose (few shared words with the clause) so dense retrieval
has to earn its keep. Add your own contracts + questions to golden.json to grow the set.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.engine.analysis import load_document  # noqa: E402
from app.engine.retrieval import load_embedder, load_reranker, HashingEmbedder  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerank", action="store_true")
    args = ap.parse_args()
    emb = load_embedder()
    print(f"embedder: {type(emb).__name__}" + ("  (fallback: install fastembed)"
                                                if isinstance(emb, HashingEmbedder) else ""))
    rr = load_reranker() if args.rerank else None
    gold = json.loads((Path(__file__).parent / "golden.json").read_text())
    docs = {f: load_document(f, (ROOT / "backend" / "samples" / f).read_bytes(), emb, rr)
            for f in {g["file"] for g in gold}}

    rows = []
    for mode in ("bm25", "dense", "hybrid"):
        h1 = h3 = mrr = 0.0
        for g in gold:
            hits = docs[g["file"]].index.search(g["q"], k=5, mode=mode)
            ranks = [i for i, h in enumerate(hits, 1) if h.chunk.heading == g["heading"]]
            r = ranks[0] if ranks else None
            h1 += r == 1; h3 += bool(r and r <= 3); mrr += 1 / r if r else 0
        n = len(gold)
        rows.append((mode + ("+rerank" if rr and mode == "hybrid" else ""), h1 / n, h3 / n, mrr / n))
    print(f"\n{len(gold)} questions\n{'method':<16}{'hit@1':>8}{'hit@3':>8}{'MRR':>8}")
    for m, a, b, c in rows:
        print(f"{m:<16}{a:>8.2f}{b:>8.2f}{c:>8.2f}")


if __name__ == "__main__":
    main()

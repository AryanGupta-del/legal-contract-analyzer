"""Hybrid retrieval: dense (FAISS, cosine) + lexical (BM25) fused with Reciprocal Rank Fusion,
with an optional cross-encoder reranker."""
from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from .schemas import Chunk, Hit

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    def __init__(self, name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(name)

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype="float32")


class FastEmbedEmbedder:
    """ONNX embeddings via fastembed: no PyTorch, small image, quick cold start."""

    def __init__(self, name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=name)

    def encode(self, texts: list[str]) -> np.ndarray:
        v = np.asarray(list(self.model.embed(texts)), dtype="float32")
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


class HashingEmbedder:
    """Dependency-free fallback (hashed bag-of-words). Used if the neural model is unavailable
    and in unit tests; BM25 still carries most of the ranking in that case."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype="float32")
        for i, t in enumerate(texts):
            for tok in tokenize(t):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1.0 if (h >> 20) & 1 else -1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(norms, 1e-9)


def load_embedder() -> Embedder:
    """Best available embedder: fastembed -> sentence-transformers -> hashing fallback."""
    for factory in (FastEmbedEmbedder, SentenceTransformerEmbedder):
        try:
            return factory()
        except Exception:
            continue
    return HashingEmbedder()


def load_reranker():
    """Cross-encoder reranker, or None if unavailable."""
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception:
        return None


class HybridIndex:
    def __init__(self, chunks: list[Chunk], embedder: Embedder, reranker=None):
        import faiss
        from rank_bm25 import BM25Okapi

        if not chunks:
            raise ValueError("Cannot index an empty document.")
        self.chunks = chunks
        self.embedder = embedder
        self.reranker = reranker
        vecs = embedder.encode([c.embed_text for c in chunks]).astype("float32")
        self.faiss = faiss.IndexFlatIP(vecs.shape[1])  # inner product == cosine (normalised)
        self.faiss.add(vecs)
        self.bm25 = BM25Okapi([tokenize(c.embed_text) for c in chunks])

    def search(self, query: str, k: int = 5, pool: int = 20, rrf_k: int = 60,
               mode: str = "hybrid") -> list[Hit]:
        pool = min(pool, len(self.chunks))
        q = self.embedder.encode([query]).astype("float32")
        _, dense_ids = self.faiss.search(q, pool)
        bm = self.bm25.get_scores(tokenize(query))
        sparse_ids = np.argsort(bm)[::-1][:pool]

        rankings = {"hybrid": (dense_ids[0], sparse_ids), "dense": (dense_ids[0],),
                    "bm25": (sparse_ids,)}[mode]
        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                if idx < 0:
                    continue
                fused[int(idx)] = fused.get(int(idx), 0.0) + 1.0 / (rrf_k + rank + 1)
        ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:pool]

        if self.reranker is not None and len(ranked) > 1:
            pairs = [(query, self.chunks[i].embed_text) for i, _ in ranked]
            scores = self.reranker.predict(pairs)
            ranked = sorted(zip([i for i, _ in ranked], map(float, scores)),
                            key=lambda kv: kv[1], reverse=True)
        return [Hit(self.chunks[i], float(s)) for i, s in ranked[:k]]

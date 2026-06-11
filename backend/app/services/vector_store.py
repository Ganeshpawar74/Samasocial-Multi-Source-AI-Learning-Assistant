"""
Embedding generation and per-session FAISS vector index.

Embeddings are computed locally with sentence-transformers (free, no API
calls), so retrieval has zero marginal cost and no rate limits - only the
final LLM call uses the Mistral API.
"""
from __future__ import annotations

import threading

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.schemas import Chunk

_settings = get_settings()

# Loaded once per process; sentence-transformers model is thread-safe for inference.
_model_lock = threading.Lock()
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(_settings.embedding_model_name)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, _settings.embedding_dim), dtype="float32")
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype="float32")


class VectorStore:
    """
    A small wrapper around a FAISS flat index (cosine similarity via
    normalized inner product) plus the chunk metadata needed to map
    index positions back to source text and citations.
    """

    def __init__(self, dim: int = _settings.embedding_dim):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: list[Chunk] = []
        self._lock = threading.Lock()

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        vectors = embed_texts([c.text for c in chunks])
        with self._lock:
            self.index.add(vectors)
            self.chunks.extend(chunks)

    def remove_source(self, source_id: str) -> None:
        """
        FAISS flat indexes don't support efficient deletion, so we rebuild
        the index excluding the given source. Fine at this scale (single
        session, modest document counts).
        """
        with self._lock:
            remaining = [c for c in self.chunks if c.source_id != source_id]
            self.chunks = remaining
            self.index = faiss.IndexFlatIP(self.dim)
            if remaining:
                vectors = embed_texts([c.text for c in remaining])
                self.index.add(vectors)

    def search(self, query: str, top_k: int, source_id: str | None = None) -> list[tuple[Chunk, float]]:
        if self.index.ntotal == 0:
            return []
        query_vec = embed_texts([query])
        with self._lock:
            # Over-fetch when filtering by source so we still return top_k results
            fetch_k = min(self.index.ntotal, top_k * 4 if source_id else top_k)
            scores, indices = self.index.search(query_vec, fetch_k)

        results: list[tuple[Chunk, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue
            chunk = self.chunks[idx]
            if source_id and chunk.source_id != source_id:
                continue
            results.append((chunk, float(score)))
            if len(results) >= top_k:
                break
        return results

    def __len__(self) -> int:
        return len(self.chunks)

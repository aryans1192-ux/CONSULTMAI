"""
knowledge/embedder.py
Wraps the embedding model. Uses sentence-transformers locally (free, no API key).
Falls back to a simple hash-based stub if the library isn't installed yet.
"""

from __future__ import annotations

_model = None


def get_embedder():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        _model = _StubEmbedder()
    return _model


def embed(text: str) -> list[float]:
    model = get_embedder()
    if isinstance(model, _StubEmbedder):
        return model.encode(text)
    vec = model.encode(text, convert_to_numpy=True)
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    if isinstance(model, _StubEmbedder):
        return [model.encode(t) for t in texts]
    vecs = model.encode(texts, convert_to_numpy=True)
    return [v.tolist() for v in vecs]


class _StubEmbedder:
    """
    Deterministic 384-dim stub used when sentence-transformers is not installed.
    Enables the rest of the system to run without the ML dependency.
    Install properly: pip install sentence-transformers
    """
    DIM = 384

    def encode(self, text: str) -> list[float]:
        import hashlib, math
        h = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        vec = []
        for i in range(self.DIM):
            val = math.sin(h * (i + 1) * 1e-6)
            vec.append(val)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

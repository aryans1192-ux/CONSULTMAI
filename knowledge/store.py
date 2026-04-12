"""
knowledge/store.py
ChromaDB vector store wrapper.
Handles: add documents, query by embedding, persist to disk.
"""

from __future__ import annotations
import os
from pathlib import Path

CHROMA_DIR = str(Path(__file__).parent / "chroma_db")


def _get_collection():
    try:
        import chromadb
    except ImportError:
        raise ImportError("chromadb not installed — run: pip install chromadb sentence-transformers")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name="consultmai_knowledge",
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    col = _get_collection()
    col.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def retrieve(
    query_embedding: list[float],
    top_k: int = 5,
    where: dict | None = None,
) -> list[dict]:
    """
    Returns top_k most relevant chunks as list of:
    { "id", "text", "metadata", "distance" }
    """
    col = _get_collection()
    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=min(top_k, col.count() or 1),
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where

    results = col.query(**kwargs)

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id":       results["ids"][0][i],
            "text":     results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return output


def count() -> int:
    return _get_collection().count()


def is_empty() -> bool:
    return count() == 0

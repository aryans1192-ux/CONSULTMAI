"""
ingestion/ingest.py
One-time (and re-runnable) script: reads all .md docs from knowledge/docs/,
chunks them, embeds them, and upserts into ChromaDB.

Run: python -m ingestion.ingest
"""

from __future__ import annotations
import os
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "knowledge" / "docs"


def ingest_all(force: bool = False) -> int:
    from knowledge.store import add_documents, is_empty, count
    from knowledge.embedder import embed_batch
    from ingestion.chunker import chunk_markdown

    if not force and not is_empty():
        print(f"[ingest] Store already has {count()} chunks. Use force=True to re-ingest.")
        return 0

    md_files = list(DOCS_DIR.rglob("*.md"))
    if not md_files:
        print("[ingest] No .md files found in knowledge/docs/")
        return 0

    all_chunks: list[dict] = []
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(DOCS_DIR))
        chunks = chunk_markdown(text, source=relative)
        all_chunks.extend(chunks)

    ids        = [f"{c['source']}::chunk_{c['chunk_index']}" for c in all_chunks]
    texts      = [c["text"] for c in all_chunks]
    metadatas  = [{"source": c["source"], "chunk_index": c["chunk_index"]} for c in all_chunks]

    print(f"[ingest] Embedding {len(texts)} chunks from {len(md_files)} files...")
    embeddings = embed_batch(texts)

    add_documents(ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)
    print(f"[ingest] Done. {len(texts)} chunks indexed.")
    return len(texts)


if __name__ == "__main__":
    ingest_all(force=True)

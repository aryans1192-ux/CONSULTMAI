"""
ingestion/chunker.py
Splits a markdown or plain-text document into overlapping chunks
suitable for embedding and retrieval.
"""

from __future__ import annotations
import re


def chunk_markdown(
    text: str,
    source: str,
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[dict]:
    """
    Splits text into chunks. Returns list of:
    { "text": str, "source": str, "chunk_index": int }

    Strategy:
    1. Try to split on markdown headings (##, ###) first — keeps semantic sections together.
    2. If a section is too long, fall back to sliding-window word chunks.
    """
    sections = _split_on_headings(text)
    chunks = []
    for section in sections:
        words = section.split()
        if len(words) <= chunk_size:
            chunks.append(section.strip())
        else:
            chunks.extend(_sliding_window(words, chunk_size, overlap))

    return [
        {"text": c, "source": source, "chunk_index": i}
        for i, c in enumerate(chunks)
        if c.strip()
    ]


def _split_on_headings(text: str) -> list[str]:
    parts = re.split(r"(?=^#{1,3} )", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _sliding_window(words: list[str], size: int, overlap: int) -> list[str]:
    chunks = []
    step = max(1, size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + size])
        chunks.append(chunk)
        if i + size >= len(words):
            break
    return chunks
